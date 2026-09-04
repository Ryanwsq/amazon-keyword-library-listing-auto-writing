#!/usr/bin/env python3
"""Run deterministic fixtures for the lossless runtime optimization layer."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import keyword_deterministic_core as core
import runtime_contract as runtime


HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
REVISION = "d" * 40


def expect_error(function, contains: str) -> None:
    try:
        function()
    except (core.CoreError, runtime.ContractError) as exc:
        assert contains in str(exc), (contains, str(exc))
    else:
        raise AssertionError(f"expected error containing {contains!r}")


def spec(run_type: str = "production", qa_mode=None, change_flags=None):
    value = {
        "run_id": "AKW-FIXTURE-01",
        "run_type": run_type,
        "revision": REVISION,
        "site": "Amazon-US",
        "input_hashes": {
            "product_basic_configuration": HASH_A,
            "product_selling_points": HASH_B,
            "competitor_asins": HASH_C,
        },
        "locks": {
            "target_amazon_category": "fixture category",
            "has_multiple_stable_product_types": True,
            "original_asin_count": 7,
            "selected_asin_count": 3,
            "excluded_asin_count": 4,
        },
        "change_flags": change_flags or [],
    }
    if qa_mode is not None:
        value["qa_mode"] = qa_mode
    return value


def test_runtime_contract() -> None:
    production = runtime.build_contract(spec())
    runtime.verify_contract(production)
    assert production["marketplace_route"]["domain"] == "amazon.com"
    assert production["parallel_waves"]["core-sources"] == [
        "amazon-autocomplete",
        "sellersprite",
    ]
    german_spec = spec()
    german_spec["site"] = "Amazon-DE"
    german = runtime.build_contract(german_spec)
    assert german["marketplace_route"] == {
        "domain": "amazon.de",
        "department": "Alle",
        "postal_code": "80539",
        "shopping_assistant": "Rufus",
        "prompt_language": "German",
    }
    invalid_site = spec()
    invalid_site["site"] = "Amazon-UK"
    expect_error(
        lambda: runtime.build_contract(invalid_site),
        "Amazon-US or Amazon-DE",
    )
    assert "quality-validation" not in production["stages"]
    assert production["quality_routing"] == "not_applicable"
    assert runtime.descendants("word-frequency", "production") == ["assembly"]
    assert runtime.descendants("classification", "production") == [
        "competition",
        "trend",
        "assembly",
    ]
    expect_error(
        lambda: runtime.build_contract(
            spec("test-validation", "compact-validation", ["skill-change"])
        ),
        "requires full-regression",
    )
    regression = runtime.build_contract(
        spec("test-validation", "full-regression", ["skill-change", "checker-change"])
    )
    runtime.verify_contract(regression)
    assert "quality-validation" in regression["stages"]
    tampered = json.loads(json.dumps(production))
    tampered["site"] = "tampered"
    expect_error(lambda: runtime.verify_contract(tampered), "content hash mismatch")
    unsafe = spec()
    unsafe["locks"]["source_path"] = "/machine/private/input.xlsx"
    expect_error(lambda: runtime.build_contract(unsafe), "absolute machine path")
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        preflight = {
            "schema": runtime.PREFLIGHT_SCHEMA,
            "providers": {
                "amazon": {
                    "status": "authenticated",
                    "checked_at": "2026-09-02T10:00:00+08:00",
                },
                "sif": {"status": "authenticated", "checked_at": "2026-09-02T10:00:00+08:00"},
                "sellersprite": {
                    "status": "awaiting_login",
                    "checked_at": "2026-09-02T10:00:00+08:00",
                },
            },
        }
        preflight_path = directory / "preflight.json"
        preflight_path.write_text(json.dumps(preflight), encoding="utf-8")
        ready_sif = runtime.ready_for_stage(
            production, "sif", directory / "statuses", preflight_path
        )
        ready_seller = runtime.ready_for_stage(
            production, "sellersprite", directory / "statuses", preflight_path
        )
        assert ready_sif["ready"] is True
        assert ready_seller["ready"] is False
        assert ready_seller["preflight"] == "awaiting_login"


def test_source_merge() -> None:
    payload = {
        "sources": {
            "sif": [{"keyword": " Office  Chair "}, {"keyword": "mesh chair"}],
            "autocomplete": [{"keyword": "office chair"}],
            "sellersprite": [{"keyword": "OFFICE CHAIR"}],
        },
        "merged": [
            {
                "keyword": "office chair",
                "keyword_sources": ["sif", "autocomplete", "sellersprite"],
            },
            {"keyword": "mesh chair", "keyword_sources": ["sif"]},
        ],
    }
    result = core.validate_source_merge(payload)
    assert result["raw_row_count"] == 4
    assert result["unique_keyword_count"] == 2
    broken = json.loads(json.dumps(payload))
    broken["merged"].pop()
    expect_error(lambda: core.validate_source_merge(broken), "union mismatch")


def test_word_frequency() -> None:
    payload = {
        "rows": [
            {"keyword_id": "K1", "keyword": "paddle board for adults", "eligibility": "纳入"},
            {"keyword_id": "K2", "keyword": "the chair with footrest", "eligibility": "纳入"},
            {"keyword_id": "K3", "keyword": "ignored keyword", "eligibility": "不纳入"},
        ]
    }
    result = core.word_frequency(payload)
    words = {row["word"]: row["count"] for row in result["words"]}
    pairs = {row["ordered_pair"]: row["count"] for row in result["ordered_pairs"]}
    assert result["preposition_contract"]["token_count"] == 48
    assert "for" not in words and "with" not in words
    assert words["the"] == 1
    assert pairs == {"paddle board": 1, "the chair": 1}
    assert "board adults" not in pairs and "chair footrest" not in pairs


def test_traffic_and_competition() -> None:
    traffic = core.classify_traffic(
        {
            "rows": [
                {"keyword_id": "K1", "aba_rank": 1, "search_volume": 100},
                {"keyword_id": "K2", "aba_rank": 10001, "search_volume": None},
                {"keyword_id": "K3", "aba_rank": 50000, "search_volume": 0},
                {"keyword_id": "K4", "aba_rank": None, "search_volume": 50},
                {"keyword_id": "K5", "aba_rank": 100001, "search_volume": 1},
            ]
        }
    )
    assert [row["traffic_layer"] for row in traffic["rows"]] == [
        "F1", "F2", "F3", None, "F5"
    ]
    assert traffic["rows"][1]["classification_status"] == "搜索量缺失"
    assert traffic["rows"][2]["classification_status"] == "没有搜索量"
    assert traffic["rows"][3]["classification_status"] == "关键词ABA排名缺失"
    competition = core.competition(
        {
            "rows": [
                {
                    "keyword_id": "K1",
                    "eligibility": "纳入",
                    "traffic_layer": "F1",
                    "top3_click_share": 0.2,
                    "top3_conversion_share": 0.75,
                    "unit": "fraction",
                    "exact_match": True,
                    "same_period": True,
                },
                {
                    "keyword_id": "K2",
                    "eligibility": "纳入",
                    "traffic_layer": "F2",
                    "top3_click_share": None,
                    "top3_conversion_share": 40,
                    "unit": "percent",
                    "exact_match": True,
                    "same_period": True,
                },
                {
                    "keyword_id": "K3",
                    "eligibility": "不纳入",
                    "traffic_layer": "F1",
                },
                {
                    "keyword_id": "K4",
                    "eligibility": "纳入",
                    "traffic_layer": "F4",
                    "top3_click_share": 30,
                    "top3_conversion_share": 40,
                    "unit": None,
                    "exact_match": True,
                    "same_period": True,
                },
            ]
        }
    )
    assert competition["population"]["applicable"] == 3
    assert competition["rows"][0]["competition_level"] == "高"
    assert competition["rows"][0]["structure"] == "头部转化效率壁垒"
    assert competition["rows"][1]["data_status"] == "数据不足/人工复核"
    assert competition["rows"][2]["data_status"] == "数据不足/人工复核"


def test_cleaning_ledger() -> None:
    payload = {
        "input_ids": ["K1", "K2", "K3", "K4"],
        "sheet2": [
            {"keyword_id": "K1", "eligibility": "纳入"},
            {"keyword_id": "K2", "eligibility": "不纳入"},
        ],
        "sheet3": ["K3"],
        "sheet4": ["K4"],
        "omission_family_ids": ["K1"],
        "risk_population_ids": ["K1", "K2", "K3", "K4"],
        "reviewed_risk_ids": ["K1", "K2", "K3", "K4"],
        "reviewed_omission_family_ids": ["K1"],
    }
    result = core.validate_cleaning_ledger(payload)
    assert result["population"]["input"] == 4
    broken = json.loads(json.dumps(payload))
    broken["reviewed_risk_ids"].pop()
    expect_error(
        lambda: core.validate_cleaning_ledger(broken),
        "every risk-population ID must be reviewed",
    )


def test_trend() -> None:
    months = {}
    current = "2024-03"
    for index in range(30):
        months[current] = 100 + index
        current = core.shift_month(current, 1)
    result = core.trend(
        {
            "provider": "SellerSprite",
            "latest_complete_month": "2026-08",
            "rows": [
                {
                    "keyword_id": "K1",
                    "eligibility": "纳入",
                    "traffic_layer": "F1",
                    "provider": "SellerSprite",
                    "months": months,
                },
                {
                    "keyword_id": "K2",
                    "eligibility": "待复核",
                    "traffic_layer": "F1",
                    "provider": "SellerSprite",
                    "months": months,
                },
            ],
        }
    )
    assert result["status"] == "completed"
    assert result["population"]["applicable"] == 1
    assert len(result["monthly_matrix"]) == 36
    assert len(result["quarterly_matrix"]) == 12
    assert result["charts"]["percentage_series"] == 0
    assert len(result["charts"]["monthly_actual_search_volume"]["series"]["K1"]) == 30


def main() -> int:
    tests = [
        test_runtime_contract,
        test_source_merge,
        test_word_frequency,
        test_traffic_and_competition,
        test_cleaning_ledger,
        test_trend,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"Runtime fixtures passed: {len(tests)} groups.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
