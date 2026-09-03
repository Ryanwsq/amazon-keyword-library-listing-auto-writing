#!/usr/bin/env python3
"""Audit trend-workbook formulas and charts through OOXML relationships.

The audit deliberately distinguishes a business-contract failure from an
auditor failure. If the package or manifest declares charts/formulas but the
relationship traversal reports zero, the result is 'auditor_failure' rather
than a false business failure or a silent pass.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET


PERCENT_NUMFMT_IDS = {9, 10}
MONTH_ROLE_TOKENS = ("月度", "monthly")
QUARTER_ROLE_TOKENS = ("季度", "quarterly")
ACTUAL_VOLUME_TOKENS = ("实际搜索量", "search volume")
PERCENT_TOKENS = (
    "环比",
    "同比",
    "mom",
    "yoy",
    "qoq",
    "percent",
    "percentage",
    "%",
)
MONTH_LABEL_RE = re.compile(r"^\d{4}[-/]?(?:0[1-9]|1[0-2])$")
QUARTER_LABEL_RE = re.compile(r"^\d{4}\s*Q[1-4]$", re.IGNORECASE)
CELL_RE = re.compile(r"^\$?([A-Z]{1,3})\$?(\d+)$")
INTERNAL_RANGE_RE = re.compile(
    r"^(?:'((?:[^']|'')+)'|([^!]+))!"
    r"(\$?[A-Z]{1,3}\$?\d+)"
    r"(?::(\$?[A-Z]{1,3}\$?\d+))?$"
)


class AuditInputError(RuntimeError):
    """The input is unreadable or not an OOXML workbook."""


@dataclass(frozen=True)
class Relationship:
    rel_id: str
    rel_type: str
    target: str
    target_mode: str | None


@dataclass(frozen=True)
class CellRange:
    sheet_name: str
    start_col: int
    start_row: int
    end_col: int
    end_row: int


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":", 1)[-1]


def iter_local(root: ET.Element, name: str) -> Iterable[ET.Element]:
    for element in root.iter():
        if local_name(element.tag) == name:
            yield element


def child_local(element: ET.Element, name: str) -> ET.Element | None:
    for child in element:
        if local_name(child.tag) == name:
            return child
    return None


def descendants_local(element: ET.Element, name: str) -> list[ET.Element]:
    return [item for item in element.iter() if local_name(item.tag) == name]


def parse_xml(raw: bytes, part: str) -> ET.Element:
    try:
        return ET.fromstring(raw)
    except ET.ParseError as exc:
        raise AuditInputError(f"invalid XML part {part}: {exc}") from exc


def relationship_part(source_part: str) -> str:
    directory = posixpath.dirname(source_part)
    basename = posixpath.basename(source_part)
    return posixpath.join(directory, "_rels", basename + ".rels")


def resolve_target(source_part: str, target: str) -> str:
    normalized_target = target.replace("\\", "/")
    if normalized_target.startswith("/"):
        resolved = posixpath.normpath(normalized_target.lstrip("/"))
    else:
        resolved = posixpath.normpath(
            posixpath.join(posixpath.dirname(source_part), normalized_target)
        )
    if resolved == ".." or resolved.startswith("../"):
        raise AuditInputError(
            f"relationship target escapes package root: {source_part} -> {target}"
        )
    return resolved


def read_relationships(
    archive: zipfile.ZipFile, source_part: str
) -> tuple[list[Relationship], str | None]:
    rel_part = relationship_part(source_part)
    if rel_part not in archive.namelist():
        return [], None
    root = parse_xml(archive.read(rel_part), rel_part)
    relationships: list[Relationship] = []
    for element in root.iter():
        if local_name(element.tag) != "Relationship":
            continue
        relationships.append(
            Relationship(
                rel_id=element.attrib.get("Id", ""),
                rel_type=element.attrib.get("Type", ""),
                target=element.attrib.get("Target", ""),
                target_mode=element.attrib.get("TargetMode"),
            )
        )
    return relationships, rel_part


def relationship_map(
    relationships: Iterable[Relationship],
) -> dict[str, Relationship]:
    return {relationship.rel_id: relationship for relationship in relationships}


def relationship_id(element: ET.Element) -> str | None:
    for attribute, value in element.attrib.items():
        if local_name(attribute).lower() == "id":
            return value
    return None


def is_internal(relationship: Relationship) -> bool:
    return (relationship.target_mode or "").lower() != "external"


def rel_type_endswith(relationship: Relationship, suffix: str) -> bool:
    return relationship.rel_type.rstrip("/").lower().endswith("/" + suffix.lower())


def column_index(column: str) -> int:
    value = 0
    for char in column:
        value = value * 26 + ord(char) - ord("A") + 1
    return value


def parse_cell(cell: str) -> tuple[int, int]:
    match = CELL_RE.match(cell.upper())
    if not match:
        raise ValueError(f"unsupported cell reference: {cell}")
    return column_index(match.group(1)), int(match.group(2))


def parse_internal_range(formula: str, default_sheet: str | None = None) -> CellRange:
    candidate = formula.strip()
    if candidate.startswith("="):
        candidate = candidate[1:]
    if "[" in candidate or "]" in candidate:
        raise ValueError(f"external workbook reference is not allowed: {formula}")
    match = INTERNAL_RANGE_RE.match(candidate)
    if not match and default_sheet:
        bare_match = re.match(
            r"^(\$?[A-Z]{1,3}\$?\d+)(?::(\$?[A-Z]{1,3}\$?\d+))?$",
            candidate,
        )
        if bare_match:
            match_groups = (
                default_sheet,
                None,
                bare_match.group(1),
                bare_match.group(2),
            )
        else:
            match_groups = None
    elif match:
        match_groups = match.groups()
    else:
        match_groups = None
    if not match_groups:
        raise ValueError(f"unsupported internal range formula: {formula}")
    quoted_sheet, bare_sheet, start_cell, end_cell = match_groups
    sheet_name = (quoted_sheet or bare_sheet or default_sheet or "").replace("''", "'")
    start_col, start_row = parse_cell(start_cell)
    end_col, end_row = parse_cell(end_cell or start_cell)
    return CellRange(
        sheet_name=sheet_name,
        start_col=min(start_col, end_col),
        start_row=min(start_row, end_row),
        end_col=max(start_col, end_col),
        end_row=max(start_row, end_row),
    )


def range_contains(container: CellRange, candidate: CellRange) -> bool:
    return (
        container.sheet_name == candidate.sheet_name
        and container.start_col <= candidate.start_col
        and container.start_row <= candidate.start_row
        and container.end_col >= candidate.end_col
        and container.end_row >= candidate.end_row
    )


def range_cells(cell_range: CellRange, limit: int = 100_000) -> Iterable[str]:
    count = (
        (cell_range.end_col - cell_range.start_col + 1)
        * (cell_range.end_row - cell_range.start_row + 1)
    )
    if count > limit:
        raise ValueError(f"range expands to {count} cells, above audit limit")
    for row in range(cell_range.start_row, cell_range.end_row + 1):
        for column in range(cell_range.start_col, cell_range.end_col + 1):
            value = column
            label = ""
            while value:
                value, remainder = divmod(value - 1, 26)
                label = chr(ord("A") + remainder) + label
            yield f"{label}{row}"


def normalized_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def has_token(value: Any, tokens: Iterable[str]) -> bool:
    normalized = normalized_text(value)
    return any(token.lower() in normalized for token in tokens)


def cached_values(element: ET.Element | None) -> list[str]:
    if element is None:
        return []
    values: list[str] = []
    for point in descendants_local(element, "pt"):
        value = child_local(point, "v")
        if value is not None and value.text is not None:
            values.append(value.text)
    return values


def first_formula(element: ET.Element | None) -> str | None:
    if element is None:
        return None
    for formula in descendants_local(element, "f"):
        if formula.text:
            return formula.text
    return None


def extract_chart_title(root: ET.Element) -> str:
    title = next(iter_local(root, "title"), None)
    if title is None:
        return ""
    texts = [
        element.text.strip()
        for element in descendants_local(title, "t")
        if element.text and element.text.strip()
    ]
    if not texts:
        texts = [
            element.text.strip()
            for element in descendants_local(title, "v")
            if element.text and element.text.strip()
        ]
    return " ".join(texts)


def extract_series_name(series: ET.Element) -> str:
    tx = child_local(series, "tx")
    if tx is None:
        return ""
    direct_value = child_local(tx, "v")
    if direct_value is not None and direct_value.text:
        return direct_value.text
    cached = cached_values(tx)
    if cached:
        return cached[0]
    return first_formula(tx) or ""


def series_formula(series: ET.Element, container_names: tuple[str, ...]) -> str | None:
    for container_name in container_names:
        container = child_local(series, container_name)
        formula = first_formula(container)
        if formula:
            return formula
    return None


def series_categories(series: ET.Element) -> list[str]:
    for container_name in ("cat", "xVal"):
        container = child_local(series, container_name)
        cached = cached_values(container)
        if cached:
            return cached
    return []


def infer_chart_role(title: str, category_values: list[str]) -> tuple[str | None, list[str]]:
    evidence: list[str] = []
    title_month = has_token(title, MONTH_ROLE_TOKENS)
    title_quarter = has_token(title, QUARTER_ROLE_TOKENS)
    if title_month:
        evidence.append("title:monthly")
    if title_quarter:
        evidence.append("title:quarterly")
    labels = [normalized_text(value) for value in category_values if value is not None]
    month_labels = sum(bool(MONTH_LABEL_RE.match(value)) for value in labels)
    quarter_labels = sum(bool(QUARTER_LABEL_RE.match(value)) for value in labels)
    if labels and month_labels == len(labels):
        evidence.append("categories:monthly")
    if labels and quarter_labels == len(labels):
        evidence.append("categories:quarterly")
    month_evidence = title_month or bool(labels and month_labels == len(labels))
    quarter_evidence = title_quarter or bool(labels and quarter_labels == len(labels))
    if month_evidence and not quarter_evidence:
        return "monthly", evidence
    if quarter_evidence and not month_evidence:
        return "quarterly", evidence
    return None, evidence


def parse_styles(archive: zipfile.ZipFile) -> tuple[dict[int, str], list[int]]:
    if "xl/styles.xml" not in archive.namelist():
        return {}, [0]
    root = parse_xml(archive.read("xl/styles.xml"), "xl/styles.xml")
    custom_formats: dict[int, str] = {}
    for num_fmt in iter_local(root, "numFmt"):
        try:
            custom_formats[int(num_fmt.attrib.get("numFmtId", "-1"))] = num_fmt.attrib.get(
                "formatCode", ""
            )
        except ValueError:
            continue
    cell_xfs = next(iter_local(root, "cellXfs"), None)
    style_num_fmt_ids: list[int] = []
    if cell_xfs is not None:
        for xf in cell_xfs:
            if local_name(xf.tag) != "xf":
                continue
            try:
                style_num_fmt_ids.append(int(xf.attrib.get("numFmtId", "0")))
            except ValueError:
                style_num_fmt_ids.append(0)
    return custom_formats, style_num_fmt_ids or [0]


def style_is_percent(
    style_index: int | None,
    custom_formats: dict[int, str],
    style_num_fmt_ids: list[int],
) -> bool:
    if style_index is None or style_index < 0 or style_index >= len(style_num_fmt_ids):
        return False
    num_fmt_id = style_num_fmt_ids[style_index]
    if num_fmt_id in PERCENT_NUMFMT_IDS:
        return True
    format_code = custom_formats.get(num_fmt_id, "")
    return "%" in format_code.replace(r"\%", "")


def parse_cells(sheet_root: ET.Element) -> dict[str, dict[str, Any]]:
    cells: dict[str, dict[str, Any]] = {}
    for cell in iter_local(sheet_root, "c"):
        reference = cell.attrib.get("r")
        if not reference:
            continue
        formula = child_local(cell, "f")
        value = child_local(cell, "v")
        try:
            style_index = int(cell.attrib.get("s", "0"))
        except ValueError:
            style_index = 0
        cells[reference.upper()] = {
            "formula": (formula.text or "") if formula is not None else None,
            "value": value.text if value is not None else None,
            "style_index": style_index,
        }
    return cells


def manifest_find_first(value: Any, keys: set[str]) -> Any:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in keys:
                return child
        for child in value.values():
            found = manifest_find_first(child, keys)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = manifest_find_first(child, keys)
            if found is not None:
                return found
    return None


def int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def chart_expectation(manifest: dict[str, Any] | None, role: str) -> dict[str, Any]:
    if not manifest:
        return {}
    candidate = manifest_find_first(
        manifest, {role, f"{role}_chart", f"{role}Chart"}
    )
    return candidate if isinstance(candidate, dict) else {}


def read_expectations(
    manifest: dict[str, Any] | None,
    expected_series_count: int | None,
    expected_formula_count: int | None,
) -> dict[str, Any]:
    chart_container = manifest_find_first(manifest, {"charts"}) if manifest else None
    chart_count = None
    if isinstance(chart_container, dict):
        chart_count = int_value(chart_container.get("count"))
    if chart_count is None and manifest:
        chart_count = int_value(
            manifest_find_first(manifest, {"chart_count", "expected_chart_count"})
        )
    formula_count = expected_formula_count
    if formula_count is None and manifest:
        formula_count = int_value(
            manifest_find_first(
                manifest,
                {
                    "actual_formula_count",
                    "expected_formula_count",
                    "formula_count",
                },
            )
        )
    population_count = expected_series_count
    if population_count is None and manifest:
        population = manifest_find_first(manifest, {"population"})
        if isinstance(population, dict):
            population_count = int_value(
                population.get("actual")
                or population.get("actual_count")
                or population.get("expected")
            )
        if population_count is None:
            population_count = int_value(
                manifest_find_first(
                    manifest,
                    {
                        "population_count",
                        "keyword_count",
                        "expected_series_count",
                    },
                )
            )
    roles = {}
    for role in ("monthly", "quarterly"):
        source = chart_expectation(manifest, role)
        roles[role] = {
            "series_count": int_value(
                source.get("series")
                or source.get("series_count")
                or source.get("theoretical_series_count")
            )
            or population_count,
            "percentage_series": int_value(
                source.get("percentage_series")
                if "percentage_series" in source
                else source.get("percentage_series_count")
            ),
            "metric": source.get("metric"),
            "source_range": source.get("source_range"),
        }
    return {
        "chart_count": chart_count,
        "formula_count": formula_count,
        "population_count": population_count,
        "roles": roles,
    }


def audit_workbook(
    workbook_path: Path,
    manifest: dict[str, Any] | None = None,
    *,
    expected_series_count: int | None = None,
    expected_formula_count: int | None = None,
) -> dict[str, Any]:
    expectations = read_expectations(
        manifest, expected_series_count, expected_formula_count
    )
    auditor_failures: list[str] = []
    business_failures: list[str] = []

    try:
        archive = zipfile.ZipFile(workbook_path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise AuditInputError(f"cannot open workbook as OOXML ZIP: {exc}") from exc

    with archive:
        names = set(archive.namelist())
        if "xl/workbook.xml" not in names:
            raise AuditInputError("missing xl/workbook.xml")
        workbook_root = parse_xml(archive.read("xl/workbook.xml"), "xl/workbook.xml")
        workbook_rels, workbook_rels_part = read_relationships(
            archive, "xl/workbook.xml"
        )
        workbook_rel_map = relationship_map(workbook_rels)
        custom_formats, style_num_fmt_ids = parse_styles(archive)

        package_worksheet_parts = sorted(
            name
            for name in names
            if re.match(r"^xl/worksheets/[^/]+\.xml$", name)
        )
        package_chart_parts = sorted(
            name
            for name in names
            if re.match(r"^xl/(?:drawings/)?charts/[^/]+\.xml$", name)
        )
        package_drawing_parts = sorted(
            name
            for name in names
            if re.match(r"^xl/drawings/[^/]+\.xml$", name)
        )
        formula_declaration_parts = sorted(
            name for name in names if name == "xl/calcChain.xml"
        )

        declared_sheets: list[dict[str, Any]] = []
        worksheet_names_by_part: dict[str, str] = {}
        for sheet in iter_local(workbook_root, "sheet"):
            sheet_name = sheet.attrib.get("name", "")
            rel_id = relationship_id(sheet)
            record: dict[str, Any] = {
                "name": sheet_name,
                "relationship_id": rel_id,
                "part": None,
            }
            if not rel_id or rel_id not in workbook_rel_map:
                auditor_failures.append(
                    f"worksheet {sheet_name!r} has no resolvable workbook relationship"
                )
            else:
                relationship = workbook_rel_map[rel_id]
                if not rel_type_endswith(relationship, "worksheet"):
                    auditor_failures.append(
                        f"workbook relationship {rel_id} for {sheet_name!r} is not a worksheet"
                    )
                elif not is_internal(relationship):
                    auditor_failures.append(
                        f"worksheet {sheet_name!r} unexpectedly uses an external target"
                    )
                else:
                    part = resolve_target("xl/workbook.xml", relationship.target)
                    record["part"] = part
                    worksheet_names_by_part[part] = sheet_name
                    if part not in names:
                        auditor_failures.append(
                            f"worksheet target is missing: {sheet_name!r} -> {part}"
                        )
            declared_sheets.append(record)

        worksheet_records: list[dict[str, Any]] = []
        cell_maps: dict[str, dict[str, dict[str, Any]]] = {}
        chart_links: dict[str, dict[str, Any]] = {}
        linked_drawing_parts: set[str] = set()
        chart_relationship_declarations = 0
        formula_count = 0

        for worksheet_part in package_worksheet_parts:
            sheet_name = worksheet_names_by_part.get(
                worksheet_part, f"<orphan:{worksheet_part}>"
            )
            sheet_root = parse_xml(archive.read(worksheet_part), worksheet_part)
            cells = parse_cells(sheet_root)
            cell_maps[sheet_name] = cells
            sheet_formula_count = sum(
                1 for cell in cells.values() if cell.get("formula") is not None
            )
            formula_count += sheet_formula_count
            sheet_rels, sheet_rels_part = read_relationships(archive, worksheet_part)
            sheet_rel_map = relationship_map(sheet_rels)
            drawing_ids = [
                relationship_id(element)
                for element in iter_local(sheet_root, "drawing")
                if relationship_id(element)
            ]
            drawing_parts: list[str] = []
            for drawing_id in drawing_ids:
                relationship = sheet_rel_map.get(drawing_id or "")
                if relationship is None:
                    auditor_failures.append(
                        f"{sheet_name!r} drawing {drawing_id!r} has no relationship"
                    )
                    continue
                if not rel_type_endswith(relationship, "drawing"):
                    auditor_failures.append(
                        f"{sheet_name!r} relationship {drawing_id!r} is not a drawing"
                    )
                    continue
                if not is_internal(relationship):
                    auditor_failures.append(
                        f"{sheet_name!r} drawing {drawing_id!r} is external"
                    )
                    continue
                drawing_part = resolve_target(worksheet_part, relationship.target)
                drawing_parts.append(drawing_part)
                linked_drawing_parts.add(drawing_part)
                if drawing_part not in names:
                    auditor_failures.append(
                        f"{sheet_name!r} drawing target is missing: {drawing_part}"
                    )
                    continue

                drawing_root = parse_xml(archive.read(drawing_part), drawing_part)
                drawing_rels, _drawing_rels_part = read_relationships(
                    archive, drawing_part
                )
                drawing_rel_map = relationship_map(drawing_rels)
                chart_ids = [
                    relationship_id(element)
                    for element in iter_local(drawing_root, "chart")
                    if relationship_id(element)
                ]
                chart_relationship_declarations += len(chart_ids)
                for chart_id in chart_ids:
                    chart_relationship = drawing_rel_map.get(chart_id or "")
                    if chart_relationship is None:
                        auditor_failures.append(
                            f"{drawing_part} chart {chart_id!r} has no relationship"
                        )
                        continue
                    if not rel_type_endswith(chart_relationship, "chart"):
                        auditor_failures.append(
                            f"{drawing_part} relationship {chart_id!r} is not a chart"
                        )
                        continue
                    if not is_internal(chart_relationship):
                        auditor_failures.append(
                            f"{drawing_part} chart {chart_id!r} is external"
                        )
                        continue
                    chart_part = resolve_target(
                        drawing_part, chart_relationship.target
                    )
                    if chart_part not in names:
                        auditor_failures.append(
                            f"{drawing_part} chart target is missing: {chart_part}"
                        )
                        continue
                    chart_links.setdefault(
                        chart_part,
                        {
                            "part": chart_part,
                            "owner_sheets": [],
                            "drawing_parts": [],
                        },
                    )
                    if sheet_name not in chart_links[chart_part]["owner_sheets"]:
                        chart_links[chart_part]["owner_sheets"].append(sheet_name)
                    if drawing_part not in chart_links[chart_part]["drawing_parts"]:
                        chart_links[chart_part]["drawing_parts"].append(drawing_part)

            worksheet_records.append(
                {
                    "name": sheet_name,
                    "part": worksheet_part,
                    "declared_in_workbook": worksheet_part
                    in worksheet_names_by_part,
                    "formula_count": sheet_formula_count,
                    "drawing_relationship_part": sheet_rels_part,
                    "drawing_relationship_ids": drawing_ids,
                    "drawing_parts": drawing_parts,
                }
            )

        declared_parts = {
            record["part"] for record in declared_sheets if record.get("part")
        }
        orphan_worksheet_parts = sorted(
            set(package_worksheet_parts) - declared_parts
        )
        if orphan_worksheet_parts:
            auditor_failures.append(
                "worksheet parts are not declared by workbook.xml: "
                + ", ".join(orphan_worksheet_parts)
            )

        chart_records: list[dict[str, Any]] = []
        for chart_part in sorted(chart_links):
            chart_root = parse_xml(archive.read(chart_part), chart_part)
            title = extract_chart_title(chart_root)
            series_records: list[dict[str, Any]] = []
            category_values: list[str] = []
            for series in iter_local(chart_root, "ser"):
                category_formula = series_formula(series, ("cat", "xVal"))
                value_formula = series_formula(series, ("val", "yVal"))
                categories = series_categories(series)
                if len(categories) > len(category_values):
                    category_values = categories
                series_record = {
                    "name": extract_series_name(series),
                    "category_formula": category_formula,
                    "value_formula": value_formula,
                    "category_cache": categories,
                    "percent_style_cells": [],
                    "percentage_token_evidence": [],
                    "range_errors": [],
                }
                if has_token(series_record["name"], PERCENT_TOKENS):
                    series_record["percentage_token_evidence"].append("series_name")
                if value_formula:
                    try:
                        value_range = parse_internal_range(value_formula)
                        cells = cell_maps.get(value_range.sheet_name)
                        if cells is None:
                            series_record["range_errors"].append(
                                f"value range sheet not found: {value_range.sheet_name}"
                            )
                        else:
                            for cell_reference in range_cells(value_range):
                                cell = cells.get(cell_reference)
                                if not cell:
                                    continue
                                if style_is_percent(
                                    cell.get("style_index"),
                                    custom_formats,
                                    style_num_fmt_ids,
                                ):
                                    series_record["percent_style_cells"].append(
                                        f"{value_range.sheet_name}!{cell_reference}"
                                    )
                                if has_token(cell.get("formula"), PERCENT_TOKENS):
                                    series_record["percentage_token_evidence"].append(
                                        f"formula:{value_range.sheet_name}!{cell_reference}"
                                    )
                    except ValueError as exc:
                        series_record["range_errors"].append(str(exc))
                else:
                    series_record["range_errors"].append(
                        "series has no value range formula"
                    )
                series_records.append(series_record)

            role, role_evidence = infer_chart_role(title, category_values)
            chart_records.append(
                {
                    **chart_links[chart_part],
                    "title": title,
                    "role": role,
                    "role_evidence": role_evidence,
                    "series_count": len(series_records),
                    "series": series_records,
                }
            )

        active_chart_parts = set(chart_links)
        orphan_drawing_parts = sorted(
            set(package_drawing_parts) - linked_drawing_parts
        )
        orphan_chart_parts = sorted(set(package_chart_parts) - active_chart_parts)
        expected_chart_count = expectations.get("chart_count")
        formula_declared = bool(formula_declaration_parts) or (
            expectations.get("formula_count") or 0
        ) > 0
        chart_declared = (
            bool(package_chart_parts)
            or chart_relationship_declarations > 0
            or (expected_chart_count or 0) > 0
        )
        if chart_declared and not chart_records:
            auditor_failures.append(
                "charts are declared by the package/manifest but relationship audit resolved zero charts"
            )
        if formula_declared and formula_count == 0:
            auditor_failures.append(
                "formulas are declared by the package/manifest but formula audit resolved zero formulas"
            )
        if orphan_chart_parts:
            auditor_failures.append(
                "chart parts are not reachable from worksheet drawing relationships: "
                + ", ".join(orphan_chart_parts)
            )
        if orphan_drawing_parts:
            auditor_failures.append(
                "drawing parts are not reachable from worksheet relationships: "
                + ", ".join(orphan_drawing_parts)
            )

        if manifest is not None:
            if expectations.get("chart_count") is None:
                business_failures.append("manifest does not declare charts.count")
            if expectations.get("formula_count") is None:
                business_failures.append("manifest does not declare formula_count")
            if expectations.get("population_count") is None:
                business_failures.append("manifest does not declare population.actual")

        if expected_chart_count is not None and len(chart_records) != expected_chart_count:
            business_failures.append(
                f"manifest expects {expected_chart_count} charts; workbook has {len(chart_records)}"
            )
        expected_formula_total = expectations.get("formula_count")
        if expected_formula_total is not None and formula_count != expected_formula_total:
            business_failures.append(
                f"manifest expects {expected_formula_total} formulas; workbook has {formula_count}"
            )
        if formula_count == 0 and not formula_declared:
            business_failures.append(
                "trend workbook contains zero formulas and no positive formula declaration"
            )

        charts_by_role: dict[str, list[dict[str, Any]]] = {
            "monthly": [],
            "quarterly": [],
        }
        for chart in chart_records:
            role = chart.get("role")
            if role in charts_by_role:
                charts_by_role[role].append(chart)
            else:
                business_failures.append(
                    f"cannot identify chart role from title/categories: {chart['part']}"
                )

        for role in ("monthly", "quarterly"):
            role_charts = charts_by_role[role]
            if len(role_charts) != 1:
                business_failures.append(
                    f"expected exactly one {role} chart; found {len(role_charts)}"
                )
                continue
            chart = role_charts[0]
            role_expectation = expectations["roles"][role]
            expected_role_series = role_expectation.get("series_count")
            if (
                expected_role_series is not None
                and chart["series_count"] != expected_role_series
            ):
                business_failures.append(
                    f"{role} chart expects {expected_role_series} series; "
                    f"found {chart['series_count']}"
                )
            if chart["series_count"] <= 0:
                business_failures.append(f"{role} chart has no series")
            if not has_token(chart["title"], ACTUAL_VOLUME_TOKENS):
                business_failures.append(
                    f"{role} chart title does not identify actual search volume"
                )
            if has_token(chart["title"], PERCENT_TOKENS):
                business_failures.append(
                    f"{role} chart title indicates a percentage metric"
                )
            metric = role_expectation.get("metric")
            if manifest is not None and metric is None:
                business_failures.append(f"manifest {role} metric is missing")
            if metric is not None:
                if not has_token(metric, ACTUAL_VOLUME_TOKENS):
                    business_failures.append(
                        f"manifest {role} metric is not actual search volume: {metric!r}"
                    )
                if has_token(metric, PERCENT_TOKENS):
                    business_failures.append(
                        f"manifest {role} metric indicates a percentage: {metric!r}"
                    )
            manifest_percentage = role_expectation.get("percentage_series")
            if manifest is not None and manifest_percentage is None:
                business_failures.append(
                    f"manifest {role} percentage_series is missing"
                )
            if manifest_percentage not in (None, 0):
                business_failures.append(
                    f"manifest {role} percentage_series must be 0; found {manifest_percentage}"
                )
            source_range_text = role_expectation.get("source_range")
            if manifest is not None and not source_range_text:
                business_failures.append(
                    f"manifest {role} source_range is missing"
                )
            expected_source_range = None
            if source_range_text:
                try:
                    expected_source_range = parse_internal_range(
                        str(source_range_text), chart["owner_sheets"][0]
                    )
                except ValueError as exc:
                    business_failures.append(
                        f"manifest {role} source_range is invalid: {exc}"
                    )
            for index, series in enumerate(chart["series"], start=1):
                if series["percent_style_cells"]:
                    business_failures.append(
                        f"{role} series {index} uses percentage-formatted value cells: "
                        + ", ".join(series["percent_style_cells"][:5])
                    )
                if series["percentage_token_evidence"]:
                    business_failures.append(
                        f"{role} series {index} contains percentage metric evidence: "
                        + ", ".join(series["percentage_token_evidence"])
                    )
                if series["range_errors"]:
                    business_failures.append(
                        f"{role} series {index} has invalid source range: "
                        + "; ".join(series["range_errors"])
                    )
                if expected_source_range:
                    for formula_kind in ("category_formula", "value_formula"):
                        formula = series.get(formula_kind)
                        if not formula:
                            continue
                        try:
                            actual_range = parse_internal_range(formula)
                        except ValueError:
                            continue
                        if not range_contains(expected_source_range, actual_range):
                            business_failures.append(
                                f"{role} series {index} {formula_kind} {formula!r} "
                                f"is outside manifest source_range {source_range_text!r}"
                            )

        if (
            expectations.get("population_count") is None
            and len(charts_by_role["monthly"]) == 1
            and len(charts_by_role["quarterly"]) == 1
            and charts_by_role["monthly"][0]["series_count"]
            != charts_by_role["quarterly"][0]["series_count"]
        ):
            business_failures.append(
                "monthly and quarterly chart series counts differ without a manifest population count"
            )

        if auditor_failures:
            status = "auditor_failure"
            exit_code = 2
        elif business_failures:
            status = "business_failure"
            exit_code = 1
        else:
            status = "pass"
            exit_code = 0

        return {
            "schema_version": "trend-ooxml-audit/v1",
            "status": status,
            "exit_code": exit_code,
            "workbook": str(workbook_path),
            "manifest_provided": manifest is not None,
            "expectations": expectations,
            "package_declarations": {
                "workbook_relationships_part": workbook_rels_part,
                "declared_sheet_count": len(declared_sheets),
                "worksheet_part_count": len(package_worksheet_parts),
                "package_drawing_part_count": len(package_drawing_parts),
                "package_chart_part_count": len(package_chart_parts),
                "chart_relationship_declaration_count": chart_relationship_declarations,
                "formula_declaration_parts": formula_declaration_parts,
            },
            "formula_count": formula_count,
            "worksheets": worksheet_records,
            "drawings": sorted(linked_drawing_parts),
            "charts": chart_records,
            "orphan_worksheet_parts": orphan_worksheet_parts,
            "orphan_drawing_parts": orphan_drawing_parts,
            "orphan_chart_parts": orphan_chart_parts,
            "auditor_failures": auditor_failures,
            "business_failures": business_failures,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit every worksheet/drawing/chart relationship in a trend XLSX and "
            "verify monthly/quarterly actual-search-volume series."
        )
    )
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--expected-series-count", type=int)
    parser.add_argument("--expected-formula-count", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = None
        if args.manifest:
            manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
            if not isinstance(manifest, dict):
                raise AuditInputError("manifest root must be a JSON object")
        result = audit_workbook(
            args.workbook,
            manifest,
            expected_series_count=args.expected_series_count,
            expected_formula_count=args.expected_formula_count,
        )
    except (AuditInputError, OSError, json.JSONDecodeError) as exc:
        result = {
            "schema_version": "trend-ooxml-audit/v1",
            "status": "auditor_failure",
            "exit_code": 2,
            "workbook": str(args.workbook),
            "auditor_failures": [str(exc)],
            "business_failures": [],
        }
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output, encoding="utf-8")
    sys.stdout.write(output)
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
