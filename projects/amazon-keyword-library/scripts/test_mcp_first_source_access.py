"""Synthetic current routing boundary tests; no live source or account access."""
import copy
from pathlib import Path
import test_source_execution
import unittest
import runtime_contract as runtime
import source_execution as source


class CurrentAccessTests(unittest.TestCase):
    setUp = test_source_execution.SourceTests.setUp
    tearDown = test_source_execution.SourceTests.tearDown
    record = test_source_execution.SourceTests.record
    primary = test_source_execution.SourceTests.primary
    def current(self, stage, web=False):
        provider = {"sif": "SIF", "sellersprite": "SellerSprite"}[stage]
        proof, query = self.primary()
        q = runtime.read_json(Path(query["path"]))
        q.update(source_provider=provider, source_policy=runtime.MCP_ERROR_ONLY_POLICY)
        if stage == "sellersprite":
            q.pop("limit_per_asin")
        primary = self.record("current-query.json", q)
        identity = {k: proof[k] for k in ("run_id", "task_id", "host")}
        proof.update(schema="amazon-keyword-source-access/v2", source_provider=provider,
                     query_lock_sha256=primary["sha256"], authentication_evidence=self.record("current-auth.json",
                         dict(identity, schema="amazon-keyword-mcp-authentication/v1", provider=provider,
                              entry_type="mcp", authenticated=True)))
        if not web:
            return proof, primary
        q.update(entry_type="web", queries=["SYNTHETIC-B"])
        query = self.record("current-web-query.json", q)
        error = dict(identity, schema="amazon-keyword-mcp-error/v1", provider=provider, entry_type="mcp",
                     is_error=True, error_code="transport_timeout", query_lock_sha256=primary["sha256"],
                     evidence=[self.record("raw-error.json", {"isError": True, "message": "synthetic timeout"})])
        proof.update(entry_type="web", query_lock_sha256=query["sha256"], primary_query_lock=primary,
                     completed_queries=["SYNTHETIC-A"], reason="mcp_error",
                     mcp_error_evidence=self.record("current-error.json", error),
                     login_notice=self.record("notice.json", dict(identity, schema="amazon-keyword-web-login-notice/v1",
                         provider=provider, login_requested=True)),
                     authentication_evidence=self.record("current-web-auth.json", dict(identity,
                         schema="amazon-keyword-web-authentication/v1", provider=provider, entry_type="web", authenticated=True)))
        return proof, query

    def test_both_sources_mcp_without_website_login(self):
        for stage in ("sif", "sellersprite"):
            proof, query = self.current(stage)
            self.assertEqual("authenticated_mcp", source.mcp_first_source_access(proof, query["path"], stage)["status"])

    def test_error_then_login_allows_only_remaining_original_queries(self):
        for stage in ("sif", "sellersprite"):
            proof, query = self.current(stage, True)
            self.assertEqual("authenticated_web", source.mcp_first_source_access(proof, query["path"], stage)["status"])
            for field in ("mcp_error_evidence", "login_notice", "authentication_evidence"):
                changed = {k:v for k,v in proof.items() if k != field}
                with self.subTest(stage=stage, missing=field), self.assertRaises(runtime.ContractError):
                    source.mcp_first_source_access(changed, query["path"], stage)
            changed = copy.deepcopy(proof)
            changed["completed_queries"] = []
            with self.assertRaises(runtime.ContractError):
                source.mcp_first_source_access(changed, query["path"], stage)

    def test_nonerror_gaps_zero_and_foreign_evidence_cannot_fallback(self):
        for stage in ("sif", "sellersprite"):
            proof, query = self.current(stage, True)
            for reason in ("mcp_incomplete", "zero_results", "missing_fields", "mcp_unavailable"):
                with self.subTest(stage=stage, reason=reason), self.assertRaises(runtime.ContractError):
                    source.mcp_first_source_access(dict(proof, reason=reason), query["path"], stage)
            original = runtime.read_json(Path(proof["mcp_error_evidence"]["path"]))
            for override in ({"is_error": False}, {"is_error": 1}, {"provider": "other"}, {"task_id": "other"}, {"error_code": ""}, {"evidence": []}):
                lock = self.record("invalid-error.json", dict(original, **override))
                with self.subTest(stage=stage, override=override), self.assertRaises(runtime.ContractError):
                    source.mcp_first_source_access(dict(proof, mcp_error_evidence=lock), query["path"], stage)


if __name__ == "__main__":
    unittest.main()
