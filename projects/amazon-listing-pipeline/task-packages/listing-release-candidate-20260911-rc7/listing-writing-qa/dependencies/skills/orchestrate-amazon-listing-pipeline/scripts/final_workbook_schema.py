#!/usr/bin/env python3
"""Fixed layout preflight, before render/source transfer and again on sealed XLSX.

No business decisions, workbook writes, source-copy claims, or independent QA.
The JSON scaffold is consumed by the owning spreadsheet builder, not a second schema.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from xml.etree import ElementTree as ET

from validate_input import XlsxReader

CONTRACT = Path(__file__).resolve().parents[1] / "references" / "final-workbook-schema.json"


def specifications(phase):
    if phase not in {"base", "final"}:
        raise ValueError("phase must be base or final")
    return [item for item in json.loads(CONTRACT.read_text())["sheets"]
            if phase == "final" or not item.get("preserved")]


def scaffold(phase):
    return {item["name"]: [item["headers"] + ([item["optional_last"]] if item.get("optional_last") else [])]
            if item["headers"] else [] for item in specifications(phase)}


def check_rows(sheets, phase="final"):
    specs = specifications(phase)
    errors = []
    if list(sheets) != [item["name"] for item in specs]:
        errors.append("Sheet names/order differ from fixed contract")
    for item in specs:
        name, expected = item["name"], item["headers"]
        if expected is None or name not in sheets:
            continue  # Open-layout sheets and preserved sources have their own owner contracts.
        rows = sheets[name]
        # Fixed table header may follow a title/summary; never accept a header hidden in body data.
        candidates = [r for r in rows[:10] if r and r[0] == expected[0]]
        if len(candidates) != 1:
            errors.append(f"{name}: one identifiable table header required in first 10 rows")
            continue
        actual = list(candidates[0])
        while actual and actual[-1] in (None, ""):
            actual.pop()
        if actual[:len(expected)] != expected:
            errors.append(f"{name}: missing/reordered/renamed fixed columns")
        elif not item.get("allow_audit_columns"):
            extra = actual[len(expected):]
            if extra and extra != ([item["optional_last"]] if item.get("optional_last") else []):
                errors.append(f"{name}: undeclared columns")
    return errors


def check_xlsx(path, phase="final"):
    path = Path(path)
    contract = json.loads(CONTRACT.read_text())
    errors = []
    if phase == "final" and path.name != contract["filename"]:
        errors.append("Final filename differs from fixed contract")
    reader = XlsxReader(path)
    try:
        if reader.archive.testzip():
            errors.append("XLSX ZIP integrity failure")
        sheets = {name: reader.rows(name, preserve_row_numbers=True)[0] for name in reader.sheets}
        errors.extend(check_rows(sheets, phase))
    finally:
        reader.close()
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["base", "final"], default="final")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--xlsx", type=Path)
    group.add_argument("--rows-json", type=Path, help="Ordered sheet-name to row-matrix object")
    group.add_argument("--scaffold", action="store_true")
    args = parser.parse_args()
    if args.scaffold:
        print(json.dumps(scaffold(args.phase), ensure_ascii=False, indent=2))
        return 0
    try:
        errors = check_xlsx(args.xlsx, args.phase) if args.xlsx else check_rows(
            json.loads(args.rows_json.read_text()), args.phase)
        result = {"scope": "fixed_layout_only", "phase": args.phase, "errors": errors,
                  "valid": not errors, "business_ready": False, "p1": False,
                  "schema_sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
                  "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        if args.xlsx:
            result["workbook_sha256"] = hashlib.sha256(args.xlsx.read_bytes()).hexdigest()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if errors else 0
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, ET.ParseError) as exc:
        print(json.dumps({"valid": False, "scope": "fixed_layout_only", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
