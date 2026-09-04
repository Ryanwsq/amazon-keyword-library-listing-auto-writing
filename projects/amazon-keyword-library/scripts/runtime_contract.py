#!/usr/bin/env python3
"""Build and verify content-addressed runtime contracts for keyword-library runs.

This utility governs execution identity, rule drift, resumability, dependency
readiness and login preflight. It deliberately does not make keyword business
judgments.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
RULE_MAP_PATH = ROOT / "contracts" / "runtime-rule-map.json"
CONTRACT_SCHEMA = "amazon-keyword-run-contract/v1"
STATUS_SCHEMA = "amazon-keyword-stage-status/v1"
PREFLIGHT_SCHEMA = "amazon-keyword-source-preflight/v1"
EXECUTOR_VERSION = "runtime-contract/1.1.0"

MARKETPLACE_ROUTES: Dict[str, Dict[str, str]] = {
    "Amazon-US": {
        "domain": "amazon.com",
        "department": "All",
        "postal_code": "10001",
        "shopping_assistant": "Alexa for Shopping",
        "prompt_language": "English",
    },
    "Amazon-DE": {
        "domain": "amazon.de",
        "department": "Alle",
        "postal_code": "80539",
        "shopping_assistant": "Rufus",
        "prompt_language": "German",
    },
}

PARALLEL_WAVES = {
    "core-sources": ["amazon-autocomplete", "sellersprite"],
}

STAGE_GRAPH: Dict[str, List[str]] = {
    "sif": [],
    "core-lock": ["sif"],
    "amazon-autocomplete": ["core-lock"],
    "sellersprite": ["core-lock"],
    "first-board": ["sif", "amazon-autocomplete", "sellersprite"],
    "cleaning": ["first-board"],
    "word-frequency": ["cleaning"],
    "classification": ["cleaning"],
    "competition": ["classification"],
    "trend": ["classification"],
    "assembly": ["word-frequency", "classification", "competition", "trend"],
    "quality-validation": ["assembly"],
}

SOURCE_PREFLIGHT = {
    "amazon-autocomplete": "amazon",
    "sif": "sif",
    "sellersprite": "sellersprite",
}

COMPLETED_STATUSES = {"completed", "completed_with_gaps"}
STAGE_STATUSES = COMPLETED_STATUSES | {
    "pending",
    "running",
    "awaiting_login",
    "incomplete",
    "blocked",
    "not_executed",
    "not_applicable",
}
PREFLIGHT_STATUSES = {"authenticated", "awaiting_login", "unavailable"}
REQUIRED_INPUT_HASHES = {
    "product_basic_configuration",
    "product_selling_points",
    "competitor_asins",
}

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
SECRET_RE = re.compile(
    r"(?:\bsk-[A-Za-z0-9]{20,}\b|\bgh[opusr]_[A-Za-z0-9]{20,}\b|"
    r"\bgithub_pat_[A-Za-z0-9_]{20,}\b|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)
FORBIDDEN_KEYS = {
    "password",
    "passwd",
    "secret",
    "secret_key",
    "access_token",
    "refresh_token",
    "cookie",
    "cookies",
    "credential",
    "credentials",
}


class ContractError(ValueError):
    """Raised for a deterministic contract failure."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot read JSON {path}: {exc}") from exc


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def require_sha256(value: Any, label: str) -> str:
    normalized = str(value).lower()
    if not SHA256_RE.fullmatch(normalized):
        raise ContractError(f"{label} must be a 64-character SHA-256")
    return normalized


