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
    def init_run(self, root: Path, run_id: str = "ALP-TEST-DE-LOGIN-GATE") -> Path:
        workbook = root / "input.xlsx"
        workbook.write_bytes(b"synthetic lock payload")
        run_dir = root / "run"
        pipeline_state.cmd_init(
            argparse.Namespace(
                input=str(workbook),
                run_dir=str(run_dir),
                run_id=run_id,
                product_asin="B0TEST0001",
                marketplace="Amazon-DE",
            )
        )
        return run_dir / "run-manifest.json"

    def confirm_session(
        self,
        manifest_path: Path,
        session: dict[str, object],
        index: int,
        *,
        status: str = "authenticated_web",
        task_id: str | None = None,
        observed_domain: str | None = None,
        postal_code: str | None = None,
        assistant: str | None = None,
        user_approval_ref: str | None = None,
        mcp_authenticated: bool = False,
    ) -> None:
        manifest = json.loads(manifest_path.read_text())
        evidence = Path(manifest["directories"]["evidence"]) / f"login-{index}.json"
        evidence.write_text(json.dumps({"session_key": session["session_key"], "authenticated": True}))
        provider = str(session["provider"])
        pipeline_state.cmd_confirm_login_session(
            argparse.Namespace(
                manifest=str(manifest_path),
                session_key=session["session_key"],
                task_id=task_id or f"task-{index}",
                host="test-host",
                dispatch_id=f"dispatch-{index}",
                status=status,
                observed_domain=observed_domain or session.get("expected_domain") or f"{provider}.example",
                postal_code=postal_code if postal_code is not None else session.get("expected_postal_code"),
                assistant=assistant if assistant is not None else session.get("expected_assistant"),
                evidence_file=str(evidence),
                user_approval_ref=user_approval_ref,
                mcp_authenticated=mcp_authenticated,
            )
        )

    def confirm_all_sessions(self, manifest_path: Path) -> None:
        manifest = json.loads(manifest_path.read_text())
        for index, session in enumerate(manifest["login_sessions"]["requirements"], start=1):
            self.confirm_session(manifest_path, session, index)

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

    def test_input_template_headers_are_locked_and_secret_free(self) -> None:
        template = Path(__file__).resolve().parents[1] / "assets" / "amazon-listing-pipeline-input-template.xlsx"
        reader = validate_input.XlsxReader(template)
        try:
            self.assertNotIn("运行配置", reader.sheets)
            product_rows, _, _ = reader.rows("新品基础信息")
            login_rows, _, _ = reader.rows("登录准备")
            self.assertEqual(product_rows[0], validate_input.REQUIRED_SHEETS["新品基础信息"])
            self.assertEqual(login_rows[0], validate_input.LOGIN_HEADERS)
            header_text = "|".join(str(value).lower() for value in login_rows[0])
            for forbidden in validate_input.FORBIDDEN_SECRET_HEADERS:
                self.assertNotIn(forbidden, header_text)
        finally:
            reader.close()

    def test_plaintext_password_header_is_rejected(self) -> None:
        errors: list[str] = []
        validate_input.reject_secret_headers("登录准备", [["服务", "账户密码"]], errors)
        self.assertEqual(len(errors), 1)

    def test_new_run_has_exact_task_session_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = self.init_run(Path(directory))
            manifest = json.loads(manifest_path.read_text())
            requirements = manifest["login_sessions"]["requirements"]
            self.assertEqual(len(requirements), 8)
            self.assertEqual(len({item["session_key"] for item in requirements}), 8)
            self.assertEqual(sum(item["provider"] == "amazon" for item in requirements), 6)

    def test_run_state_blocks_collection_until_all_logins_confirmed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = self.init_run(root)
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
            with self.assertRaisesRegex(ValueError, "login matrix"):
                pipeline_state.cmd_set_stage(stage_args)
            self.confirm_all_sessions(manifest_path)
            pipeline_state.cmd_finalize_login_gate(argparse.Namespace(manifest=str(manifest_path)))
            self.assertEqual(pipeline_state.cmd_set_stage(stage_args), 0)

    def test_one_task_binding_cannot_satisfy_two_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = self.init_run(Path(directory))
            requirements = json.loads(manifest_path.read_text())["login_sessions"]["requirements"]
            self.confirm_session(manifest_path, requirements[0], 1, task_id="same-task")
            with self.assertRaisesRegex(ValueError, "cannot satisfy two"):
                self.confirm_session(manifest_path, requirements[1], 2, task_id="same-task")

    def test_amazon_receipt_requires_locked_domain_and_postal_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = self.init_run(Path(directory))
            session = json.loads(manifest_path.read_text())["login_sessions"]["requirements"][0]
            with self.assertRaisesRegex(ValueError, "domain"):
                self.confirm_session(manifest_path, session, 1, observed_domain="amazon.com")
            with self.assertRaisesRegex(ValueError, "postal code"):
                self.confirm_session(manifest_path, session, 1, postal_code="10001")

    def test_sif_mcp_fallback_requires_user_approval_and_authentication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = self.init_run(Path(directory))
            requirements = json.loads(manifest_path.read_text())["login_sessions"]["requirements"]
            sif = next(item for item in requirements if item["provider"] == "sif")
            with self.assertRaisesRegex(ValueError, "approval"):
                self.confirm_session(
                    manifest_path,
                    sif,
                    1,
                    status="user_approved_same_provider_mcp",
                    mcp_authenticated=True,
                )
            with self.assertRaisesRegex(ValueError, "authentication"):
                self.confirm_session(
                    manifest_path,
                    sif,
                    1,
                    status="user_approved_same_provider_mcp",
                    user_approval_ref="user-message-1",
                )
            self.confirm_session(
                manifest_path,
                sif,
                1,
                status="user_approved_same_provider_mcp",
                user_approval_ref="user-message-1",
                mcp_authenticated=True,
            )

    def test_invalidated_session_blocks_only_its_dependent_stage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = self.init_run(Path(directory))
            self.confirm_all_sessions(manifest_path)
            pipeline_state.cmd_finalize_login_gate(argparse.Namespace(manifest=str(manifest_path)))
            pipeline_state.cmd_invalidate_login_session(
                argparse.Namespace(
                    manifest=str(manifest_path),
                    session_key="listing:product-audit:amazon",
                    reason="session expired",
                )
            )
            product_args = argparse.Namespace(
                manifest=str(manifest_path), stage="product_audit", status="running", message=None, output=None, force=False
            )
            keyword_args = argparse.Namespace(
                manifest=str(manifest_path), stage="keywords", status="running", message=None, output=None, force=False
            )
            with self.assertRaisesRegex(ValueError, "product-audit"):
                pipeline_state.cmd_set_stage(product_args)
            self.assertEqual(pipeline_state.cmd_set_stage(keyword_args), 0)


if __name__ == "__main__":
    unittest.main()
