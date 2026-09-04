#!/usr/bin/env python3
"""Regression checks for the explicit US/DE marketplace input route."""

from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

import validate_input
import pipeline_state


class MarketplaceRouteTests(unittest.TestCase):
    def test_german_route_is_fixed(self) -> None:
        self.assertEqual(validate_input.normalize_marketplace("amazon.de"), "Amazon-DE")
        self.assertEqual(
            validate_input.MARKETPLACE_ROUTES["Amazon-DE"],
            {
                "domain": "amazon.de",
                "postal_code": "80539",
                "shopping_assistant": "Rufus",
                "prompt_language": "German",
            },
        )

    def test_us_route_is_fixed(self) -> None:
        self.assertEqual(validate_input.normalize_marketplace("amazon.com"), "Amazon-US")
        self.assertEqual(validate_input.MARKETPLACE_ROUTES["Amazon-US"]["postal_code"], "10001")

    def test_marketplace_never_defaults(self) -> None:
        self.assertIsNone(validate_input.normalize_marketplace(""))
        self.assertIsNone(validate_input.normalize_marketplace("Amazon-UK"))

    def test_language_is_derived_from_marketplace(self) -> None:
        self.assertEqual(
            validate_input.MARKETPLACE_ROUTES["Amazon-DE"]["prompt_language"],
            "German",
        )
        self.assertEqual(
            validate_input.MARKETPLACE_ROUTES["Amazon-US"]["prompt_language"],
            "English",
        )

    def test_run_state_uses_same_route_contract(self) -> None:
        self.assertEqual(pipeline_state.MARKETPLACE_ROUTES, validate_input.MARKETPLACE_ROUTES)
        self.assertIn("login_gate", pipeline_state.STAGES)
        self.assertIn("keywords", pipeline_state.LOGIN_GATED_STAGES)

    def test_run_state_blocks_collection_until_all_logins_confirmed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workbook = root / "input.xlsx"
            workbook.write_bytes(b"synthetic lock payload")
            run_dir = root / "run"
            pipeline_state.cmd_init(
                argparse.Namespace(
                    input=str(workbook),
                    run_dir=str(run_dir),
                    run_id="ALP-TEST-DE-LOGIN-GATE",
                    product_asin="B0TEST0001",
                    marketplace="Amazon-DE",
                )
            )
            manifest_path = run_dir / "run-manifest.json"
            manifest = json.loads(manifest_path.read_text())
            self.assertEqual(manifest["marketplace_route"]["postal_code"], "80539")
            stage_args = argparse.Namespace(
                manifest=str(manifest_path),
                stage="keywords",
                status="running",
                message=None,
                output=None,
                force=False,
            )
            with self.assertRaisesRegex(ValueError, "login gate"):
                pipeline_state.cmd_set_stage(stage_args)
            pipeline_state.cmd_confirm_login(
                argparse.Namespace(
                    manifest=str(manifest_path),
                    amazon="authenticated",
                    sif="authenticated",
                    sellersprite="authenticated",
                )
            )
            self.assertEqual(pipeline_state.cmd_set_stage(stage_args), 0)


if __name__ == "__main__":
    unittest.main()
