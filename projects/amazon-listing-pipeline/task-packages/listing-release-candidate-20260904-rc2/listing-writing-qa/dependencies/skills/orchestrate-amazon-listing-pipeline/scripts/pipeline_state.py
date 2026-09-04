#!/usr/bin/env python3
"""Create and update an auditable Amazon Listing pipeline run manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "2.0"
WRITING_RULES_VERSION = "v2.2"
BULLET_COUNT_POLICY = "coverage_based_5_to_6"
SUPPORTED_SCHEMA_VERSIONS = {"1.0", "2.0"}
STAGES = (
    "preflight",
    "login_gate",
    "product_audit",
    "market_insights",
    "tag_priority",
    "pain_points",
    "keywords",
    "selling_point_decision",
    "human_checkpoint",
    "painpoint_phrasing",
    "keyword_allocation",
    "listing_draft",
    "copy_checkpoint",
    "listing_generation",
    "final_qa",
)
STATUSES = {"pending", "running", "completed", "needs_input", "failed", "skipped"}
MARKETPLACE_ROUTES = {
    "Amazon-US": {
        "domain": "amazon.com",
        "postal_code": "10001",
        "shopping_assistant": "Alexa for Shopping",
        "prompt_language": "English",
    },
    "Amazon-DE": {
        "domain": "amazon.de",
        "postal_code": "80539",
        "shopping_assistant": "Rufus",
        "prompt_language": "German",
    },
}
LOGIN_GATED_STAGES = {
    "product_audit",
    "market_insights",
    "tag_priority",
    "pain_points",
    "keywords",
    "painpoint_phrasing",
}
CALIBRATION_SCOPE = (
    "人群、场景、用途、频率标签排序",
    "全部卖点及优势/劣势",
    "痛点与样本限制",
    "P0卖点选择",
    "主图1–9初步排布",
    "A+1–7初步排布及动态挤压",
    "ST去重范围等未决规则",
)
POST_CONFIRMATION_STAGES = {
    "painpoint_phrasing",
    "keyword_allocation",
    "listing_draft",
    "copy_checkpoint",
    "listing_generation",
    "final_qa",
}
TRANSITIONS = {
    "pending": {"running", "needs_input", "failed", "skipped"},
    "running": {"completed", "needs_input", "failed", "skipped"},
    "needs_input": {"running", "failed", "skipped"},
    "failed": {"running", "skipped"},
    "completed": {"completed"},
    "skipped": {"running", "skipped"},
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest.get("schema_version") not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(f"Unsupported manifest schema: {manifest.get('schema_version')!r}")
    return manifest


def append_event(manifest: dict[str, Any], event: str, **details: Any) -> None:
    manifest.setdefault("events", []).append({"at": now_iso(), "event": event, **details})
    manifest["updated_at"] = now_iso()


def verify_calibration_lock(manifest: dict[str, Any]) -> None:
    checkpoint = manifest.get("checkpoint", {})
    if checkpoint.get("status") != "confirmed":
        raise ValueError("Full seven-part information calibration must be confirmed first")
    if tuple(checkpoint.get("confirmed_scope", [])) != CALIBRATION_SCOPE:
        raise ValueError("Confirmed calibration scope is incomplete or out of contract")
    calibration_file = checkpoint.get("calibration_file")
    calibration_hash = checkpoint.get("calibration_sha256")
    if not calibration_file or not calibration_hash:
        raise ValueError("Confirmed calibration file path and SHA-256 are required")
    calibration_path = Path(calibration_file)
    if not calibration_path.is_file():
        raise FileNotFoundError(f"Confirmed calibration workbook not found: {calibration_path}")
    if sha256_file(calibration_path) != calibration_hash:
        raise ValueError("Confirmed calibration workbook SHA-256 has changed; reconfirmation is required")


def uses_copy_gate(manifest: dict[str, Any]) -> bool:
    return manifest.get("schema_version") == "2.0"


def validate_product_asin(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Z0-9]{10}", value):
        raise ValueError("A locked product ASIN of ten uppercase letters/digits is required")
    return value


def validate_marketplace(value: Any) -> str:
    if value not in MARKETPLACE_ROUTES:
        raise ValueError("marketplace must be exactly Amazon-US or Amazon-DE")
    return str(value)


def verify_copy_payload(manifest: dict[str, Any], path: Path) -> dict[str, Any]:
    """Validate exact draft text and its original source locks, not just current files."""
    if path.suffix.lower() != ".json":
        raise ValueError("The copy confirmation artifact must be a JSON file")
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("run_id") != manifest["run_id"]:
        raise ValueError("Copy draft Run_ID mismatch")
    product_asin = validate_product_asin(manifest["input"].get("product_asin"))
    if validate_product_asin(payload.get("asin")) != product_asin:
        raise ValueError("Copy draft ASIN mismatch with locked product identity")
    if not isinstance(payload.get("revision"), str) or not payload["revision"].strip():
        raise ValueError("Copy draft requires a nonempty revision string")
    for field in ("title", "item_highlights"):
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            raise ValueError(f"Missing nonempty {field}")
    bullets = payload.get("bullet_points")
    writing_version = manifest.get("writing_rules_version")
    requires_count_approval = False
    if writing_version is None:
        # Older version2 Runs retain their originally locked five-bullet contract.
        if not isinstance(bullets, list) or len(bullets) != 5 or not all(isinstance(x, str) and x.strip() for x in bullets):
            raise ValueError("Legacy copy draft requires exactly five nonempty bullet_points")
    else:
        if writing_version != WRITING_RULES_VERSION or payload.get("writing_rules_version") != writing_version:
            raise ValueError("Copy draft writing_rules_version mismatch or unsupported version")
        count_policy = manifest.get("bullet_count_policy")
        if (count_policy not in (None, BULLET_COUNT_POLICY)
                or payload.get("bullet_count_policy") != count_policy):
            raise ValueError("Copy draft bullet_count_policy mismatch or unsupported policy")
        # Only newly locked policy uses 5–6 by coverage; old v2.2 Runs keep their contract.
        minimum = 5 if count_policy == BULLET_COUNT_POLICY else 3
        if not isinstance(bullets, list) or len(bullets) < minimum or not all(isinstance(x, str) and x.strip() for x in bullets):
            raise ValueError(f"Copy draft requires nonempty bullet_points and at least {minimum} entries")
        if len(payload["title"]) > 75 or len(payload["item_highlights"]) > 125:
            raise ValueError("Title/Item Highlights exceed 75/125 characters")
        requires_count_approval = len(bullets) > 6 if count_policy == BULLET_COUNT_POLICY else len(bullets) != 6
        if requires_count_approval:
            approval = payload.get("bullet_count_approval", {})
            if (not isinstance(approval, dict) or type(approval.get("count")) is not int
                    or approval["count"] != len(bullets)
                    or not all(isinstance(approval.get(k), str) and approval[k].strip() for k in ("confirmed_by", "note"))
                    or not isinstance(approval.get("source_lock"), dict)):
                raise ValueError("Non-default bullet count requires explicit bullet_count_approval and evidence")
    # Project bullet length is intentionally unrestricted; backend limits belong in QA.
    expected = {
        str(Path(manifest["checkpoint"]["calibration_file"]).resolve()): manifest["checkpoint"]["calibration_sha256"],
        str(Path(manifest["input"]["locked_path"]).resolve()): manifest["input"]["sha256"],
    }
    for supplement in manifest["input"].get("user_fact_supplements", []):
        expected[str(Path(supplement["path"]).resolve())] = supplement["sha256"]
    keyword_paths = [Path(p).resolve() for p in manifest["stages"]["keywords"].get("outputs", []) if Path(p).name == "06_SKU可用关键词库.xlsx"]
    if manifest["stages"]["keywords"]["status"] != "completed" or len(keyword_paths) != 1:
        raise ValueError("Exactly one accepted 06 keyword workbook is required")
    accepted_hashes = {str(Path(p).resolve()): digest for p, digest in manifest["stages"]["keywords"].get("output_sha256", {}).items()}
    accepted_keyword_hash = accepted_hashes.get(str(keyword_paths[0]))
    if not accepted_keyword_hash:
        raise ValueError("Accepted 06 SHA-256 is required; register the verified keyword output before drafting")
    expected[str(keyword_paths[0])] = accepted_keyword_hash
    locks = payload.get("source_locks")
    if not isinstance(locks, list):
        raise ValueError("Copy draft source_locks must preserve its actual source versions")
    seen: dict[str, str] = {}
    for lock in locks:
        locked_path = Path(lock["path"]).resolve()
        key = str(locked_path)
        if key in seen:
            raise ValueError("Duplicate draft source lock")
        seen[key] = lock["sha256"]
        if not locked_path.is_file() or sha256_file(locked_path) != lock["sha256"]:
            raise ValueError(f"Copy draft source changed: {locked_path}")
    if any(seen.get(p) != digest for p, digest in expected.items()):
        raise ValueError("Copy draft does not match current 07, 06 and all product fact locks")
    if requires_count_approval:
        proof = payload["bullet_count_approval"]["source_lock"]
        if (not isinstance(proof.get("path"), str) or not proof["path"].strip()
                or not isinstance(proof.get("sha256"), str)
                or not re.fullmatch(r"[a-f0-9]{64}", proof["sha256"])
                or seen.get(str(Path(proof["path"]).resolve())) != proof["sha256"]):
            raise ValueError("Bullet count approval evidence must be present in verified source_locks")
    return payload


def verify_copy_lock(manifest: dict[str, Any]) -> None:
    if not uses_copy_gate(manifest):
        return  # Existing version1 Runs retain their locked delivery contract.
    gate = manifest.get("copy_checkpoint", {})
    if gate.get("status") != "confirmed":
        raise ValueError("User must confirm Title, Item Highlights and every Bullet before final assembly")
    draft = Path(gate["copy_file"])
    if not draft.is_file() or sha256_file(draft) != gate.get("copy_sha256"):
        raise ValueError("Confirmed copy changed; reopen the copy checkpoint")
    if gate.get("calibration_sha256") != manifest["checkpoint"].get("calibration_sha256"):
        raise ValueError("07 changed after copy confirmation")
    verify_copy_payload(manifest, draft)


def derive_overall_status(manifest: dict[str, Any]) -> str:
    stages = manifest["stages"]
    if stages["final_qa"]["status"] == "completed":
        return "COMPLETED"
    if stages["human_checkpoint"]["status"] == "needs_input":
        return "WAITING_HUMAN_CONFIRMATION"
    if stages.get("copy_checkpoint", {}).get("status") == "needs_input":
        return "WAITING_COPY_CONFIRMATION"
    if any(item["status"] == "running" for item in stages.values()):
        return "RUNNING"
    if any(item["status"] == "failed" for item in stages.values()):
        return "FAILED"
    if any(item["status"] == "needs_input" for item in stages.values()):
        return "NEEDS_INPUT"
    if manifest.get("checkpoint", {}).get("status") == "confirmed":
        return "CONFIRMED_FOR_LISTING"
    return "READY"


def cmd_init(args: argparse.Namespace) -> int:
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"Input workbook not found: {input_path}")
    if input_path.suffix.lower() != ".xlsx":
        raise ValueError("The locked input must be an .xlsx workbook")
    product_asin = validate_product_asin(getattr(args, "product_asin", None))
    marketplace = validate_marketplace(getattr(args, "marketplace", None))
    marketplace_route = dict(MARKETPLACE_ROUTES[marketplace])

    input_hash = sha256_file(input_path)
    run_id = args.run_id or f"ALP-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{input_hash[:6]}"
    run_dir = Path(args.run_dir).expanduser().resolve()
    manifest_path = run_dir / "run-manifest.json"
    if manifest_path.exists():
        raise FileExistsError(f"Run manifest already exists: {manifest_path}")

    locked_dir = run_dir / "locked-input"
    output_dir = run_dir / "outputs"
    evidence_dir = run_dir / "evidence"
    locked_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    locked_path = locked_dir / "00_锁定输入.xlsx"
    shutil.copy2(input_path, locked_path)
    locked_hash = sha256_file(locked_path)
    if locked_hash != input_hash:
        raise IOError("Locked input hash does not match source input")

    created = now_iso()
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "pipeline_contract_version": "listing-v2.1-marketplace-route-login-gate",
        "writing_rules_version": WRITING_RULES_VERSION,
        "bullet_count_policy": BULLET_COUNT_POLICY,
        "run_id": run_id,
        "marketplace": marketplace,
        "marketplace_route": marketplace_route,
        "overall_status": "READY",
        "created_at": created,
        "updated_at": created,
        "input": {
            "original_path": str(input_path),
            "locked_path": str(locked_path),
            "sha256": input_hash,
            "product_asin": product_asin,
            "marketplace": marketplace,
        },
        "directories": {
            "run": str(run_dir),
            "outputs": str(output_dir),
            "evidence": str(evidence_dir),
        },
        "stages": {
            stage: {
                "status": "pending",
                "started_at": None,
                "ended_at": None,
                "message": "",
                "outputs": [],
            }
            for stage in STAGES
        },
        "checkpoint": {
            "status": "pending",
            "calibration_file": None,
            "calibration_sha256": None,
            "confirmed_scope": [],
            "candidate_id": None,
            "statement_zh": None,
            "direction_en": None,
            "note": None,
            "confirmed_by": None,
            "confirmed_at": None,
        },
        "copy_checkpoint": {
            "status": "pending",
            "copy_file": None,
            "copy_sha256": None,
            "calibration_sha256": None,
            "confirmed_scope": [],
            "confirmed_at": None,
            "confirmed_by": None,
        },
        "events": [],
    }
    append_event(
        manifest,
        "run_initialized",
        run_id=run_id,
        input_sha256=input_hash,
        marketplace=marketplace,
        marketplace_route=marketplace_route,
    )
    atomic_write(manifest_path, manifest)
    print(json.dumps({"manifest": str(manifest_path), "run_id": run_id}, ensure_ascii=False))
    return 0


def cmd_set_stage(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).expanduser().resolve()
    manifest = load_manifest(manifest_path)
    stage = args.stage
    new_status = args.status
    if stage not in STAGES:
        raise ValueError(f"Unknown stage: {stage}")
    if new_status not in STATUSES:
        raise ValueError(f"Unknown stage status: {new_status}")
    if stage == "human_checkpoint" and new_status == "completed":
        raise ValueError("Use the confirm command to complete the human checkpoint")
    if stage not in manifest["stages"]:
        raise ValueError("This legacy Run has no new copy stages; do not silently upgrade its locked contract")
    if stage == "login_gate" and new_status == "completed":
        raise ValueError("Use confirm-login to complete the three-session login gate")
    if stage == "copy_checkpoint" and new_status == "completed":
        raise ValueError("Use confirm-copy to complete the copy checkpoint")
    if (
        stage in LOGIN_GATED_STAGES
        and new_status in {"running", "completed"}
        and "login_gate" in manifest["stages"]
        and manifest["stages"]["login_gate"]["status"] != "completed"
    ):
        raise ValueError("Amazon, SIF and SellerSprite login gate must be confirmed first")
    if stage in POST_CONFIRMATION_STAGES and new_status in {"running", "completed"}:
        verify_calibration_lock(manifest)
    if uses_copy_gate(manifest) and stage == "listing_draft" and new_status in {"running", "completed"} and manifest["stages"]["keyword_allocation"]["status"] != "completed":
        raise ValueError("09 keyword allocation plan must complete before copy drafting")
    if stage in {"listing_generation", "final_qa"} and new_status in {"running", "completed"}:
        verify_copy_lock(manifest)
        if uses_copy_gate(manifest) and manifest["stages"]["keyword_allocation"]["status"] != "completed":
            raise ValueError("09 keyword allocation must be completed before final assembly")
    if uses_copy_gate(manifest) and stage == "final_qa" and new_status == "completed" and manifest["stages"]["listing_generation"]["status"] != "completed":
        raise ValueError("Final listing output must complete before final QA")

    record = manifest["stages"][stage]
    old_status = record["status"]
    if uses_copy_gate(manifest) and stage in {"listing_draft", "copy_checkpoint"}:
        if manifest.get("copy_checkpoint", {}).get("status") == "confirmed":
            raise ValueError("Use reopen-copy before changing a confirmed copy stage")
        if stage == "listing_draft" and old_status == "completed":
            raise ValueError("Use reopen-copy before replacing a registered completed draft")
    if not args.force and new_status not in TRANSITIONS[old_status]:
        raise ValueError(f"Invalid transition for {stage}: {old_status} -> {new_status}")

    outputs: list[str] = []
    for output in args.output or []:
        output_path = Path(output).expanduser().resolve()
        if new_status == "completed" and not output_path.exists():
            raise FileNotFoundError(f"Completed-stage output does not exist: {output_path}")
        outputs.append(str(output_path))
    if stage == "listing_draft" and new_status == "completed":
        draft_outputs = [Path(p) for p in outputs if Path(p).suffix.lower() == ".json"]
        if len(draft_outputs) != 1:
            raise ValueError("Register exactly one copy-draft JSON as the listing_draft output")
        verify_copy_payload(manifest, draft_outputs[0])

    if new_status == "running" and not record.get("started_at"):
        record["started_at"] = now_iso()
    if new_status in {"completed", "failed", "skipped"}:
        record["ended_at"] = now_iso()
    elif new_status in {"running", "needs_input"}:
        record["ended_at"] = None

    record["status"] = new_status
    if args.message is not None:
        record["message"] = args.message
    if outputs:
        record["outputs"] = outputs
        if new_status == "completed" and uses_copy_gate(manifest):
            record["output_sha256"] = {p: sha256_file(Path(p)) for p in outputs if Path(p).is_file()}

    if stage == "human_checkpoint" and new_status == "needs_input":
        manifest["checkpoint"]["status"] = "waiting"
    if stage == "copy_checkpoint" and new_status == "needs_input":
        manifest["copy_checkpoint"]["status"] = "waiting"

    append_event(
        manifest,
        "stage_status_changed",
        stage=stage,
        old_status=old_status,
        new_status=new_status,
        message=record.get("message", ""),
    )
    manifest["overall_status"] = derive_overall_status(manifest)
    atomic_write(manifest_path, manifest)
    print(json.dumps({"stage": stage, "status": new_status, "overall_status": manifest["overall_status"]}, ensure_ascii=False))
    return 0


def cmd_confirm_login(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).expanduser().resolve()
    manifest = load_manifest(manifest_path)
    if "login_gate" not in manifest.get("stages", {}):
        raise ValueError("This historical Run has no login gate; do not silently upgrade it")
    marketplace = validate_marketplace(manifest.get("marketplace"))
    if manifest.get("marketplace_route") != MARKETPLACE_ROUTES[marketplace]:
        raise ValueError("Run marketplace route is missing or has drifted")
    receipts = {
        "amazon": args.amazon,
        "sif": args.sif,
        "sellersprite": args.sellersprite,
    }
    if any(value != "authenticated" for value in receipts.values()):
        raise ValueError("Amazon, SIF and SellerSprite must each return authenticated")
    record = manifest["stages"]["login_gate"]
    if record["status"] == "completed":
        if record.get("receipts") != receipts:
            raise ValueError("Completed login receipts cannot be overwritten")
        print(json.dumps({"status": "already_confirmed", "receipts": receipts}, ensure_ascii=False))
        return 0
    if record["status"] not in {"pending", "running", "needs_input", "failed"}:
        raise ValueError(f"Invalid login gate state: {record['status']}")
    confirmed_at = now_iso()
    record.update(
        {
            "status": "completed",
            "started_at": record.get("started_at") or confirmed_at,
            "ended_at": confirmed_at,
            "message": "All required owner-task website sessions authenticated",
            "receipts": receipts,
        }
    )
    append_event(
        manifest,
        "website_login_gate_confirmed",
        marketplace=marketplace,
        receipts=receipts,
        credentials_persisted=False,
    )
    manifest["overall_status"] = derive_overall_status(manifest)
    atomic_write(manifest_path, manifest)
    print(
        json.dumps(
            {
                "status": "completed",
                "marketplace": marketplace,
                "marketplace_route": manifest["marketplace_route"],
                "receipts": receipts,
            },
            ensure_ascii=False,
        )
    )
    return 0


def cmd_confirm(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).expanduser().resolve()
    manifest = load_manifest(manifest_path)
    if manifest["stages"]["selling_point_decision"]["status"] != "completed":
        raise ValueError("selling_point_decision must be completed before confirmation")

    calibration_path = Path(args.calibration_file).expanduser().resolve()
    if not calibration_path.is_file():
        raise FileNotFoundError(f"Calibration workbook not found: {calibration_path}")
    if calibration_path.suffix.lower() != ".xlsx":
        raise ValueError("The calibration file must be an .xlsx workbook")
    registered_outputs = {
        str(Path(path).expanduser().resolve())
        for path in manifest["stages"]["selling_point_decision"].get("outputs", [])
    }
    if str(calibration_path) not in registered_outputs:
        raise ValueError("Calibration workbook must be a registered selling_point_decision output")
    calibration_hash = sha256_file(calibration_path)

    checkpoint = manifest["checkpoint"]
    prior_calibration_hash = checkpoint.get("calibration_sha256")
    if uses_copy_gate(manifest) and prior_calibration_hash and prior_calibration_hash != calibration_hash:
        prior_copy = manifest.get("copy_checkpoint", {}).copy()
        manifest.setdefault("copy_confirmation_history", []).append(prior_copy)
        manifest["copy_checkpoint"] = {"status": "waiting", "confirmed_scope": []}
        for stage in ("keyword_allocation", "listing_draft", "copy_checkpoint", "listing_generation", "final_qa"):
            manifest["stages"][stage].update({"status": "needs_input" if stage == "copy_checkpoint" else "pending", "started_at": None, "ended_at": None, "message": "07 changed; downstream plan and copy approval invalidated"})
        append_event(manifest, "calibration_change_invalidated_copy", prior_confirmation=prior_copy, prior_files_preserved=True)
    checkpoint.update(
        {
            "status": "confirmed",
            "calibration_file": str(calibration_path),
            "calibration_sha256": calibration_hash,
            "confirmed_scope": list(CALIBRATION_SCOPE),
            "candidate_id": args.candidate_id,
            "statement_zh": args.statement_zh,
            "direction_en": args.direction_en or "",
            "note": args.note or "",
            "confirmed_by": args.confirmed_by,
            "confirmed_at": now_iso(),
        }
    )
    record = manifest["stages"]["human_checkpoint"]
    old_status = record["status"]
    record.update(
        {
            "status": "completed",
            "started_at": record.get("started_at") or now_iso(),
            "ended_at": now_iso(),
            "message": f"Confirmed full information calibration; P0={args.candidate_id}",
        }
    )
    append_event(
        manifest,
        "information_calibration_confirmed",
        candidate_id=args.candidate_id,
        statement_zh=args.statement_zh,
        calibration_file=str(calibration_path),
        calibration_sha256=calibration_hash,
        confirmed_scope=list(CALIBRATION_SCOPE),
        previous_stage_status=old_status,
    )
    manifest["overall_status"] = derive_overall_status(manifest)
    atomic_write(manifest_path, manifest)
    print(
        json.dumps(
            {
                "checkpoint": "confirmed",
                "candidate_id": args.candidate_id,
                "calibration_sha256": calibration_hash,
                "confirmed_scope_count": len(CALIBRATION_SCOPE),
            },
            ensure_ascii=False,
        )
    )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).expanduser().resolve()
    manifest = load_manifest(manifest_path)
    current = [
        {"stage": stage, "status": item["status"], "message": item.get("message", "")}
        for stage, item in manifest["stages"].items()
        if item["status"] != "pending"
    ]
    result = {
        "run_id": manifest["run_id"],
        "marketplace": manifest.get("marketplace"),
        "marketplace_route": manifest.get("marketplace_route"),
        "overall_status": derive_overall_status(manifest),
        "input_sha256": manifest["input"]["sha256"],
        "active_or_finished_stages": current,
        "checkpoint": manifest["checkpoint"],
        "copy_checkpoint": manifest.get("copy_checkpoint"),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_confirm_copy(args: argparse.Namespace) -> int:
    path = Path(args.manifest).expanduser().resolve()
    manifest = load_manifest(path)
    if not uses_copy_gate(manifest):
        raise ValueError("New copy gate applies to version2 Runs; legacy Runs are not upgraded implicitly")
    verify_calibration_lock(manifest)
    draft = Path(args.copy_file).expanduser().resolve()
    prior_gate = manifest.get("copy_checkpoint", {})
    if prior_gate.get("status") == "confirmed":
        if (draft.is_file() and str(draft) == str(Path(prior_gate["copy_file"]).resolve())
                and sha256_file(draft) == prior_gate.get("copy_sha256")):
            verify_copy_lock(manifest)
            print(json.dumps({"status": "already_confirmed", "copy_sha256": prior_gate["copy_sha256"]}, ensure_ascii=False))
            return 0
        raise ValueError("Use reopen-copy before confirming changed copy; prior approval cannot be overwritten")
    if manifest["stages"]["listing_draft"]["status"] != "completed":
        raise ValueError("listing_draft must be completed before copy confirmation")
    registered = {str(Path(p).resolve()) for p in manifest["stages"]["listing_draft"].get("outputs", [])}
    if str(draft) not in registered:
        raise ValueError("Copy file must be the registered listing_draft output")
    registered_hashes = {str(Path(p).resolve()): digest for p, digest in manifest["stages"]["listing_draft"].get("output_sha256", {}).items()}
    draft_hash = sha256_file(draft)
    if registered_hashes.get(str(draft)) != draft_hash:
        raise ValueError("Registered draft SHA-256 missing or changed; reopen-copy and review a new draft")
    payload = verify_copy_payload(manifest, draft)
    gate = {
        "status": "confirmed", "copy_file": str(draft), "copy_sha256": draft_hash,
        "asin": payload["asin"], "revision": payload["revision"], "copy_snapshot": payload,
        "calibration_sha256": manifest["checkpoint"]["calibration_sha256"],
        "confirmed_scope": ["Title", "Item Highlights"] + [f"Bullet {i}" for i in range(1, len(payload["bullet_points"]) + 1)],
        "confirmed_at": now_iso(), "confirmed_by": args.confirmed_by, "note": args.note or "",
    }
    manifest["copy_checkpoint"] = gate
    manifest["stages"]["copy_checkpoint"].update({"status":"completed", "started_at":now_iso(), "ended_at":now_iso(), "message":f"User confirmed all {len(gate['confirmed_scope'])} copy fields", "outputs":[str(draft)]})
    append_event(manifest, "listing_copy_confirmed", **gate)
    manifest["overall_status"] = derive_overall_status(manifest)
    atomic_write(path, manifest)
    print(json.dumps(gate, ensure_ascii=False))
    return 0


def cmd_reopen_copy(args: argparse.Namespace) -> int:
    path = Path(args.manifest).expanduser().resolve()
    manifest = load_manifest(path)
    if not uses_copy_gate(manifest):
        raise ValueError("Legacy Run has no copy checkpoint")
    prior = manifest.get("copy_checkpoint", {}).copy()
    manifest.setdefault("copy_confirmation_history", []).append(prior)
    manifest["copy_checkpoint"] = {"status":"waiting", "copy_file":None, "copy_sha256":None, "calibration_sha256":None, "confirmed_scope":[], "confirmed_at":None, "confirmed_by":None}
    for stage in ("listing_draft", "copy_checkpoint", "listing_generation", "final_qa"):
        record = manifest["stages"][stage]
        record.update({"status":"needs_input" if stage=="copy_checkpoint" else "pending", "started_at":None, "ended_at":None, "message":args.reason})
    append_event(manifest, "listing_copy_reopened", reason=args.reason, prior_confirmation=prior, prior_files_preserved=True)
    manifest["overall_status"] = derive_overall_status(manifest)
    atomic_write(path, manifest)
    print(json.dumps({"status":"WAITING_COPY_CONFIRMATION", "reason":args.reason}, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a new run and lock the input workbook")
    init_parser.add_argument("--input", required=True)
    init_parser.add_argument("--run-dir", required=True)
    init_parser.add_argument("--run-id")
    init_parser.add_argument("--product-asin", required=True, help="Product ASIN verified against the current locked input")
    init_parser.add_argument("--marketplace", required=True, choices=sorted(MARKETPLACE_ROUTES))
    init_parser.set_defaults(func=cmd_init)

    login_parser = subparsers.add_parser(
        "confirm-login", help="Confirm authenticated Amazon, SIF and SellerSprite owner sessions"
    )
    login_parser.add_argument("--manifest", required=True)
    login_parser.add_argument("--amazon", required=True, choices=["authenticated"])
    login_parser.add_argument("--sif", required=True, choices=["authenticated"])
    login_parser.add_argument("--sellersprite", required=True, choices=["authenticated"])
    login_parser.set_defaults(func=cmd_confirm_login)

    stage_parser = subparsers.add_parser("set-stage", help="Update one pipeline stage")
    stage_parser.add_argument("--manifest", required=True)
    stage_parser.add_argument("--stage", required=True, choices=STAGES)
    stage_parser.add_argument("--status", required=True, choices=sorted(STATUSES))
    stage_parser.add_argument("--message")
    stage_parser.add_argument("--output", action="append")
    stage_parser.add_argument("--force", action="store_true")
    stage_parser.set_defaults(func=cmd_set_stage)

    confirm_parser = subparsers.add_parser("confirm", help="Record the full human information-calibration confirmation")
    confirm_parser.add_argument("--manifest", required=True)
    confirm_parser.add_argument("--calibration-file", required=True)
    confirm_parser.add_argument("--candidate-id", required=True)
    confirm_parser.add_argument("--statement-zh", required=True)
    confirm_parser.add_argument("--direction-en")
    confirm_parser.add_argument("--note")
    confirm_parser.add_argument("--confirmed-by", default="User")
    confirm_parser.set_defaults(func=cmd_confirm)

    copy_parser = subparsers.add_parser("confirm-copy", help="Lock user-approved Title, Item Highlights and every Bullet")
    copy_parser.add_argument("--manifest", required=True)
    copy_parser.add_argument("--copy-file", required=True)
    copy_parser.add_argument("--confirmed-by", default="User")
    copy_parser.add_argument("--note")
    copy_parser.set_defaults(func=cmd_confirm_copy)

    reopen_parser = subparsers.add_parser("reopen-copy", help="Invalidate copy approval without deleting prior artifacts")
    reopen_parser.add_argument("--manifest", required=True)
    reopen_parser.add_argument("--reason", required=True)
    reopen_parser.set_defaults(func=cmd_reopen_copy)

    status_parser = subparsers.add_parser("status", help="Print a compact run status")
    status_parser.add_argument("--manifest", required=True)
    status_parser.set_defaults(func=cmd_status)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
