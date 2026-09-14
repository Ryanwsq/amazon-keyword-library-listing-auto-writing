"""Read-only admission helpers; not a sandbox or a Codex tool interceptor."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess

VERSION = "20260914"


def verify_front_review(payload, source_locks):
    """Check review binding/completeness, not the truth of semantic self-review."""
    review = payload.get("front_copy_review", {})
    for field, limit in (("title", 75), ("item_highlights", 125)):
        text = payload[field]
        record = review.get(field, {})
        if (record.get("text_sha256") != hashlib.sha256(text.encode()).hexdigest()
                or record.get("characters") != len(text) or record.get("remaining_budget") != limit - len(text)):
            raise ValueError("Front copy review text/count binding mismatch")
        for key in ("ordering_rationale", "prefix_review", "remaining_candidates_and_tradeoffs", "buyer_understanding"):
            if not isinstance(record.get(key), str) or not record[key].strip():
                raise ValueError("Front copy review missing " + key)
        refs = record.get("source_refs", [])
        if not refs or any(not ref.get("locator") or source_locks.get(str(Path(ref["path"]).resolve()))
                           != ref.get("sha256") for ref in refs):
            raise ValueError("Front copy review needs current source/fact locators")
    if not isinstance(review.get("bullet_count_rationale"), str) or not review["bullet_count_rationale"].strip():
        raise ValueError("Explain five-bullet coverage or the distinct need for extra bullets")


def enabled(manifest):
    return manifest.get("runtime_repairs_version") == VERSION


def file_lock(record):
    path = Path(record["path"])
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
        raise ValueError("Runtime recovery evidence path/hash drift")
    return json.loads(path.read_text(encoding="utf-8"))


def active_owner(board, role):
    """Titles are display-only. Retired entries never become fallback targets."""
    entries = board.get("role_bindings", {}).get(role, [])
    active = [item for item in entries if item.get("state") == "active"]
    if len(active) != 1:
        raise ValueError("Exactly one active owner required for role: " + role)
    owner = active[0]
    if not all(isinstance(owner.get(k), str) and owner[k].strip()
               for k in ("task_id", "host", "business_cwd", "package_manifest_sha256")):
        raise ValueError("Incomplete current owner binding")
    if not Path(owner["business_cwd"]).is_dir():
        raise ValueError("Current business cwd missing; explicit rebind required")
    if not owner.get("package_manifest"):
        raise ValueError("Explicit role package manifest required")
    package = Path(owner["package_manifest"])
    if (not package.is_file() or hashlib.sha256(package.read_bytes()).hexdigest()
            != owner["package_manifest_sha256"]):
        raise ValueError("Owner role package changed or missing")
    payload = json.loads(package.read_text(encoding="utf-8"))
    if payload.get("role") != role:
        raise ValueError("Wrong role package")
    return owner


def current_activity(manifest, board, node, proof, owner, now=None):
    """Fresh app observation is distinct from the old successful send receipt."""
    if any(proof.get(k) != owner[k] for k in ("task_id", "host")):
        return "reconcile_dispatch", "dispatch points to a retired or different owner"
    lock = board.get("observations", {}).get(node)
    if not lock:
        return "inspect_activity", "actual current task observation required"
    observation = file_lock(lock)
    expected = {"run_id": manifest["run_id"], "task_id": owner["task_id"],
                "host": owner["host"], "dispatch_id": proof["dispatch_id"]}
    if any(observation.get(k) != v for k, v in expected.items()):
        return "reconcile_dispatch", "observation identity mismatch"
    try:
        observed = datetime.fromisoformat(observation["observed_at"].replace("Z", "+00:00"))
        if observed.tzinfo is None:
            raise ValueError("timezone required")
        age = ((now or datetime.now(timezone.utc)) - observed).total_seconds()
    except (KeyError, TypeError, ValueError):
        return "inspect_activity", "invalid actual observation timestamp"
    # Operational polling freshness only; not a source freshness/business threshold.
    if age < -5 or age > 120:
        return "inspect_activity", "refresh actual task metadata; do not restamp old evidence"
    status = observation.get("status")
    if status == "running":
        return "in_flight", "fresh running observation; not proof of business completion"
    if status in {"idle", "completed"}:
        return "resolve_or_resume", "inspect return/checkpoint before resuming the same assignment"
    if status == "needs_input":
        return "resolve_or_resume", observation.get("reason") or "owner needs input"
    return "inspect_activity", "unknown task state is not active execution"


def quality_contract_bound(rules, current_contract, receipt):
    """Allow same-candidate role copies by source identity and bytes, never basename."""
    current_contract = Path(current_contract).resolve()
    if any(Path(item["path"]).resolve() == current_contract for item in rules):
        return True
    binding = receipt.get("quality_contract_binding", {})
    # Caller locks the accepted owner manifest hash; do not trust a self-named copy.
    owner = file_lock(binding["owner_manifest"])
    main = file_lock(binding["main_manifest"])
    if (owner.get("role") != "listing-writing-qa" or main.get("role") != "main"
            or owner.get("version") != main.get("version")):
        return False
    source = ".agents/skills/orchestrate-amazon-listing-pipeline/references/quality-gates.md"
    main_root = Path(binding["main_manifest"]["path"]).resolve().parent
    owner_root = Path(binding["owner_manifest"]["path"]).resolve().parent
    current_hash = hashlib.sha256(current_contract.read_bytes()).hexdigest()
    def matches(manifest, root, path):
        return any(item.get("source") == source and (root / item["path"]).resolve() == path
                   and item.get("sha256") == current_hash for item in manifest.get("files", []))
    return matches(main, main_root, current_contract) and any(
        item["sha256"] == current_hash and matches(owner, owner_root, Path(item["path"]).resolve())
        for item in rules)


def verify_assignment(assignment, *, run_id, role, task_id, host, reads=(), writes=()):
    """Check one explicit assignment before START/resume/access. Does not execute it."""
    expected = {"run_id": run_id, "role": role, "task_id": task_id, "host": host}
    if assignment.get("schema") != "listing-runtime-assignment/v1" or any(
            assignment.get(k) != value for k, value in expected.items()):
        raise ValueError("Current assignment identity mismatch; no historical fallback")
    if assignment.get("mode") not in {"PREP", "START"} or not assignment.get("dispatch_id"):
        raise ValueError("Explicit PREP/START and dispatch identity required")
    manifest = file_lock(assignment["run_manifest"])
    if (manifest["run_id"] != run_id or manifest["input"].get("product_asin") != assignment.get("asin")
            or manifest.get("marketplace") != assignment.get("marketplace")):
        raise ValueError("Run/product/marketplace mismatch")
    input_path = Path(manifest["input"]["locked_path"])
    if hashlib.sha256(input_path.read_bytes()).hexdigest() != manifest["input"]["sha256"]:
        raise ValueError("Current product input changed")
    for item in manifest["input"].get("user_fact_supplements", []):
        if hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("Current fact supplement changed")
    # App cwd, business checkout and read-only rule checkout have distinct identities.
    for key in ("business", "rule_source"):
        binding = assignment[key]
        root = Path(binding["cwd"]).resolve()
        if not root.is_dir():
            raise ValueError(key + " cwd missing; do not recreate/rebind implicitly")
        def git(*args):
            return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()
        if Path(git("rev-parse", "--show-toplevel")).resolve() != Path(binding["git_root"]).resolve():
            raise ValueError(key + " Git root mismatch")
        if git("rev-parse", "HEAD") != binding["revision"]:
            raise ValueError(key + " Git revision changed; no automatic checkout")
    package_lock = assignment["package_manifest"]
    package = file_lock(package_lock)
    package_root = Path(package_lock["path"]).resolve().parent
    if package.get("role") != role or package.get("version") != assignment["package_version"]:
        raise ValueError("Wrong package role/version")
    for item in package["files"]:
        path = (package_root / item["path"]).resolve()
        if not path.is_relative_to(package_root) or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("Role package content changed")
    allowed = {}
    for lock in assignment["read_locks"]:
        path = Path(lock["path"]).resolve()
        if str(path) in allowed or hashlib.sha256(path.read_bytes()).hexdigest() != lock["sha256"]:
            raise ValueError("Read lock duplicate or changed")
        allowed[str(path)] = lock["sha256"]
    required_facts = [(input_path, manifest["input"]["sha256"])] + [
        (Path(item["path"]), item["sha256"]) for item in manifest["input"].get("user_fact_supplements", [])]
    if any(allowed.get(str(path.resolve())) != sha for path, sha in required_facts):
        raise ValueError("Assignment omits current input/fact supplements")
    if any(str(Path(path).resolve()) not in allowed for path in reads):
        raise ValueError("Read outside explicit current assignment")
    permitted_writes = {str(Path(path).resolve()) for path in assignment["write_files"]}
    if any(str(Path(path).resolve()) not in permitted_writes for path in writes):
        raise ValueError("Write outside explicit current assignment")
    if assignment["mode"] == "PREP" and writes:
        raise ValueError("PREP cannot write business artifacts")
    if any(Path(path).exists() for path in writes):
        raise ValueError("Preserve existing artifact; authorize a new versioned output path")
    return {"status": "ADMISSION_CHECKED", "mode": assignment["mode"], **expected,
            "business_cwd": assignment["business"]["cwd"], "business_ready": False}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("assignment", "run-id", "role", "task-id", "host"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--read", action="append", default=[])
    parser.add_argument("--write", action="append", default=[])
    args = parser.parse_args()
    try:
        print(json.dumps(verify_assignment(json.loads(Path(args.assignment).read_text()),
            run_id=args.run_id, role=args.role, task_id=args.task_id, host=args.host,
            reads=args.read, writes=args.write), ensure_ascii=False))
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(2)