def validate_payload_safety(value: Any, trail: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if key_text.lower() in FORBIDDEN_KEYS:
                raise ContractError(f"{trail}.{key_text}: credential field is forbidden")
            validate_payload_safety(item, f"{trail}.{key_text}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            validate_payload_safety(item, f"{trail}[{index}]")
        return
    if not isinstance(value, str):
        return
    if value.startswith(("/", "~/")) or re.match(r"^[A-Za-z]:[\\/]", value):
        raise ContractError(f"{trail}: absolute machine path is forbidden")
    if UUID_RE.search(value):
        raise ContractError(f"{trail}: task-like UUID is forbidden")
    if SECRET_RE.search(value):
        raise ContractError(f"{trail}: secret-like value is forbidden")


def active_stages(run_type: str) -> List[str]:
    stages = list(STAGE_GRAPH)
    if run_type == "production":
        stages.remove("quality-validation")
    return stages


def load_rule_map() -> Dict[str, Any]:
    data = read_json(RULE_MAP_PATH)
    if data.get("schema") != "amazon-keyword-rule-map/v1":
        raise ContractError("unsupported runtime rule map schema")
    rules = data.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ContractError("runtime rule map has no rules")
    seen = set()
    for rule in rules:
        rule_id = rule.get("id")
        owner = rule.get("owner")
        anchor = rule.get("anchor")
        stages = rule.get("stages")
        if not isinstance(rule_id, str) or not rule_id:
            raise ContractError("runtime rule has no id")
        if rule_id in seen:
            raise ContractError(f"duplicate runtime rule id: {rule_id}")
        seen.add(rule_id)
        if not isinstance(owner, str) or Path(owner).is_absolute() or ".." in Path(owner).parts:
            raise ContractError(f"{rule_id}: owner must be a repository-relative path")
        owner_path = ROOT / owner
        if not owner_path.is_file():
            raise ContractError(f"{rule_id}: owner does not exist: {owner}")
        text = owner_path.read_text(encoding="utf-8")
        if not isinstance(anchor, str) or anchor not in text:
            raise ContractError(f"{rule_id}: anchor is absent from {owner}")
        if not isinstance(stages, list) or not stages:
            raise ContractError(f"{rule_id}: stages must be a non-empty list")
        unknown = sorted(set(stages) - STAGE_GRAPH.keys())
        if unknown:
            raise ContractError(f"{rule_id}: unknown stages {unknown}")
    return data


def rule_snapshot(rule_map: Mapping[str, Any]) -> List[Dict[str, Any]]:
    snapshots = []
    for rule in rule_map["rules"]:
        owner = rule["owner"]
        snapshots.append(
            {
                "id": rule["id"],
                "owner": owner,
                "owner_sha256": sha256_file(ROOT / owner),
                "anchor": rule["anchor"],
                "stages": list(rule["stages"]),
            }
        )
    return snapshots


def validate_spec(spec: Mapping[str, Any]) -> None:
    validate_payload_safety(spec)
    if not RUN_ID_RE.fullmatch(str(spec.get("run_id", ""))):
        raise ContractError("run_id has an invalid format")
    run_type = spec.get("run_type")
    if run_type not in {"production", "test-validation"}:
        raise ContractError("run_type must be production or test-validation")
    qa_mode = spec.get("qa_mode")
    change_flags = spec.get("change_flags", [])
    if not isinstance(change_flags, list) or any(
        not isinstance(item, str) or not item for item in change_flags
    ):
        raise ContractError("change_flags must be a list of non-empty strings")
    if run_type == "production":
        if qa_mode not in {None, "not_applicable"}:
            raise ContractError("production qa_mode must be omitted or not_applicable")
    else:
        if qa_mode not in {"compact-validation", "full-regression"}:
            raise ContractError(
                "test-validation qa_mode must be compact-validation or full-regression"
            )
        if change_flags and qa_mode != "full-regression":
            raise ContractError("test-validation with contract changes requires full-regression")
    revision = str(spec.get("revision", "")).lower()
    if not REVISION_RE.fullmatch(revision):
        raise ContractError("revision must be a 40-character Git commit")
    site = spec.get("site")
    if site not in MARKETPLACE_ROUTES:
        raise ContractError("site must be exactly Amazon-US or Amazon-DE")
    hashes = spec.get("input_hashes")
    if not isinstance(hashes, Mapping):
        raise ContractError("input_hashes must be an object")
    if set(hashes) != REQUIRED_INPUT_HASHES:
        raise ContractError(
            "input_hashes must contain exactly product_basic_configuration, "
            "product_selling_points and competitor_asins"
        )
    for name, value in hashes.items():
        require_sha256(value, f"input_hashes.{name}")
    locks = spec.get("locks")
    if not isinstance(locks, Mapping):
        raise ContractError("locks must be an object")
    required_locks = {
        "target_amazon_category",
        "has_multiple_stable_product_types",
        "original_asin_count",
        "selected_asin_count",
        "excluded_asin_count",
    }
    missing = sorted(required_locks - locks.keys())
    if missing:
        raise ContractError(f"locks missing required fields: {missing}")
    if not isinstance(locks["has_multiple_stable_product_types"], bool):
        raise ContractError("locks.has_multiple_stable_product_types must be boolean")
    counts = [locks[name] for name in required_locks if name.endswith("_count")]
    if any(not isinstance(value, int) or value < 0 for value in counts):
        raise ContractError("ASIN population counts must be non-negative integers")
    if locks["original_asin_count"] != (
        locks["selected_asin_count"] + locks["excluded_asin_count"]
    ):
        raise ContractError("original ASIN population must equal selected plus excluded")
    if not 1 <= locks["selected_asin_count"] <= 5:
        raise ContractError("selected ASIN population must be between 1 and 5")


def compute_stage_keys(contract: MutableMapping[str, Any]) -> None:
    input_hashes = contract["input_hashes"]
    rule_by_id = {rule["id"]: rule for rule in contract["rules"]}
    stages = contract["stages"]
    for stage_name in active_stages(contract["run_type"]):
        stage = stages[stage_name]
        dependency_keys = {
            name: stages[name]["stage_key"] for name in stage["dependencies"]
        }
        stage_rules = [
            {
                "id": rule_id,
                "owner_sha256": rule_by_id[rule_id]["owner_sha256"],
            }
            for rule_id in stage["rule_ids"]
        ]
        stage["stage_key"] = sha256_bytes(
            canonical_bytes(
                {
                    "schema": CONTRACT_SCHEMA,
                    "run_id": contract["run_id"],
                    "run_type": contract["run_type"],
                    "revision": contract["revision"],
                    "site": contract["site"],
                    "marketplace_route": contract["marketplace_route"],
                    "input_hashes": input_hashes,
                    "locks": contract["locks"],
                    "quality_routing": (
                        contract["quality_routing"]
                        if stage_name in {"assembly", "quality-validation"}
                        else None
                    ),
                    "change_flags": (
                        contract["change_flags"]
                        if stage_name in {"assembly", "quality-validation"}
                        else []
                    ),
                    "stage": stage_name,
                    "dependencies": dependency_keys,
                    "rules": stage_rules,
                    "executor_version": stage["executor_version"],
                }
            )
        )


def build_contract(spec: Mapping[str, Any]) -> Dict[str, Any]:
    validate_spec(spec)
    rule_map = load_rule_map()
    snapshots = rule_snapshot(rule_map)
    run_type = str(spec["run_type"])
    versions = spec.get("executor_versions", {})
    if not isinstance(versions, Mapping):
        raise ContractError("executor_versions must be an object")
    unknown_versions = sorted(set(versions) - STAGE_GRAPH.keys())
    if unknown_versions:
        raise ContractError(f"executor_versions has unknown stages: {unknown_versions}")
    stages: Dict[str, Dict[str, Any]] = {}
    for stage_name in active_stages(run_type):
        stages[stage_name] = {
            "dependencies": [
                item
                for item in STAGE_GRAPH[stage_name]
                if item in active_stages(run_type)
            ],
            "executor_version": str(versions.get(stage_name, EXECUTOR_VERSION)),
            "rule_ids": sorted(
                rule["id"] for rule in snapshots if stage_name in rule["stages"]
            ),
            "stage_key": "",
        }
    contract: Dict[str, Any] = {
        "schema": CONTRACT_SCHEMA,
        "contract_version": EXECUTOR_VERSION,
        "run_id": spec["run_id"],
        "run_type": run_type,
        "revision": str(spec["revision"]).lower(),
        "site": spec["site"],
        "marketplace_route": dict(MARKETPLACE_ROUTES[str(spec["site"])]),
        "parallel_waves": PARALLEL_WAVES,
        "input_hashes": {
            key: require_sha256(value, f"input_hashes.{key}")
            for key, value in spec["input_hashes"].items()
        },
        "locks": dict(spec["locks"]),
        "change_flags": sorted(set(spec.get("change_flags", []))),
        "rules": snapshots,
        "stages": stages,
        "quality_routing": (
            "not_applicable" if run_type == "production" else spec["qa_mode"]
        ),
    }
    compute_stage_keys(contract)
    contract["contract_sha256"] = sha256_bytes(
        canonical_bytes({key: value for key, value in contract.items() if key != "contract_sha256"})
    )
    validate_payload_safety(contract)
    return contract


def verify_contract(contract: Mapping[str, Any], check_current_rules: bool = True) -> None:
    validate_payload_safety(contract)
    if contract.get("schema") != CONTRACT_SCHEMA:
        raise ContractError("unsupported run contract schema")
    expected_sha = require_sha256(contract.get("contract_sha256"), "contract_sha256")
    actual_sha = sha256_bytes(
        canonical_bytes({key: value for key, value in contract.items() if key != "contract_sha256"})
    )
    if actual_sha != expected_sha:
        raise ContractError("run contract content hash mismatch")
    run_type = contract.get("run_type")
    if run_type not in {"production", "test-validation"}:
        raise ContractError("run contract has invalid run_type")
    expected_stage_names = set(active_stages(str(run_type)))
    stages = contract.get("stages")
    if not isinstance(stages, Mapping) or set(stages) != expected_stage_names:
        raise ContractError("run contract stage population does not match run_type")
    if run_type == "production" and contract.get("quality_routing") != "not_applicable":
        raise ContractError("production quality routing must be not_applicable")
    if run_type == "test-validation":
        if contract.get("quality_routing") not in {
            "compact-validation",
            "full-regression",
        }:
            raise ContractError("test-validation quality routing is invalid")
        if contract.get("change_flags") and contract.get("quality_routing") != "full-regression":
            raise ContractError("test-validation with contract changes requires full-regression")
    site = contract.get("site")
    if site not in MARKETPLACE_ROUTES:
        raise ContractError("run contract has invalid site")
    if contract.get("marketplace_route") != MARKETPLACE_ROUTES[str(site)]:
        raise ContractError("run contract marketplace route does not match site")
    if contract.get("parallel_waves") != PARALLEL_WAVES:
        raise ContractError("run contract parallel dispatch waves drifted")
    copy = json.loads(json.dumps(contract, ensure_ascii=False))
    compute_stage_keys(copy)
    for stage_name in expected_stage_names:
        if copy["stages"][stage_name]["stage_key"] != stages[stage_name].get("stage_key"):
            raise ContractError(f"{stage_name}: stage key mismatch")
    if check_current_rules:
        current = {item["id"]: item for item in rule_snapshot(load_rule_map())}
        recorded = {item["id"]: item for item in contract.get("rules", [])}
        if set(current) != set(recorded):
            raise ContractError("runtime rule population drifted")
        for rule_id, current_rule in current.items():
            recorded_rule = recorded[rule_id]
            if current_rule != recorded_rule:
                raise ContractError(f"{rule_id}: authoritative rule drifted")


def validate_preflight(preflight: Mapping[str, Any]) -> None:
    validate_payload_safety(preflight)
    if preflight.get("schema") != PREFLIGHT_SCHEMA:
        raise ContractError("unsupported source preflight schema")
    providers = preflight.get("providers")
    if not isinstance(providers, Mapping) or set(providers) != {
        "amazon",
        "sif",
        "sellersprite",
    }:
        raise ContractError("preflight must contain exactly amazon, sif and sellersprite")
    for provider, record in providers.items():
        if not isinstance(record, Mapping):
            raise ContractError(f"{provider}: preflight record must be an object")
        if record.get("status") not in PREFLIGHT_STATUSES:
            raise ContractError(f"{provider}: invalid preflight status")
        if "checked_at" not in record or not str(record["checked_at"]).strip():
            raise ContractError(f"{provider}: checked_at is required")


def validate_stage_status(
    status: Mapping[str, Any], contract: Mapping[str, Any], expected_stage: str
) -> None:
    validate_payload_safety(status)
    if status.get("schema") != STATUS_SCHEMA:
        raise ContractError("unsupported stage status schema")
    if status.get("stage") != expected_stage:
        raise ContractError(f"stage status is not for {expected_stage}")
    if expected_stage not in contract["stages"]:
        raise ContractError(f"{expected_stage} is not active for this run")
    if status.get("stage_key") != contract["stages"][expected_stage]["stage_key"]:
        raise ContractError(f"{expected_stage}: stage key drifted")
    if status.get("status") not in STAGE_STATUSES:
        raise ContractError(f"{expected_stage}: invalid status")
    if status.get("status") in COMPLETED_STATUSES:
        require_sha256(status.get("output_sha256"), "output_sha256")
        require_sha256(status.get("evidence_sha256"), "evidence_sha256")
        if not isinstance(status.get("population"), Mapping):
            raise ContractError(f"{expected_stage}: population lock is required")


def load_statuses(status_dir: Path) -> Dict[str, Mapping[str, Any]]:
    statuses: Dict[str, Mapping[str, Any]] = {}
    if not status_dir.is_dir():
        return statuses
    for path in sorted(status_dir.glob("*.json")):
        value = read_json(path)
        stage = value.get("stage") if isinstance(value, Mapping) else None
        if isinstance(stage, str):
            statuses[stage] = value
    return statuses


def ready_for_stage(
    contract: Mapping[str, Any], stage: str, status_dir: Path, preflight_path: Path | None
) -> Dict[str, Any]:
    verify_contract(contract)
    if stage not in contract["stages"]:
        raise ContractError(f"{stage} is not active for this run")
    statuses = load_statuses(status_dir)
    blocked_dependencies = []
    for dependency in contract["stages"][stage]["dependencies"]:
        status = statuses.get(dependency)
        if status is None:
            blocked_dependencies.append({"stage": dependency, "reason": "missing_status"})
            continue
        try:
            validate_stage_status(status, contract, dependency)
        except ContractError as exc:
            blocked_dependencies.append({"stage": dependency, "reason": str(exc)})
            continue
        if status["status"] not in COMPLETED_STATUSES:
            blocked_dependencies.append(
                {"stage": dependency, "reason": f"status={status['status']}"}
            )
    preflight_result = "not_required"
    provider = SOURCE_PREFLIGHT.get(stage)
    if provider:
        if preflight_path is None:
            preflight_result = "missing"
        else:
            preflight = read_json(preflight_path)
            validate_preflight(preflight)
            preflight_result = preflight["providers"][provider]["status"]
    ready = not blocked_dependencies and preflight_result in {
        "not_required",
        "authenticated",
    }
    return {
        "stage": stage,
        "ready": ready,
        "blocked_dependencies": blocked_dependencies,
        "preflight": preflight_result,
    }


def descendants(stage: str, run_type: str) -> List[str]:
    if stage not in active_stages(run_type):
        raise ContractError(f"{stage} is not active for run_type={run_type}")
    result = set()
    changed = True
    while changed:
        changed = False
        for candidate in active_stages(run_type):
            deps = set(STAGE_GRAPH[candidate])
            if stage in deps or deps & result:
                if candidate not in result:
                    result.add(candidate)
                    changed = True
    return [item for item in active_stages(run_type) if item in result]


def create_status(args: argparse.Namespace) -> Dict[str, Any]:
    contract = read_json(Path(args.contract))
    verify_contract(contract)
    if args.stage not in contract["stages"]:
        raise ContractError(f"{args.stage} is not active for this run")
    population = read_json(Path(args.population))
    if not isinstance(population, Mapping):
        raise ContractError("population JSON must be an object")
    status = {
        "schema": STATUS_SCHEMA,
        "stage": args.stage,
        "stage_key": contract["stages"][args.stage]["stage_key"],
        "executor_version": contract["stages"][args.stage]["executor_version"],
        "status": args.status,
        "output_sha256": require_sha256(args.output_sha256, "output_sha256"),
        "evidence_sha256": require_sha256(args.evidence_sha256, "evidence_sha256"),
        "population": dict(population),
    }
    validate_stage_status(status, contract, args.stage)
    return status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="build a locked run contract")
    build.add_argument("--spec", required=True)
    build.add_argument("--out", required=True)

    verify = subparsers.add_parser("verify", help="verify a run contract and current rules")
    verify.add_argument("--contract", required=True)

    preflight = subparsers.add_parser("verify-preflight", help="verify a source preflight file")
    preflight.add_argument("--preflight", required=True)

    ready = subparsers.add_parser("ready", help="check whether one stage may start")
    ready.add_argument("--contract", required=True)
    ready.add_argument("--stage", required=True, choices=sorted(STAGE_GRAPH))
    ready.add_argument("--status-dir", required=True)
    ready.add_argument("--preflight")

    resume = subparsers.add_parser("resume", help="verify exact content-addressed reuse")
    resume.add_argument("--contract", required=True)
    resume.add_argument("--stage", required=True, choices=sorted(STAGE_GRAPH))
    resume.add_argument("--status", required=True)

    impact = subparsers.add_parser("impact", help="show only downstream stages blocked by failure")
    impact.add_argument("--stage", required=True, choices=sorted(STAGE_GRAPH))
    impact.add_argument(
        "--run-type", required=True, choices=["production", "test-validation"]
    )

    make_status = subparsers.add_parser("make-status", help="write a completed stage status")
    make_status.add_argument("--contract", required=True)
    make_status.add_argument("--stage", required=True, choices=sorted(STAGE_GRAPH))
    make_status.add_argument("--status", required=True, choices=sorted(COMPLETED_STATUSES))
    make_status.add_argument("--output-sha256", required=True)
    make_status.add_argument("--evidence-sha256", required=True)
    make_status.add_argument("--population", required=True)
    make_status.add_argument("--out", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "build":
            contract = build_contract(read_json(Path(args.spec)))
            write_json(Path(args.out), contract)
            print(json.dumps({"status": "pass", "contract_sha256": contract["contract_sha256"]}))
        elif args.command == "verify":
            verify_contract(read_json(Path(args.contract)))
            print(json.dumps({"status": "pass"}))
        elif args.command == "verify-preflight":
            validate_preflight(read_json(Path(args.preflight)))
            print(json.dumps({"status": "pass"}))
        elif args.command == "ready":
            result = ready_for_stage(
                read_json(Path(args.contract)),
                args.stage,
                Path(args.status_dir),
                Path(args.preflight) if args.preflight else None,
            )
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 0 if result["ready"] else 1
        elif args.command == "resume":
            contract = read_json(Path(args.contract))
            verify_contract(contract)
            status = read_json(Path(args.status))
            validate_stage_status(status, contract, args.stage)
            if status["status"] not in COMPLETED_STATUSES:
                raise ContractError(f"{args.stage}: status is not reusable")
            print(json.dumps({"status": "pass", "resume": True, "stage": args.stage}))
        elif args.command == "impact":
            print(
                json.dumps(
                    {
                        "failed_stage": args.stage,
                        "blocked_downstream": descendants(args.stage, args.run_type),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        elif args.command == "make-status":
            status = create_status(args)
            write_json(Path(args.out), status)
            print(json.dumps({"status": "pass", "stage": args.stage}))
        return 0
    except ContractError as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
