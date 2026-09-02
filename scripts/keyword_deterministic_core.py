#!/usr/bin/env python3
"""Deterministic, boundary-preserving calculations for keyword-library runs.

Inputs and outputs are JSON so workbook I/O remains owned by the relevant Skill.
The program never decides category relevance, product type, semantic labels,
strong equivalence, negative-keyword meaning or other model-owned semantics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


SCHEMA = "amazon-keyword-deterministic-core/v1"
VERSION = "keyword-deterministic-core/1.0.0"
ELIGIBLE = "纳入"
TRAFFIC_LEVELS = {"F1", "F2", "F3", "F4", "F5"}
COMPETITION_LEVELS = ("低", "中", "高", "极高")

PREPOSITIONS = (
    "about", "above", "across", "after", "against", "along", "among", "around",
    "at", "before", "behind", "below", "beneath", "beside", "between", "beyond",
    "by", "despite", "during", "except", "for", "from", "in", "inside", "into",
    "near", "of", "on", "onto", "opposite", "outside", "over", "past", "per",
    "since", "through", "throughout", "to", "toward", "towards", "under",
    "underneath", "until", "upon", "via", "with", "within", "without",
)
PREPOSITION_SET = set(PREPOSITIONS)
PREPOSITION_SHA256 = hashlib.sha256("\n".join(PREPOSITIONS).encode("ascii")).hexdigest()

COMPETITION_MATRIX = {
    "低": {"低": "低", "中": "中", "高": "高", "极高": "高"},
    "中": {"低": "中", "中": "中", "高": "高", "极高": "高"},
    "高": {"低": "高", "中": "高", "高": "高", "极高": "极高"},
    "极高": {"低": "高", "中": "高", "高": "极高", "极高": "极高"},
}


class CoreError(ValueError):
    """Raised when a deterministic input or population contract fails."""


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CoreError(f"cannot read JSON {path}: {exc}") from exc


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def mechanical_key(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value)).strip().lower()
    return re.sub(r"\s+", " ", text)


def require_rows(payload: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise CoreError("rows must be a list")
    if any(not isinstance(row, Mapping) for row in rows):
        raise CoreError("every row must be an object")
    return rows


def require_unique_ids(rows: Sequence[Mapping[str, Any]]) -> None:
    identifiers = [str(row.get("keyword_id", "")) for row in rows]
    if any(not item for item in identifiers):
        raise CoreError("every row requires keyword_id")
    duplicates = sorted(item for item, count in Counter(identifiers).items() if count > 1)
    if duplicates:
        raise CoreError(f"duplicate keyword_id values: {duplicates[:10]}")


def number(value: Any, label: str, allow_zero: bool = True) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise CoreError(f"{label}: boolean is not numeric")
    if isinstance(value, str):
        value = value.replace(",", "").strip()
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise CoreError(f"{label}: invalid number {value!r}") from exc
    if parsed < 0 or (not allow_zero and parsed == 0):
        raise CoreError(f"{label}: out-of-range value {parsed}")
    return parsed


def validate_source_merge(payload: Mapping[str, Any]) -> Dict[str, Any]:
    sources = payload.get("sources")
    merged = payload.get("merged")
    if not isinstance(sources, Mapping) or not isinstance(merged, list):
        raise CoreError("sources must be an object and merged must be a list")
    expected: Dict[str, set[str]] = {}
    raw_count = 0
    for source_name, rows in sources.items():
        if not isinstance(rows, list):
            raise CoreError(f"sources.{source_name} must be a list")
        for row in rows:
            if not isinstance(row, Mapping):
                raise CoreError(f"sources.{source_name} contains a non-object row")
            key = mechanical_key(row.get("keyword", ""))
            if not key:
                raise CoreError(f"sources.{source_name} contains an empty keyword")
            expected.setdefault(key, set()).add(str(source_name))
            raw_count += 1
    actual: Dict[str, set[str]] = {}
    for row in merged:
        if not isinstance(row, Mapping):
            raise CoreError("merged contains a non-object row")
        key = mechanical_key(row.get("keyword", ""))
        if not key:
            raise CoreError("merged contains an empty keyword")
        if key in actual:
            raise CoreError(f"merged contains duplicate mechanical key: {key}")
        provenance = row.get("keyword_sources")
        if not isinstance(provenance, list) or not provenance:
            raise CoreError(f"{key}: keyword_sources must be a non-empty list")
        actual[key] = {str(item) for item in provenance}
    if set(actual) != set(expected):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        raise CoreError(f"merged union mismatch; missing={missing[:10]}, extra={extra[:10]}")
    for key in sorted(expected):
        if actual[key] != expected[key]:
            raise CoreError(
                f"{key}: provenance mismatch expected={sorted(expected[key])} "
                f"actual={sorted(actual[key])}"
            )
    return {
        "schema": SCHEMA,
        "executor_version": VERSION,
        "status": "pass",
        "raw_row_count": raw_count,
        "unique_keyword_count": len(expected),
        "duplicate_row_count": raw_count - len(expected),
        "population_sha256": canonical_sha256(sorted(expected)),
    }


def tokens(keyword: str) -> List[str]:
    normalized = unicodedata.normalize("NFKC", keyword).lower()
    return re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)


def word_frequency(payload: Mapping[str, Any]) -> Dict[str, Any]:
    rows = require_rows(payload)
    require_unique_ids(rows)
    word_counts: Counter[str] = Counter()
    pair_counts: Counter[str] = Counter()
    prep_counts: Counter[str] = Counter()
    input_ids = []
    raw_tokens = 0
    eligible_rows = 0
    for row in rows:
        if row.get("eligibility") != ELIGIBLE:
            continue
        keyword = row.get("keyword")
        if not isinstance(keyword, str) or not keyword.strip():
            continue
        eligible_rows += 1
        input_ids.append(str(row["keyword_id"]))
        row_tokens = tokens(keyword)
        raw_tokens += len(row_tokens)
        segment: List[str] = []
        for token in row_tokens + [""]:
            if token in PREPOSITION_SET or token == "":
                if token:
                    prep_counts[token] += 1
                for item in segment:
                    word_counts[item] += 1
                for left, right in zip(segment, segment[1:]):
                    pair_counts[f"{left} {right}"] += 1
                segment = []
            else:
                segment.append(token)
    def ranked(counter: Counter[str], field: str) -> List[Dict[str, Any]]:
        ordered = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
        return [
            {"rank": index, field: value, "count": count}
            for index, (value, count) in enumerate(ordered, start=1)
        ]
    filtered_total = sum(prep_counts.values())
    return {
        "schema": SCHEMA,
        "executor_version": VERSION,
        "status": "completed",
        "input_population": {
            "sheet2_rows": len(rows),
            "eligible_nonempty_rows": eligible_rows,
            "eligible_keyword_ids_sha256": canonical_sha256(sorted(input_ids)),
        },
        "preposition_contract": {
            "version": "EN_PREP_CORE_V1",
            "token_count": len(PREPOSITIONS),
            "content_sha256": PREPOSITION_SHA256,
            "filtered_total": filtered_total,
            "filtered_by_token": dict(sorted(prep_counts.items())),
        },
        "counts": {
            "raw_tokens": raw_tokens,
            "valid_words": sum(word_counts.values()),
            "unique_words": len(word_counts),
            "ordered_pairs": sum(pair_counts.values()),
            "unique_ordered_pairs": len(pair_counts),
        },
        "words": ranked(word_counts, "word"),
        "ordered_pairs": ranked(pair_counts, "ordered_pair"),
    }


def traffic_layer(aba: float | None) -> str | None:
    if aba is None or aba < 1:
        return None
    if aba <= 10_000:
        return "F1"
    if aba <= 20_000:
        return "F2"
    if aba <= 50_000:
        return "F3"
    if aba <= 100_000:
        return "F4"
    return "F5"


def classify_traffic(payload: Mapping[str, Any]) -> Dict[str, Any]:
    rows = require_rows(payload)
    require_unique_ids(rows)
    output = []
    counts: Counter[str] = Counter()
    for row in rows:
        aba = number(row.get("aba_rank"), f"{row['keyword_id']}.aba_rank")
        search_volume = number(
            row.get("search_volume"), f"{row['keyword_id']}.search_volume"
        )
        layer = traffic_layer(aba)
        if layer is None:
            status = "关键词ABA排名缺失"
        elif search_volume is None:
            status = "搜索量缺失"
        elif search_volume == 0:
            status = "没有搜索量"
        else:
            status = ""
        counts[layer or "unclassified"] += 1
        if status:
            counts[status] += 1
        output.append(
            {
                "keyword_id": str(row["keyword_id"]),
                "traffic_layer": layer,
                "classification_status": status,
            }
        )
    return {
        "schema": SCHEMA,
        "executor_version": VERSION,
        "status": "completed_with_gaps" if counts["unclassified"] else "completed",
        "population": {"input": len(rows), "output": len(output)},
        "counts": dict(sorted(counts.items())),
        "rows": output,
    }


def share(value: Any, unit: Any, label: str) -> float | None:
    parsed = number(value, label)
    if parsed is None:
        return None
    if unit == "fraction":
        if parsed > 1:
            raise CoreError(f"{label}: fraction exceeds 1")
        return parsed * 100
    if unit == "percent":
        if parsed > 100:
            raise CoreError(f"{label}: percent exceeds 100")
        return parsed
    raise CoreError(f"{label}: unit must be fraction or percent")


def concentration(value: float) -> str:
    if value < 30:
        return "低"
    if value < 50:
        return "中"
    if value < 70:
        return "高"
    return "极高"


def competition(payload: Mapping[str, Any]) -> Dict[str, Any]:
    rows = require_rows(payload)
    require_unique_ids(rows)
    output = []
    for row in rows:
        if row.get("eligibility") != ELIGIBLE or row.get("traffic_layer") not in {
            "F1", "F2", "F3", "F4"
        }:
            continue
        identifier = str(row["keyword_id"])
        complete = (
            row.get("exact_match") is True
            and row.get("same_period") is True
            and row.get("unit") in {"fraction", "percent"}
        )
        click = (
            share(row.get("top3_click_share"), row.get("unit"), f"{identifier}.click")
            if complete
            else None
        )
        conversion = (
            share(
                row.get("top3_conversion_share"),
                row.get("unit"),
                f"{identifier}.conversion",
            )
            if complete
            else None
        )
        if click is None or conversion is None:
            output.append(
                {
                    "keyword_id": identifier,
                    "click_level": None,
                    "conversion_level": None,
                    "click_conversion_gap_pp": None,
                    "structure": None,
                    "competition_level": None,
                    "data_status": "数据不足/人工复核",
                }
            )
            continue
        click_level = concentration(click)
        conversion_level = concentration(conversion)
        gap = conversion - click
        if gap >= 15:
            structure = "头部转化效率壁垒"
        elif gap <= -15:
            structure = "点击流量被锁但购买相对分散"
        else:
            structure = "结构基本一致"
        output.append(
            {
                "keyword_id": identifier,
                "click_level": click_level,
                "conversion_level": conversion_level,
                "click_conversion_gap_pp": round(gap, 6),
                "structure": structure,
                "competition_level": COMPETITION_MATRIX[click_level][conversion_level],
                "data_status": "",
            }
        )
    gaps = sum(1 for row in output if row["data_status"])
    return {
        "schema": SCHEMA,
        "executor_version": VERSION,
        "status": "completed_with_gaps" if gaps else "completed",
        "population": {"input": len(rows), "applicable": len(output)},
        "gap_rows": gaps,
        "rows": output,
    }


def month_tuple(value: str) -> Tuple[int, int]:
    match = re.fullmatch(r"(\d{4})-(0[1-9]|1[0-2])", value)
    if not match:
        raise CoreError(f"invalid month: {value!r}")
    return int(match.group(1)), int(match.group(2))


def shift_month(value: str, offset: int) -> str:
    year, month = month_tuple(value)
    index = year * 12 + month - 1 + offset
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def month_range(start: str, end: str) -> List[str]:
    if month_tuple(start) > month_tuple(end):
        return []
    result = []
    current = start
    while month_tuple(current) <= month_tuple(end):
        result.append(current)
        current = shift_month(current, 1)
    return result


def ratio(current: float | None, baseline: float | None) -> float | None:
    if current is None or baseline in {None, 0}:
        return None
    return (current - baseline) / baseline


def quarter_for_month(month: str) -> Tuple[int, int]:
    year, month_number = month_tuple(month)
    return year, (month_number - 1) // 3 + 1


def quarter_label(year: int, quarter: int) -> str:
    return f"{year}-Q{quarter}"


def shift_quarter(year: int, quarter: int, offset: int) -> Tuple[int, int]:
    index = year * 4 + quarter - 1 + offset
    return index // 4, index % 4 + 1


def quarter_months(year: int, quarter: int) -> List[str]:
    first = (quarter - 1) * 3 + 1
    return [f"{year:04d}-{month:02d}" for month in range(first, first + 3)]


def trend(payload: Mapping[str, Any]) -> Dict[str, Any]:
    rows = require_rows(payload)
    require_unique_ids(rows)
    provider = payload.get("provider")
    if provider not in {"SellerSprite", "Sorftime"}:
        raise CoreError("provider must be SellerSprite or Sorftime")
    latest = str(payload.get("latest_complete_month", ""))
    month_tuple(latest)
    selected = [
        row
        for row in rows
        if row.get("eligibility") == ELIGIBLE
        and row.get("traffic_layer") in {"F1", "F2", "F3"}
    ]
    locked_months = month_range(shift_month(latest, -23), latest)
    earliest_available = None
    normalized: Dict[str, Dict[str, float | None]] = {}
    zero_valid = []
    gap_count = 0
    for row in selected:
        identifier = str(row["keyword_id"])
        if row.get("provider", provider) != provider:
            raise CoreError(f"{identifier}: mixed trend provider")
        months = row.get("months")
        if not isinstance(months, Mapping):
            raise CoreError(f"{identifier}: months must be an object")
        if any(month not in months for month in locked_months):
            raise CoreError(f"{identifier}: query does not cover 24 complete calendar months")
        values: Dict[str, float | None] = {}
        for month, value in months.items():
            month_tuple(str(month))
            if month_tuple(str(month)) > month_tuple(latest):
                continue
            values[str(month)] = number(value, f"{identifier}.{month}")
        normalized[identifier] = values
        valid = sum(value is not None for value in (values.get(month) for month in locked_months))
        if valid == 0:
            zero_valid.append(identifier)
        gap_count += len(locked_months) - valid
        local_earliest = min(values, key=month_tuple) if values else None
        if local_earliest and (
            earliest_available is None or month_tuple(local_earliest) < month_tuple(earliest_available)
        ):
            earliest_available = local_earliest
    display_months = locked_months[-12:]
    monthly = []
    for month in display_months:
        metrics = {"月搜索量": {}, "月环比": {}, "月同比": {}}
        for row in selected:
            identifier = str(row["keyword_id"])
            values = normalized[identifier]
            current = values.get(month)
            metrics["月搜索量"][identifier] = current
            metrics["月环比"][identifier] = ratio(current, values.get(shift_month(month, -1)))
            metrics["月同比"][identifier] = ratio(current, values.get(shift_month(month, -12)))
        for metric in ("月搜索量", "月环比", "月同比"):
            monthly.append({"month": month, "metric": metric, "values": metrics[metric]})
    chart_start = earliest_available or locked_months[0]
    chart_months = month_range(chart_start, latest)
    latest_year, latest_quarter = quarter_for_month(latest)
    quarter_end_month = latest_quarter * 3
    if month_tuple(latest)[1] < quarter_end_month:
        latest_year, latest_quarter = shift_quarter(latest_year, latest_quarter, -1)
    display_quarters = [
        shift_quarter(latest_year, latest_quarter, offset) for offset in range(-3, 1)
    ]
    baseline_quarters = [
        shift_quarter(latest_year, latest_quarter, offset) for offset in range(-7, 1)
    ]
    chart_quarters = []
    cursor = quarter_for_month(chart_months[0])
    while cursor <= (latest_year, latest_quarter):
        months = quarter_months(*cursor)
        if all(month in chart_months for month in months):
            chart_quarters.append(cursor)
        cursor = shift_quarter(*cursor, 1)
    all_quarters = sorted(set(baseline_quarters) | set(chart_quarters))
    quarter_values: Dict[Tuple[int, int], Dict[str, float | None]] = {}
    for year, quarter in all_quarters:
        values_by_id: Dict[str, float | None] = {}
        months = quarter_months(year, quarter)
        for row in selected:
            identifier = str(row["keyword_id"])
            values = [normalized[identifier].get(month) for month in months]
            values_by_id[identifier] = sum(values) if all(value is not None for value in values) else None
        quarter_values[(year, quarter)] = values_by_id
    quarterly = []
    for year, quarter in display_quarters:
        current_values = quarter_values[(year, quarter)]
        previous = quarter_values.get(shift_quarter(year, quarter, -1), {})
        prior_year = quarter_values.get(shift_quarter(year, quarter, -4), {})
        metrics = {
            "季度搜索量": current_values,
            "季度环比": {
                identifier: ratio(current_values[identifier], previous.get(identifier))
                for identifier in current_values
            },
            "季度同比": {
                identifier: ratio(current_values[identifier], prior_year.get(identifier))
                for identifier in current_values
            },
        }
        for metric in ("季度搜索量", "季度环比", "季度同比"):
            quarterly.append(
                {
                    "quarter": quarter_label(year, quarter),
                    "metric": metric,
                    "values": metrics[metric],
                }
            )
    if zero_valid:
        status = "incomplete"
    elif gap_count:
        status = "completed_with_gaps"
    else:
        status = "completed"
    return {
        "schema": SCHEMA,
        "executor_version": VERSION,
        "status": status,
        "provider": provider,
        "population": {
            "input": len(rows),
            "applicable": len(selected),
            "zero_valid_keyword_ids": zero_valid,
            "missing_locked_month_values": gap_count,
        },
        "monthly_matrix": monthly,
        "quarterly_matrix": quarterly,
        "charts": {
            "monthly_actual_search_volume": {
                "months": chart_months,
                "series": {
                    identifier: [normalized[identifier].get(month) for month in chart_months]
                    for identifier in normalized
                },
            },
            "quarterly_actual_search_volume": {
                "quarters": [quarter_label(*item) for item in chart_quarters],
                "series": {
                    identifier: [quarter_values[item][identifier] for item in chart_quarters]
                    for identifier in normalized
                },
            },
            "percentage_series": 0,
        },
    }


def id_set(rows: Any, label: str) -> set[str]:
    if not isinstance(rows, list):
        raise CoreError(f"{label} must be a list")
    values = []
    for row in rows:
        if isinstance(row, Mapping):
            value = str(row.get("keyword_id", ""))
        else:
            value = str(row)
        if not value:
            raise CoreError(f"{label} contains an empty keyword_id")
        values.append(value)
    duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
    if duplicates:
        raise CoreError(f"{label} contains duplicate IDs: {duplicates[:10]}")
    return set(values)


def validate_cleaning_ledger(payload: Mapping[str, Any]) -> Dict[str, Any]:
    input_ids = id_set(payload.get("input_ids"), "input_ids")
    sheet2_rows = payload.get("sheet2")
    if not isinstance(sheet2_rows, list) or any(not isinstance(row, Mapping) for row in sheet2_rows):
        raise CoreError("sheet2 must be a list of objects")
    sheet2 = id_set(sheet2_rows, "sheet2")
    sheet3 = id_set(payload.get("sheet3"), "sheet3")
    sheet4 = id_set(payload.get("sheet4"), "sheet4")
    routed = sheet2 | sheet3 | sheet4
    overlap = (sheet2 & sheet3) | (sheet2 & sheet4) | (sheet3 & sheet4)
    if overlap:
        raise CoreError(f"keyword IDs appear in multiple destinations: {sorted(overlap)[:10]}")
    if routed != input_ids:
        raise CoreError(
            f"three-destination population mismatch; missing={sorted(input_ids-routed)[:10]}, "
            f"extra={sorted(routed-input_ids)[:10]}"
        )
    eligibility: Counter[str] = Counter()
    risk_from_sheet2 = set()
    for row in sheet2_rows:
        value = row.get("eligibility")
        if value not in {"纳入", "不纳入", "待复核"}:
            raise CoreError(f"{row.get('keyword_id')}: invalid Sheet2 eligibility {value!r}")
        eligibility[str(value)] += 1
        if value in {"不纳入", "待复核"}:
            risk_from_sheet2.add(str(row["keyword_id"]))
    risk_population = id_set(payload.get("risk_population_ids"), "risk_population_ids")
    reviewed_risk = id_set(payload.get("reviewed_risk_ids"), "reviewed_risk_ids")
    omission = id_set(payload.get("omission_family_ids", []), "omission_family_ids")
    reviewed_omission = id_set(
        payload.get("reviewed_omission_family_ids", []), "reviewed_omission_family_ids"
    )
    expected_risk = risk_from_sheet2 | sheet3 | sheet4 | omission
    if risk_population != expected_risk:
        raise CoreError(
            "risk population must equal all Sheet2 non-included/pending, Sheet3, Sheet4 "
            "and omission-family IDs"
        )
    if reviewed_risk != risk_population:
        raise CoreError("every risk-population ID must be reviewed; sampling is forbidden")
    if reviewed_omission != omission:
        raise CoreError("every upper-qualifier omission-family ID must be reviewed")
    return {
        "schema": SCHEMA,
        "executor_version": VERSION,
        "status": "pass",
        "population": {
            "input": len(input_ids),
            "sheet2": len(sheet2),
            "sheet3": len(sheet3),
            "sheet4": len(sheet4),
            "eligibility": dict(sorted(eligibility.items())),
            "risk_population": len(risk_population),
            "omission_family": len(omission),
        },
        "population_sha256": canonical_sha256(sorted(input_ids)),
        "risk_population_sha256": canonical_sha256(sorted(risk_population)),
    }


COMMANDS = {
    "validate-source-merge": validate_source_merge,
    "word-frequency": word_frequency,
    "classify-traffic": classify_traffic,
    "competition": competition,
    "trend": trend,
    "validate-cleaning-ledger": validate_cleaning_ledger,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=sorted(COMMANDS))
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = read_json(Path(args.input))
        if not isinstance(payload, Mapping):
            raise CoreError("input JSON must be an object")
        result = COMMANDS[args.command](payload)
        text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.output:
            path = Path(args.output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        else:
            print(text, end="")
        return 0
    except CoreError as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
