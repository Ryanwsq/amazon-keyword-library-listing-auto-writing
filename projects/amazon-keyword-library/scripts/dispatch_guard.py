#!/usr/bin/env python3
"""Local dispatch admission, idempotency and event reduction; no business judgment.

This helper never sends a task, queries a provider, or marks runtime stages ready.
The calling main/owning task still executes the existing Skill and business gates.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
from contextlib import contextmanager
from pathlib import Path

import runtime_contract as runtime

VERSION = "dispatch-guard/1.0.0"
ROLES = {
    "sif": "keyword-sif-collector",
    "amazon-autocomplete": "keyword-autocomplete-collector",
    "sellersprite": "keyword-sellersprite-collector",
    "cleaning": "keyword-cleaner",
    "word-frequency": "keyword-word-frequency-analyst",
    "classification": "keyword-classifier",
    "competition": "keyword-competition-analyst",
    "trend": "keyword-trend-analyst",
    "assembly": "keyword-final-workbook-assembler",
    "quality-validation": "keyword-quality-reviewer",
}
TITLES = dict(zip(ROLES, [f"Amazon关键词词库｜{name}｜main" for name in (
    "SIF竞品反查", "Amazon联想采集", "卖家精灵扩词", "关键词清洗", "词频统计",
    "关键词分类", "竞争性分析", "趋势性分析", "最终工作簿装配", "独立质量验证",
)]))
TERMINAL = {"completed", "completed_with_gaps", "blocked", "incomplete", "cancelled", "not_executed"}
EVENT_STATES = TERMINAL | {"accepted", "running", "awaiting_login"}
REUSE_RULES = {
    ".agents/skills/amazon-keyword-library-operations/SKILL.md",
    ".agents/skills/amazon-keyword-library-operations/references/recent-library-reuse-contract.md",
    "knowledge/product-keyword-library.md", "docs/keyword-judgment-boundaries.md",
    ".agents/skills/amazon-keyword-final-workbook-assembly/SKILL.md",
    ".agents/skills/amazon-keyword-final-workbook-assembly/references/workbook-contract.md",
    "docs/dispatch-control-contract.md", "scripts/dispatch_guard.py",
}


def require(ok, message):
    if not ok:
        raise runtime.ContractError(message)


def digest(value):
    return runtime.sha256_bytes(runtime.canonical_bytes(value))


def head(cwd):
    return subprocess.check_output(
        ["git", "-C", str(cwd), "rev-parse", "HEAD"], text=True
    ).strip()


def file_record(path):
    path = Path(path).resolve(strict=True)
    require(path.is_file(), "expected a regular file")
    return {"path": str(path), "sha256": runtime.sha256_file(path)}


def verify_file(record):
    runtime.require_sha256(record.get("sha256"), "file sha256")
    require(file_record(record["path"]) == record, "file path/hash drift")


def inside(path, root):
    path, root = Path(path).resolve(), Path(root).resolve()
    require(path != root and path.is_relative_to(root), "path outside locked output root")
    return path


def validate_identity(envelope, current_run, observed):
    require(envelope["run_id"] == current_run, "wrong current Run")
    require(ROLES.get(envelope["stage"]) == envelope["role"], "wrong stage/role")
    expected = envelope["target"]
    require(expected.get("title") == TITLES[envelope["stage"]], "wrong fixed task title")
    require(set(expected) == {"thread_id", "host", "title", "cwd"}, "invalid target fields")
    for field, value in expected.items():
        require(isinstance(value, str) and bool(value), "empty target identity")
        require(observed.get(field) == value, f"wrong target {field}")
    cwd = Path(expected["cwd"])
    require(str(cwd.resolve()) == str(cwd), "target cwd must be canonical")
    require(head(cwd) == envelope["revision"], "target revision drift")
    run_root = cwd / ".local" / "runs" / current_run
    output = Path(envelope["output_root"])
    inside(output, run_root)
    require(output.resolve() == output, "output root symlink/alias")


def verify_admission(envelope):
    """Recheck exact locks; qualification/semantic judgments remain with owners."""
    verify_file(envelope["contract"])
    contract = runtime.read_json(Path(envelope["contract"]["path"]))
    for field in ("run_id", "run_type", "revision", "input_hashes"):
        require(contract.get(field) == envelope.get(field), f"contract {field} mismatch")
    require(set(envelope["input_hashes"]) == runtime.REQUIRED_INPUT_HASHES, "three input locks required")
    for value in envelope["input_hashes"].values():
        runtime.require_sha256(value, "input hash")
    for record in envelope["dependency_files"]:
        verify_file(record)
    mode, stage = envelope["execution_mode"], envelope["stage"]
    if mode == "fresh-collection":
        require(contract.get("schema") == runtime.CONTRACT_SCHEMA, "wrong fresh contract schema")
        runtime.verify_contract(contract)
        for rule in contract["rules"]:
            require(runtime.sha256_file(Path(envelope["target"]["cwd"]) / rule["owner"])
                    == rule["owner_sha256"], "receiver rule file drift")
        require(stage in contract["stages"], "stage not active for run_type")
        require(envelope["stage_key"] == contract["stages"][stage]["stage_key"], "stage key drift")
        admission = envelope["admission"]
        ready = runtime.ready_for_stage(
            contract, stage, Path(admission["status_dir"]),
            Path(admission["preflight"]) if admission.get("preflight") else None,
        )
        require(ready["ready"], "business dependencies/login not ready")
        # Freeze the actual dependency files, not just the declarations in them.
        required = [Path(admission["status_dir"]) / f"{s}.json"
                    for s in contract["stages"][stage]["dependencies"]]
        if stage in runtime.SOURCE_PREFLIGHT:
            required.append(Path(admission["preflight"]))
        locked = {x["path"] for x in envelope["dependency_files"]}
        require(all(str(p.resolve()) in locked for p in required), "unlocked dependency/preflight file")
    else:
        require(mode == "recent-library-reuse", "unknown execution mode")
        require(contract.get("schema") == "amazon-keyword-recent-library-reuse/v1", "wrong reuse schema")
        require(contract.get("execution_mode") == mode, "wrong reuse execution mode")
        require(contract.get("run_type") in {"production", "test-validation"}, "invalid reuse run type")
        if contract["run_type"] == "test-validation":
            require(contract.get("qa_mode") in {"compact-validation", "full-regression"}, "reuse QA mode missing")
            require(not contract.get("change_flags") or contract["qa_mode"] == "full-regression", "reuse changes require full regression")
        rules = contract.get("rule_owner_hashes")
        require(isinstance(rules, dict) and bool(rules), "reuse rule hashes required")
        required_rules = set(REUSE_RULES)
        if contract["run_type"] == "test-validation":
            required_rules.update({".agents/skills/amazon-keyword-quality-validation/SKILL.md",
                                   ".agents/skills/amazon-keyword-quality-validation/references/quality-contract.md"})
        require(required_rules <= set(rules), "reuse owning rule hash set incomplete")
        for owner, expected_hash in rules.items():
            require(not Path(owner).is_absolute() and ".." not in Path(owner).parts, "invalid rule owner")
            runtime.require_sha256(expected_hash, "rule owner hash")
            require(runtime.sha256_file(Path(envelope["target"]["cwd"]) / owner) == expected_hash,
                    "receiver reuse rule file drift")
        require(stage == "assembly" or (stage == "quality-validation" and contract["run_type"] == "test-validation"),
                "reuse cannot dispatch upstream/production QA")
        require(envelope["stage_key"] == digest({"contract": envelope["contract"]["sha256"],
                                                "stage": stage, "executor": VERSION}), "reuse stage key drift")
        receipt = envelope["admission"]["receipt"]
        verify_file(receipt)
        review = runtime.read_json(Path(receipt["path"]))
        require(review.get("run_id") == contract["run_id"] and review.get("stage") == stage
                and review.get("contract_file_sha256") == envelope["contract"]["sha256"]
                and review.get("ready") is True, "reuse admission not bound/ready")
        require(bool(envelope["dependency_files"]), "reuse evidence locks required")
        require(review.get("evidence_files") == envelope["dependency_files"], "reuse evidence lock mismatch")


def validate(envelope, current_run, observed):
    require(envelope.get("schema") == VERSION, "unknown dispatch schema")
    require(envelope.get("dispatch_id") == digest({k: v for k, v in envelope.items() if k != "dispatch_id"}),
            "dispatch digest mismatch")
    require(runtime.RUN_ID_RE.fullmatch(current_run) is not None, "invalid current Run")
    validate_identity(envelope, current_run, observed)
    verify_admission(envelope)


def build(request, current_run):
    """Derive identifiers from the locked contract; never type stage hashes by hand."""
    record = file_record(request["contract_path"])
    contract = runtime.read_json(Path(record["path"]))
    require(contract.get("run_id") == current_run, "wrong build Run")
    stage = request["stage"]
    require(stage in ROLES, "unknown dispatch stage")
    mode = "fresh-collection" if contract.get("schema") == runtime.CONTRACT_SCHEMA else "recent-library-reuse"
    admission = request["admission"]
    if mode == "fresh-collection":
        require(stage in contract["stages"], "stage not active")
        key = contract["stages"][stage]["stage_key"]
        files = [file_record(Path(admission["status_dir"]) / f"{s}.json")
                 for s in contract["stages"][stage]["dependencies"]]
        if stage in runtime.SOURCE_PREFLIGHT:
            files.append(file_record(admission["preflight"]))
    else:
        key = digest({"contract": record["sha256"], "stage": stage, "executor": VERSION})
        verify_file(admission["receipt"])
        files = runtime.read_json(Path(admission["receipt"]["path"]))["evidence_files"]
    result = {k: contract[k] for k in ("run_id", "run_type", "revision", "input_hashes")}
    result.update(execution_mode=mode, role=ROLES[stage], stage=stage, stage_key=key,
                  contract=record, admission=admission, dependency_files=files,
                  target=request["target"], output_root=request["output_root"])
    verify_admission(result)
    return result


@contextmanager
def journal(path):
    path = Path(path).resolve()
    require(path.parent.name == "dispatch-control" and path.parent.parent.name == ".local",
            "journal must be local dispatch-control metadata")
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10, isolation_level=None)
    try:
        db.execute("BEGIN IMMEDIATE")
        db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, job_key TEXT UNIQUE, "
                   "target TEXT, state TEXT, envelope TEXT, seq INTEGER DEFAULT 0, event TEXT, cursor TEXT)")
        yield db
        db.execute("COMMIT")
    except BaseException:
        if db.in_transaction:
            db.execute("ROLLBACK")
        raise
    finally:
        db.close()


def reserve(spec, current_run, observed, ledger):
    require("dispatch_id" not in spec, "reserve takes spec, not a previous envelope")
    envelope = dict(spec)
    envelope["schema"] = VERSION
    envelope["dispatch_id"] = digest(envelope)
    validate(envelope, current_run, observed)
    job_key = digest([current_run, envelope["role"], envelope["stage_key"]])
    target = digest([envelope["target"]["host"], envelope["target"]["thread_id"]])
    with journal(ledger) as db:
        old = db.execute("SELECT id,state FROM jobs WHERE job_key=?", (job_key,)).fetchone()
        if old:
            require(old[0] == envelope["dispatch_id"], "same job key with different envelope")
            return {"allowed_to_send": False, "dispatch_id": old[0], "state": old[1]}
        busy = db.execute("SELECT id FROM jobs WHERE target=? AND state NOT IN ('completed','completed_with_gaps','cancelled','not_executed')", (target,)).fetchone()
        require(not busy and observed.get("status") == "idle", "target busy/unresolved; do not dispatch")
        db.execute("INSERT INTO jobs(id,job_key,target,state,envelope) VALUES(?,?,?,?,?)",
                   (envelope["dispatch_id"], job_key, target, "reserved", json.dumps(envelope, ensure_ascii=False)))
    return {"allowed_to_send": True, "dispatch_id": envelope["dispatch_id"], "envelope": envelope}


def load_job(db, dispatch_id):
    row = db.execute("SELECT state,envelope,seq,event,cursor FROM jobs WHERE id=?", (dispatch_id,)).fetchone()
    require(row is not None, "unknown dispatch; cannot reconcile a different Run")
    return row[0], json.loads(row[1]), row[2], json.loads(row[3]) if row[3] else None, row[4]


def sent(ledger, dispatch_id, receipt):
    with journal(ledger) as db:
        state, envelope, _, _, _ = load_job(db, dispatch_id)
        require(receipt.get("dispatch_id") == dispatch_id
                and receipt.get("thread_id") == envelope["target"]["thread_id"], "wrong send receipt")
        response = receipt.get("response", {})
        require(bool(receipt.get("tool_call_id")) or response.get("threadId") == envelope["target"]["thread_id"],
                "send receipt must retain actual tool response or exact call ID")
        if state in {"reserved", "retry_authorized"}:
            db.execute("UPDATE jobs SET state='sent' WHERE id=?", (dispatch_id,))
        else:
            require(state != "delivery_unknown", "uncertain delivery requires reconciliation")
    return {"dispatch_id": dispatch_id, "state": "sent" if state in {"reserved", "retry_authorized"} else state}


def accept(envelope, current_run, observed, ledger):
    validate(envelope, current_run, observed)
    require(str(Path.cwd().resolve()) == envelope["target"]["cwd"], "receiver process cwd mismatch")
    target = digest([observed["host"], observed["thread_id"]])
    with journal(ledger) as db:
        old = db.execute("SELECT state,envelope FROM jobs WHERE id=?", (envelope["dispatch_id"],)).fetchone()
        if old:
            require(json.loads(old[1]) == envelope, "receiver envelope conflict")
            return {"execute": False, "reason": "already_accepted", "state": old[0]}
        busy = db.execute("SELECT id FROM jobs WHERE target=? AND state NOT IN ('completed','completed_with_gaps','cancelled','not_executed')", (target,)).fetchone()
        require(not busy, "receiver has another active/unresolved Run")
        db.execute("INSERT INTO jobs(id,job_key,target,state,envelope) VALUES(?,?,?,?,?)",
                   (envelope["dispatch_id"], digest([current_run, envelope["role"], envelope["stage_key"]]),
                    target, "accepted", json.dumps(envelope, ensure_ascii=False)))
    return {"execute": True, "dispatch_id": envelope["dispatch_id"], "output_root": envelope["output_root"]}


def observe(ledger, current_run, event):
    """Owner and main each record the same small event in their own journal."""
    with journal(ledger) as db:
        state, envelope, sequence, previous, cursor = load_job(db, event["dispatch_id"])
        require(envelope["run_id"] == current_run, "wrong current Run event")
        for field in ("run_id", "role", "stage_key", "revision", "input_hashes", "output_root"):
            require(event.get(field) == envelope[field], f"wrong event {field}")
        require(event.get("thread_id") == envelope["target"]["thread_id"], "wrong event task")
        require(event.get("status") in EVENT_STATES, "invalid event status")
        seq = event.get("seq")
        require(isinstance(seq, int) and not isinstance(seq, bool) and seq > 0, "invalid event sequence")
        # Cursor/sequence-only changes are transport state, not a reason to re-read a report.
        meaningful = {k: v for k, v in event.items() if k not in {"seq", "cursor"}}
        if seq < sequence:
            return {"changed": False, "reason": "stale_event", "cursor": cursor}
        if seq == sequence:
            require(previous == meaningful, "conflicting duplicate event")
            return {"changed": False, "reason": "duplicate_event", "cursor": cursor}
        if state in TERMINAL:
            require(event["status"] == state and previous == meaningful, "terminal state cannot be overwritten")
        if event["status"] in {"completed", "completed_with_gaps"}:
            require(isinstance(event.get("population"), dict) and bool(event["population"]), "population missing")
            require(bool(event.get("artifacts")), "completion artifacts missing")
            for artifact in event["artifacts"]:
                inside(artifact["path"], envelope["output_root"])
                verify_file(artifact)
            require(isinstance(event.get("gaps"), list), "explicit gaps list required")
            require(event.get("verification") == "owner_checks_completed", "owner verification not complete")
        changed = previous != meaningful
        db.execute("UPDATE jobs SET state=?,seq=?,event=?,cursor=? WHERE id=?",
                   (event["status"], seq, json.dumps(meaningful, ensure_ascii=False), event.get("cursor"), event["dispatch_id"]))
    return {"changed": changed, "dispatch_id": event["dispatch_id"], "state": event["status"],
            "cursor": event.get("cursor"), "business_acceptance": "still_required"}


def reconcile(ledger, current_run, dispatch_id, evidence):
    """Never automatically retry an ambiguous send or unlock a still-running task."""
    with journal(ledger) as db:
        state, envelope, _, _, _ = load_job(db, dispatch_id)
        require(envelope["run_id"] == current_run, "wrong reconciliation Run")
        verify_file(evidence)
        proof = runtime.read_json(Path(evidence["path"]))
        require(proof.get("dispatch_id") == dispatch_id and proof.get("thread_id") == envelope["target"]["thread_id"], "wrong reconciliation identity")
        require(bool(proof.get("tool_call_id") or proof.get("observed_turn_id"))
                and proof.get("observed_task_status") == "idle", "live receipt/idle proof required")
        outcome = proof.get("outcome")
        if outcome == "definitely_not_sent":
            require(state == "reserved" and proof.get("business_executed") is False, "cannot retry delivered/executed dispatch")
            # Return the same identity; receiver idempotency remains in force.
            result = {"allowed_to_send": True, "dispatch_id": dispatch_id}
            db.execute("UPDATE jobs SET state='retry_authorized' WHERE id=?", (dispatch_id,))
        elif outcome == "delivered":
            require(state in {"reserved", "retry_authorized", "sent"}, "invalid delivered reconciliation")
            db.execute("UPDATE jobs SET state='sent' WHERE id=?", (dispatch_id,))
            result = {"allowed_to_send": False, "state": "sent"}
        elif outcome == "closed":
            require(state in {"blocked", "incomplete", "reserved", "sent", "accepted", "running", "awaiting_login", "retry_authorized"}
                    and proof.get("execution_stopped") is True, "task termination must be confirmed")
            db.execute("UPDATE jobs SET state='cancelled' WHERE id=?", (dispatch_id,))
            result = {"allowed_to_send": False, "state": "cancelled"}
        elif outcome == "resume_existing":
            require(state in {"accepted", "running", "awaiting_login", "blocked", "incomplete"}
                    and proof.get("execution_stopped") is True and proof.get("authorize_resume") is True,
                    "resume needs stopped, unfinished execution and explicit continuation")
            # Preserve identity, event sequence and all already-produced evidence.
            verify_admission(envelope)
            db.execute("UPDATE jobs SET state='accepted' WHERE id=?", (dispatch_id,))
            result = {"allowed_to_send": False, "resume_existing": True, "dispatch_id": dispatch_id}
        else:
            raise runtime.ContractError("ambiguous delivery; no automatic resend")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "reserve", "sent", "accept", "observe", "reconcile"])
    parser.add_argument("--ledger")
    parser.add_argument("--run", required=True)
    parser.add_argument("--input", required=True, help="local spec/envelope/event/receipt JSON")
    parser.add_argument("--observed", help="fresh app identity snapshot, not copied from spec")
    parser.add_argument("--out", help="write spec/envelope under the current Run and print only a compact receipt")
    args = parser.parse_args()
    try:
        payload = runtime.read_json(Path(args.input))
        require(args.command == "build" or args.ledger, "ledger required")
        if args.command != "build":
            require(Path(args.ledger).resolve() == Path.cwd().resolve() / ".local" / "dispatch-control" / "journal.sqlite3",
                    "use the fixed current-worktree journal, not a per-attempt ledger")
        if args.command == "build":
            result = build(payload, args.run)
        elif args.command in {"reserve", "accept"}:
            require(args.observed is not None, "observed task identity required")
            observed = runtime.read_json(Path(args.observed))
            action = reserve if args.command == "reserve" else accept
            result = action(payload, args.run, observed, args.ledger)
        elif args.command == "sent":
            with journal(args.ledger) as db:
                _, envelope, _, _, _ = load_job(db, payload["dispatch_id"])
                require(envelope["run_id"] == args.run, "wrong send Run")
            result = sent(args.ledger, payload["dispatch_id"], payload)
        elif args.command == "observe":
            result = observe(args.ledger, args.run, payload)
        else:
            result = reconcile(args.ledger, args.run, payload["dispatch_id"], payload["evidence"])
        if args.out:
            require(args.command in {"build", "reserve"}, "out only applies to spec/envelope")
            output = inside(args.out, Path.cwd() / ".local" / "runs" / args.run)
            value = result if args.command == "build" else result.get("envelope")
            if value is not None:
                if output.exists():
                    require(runtime.read_json(output) == value, "refuse to overwrite a different dispatch")
                else:
                    runtime.write_json(output, value)
            result = {k: v for k, v in result.items() if k != "envelope"} if args.command == "reserve" else {"status": "built"}
            result["file"] = str(output)
        print(json.dumps(result, ensure_ascii=False))
    except (runtime.ContractError, OSError, KeyError, TypeError, ValueError, sqlite3.Error, subprocess.CalledProcessError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
