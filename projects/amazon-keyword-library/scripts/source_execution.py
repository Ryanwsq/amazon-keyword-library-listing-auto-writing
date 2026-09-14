#!/usr/bin/env python3
"""Read-only source execution checks; no browser, credentials or business judgment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import posixpath
import xml.etree.ElementTree as ET
import zipfile

import runtime_contract as runtime

QUERY_SCHEMA = "amazon-keyword-source-query/v1"
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def require(ok, message):
    if not ok:
        raise runtime.ContractError(message)


def verify_record(record):
    path = Path(record["path"]).resolve(strict=True)
    require(path.is_file() and str(path) == record["path"], "noncanonical evidence file")
    require(runtime.sha256_file(path) == record["sha256"], "source evidence hash drift")
    return path


def validate_query_lock(lock, run_id, marketplace, stage):
    require(lock.get("schema") == QUERY_SCHEMA, "source query schema missing")
    require(lock.get("run_id") == run_id and lock.get("marketplace") == marketplace,
            "source query Run/marketplace mismatch")
    require(lock.get("source_provider") == {"sif": "SIF", "sellersprite": "SellerSprite",
            "amazon-autocomplete": "Amazon"}[stage], "source provider mismatch")
    queries = lock.get("queries")
    require(isinstance(queries, list) and bool(queries)
            and all(isinstance(q, str) and q.strip() for q in queries)
            and len(set(queries)) == len(queries), "explicit unique query population required")
    require(isinstance(lock.get("filters"), dict), "explicit query filters required")
    require(lock.get("entry_type") in {"web", "mcp"}, "explicit source entry type required")
    require(stage != "amazon-autocomplete" or lock["entry_type"] == "web", "autocomplete has no API fallback")
    if stage in {"sif", "sellersprite"}:
        period = lock.get("query_period", {})
        require(period.get("kind") == "rolling-30-days", "query period must be rolling recent 30 days")
        require(bool(period.get("source_label")), "provider period label required")
        require(not period.get("calendar_month"), "rolling period is not a calendar month")
    if stage == "sif":
        require(len(queries) <= 5 and lock.get("limit_per_asin") == 300,
                "SIF approved population/300 limit mismatch")
    elif stage == "sellersprite":
        require(len(queries) <= 2, "SellerSprite needs one or two locked seeds")
    return {"status": "query_lock_valid", "queries": len(queries)}


def sif_fallback(proof):
    """Legacy locked web-first runs only; never used to admit a new dispatch."""
    for key in ("run_id", "task_id", "host"):
        require(isinstance(proof.get(key), str) and bool(proof[key].strip()),
                "SIF fallback Run/Task/host identity required")
    require(proof.get("source_provider") == "SIF" and proof.get("mcp_authenticated") is True,
            "same-provider authenticated SIF MCP required")
    require(proof.get("reason") in {"user_cannot_login", "authenticated_export_failed"},
            "missing SIF fallback reason")
    for key in ("authorization", "failure_evidence", "authentication_evidence"):
        verify_record(proof[key])
    authentication = runtime.read_json(Path(proof["authentication_evidence"]["path"]))
    fields = {"schema", "run_id", "task_id", "host", "provider", "entry_type", "authenticated"}
    require(isinstance(authentication, dict) and fields <= set(authentication)
            and set(authentication) <= fields | {"checked_at"},
            "MCP authentication evidence must contain only non-secret identity/status fields")
    require(authentication["schema"] == "amazon-keyword-mcp-authentication/v1"
            and authentication["provider"] == "SIF" and authentication["entry_type"] == "mcp"
            and authentication["authenticated"] is True,
            "SIF MCP authentication evidence not authenticated")
    require(all(authentication[key] == proof[key] for key in ("run_id", "task_id", "host")),
            "SIF authentication evidence Run/Task/host mismatch")
    require(proof.get("user_approved") is True, "explicit SIF fallback approval required")
    if proof["reason"] == "authenticated_export_failed":
        require(proof.get("web_authenticated") is True, "export failure is not login failure")
    return {"entry_type": "user_approved_same_provider_mcp", "business_complete": False}


def sif_source_access(proof, query_path):
    """Bind MCP-first access or bounded same-provider web fallback; no live auth."""
    common = {"schema", "run_id", "task_id", "host", "source_provider", "entry_type",
              "query_lock_sha256", "authentication_evidence"}
    fallback = {"reason", "primary_query_lock", "mcp_failure_evidence", "completed_asins"}
    entry = proof.get("entry_type")
    require(entry in {"mcp", "web"}, "invalid SIF entry type")
    require(set(proof) == common | (fallback if entry == "web" else set()),
            "SIF source access requires only the non-secret entry-specific fields")
    require(proof["schema"] == "amazon-keyword-sif-source-access/v1"
            and proof["source_provider"] == "SIF", "invalid SIF source access schema/provider")
    for key in ("run_id", "task_id", "host"):
        require(isinstance(proof[key], str) and bool(proof[key].strip()), "SIF Run/Task/host identity required")
    query = runtime.read_json(Path(query_path))
    require(proof["query_lock_sha256"] == runtime.sha256_file(Path(query_path)), "SIF query lock hash drift")
    validate_query_lock(query, proof["run_id"], query.get("marketplace"), "sif")
    require(query.get("marketplace") in runtime.MARKETPLACE_ROUTES
            and query.get("source_policy") == runtime.SIF_SOURCE_POLICY
            and query["entry_type"] == entry, "SIF MCP-first query policy/entry mismatch")
    authentication = runtime.read_json(verify_record(proof["authentication_evidence"]))
    auth_fields = {"schema", "run_id", "task_id", "host", "provider", "entry_type", "authenticated"}
    require(isinstance(authentication, dict) and auth_fields <= set(authentication)
            and set(authentication) <= auth_fields | {"checked_at"},
            "authentication evidence must contain only non-secret identity/status fields")
    require(authentication["schema"] == f"amazon-keyword-{entry}-authentication/v1"
            and authentication["provider"] == "SIF" and authentication["entry_type"] == entry
            and authentication["authenticated"] is True, "SIF current entry not authenticated")
    require(all(authentication[key] == proof[key] for key in ("run_id", "task_id", "host")),
            "SIF authentication evidence Run/Task/host mismatch")
    if entry == "web":
        require(proof["reason"] in {"mcp_unavailable", "mcp_incomplete"}, "SIF MCP failure reason not eligible for web fallback")
        primary_path = verify_record(proof["primary_query_lock"])
        primary = runtime.read_json(primary_path)
        validate_query_lock(primary, proof["run_id"], query["marketplace"], "sif")
        require(primary.get("source_policy") == runtime.SIF_SOURCE_POLICY
                and primary["entry_type"] == "mcp", "web fallback requires the original MCP query lock")
        # Compare every other query field, including provider-specific parameters and dates.
        require({k: v for k, v in primary.items() if k not in {"queries", "entry_type"}} ==
                {k: v for k, v in query.items() if k not in {"queries", "entry_type"}},
                "web fallback must preserve the same locked query")
        completed = proof["completed_asins"]
        require(isinstance(completed, list) and all(isinstance(a, str) for a in completed)
                and len(set(completed)) == len(completed) and set(completed) <= set(primary["queries"]),
                "invalid completed ASIN population")
        require(query["queries"] == [a for a in primary["queries"] if a not in completed],
                "web fallback must contain exactly unfinished ASINs in original order")
        failure = runtime.read_json(verify_record(proof["mcp_failure_evidence"]))
        failure_fields = {"schema", "run_id", "task_id", "host", "provider", "entry_type", "reason",
                          "query_lock_sha256", "completed_asins", "pending_asins", "evidence"}
        require(isinstance(failure, dict) and failure_fields <= set(failure)
                and set(failure) <= failure_fields | {"checked_at"}, "invalid non-secret SIF MCP failure evidence")
        require(failure["schema"] == "amazon-keyword-sif-mcp-failure/v1"
                and failure["provider"] == "SIF" and failure["entry_type"] == "mcp"
                and all(failure[k] == proof[k] for k in ("run_id", "task_id", "host", "reason", "completed_asins"))
                and failure["query_lock_sha256"] == proof["primary_query_lock"]["sha256"]
                and failure["pending_asins"] == query["queries"], "SIF MCP failure identity/query/population mismatch")
        require(isinstance(failure["evidence"], list) and bool(failure["evidence"]), "persisted MCP failure evidence required")
        for record in failure["evidence"]:
            verify_record(record)
    return {"status": f"authenticated_{entry}", "entry_type": entry, "business_complete": False}


def mcp_first_source_access(proof, query_path, stage):
    """New runs: only a persisted explicit MCP error admits website fallback."""
    provider = {"sif": "SIF", "sellersprite": "SellerSprite"}[stage]
    query = runtime.read_json(Path(query_path))
    validate_query_lock(query, proof.get("run_id"), query.get("marketplace"), stage)
    entry = query["entry_type"]
    common = {"schema", "run_id", "task_id", "host", "source_provider", "entry_type", "query_lock_sha256", "authentication_evidence"}
    extra = {"reason", "primary_query_lock", "mcp_error_evidence", "completed_queries", "login_notice"} if entry == "web" else set()
    require(set(proof) == common | extra and proof["schema"] == "amazon-keyword-source-access/v2",
            "source access v2 non-secret schema required")
    require(query.get("source_policy") == runtime.MCP_ERROR_ONLY_POLICY
            and query.get("marketplace") in runtime.MARKETPLACE_ROUTES
            and proof["source_provider"] == provider and proof["entry_type"] == entry,
            "current MCP-first error-only policy/provider/entry required")
    require(proof["query_lock_sha256"] == runtime.sha256_file(Path(query_path)), "query lock hash drift")
    identity = {key: proof[key] for key in ("run_id", "task_id", "host")}
    require(all(isinstance(v, str) and v.strip() for v in identity.values()), "current identity required")
    auth = runtime.read_json(verify_record(proof["authentication_evidence"]))
    expected = dict(identity, schema=f"amazon-keyword-{entry}-authentication/v1", provider=provider,
                    entry_type=entry, authenticated=True)
    require(set(auth) <= set(expected) | {"checked_at"} and auth.get("authenticated") is True and all(auth.get(k) == v for k, v in expected.items()),
            "current source entry authentication required")
    if entry == "web":
        require(proof["reason"] == "mcp_error", "only explicit MCP error allows website fallback")
        primary = runtime.read_json(verify_record(proof["primary_query_lock"]))
        validate_query_lock(primary, proof["run_id"], query["marketplace"], stage)
        require(primary["entry_type"] == "mcp" and
                {k:v for k,v in primary.items() if k not in {"entry_type", "queries"}} ==
                {k:v for k,v in query.items() if k not in {"entry_type", "queries"}}, "fallback query settings changed")
        completed = proof["completed_queries"]
        require(isinstance(completed, list) and all(isinstance(q,str) for q in completed)
                and len(set(completed)) == len(completed) and set(completed) <= set(primary["queries"]),
                "invalid completed query population")
        require(query["queries"] == [q for q in primary["queries"] if q not in completed],
                "fallback may query only unfinished population in original order")
        error = runtime.read_json(verify_record(proof["mcp_error_evidence"]))
        expected_error = dict(identity, schema="amazon-keyword-mcp-error/v1", provider=provider, entry_type="mcp",
                              is_error=True, query_lock_sha256=proof["primary_query_lock"]["sha256"])
        require(set(error) <= set(expected_error) | {"error_code", "evidence", "checked_at"}
                and error.get("is_error") is True and all(error.get(k) == v for k,v in expected_error.items())
                and isinstance(error.get("error_code"),str) and error["error_code"].strip(),
                "persisted explicit MCP error identity/code required; gaps or zero are not errors")
        require(isinstance(error.get("evidence"),list) and bool(error["evidence"]), "raw MCP error evidence required")
        for lock in error["evidence"]:
            verify_record(lock)
        notice = runtime.read_json(verify_record(proof["login_notice"]))
        expected_notice = dict(identity, schema="amazon-keyword-web-login-notice/v1", provider=provider,
                               login_requested=True)
        require(set(notice) <= set(expected_notice) | {"checked_at"} and notice.get("login_requested") is True and
                all(notice.get(k) == v for k,v in expected_notice.items()), "user website login request evidence required")
    return {"status": f"authenticated_{entry}", "entry_type": entry, "business_complete": False}


def login_recovery_action(observation):
    # Closed non-secret schema: never accept a password value or account text.
    allowed = {"provider", "previously_authenticated", "login_page", "both_fields_autofilled",
               "attempts", "challenge", "wrong_account", "wrong_marketplace"}
    require(set(observation) == allowed, "only non-secret login observations are allowed")
    require(observation["provider"] in {"SIF", "SellerSprite"}, "Amazon login remains manual")
    require(type(observation["attempts"]) is int and observation["attempts"] >= 0, "invalid attempts")
    for key in allowed - {"provider", "attempts"}:
        require(type(observation[key]) is bool, "login observations must be booleans")
    eligible = (observation["previously_authenticated"] and observation["login_page"]
                and observation["both_fields_autofilled"] and observation["attempts"] == 0
                and not any(observation[k] for k in ("challenge", "wrong_account", "wrong_marketplace")))
    return {"action": "click_login_once_then_reverify" if eligible else "awaiting_login",
            "may_read_or_fill_credentials": False, "business_authorized": False}


def autocomplete_capture(proof, query_lock):
    require(proof.get("run_id") == query_lock["run_id"], "autocomplete proof Run mismatch")
    records = proof.get("records", [])
    expected = query_lock["queries"]
    require(len(records) == len(expected) and [r.get("input") for r in records] == expected,
            "durable autocomplete matrix population incomplete")
    events = 0
    for item in records:
        path = verify_record(item["capture"])
        record = runtime.read_json(path)
        require(record.get("run_id") == proof["run_id"] and record.get("input") == item["input"],
                "autocomplete capture identity mismatch")
        require(record.get("status") in {"success", "no_suggestions"},
                "failed or unexecuted matrix cell cannot close source")
        suggestions = record.get("suggestions")
        require(isinstance(suggestions, list), "durable suggestions missing")
        require((record["status"] == "no_suggestions") == (len(suggestions) == 0),
                "no-suggestions and captured rows conflict")
        require(bool(record.get("visible_evidence")), "visible evidence missing")
        for evidence in record["visible_evidence"]:
            verify_record(evidence)
        events += len(suggestions)
    return {"status": "durable_capture_complete", "inputs": len(records), "events": events,
            "semantic_visibility_review": "still_required"}


def exported_rows(path, sheet_name, keyword_column, header_row):
    """Count persisted official XLSX rows, not a page total or declared count."""
    require(type(header_row) is int and header_row >= 1, "invalid header row")
    require(isinstance(keyword_column, str) and keyword_column.isalpha(), "invalid keyword column")
    with zipfile.ZipFile(path) as book:
        workbook = ET.fromstring(book.read("xl/workbook.xml"))
        relationship_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        sheets = [s for s in workbook.findall("s:sheets/s:sheet", NS) if s.get("name") == sheet_name]
        require(len(sheets) == 1, "official export sheet missing")
        rid = sheets[0].get("{" + relationship_ns + "}id")
        rels = ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))
        target = next((r.get("Target") for r in rels if r.get("Id") == rid), None)
        require(bool(target), "official export sheet relationship missing")
        part = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
        rows = ET.fromstring(book.read(part)).findall("s:sheetData/s:row", NS)
        strings = []
        if "xl/sharedStrings.xml" in book.namelist():
            strings = ["".join(si.itertext()) for si in ET.fromstring(book.read("xl/sharedStrings.xml"))]
        def nonempty(cell):
            if cell.get("t") == "inlineStr":
                inline = cell.find("s:is", NS)
                return inline is not None and bool("".join(inline.itertext()).strip())
            value = cell.find("s:v", NS)
            text = "" if value is None else value.text or ""
            if cell.get("t") == "s" and text:
                text = strings[int(text)]
            return bool(text.strip())
        return sum(1 for row in rows if int(row.get("r", "0")) > header_row
                   and any(c.get("r", "").rstrip("0123456789") == keyword_column
                           and nonempty(c)
                           for c in row.findall("s:c", NS)))


def export_population(proof):
    path = verify_record(proof["official_export"])
    actual = exported_rows(path, proof["sheet"], proof["keyword_column"], proof["header_row"])
    require(actual == proof.get("actual_rows"), "actual rows do not match persisted export")
    declared = proof.get("page_declared_total")
    require(type(declared) is int and declared >= 0, "page declared total required")
    difference = declared - actual
    resolved_drift = False
    if difference:
        require(proof.get("population_gap") == difference, "page/export population gap must remain explicit")
        resolution = proof.get("coverage_resolution")
        if resolution is not None:
            require(resolution.get("kind") == "verified_declared_total_drift"
                    and resolution.get("complete_export_verified") is True,
                    "an export limit alone is not completeness proof")
            require(bool(resolution.get("evidence")), "declared-total drift needs source evidence")
            for record in resolution["evidence"]:
                verify_record(record)
            resolved_drift = True
        require(proof.get("completeness") == ("complete" if resolved_drift else "partial"),
                "unresolved export gap cannot be complete")
    else:
        require(proof.get("completeness") == "complete", "export completeness not closed")
    return {"actual_rows": actual, "page_declared_total": declared, "population_gap": difference,
            "status": "partial" if difference and not resolved_drift else "complete",
            "cap_reason": "not_inferred", "source_resolution_review": "still_required" if resolved_drift else "not_applicable"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["source-access", "sif-source-access", "sif-fallback", "login-recovery", "autocomplete", "export-population"])
    parser.add_argument("--stage", choices=["sif", "sellersprite"])
    parser.add_argument("--input", required=True)
    parser.add_argument("--query-lock")
    args = parser.parse_args()
    try:
        proof = runtime.read_json(Path(args.input))
        action = {"sif-fallback": sif_fallback, "login-recovery": login_recovery_action,
                  "export-population": export_population}
        if args.command == "source-access":
            require(args.query_lock and args.stage, "query lock and source stage required")
            result = mcp_first_source_access(proof, Path(args.query_lock), args.stage)
        elif args.command == "sif-source-access":
            require(args.query_lock, "query lock required")
            result = sif_source_access(proof, Path(args.query_lock))
        elif args.command == "autocomplete":
            require(args.query_lock, "query lock required")
            result = autocomplete_capture(proof, runtime.read_json(Path(args.query_lock)))
        else:
            result = action[args.command](proof)
        print(json.dumps(result, ensure_ascii=False))
    except (runtime.ContractError, OSError, ValueError, KeyError, IndexError, TypeError, ET.ParseError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
