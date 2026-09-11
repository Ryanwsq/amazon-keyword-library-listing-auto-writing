#!/usr/bin/env python3
"""Synthetic source failures; no accounts, live sources or P1 claims."""
from pathlib import Path
import tempfile
import unittest
import zipfile

import runtime_contract as runtime
import source_execution as source


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="akw-source-check-")
        self.root = Path(self.temp.name).resolve()
        self.run = "AKW-SYNTHETIC-01"

    def tearDown(self):
        self.temp.cleanup()

    def record(self, name, value):
        path = self.root / name
        runtime.write_json(path, value)
        return {"path": str(path), "sha256": runtime.sha256_file(path)}

    def sif_proof(self):
        identity = {"run_id": self.run, "task_id": "synthetic-task", "host": "local"}
        authentication = dict(identity, schema="amazon-keyword-mcp-authentication/v1", provider="SIF",
                              entry_type="mcp", authenticated=True)
        return dict(identity, source_provider="SIF", reason="authenticated_export_failed", web_authenticated=True,
                    mcp_authenticated=True, user_approved=True,
                    authorization=self.record("authorization.json", {"fixture": "approved"}),
                    failure_evidence=self.record("failure.json", {"fixture": "export failure"}),
                    authentication_evidence=self.record("authentication.json", authentication))

    def test_rolling_window_never_infers_latest_calendar_month(self):
        lock = {"schema": source.QUERY_SCHEMA, "run_id": self.run, "marketplace": "Amazon-DE",
                "source_provider": "SellerSprite", "queries": ["synthetic seed"], "filters": {}, "entry_type": "web",
                "query_period": {"kind": "rolling-30-days", "source_label": "Recent 30 days"}}
        source.validate_query_lock(lock, self.run, "Amazon-DE", "sellersprite")
        for period in ({}, {"kind": "calendar-month", "source_label": "Example month"},
                       dict(lock["query_period"], calendar_month="2001-01")):
            with self.subTest(period=period), self.assertRaises(runtime.ContractError):
                source.validate_query_lock(dict(lock, query_period=period), self.run, "Amazon-DE", "sellersprite")
        with self.assertRaises(runtime.ContractError):
            source.validate_query_lock({k: v for k, v in lock.items() if k != "filters"}, self.run, "Amazon-DE", "sellersprite")

    def test_sif_export_failure_still_needs_user_approval_and_authentication(self):
        proof = self.sif_proof()
        self.assertFalse(source.sif_fallback(proof)["business_complete"])
        for key in ("web_authenticated", "mcp_authenticated", "user_approved"):
            with self.subTest(key=key), self.assertRaises(runtime.ContractError):
                source.sif_fallback(dict(proof, **{key: False}))
        with self.assertRaises(runtime.ContractError):
            source.sif_fallback(dict(proof, source_provider="Other"))

    def test_sif_authentication_evidence_identity_is_read_and_bound(self):
        proof = self.sif_proof()
        authentication = runtime.read_json(Path(proof["authentication_evidence"]["path"]))
        for field in ("run_id", "task_id", "host"):
            with self.subTest(field=field):
                foreign = self.record(f"foreign-{field}.json", dict(authentication, **{field: "synthetic-other"}))
                with self.assertRaisesRegex(runtime.ContractError, "authentication evidence Run/Task/host mismatch"):
                    source.sif_fallback(dict(proof, authentication_evidence=foreign))
                with self.assertRaisesRegex(runtime.ContractError, "identity required"):
                    source.sif_fallback(dict(proof, **{field: ""}))

    def test_sif_authentication_requires_mcp_true_and_no_secret_fields(self):
        proof = self.sif_proof()
        authentication = runtime.read_json(Path(proof["authentication_evidence"]["path"]))
        for field, value in (("authenticated", False), ("provider", "Other"), ("entry_type", "web"),
                             ("schema", "other-schema"), ("password", "not-a-real-secret")):
            with self.subTest(field=field):
                evidence = self.record(f"invalid-{field}.json", dict(authentication, **{field: value}))
                with self.assertRaises(runtime.ContractError):
                    source.sif_fallback(dict(proof, authentication_evidence=evidence))

    def test_autofilled_login_is_one_click_only_and_never_reads_values(self):
        observation = {"provider": "SIF", "previously_authenticated": True, "login_page": True,
                       "both_fields_autofilled": True, "attempts": 0, "challenge": False,
                       "wrong_account": False, "wrong_marketplace": False}
        self.assertEqual(source.login_recovery_action(observation)["action"], "click_login_once_then_reverify")
        for key, value in (("attempts", 1), ("both_fields_autofilled", False), ("challenge", True),
                           ("wrong_account", True), ("wrong_marketplace", True), ("previously_authenticated", False)):
            with self.subTest(key=key):
                self.assertEqual(source.login_recovery_action(dict(observation, **{key: value}))["action"], "awaiting_login")
        with self.assertRaises(runtime.ContractError):
            source.login_recovery_action(dict(observation, password="not-a-real-secret"))

    def test_matrix_claim_requires_each_cell_persisted(self):
        inputs = [f"synthetic input {i}" for i in range(75)]
        lock = {"run_id": self.run, "queries": inputs}
        evidence = self.record("visible.json", {"fixture": "visible empty suggestion area"})
        records = [{"input": text, "capture": self.record(f"capture-{i}.json", {
            "run_id": self.run, "input": text, "status": "no_suggestions", "suggestions": [],
            "visible_evidence": [evidence]})} for i, text in enumerate(inputs)]
        proof = {"run_id": self.run, "records": records}
        with self.assertRaisesRegex(runtime.ContractError, "population incomplete"):
            source.autocomplete_capture(dict(proof, records=records[:10]), lock)
        self.assertEqual(source.autocomplete_capture(proof, lock)["inputs"], 75)
        Path(records[-1]["capture"]["path"]).unlink()
        with self.assertRaises(OSError):
            source.autocomplete_capture(proof, lock)

    def test_official_export_gap_is_not_page_population_or_inferred_cap(self):
        path = self.root / "synthetic-export.xlsx"
        ns = source.NS["s"]
        with zipfile.ZipFile(path, "w") as book:
            book.writestr("xl/workbook.xml", f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Data" r:id="r1"/></sheets></workbook>')
            book.writestr("xl/_rels/workbook.xml.rels", '<Relationships><Relationship Id="r1" Target="worksheets/sheet1.xml"/></Relationships>')
            book.writestr("xl/worksheets/sheet1.xml", f'<worksheet xmlns="{ns}"><sheetData>' + ''.join(f'<row r="{i}"><c r="A{i}" t="inlineStr"><is><t>synthetic {i}</t></is></c></row>' for i in range(1, 4)) + '</sheetData></worksheet>')
        proof = {"official_export": {"path": str(path), "sha256": runtime.sha256_file(path)},
                 "sheet": "Data", "keyword_column": "A", "header_row": 1, "actual_rows": 2,
                 "page_declared_total": 5, "population_gap": 3, "completeness": "partial"}
        result = source.export_population(proof)
        self.assertEqual((result["actual_rows"], result["status"], result["cap_reason"]), (2, "partial", "not_inferred"))
        with self.assertRaisesRegex(runtime.ContractError, "cannot be complete"):
            source.export_population(dict(proof, completeness="complete"))
        with self.assertRaisesRegex(runtime.ContractError, "persisted export"):
            source.export_population(dict(proof, actual_rows=5))
        resolution = {"kind": "verified_declared_total_drift", "complete_export_verified": True,
                      "evidence": [self.record("coverage.json", {"fixture": "source confirms complete export"})]}
        closed = source.export_population(dict(proof, completeness="complete", coverage_resolution=resolution))
        self.assertEqual((closed["actual_rows"], closed["population_gap"], closed["status"]), (2, 3, "complete"))
        with self.assertRaisesRegex(runtime.ContractError, "export limit"):
            source.export_population(dict(proof, completeness="complete", coverage_resolution={"kind": "export_limit"}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
