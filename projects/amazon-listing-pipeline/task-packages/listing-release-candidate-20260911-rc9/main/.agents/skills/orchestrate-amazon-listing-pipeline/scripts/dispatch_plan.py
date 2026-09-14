#!/usr/bin/env python3
"""Read-only whole-frontier audit. Never sends tasks or grants business READY."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pipeline_state as state


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def read_record(record):
    path = Path(record["path"])
    if not path.is_file() or state.sha256_file(path) != record["sha256"]:
        raise ValueError("Evidence path/hash drift")
    return json.loads(path.read_text(encoding="utf-8"))


def keyword_ready(manifest, record):
    """Verify the existing main-issued READY; this function cannot issue it."""
    ready = read_record(record)
    required = {"protocol_id", "listing_run_id", "keyword_run_id", "listing_revision",
                "keyword_revision", "input_locks", "workbook_sha256", "process_manifest_sha256", "issued_by"}
    if not required <= ready.keys() or not all(ready[k] for k in required):
        raise ValueError("Incomplete keyword READY")
    if (ready["protocol_id"] != "AKW-LISTING-INTERFACE-v1"
            or ready["listing_run_id"] != manifest["run_id"] or ready["issued_by"] != "listing_main"):
        raise ValueError("Wrong keyword READY authority or Run")
    # The local audit envelope adds the formal receipt pointer, not business fields.
    returned = read_record(record["formal_receipt"])
    for field in ("listing_run_id", "keyword_run_id", "listing_revision", "keyword_revision"):
        if ready[field] != returned.get(field):
            raise ValueError("Keyword READY and formal return disagree")
    for kind, field in (("workbook", "workbook_sha256"), ("process_manifest", "process_manifest_sha256")):
        artifact = returned["return_artifacts"][kind]
        if ready[field] != artifact["sha256"] or state.sha256_file(Path(artifact["path"])) != artifact["sha256"]:
            raise ValueError("Keyword return artifact changed")
    locks = ready["input_locks"]
    if not isinstance(locks, list) or not any(
        Path(lock["path"]).resolve() == Path(manifest["input"]["locked_path"]).resolve()
        and lock["sha256"] == manifest["input"]["sha256"] for lock in locks
    ):
        raise ValueError("Keyword READY does not bind the current product input")
    for lock in locks:
        if state.sha256_file(Path(lock["path"])) != lock["sha256"]:
            raise ValueError("Keyword READY input drift")
    return record["sha256"]


def send_target(response):
    """Read actual app results in direct or MCP-wrapped form; never guess a target."""
    if not isinstance(response, dict) or response.get("isError") is True or response.get("error"):
        raise ValueError("Missing or failed actual send response")
    candidates = []
    if response.get("threadId"):
        candidates.append(response["threadId"])
    structured = response.get("structuredContent")
    if isinstance(structured, dict):
        if structured.get("error") or structured.get("isError") is True:
            raise ValueError("Failed actual send response")
        if structured.get("threadId"):
            candidates.append(structured["threadId"])
    for block in response.get("content", []):
        if isinstance(block, dict) and block.get("type", "text") == "text":
            try:
                payload = json.loads(block.get("text", ""))
            except (ValueError, TypeError):
                continue
            if isinstance(payload, dict):
                if payload.get("isError") is True or payload.get("error"):
                    raise ValueError("Failed actual send response")
                if payload.get("threadId"):
                    candidates.append(payload["threadId"])
    if len(set(candidates)) > 1:
        raise ValueError("Conflicting actual send response")
    return candidates[0] if candidates else None


def keyword_entry_request(manifest, record):
    """Check request preparation only; the keyword owner decides reuse eligibility."""
    request = read_record(record)
    if (request.get("protocol_id") != "AKW-LISTING-INTERFACE-v1"
            or request.get("listing_run_id") != manifest["run_id"]):
        raise ValueError("Keyword entry request identity mismatch")
    context = request.get("product_context", {})
    if (context.get("marketplace") != manifest.get("marketplace")
            or context.get("marketplace_route") != manifest.get("marketplace_route")):
        raise ValueError("Keyword entry marketplace mismatch")
    locks = context.get("current_fact_sources", [])
    if not any(Path(lock["path"]).resolve() == Path(manifest["input"]["locked_path"]).resolve()
               and lock["sha256"] == manifest["input"]["sha256"] for lock in locks):
        raise ValueError("Keyword entry does not bind current input")
    entry = request.get("keyword_entry", {})
    if entry.get("policy") == "fresh-by-user-request":
        source = entry.get("source", {})
        if not source.get("locator"):
            raise ValueError("Fresh-only requires explicit user instruction source/locator")
        locks = locks + [source]
    elif entry.get("policy") != "recent-library-reuse-first":
        raise ValueError("Recent-library reuse check must precede fresh collection; test is not a fresh-only policy")
    for lock in locks:
        if state.sha256_file(Path(lock["path"])) != lock["sha256"]:
            raise ValueError("Keyword entry source hash drift")
    return record["sha256"]


def plan(manifest, board, mode):
    if board.get("run_id") != manifest["run_id"] or board.get("schema") != "listing-dispatch-board/v1":
        raise ValueError("Wrong dispatch board identity")
    if mode not in {"full_pipeline", "downstream_intake"}:
        raise ValueError("Explicit pipeline mode required")
    if state.sha256_file(Path(manifest["input"]["locked_path"])) != manifest["input"]["sha256"]:
        raise ValueError("Locked input changed")
    stages = manifest["stages"]
    jobs = board.get("jobs", {})
    rule_locks = {p.name: state.sha256_file(p) for p in
                  (Path(__file__).resolve().parents[1] / "references").glob("*.md")}
    rows = []
    invalid = {}
    entry_required = manifest.get("execution_controls_version") == "20260911" and mode == "full_pipeline"
    entry_record = board.get("keyword_request")
    entry_hash = keyword_entry_request(manifest, entry_record) if entry_required and entry_record else None
    for stage, data in stages.items():
        if data["status"] == "completed":
            for path in data.get("outputs", []):
                expected = data.get("output_sha256", {}).get(path)
                if not expected or not Path(path).is_file() or state.sha256_file(Path(path)) != expected:
                    invalid[stage] = "accepted output hash missing or changed"

    def add(node, role, dependencies=(), *, gate=None, terminal_dependencies=False, status=None):
        current = status or stages.get(node, {}).get("status", "pending")
        row = {"node": node, "role": role, "status": current}
        allowed = {"completed", "needs_input", "failed", "skipped"} if terminal_dependencies else {"completed"}
        blocked = [dep for dep in dependencies if stages[dep]["status"] not in allowed or dep in invalid]
        # A completed child cannot make a stale ancestor disappear from the frontier.
        # Propagate invalidation without changing persisted stages or rerunning siblings.
        if blocked:
            invalid[node] = "upstream not accepted under current lock: " + ", ".join(blocked)
        signature = {"run_id": manifest["run_id"], "input": manifest["input"], "node": node,
                     "mode": mode, "marketplace": manifest.get("marketplace_route"),
                     "dependencies": {dep: {"status": stages[dep]["status"],
                                              "outputs": stages[dep].get("output_sha256", {})} for dep in dependencies},
                     "gate": gate, "planner_sha256": state.sha256_file(Path(__file__))}
        signature["rule_locks"] = rule_locks
        if entry_required and node == "keyword_library":
            signature["keyword_request_sha256"] = entry_hash
        key = digest(signature)
        row["stage_key"] = key
        if node in invalid:
            row.update(action="repair_lock" if current == "completed" else "blocked", reason=invalid[node])
        elif current == "completed":
            row["action"] = "completed"
        elif current == "skipped":
            row["action"] = "skipped"
        elif node in jobs:
            proof = read_record(jobs[node])
            if any(proof.get(k) != v for k, v in {"run_id": manifest["run_id"], "node": node,
                                                 "stage_key": key, "role": role}.items()):
                row.update(action="reconcile_dispatch", reason="dispatch lock changed; do not resend")
            elif not all(proof.get(k) for k in ("dispatch_id", "task_id", "host")):
                raise ValueError("Incomplete actual dispatch identity")
            else:
                delivery = proof.get("state")
                if delivery in {"sent", "accepted", "running"}:
                    target = send_target(proof.get("response", {}))
                    if (target is not None and target != proof["task_id"]) or (target is None and not proof.get("tool_call_id")):
                        raise ValueError("Actual send response required, not an intended task list")
                    row.update(action="in_flight", dispatch_id=proof["dispatch_id"])
                elif delivery == "returned":
                    row["action"] = "accept_output"
                elif delivery in {"awaiting_login", "busy", "needs_input"}:
                    if not proof.get("reason"):
                        raise ValueError("Deferred task needs an explicit reason")
                    row.update(action="blocked", reason=proof["reason"])
                else:
                    row["action"] = "reconcile_dispatch"
        elif blocked or gate is False:
            row.update(action="blocked", dependencies=blocked)
        elif current in {"failed", "needs_input", "running"}:
            row["action"] = "resolve_or_resume"
        else:
            row["action"] = "main_action" if role == "main" else "dispatch"
        rows.append(row)

    add("preflight", "main")
    if mode == "full_pipeline":
        add("login_gate", "main", ("preflight",))
    login_ready = stages.get("login_gate", {}).get("status") == "completed" and "login_gate" not in invalid
    for stage, role, deps in (
        ("product_audit", "product-audit", ("preflight",)),
        ("market_insights", "five-dimension-insights", ("preflight",)),
        ("pain_points", "painpoint-frequency", ("preflight",)),
        ("tag_priority", "tag-priority", ("market_insights",)),
    ):
        gate = (login_ready and not state.missing_login_sessions(manifest, stage)) if mode == "full_pipeline" else True
        add(stage, role, deps, gate=gate)
    keyword_done = stages["keywords"]["status"] == "completed"
    ready_record = board.get("keyword_ready")
    ready_hash = keyword_ready(manifest, ready_record) if ready_record else None
    # 06 remains the only accepted keywords output. Upstream return never completes it.
    add("keyword_library", "keyword-main", ("preflight",),
        gate=(login_ready and not state.missing_login_sessions(manifest, "keywords") and (not entry_required or bool(entry_hash))
              if mode == "full_pipeline" else board.get("keyword_source_admitted") is True),
        status="completed" if keyword_done or ready_hash else "pending")
    if "keywords" in invalid:
        invalid["sku_keywords"] = invalid["keywords"]
    add("sku_keywords", "sku-keywords", gate=ready_hash or False,
        status="completed" if keyword_done else "pending")
    for node, role, deps in (("selling_point_intake", "selling-point-intake", ("product_audit",)),
                             ("tag_painpoint_intake", "tag-painpoint-intake", ("tag_priority", "pain_points"))):
        receipt = board.get("accepted_intakes", {}).get(node)
        if receipt:
            accepted = read_record(receipt)
            expected = {path: sha for dep in deps for path, sha in stages[dep].get("output_sha256", {}).items()}
            if (accepted.get("run_id") != manifest["run_id"] or accepted.get("role") != role
                    or not expected or accepted.get("output_sha256") != expected):
                raise ValueError("Intake acceptance does not bind current source files")
        add(node, role, deps, status="completed" if receipt else "pending")
    add("selling_point_decision", "main", ("product_audit", "tag_priority", "pain_points", "keywords"), terminal_dependencies=True)
    add("human_checkpoint", "main", ("selling_point_decision",))
    confirmed = False
    if manifest.get("checkpoint", {}).get("status") == "confirmed":
        state.verify_calibration_lock(manifest)
        confirmed = manifest["checkpoint"]["calibration_sha256"]
    add("painpoint_phrasing", "painpoint-phrasing", ("human_checkpoint", "pain_points"),
        gate=confirmed if board.get("painpoint_phrasing_required") is True else False)
    add("keyword_allocation", "main", ("human_checkpoint", "keywords"), gate=confirmed)
    add("listing_draft", "listing-writing-qa", ("keyword_allocation",), gate=confirmed)
    add("copy_checkpoint", "main", ("listing_draft",))
    copy_hash = False
    if manifest.get("copy_checkpoint", {}).get("status") == "confirmed":
        state.verify_copy_lock(manifest)
        copy_hash = manifest["copy_checkpoint"]["copy_sha256"]
    add("listing_generation", "listing-writing-qa", ("keyword_allocation", "copy_checkpoint"), gate=copy_hash)
    add("final_qa", "main", ("listing_generation",), gate=copy_hash)
    if confirmed and type(board.get("painpoint_phrasing_required")) is not bool:
        rows.append({"node": "painpoint_applicability", "role": "main", "action": "main_action"})
    if mode == "downstream_intake" and not keyword_done and not ready_hash and board.get("keyword_source_admitted") is not True:
        rows.append({"node": "keyword_source_admission", "role": "keyword-main", "action": "main_action"})
    quiet = {"completed", "skipped", "blocked", "in_flight"}
    if entry_required and not entry_hash and not keyword_done and not ready_hash:
        rows.append({"node": "keyword_entry_request", "role": "main", "action": "main_action",
                     "reason": "Bind current input and recent-library-reuse-first request before sending"})
    return {"run_id": manifest["run_id"], "wait_allowed": all(row["action"] in quiet for row in rows),
            "nodes": rows, "business_ready": "not_granted_by_planner"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--board", required=True)
    parser.add_argument("--mode", required=True, choices=["full_pipeline", "downstream_intake"])
    args = parser.parse_args()
    try:
        result = plan(state.load_manifest(Path(args.manifest)), json.loads(Path(args.board).read_text()), args.mode)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["wait_allowed"] else 1
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({"wait_allowed": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
