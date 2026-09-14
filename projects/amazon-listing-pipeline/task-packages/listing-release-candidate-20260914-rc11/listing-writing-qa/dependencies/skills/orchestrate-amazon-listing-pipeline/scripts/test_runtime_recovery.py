"""Synthetic recovery regression; no browser, business collection or P1."""
import argparse
import copy
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import dispatch_plan
import pipeline_state as state
import runtime_recovery as recovery


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.package = self.lock("package.json", {"role": "product-audit", "version": "test", "files": []})
        self.owner = {"state": "active", "task_id": "synthetic-task", "host": "local",
                      "business_cwd": str(self.root), "package_manifest": self.package["path"],
                      "package_manifest_sha256": self.package["sha256"]}
        self.board = {"role_bindings": {"product-audit": [self.owner]}}
        self.manifest = {"run_id": "TEST-CURRENT"}
        self.proof = {"task_id": "synthetic-task", "host": "local", "dispatch_id": "dispatch-current"}

    def lock(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
        return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def observation(self, status="running", **extra):
        record = {**self.proof, "run_id": "TEST-CURRENT", "status": status,
                  "observed_at": datetime.now(timezone.utc).isoformat(), **extra}
        self.board["observations"] = {"audit": self.lock("observed.json", record)}

    def activity(self):
        return recovery.current_activity(self.manifest, self.board, "audit", self.proof, self.owner)[0]

    def test_duplicate_active_roles_block_but_retired_never_fallback(self):
        self.assertEqual(recovery.active_owner(self.board, "product-audit"), self.owner)
        duplicate = dict(self.owner, task_id="other")
        self.board["role_bindings"]["product-audit"].append(duplicate)
        with self.assertRaisesRegex(ValueError, "Exactly one"):
            recovery.active_owner(self.board, "product-audit")
        duplicate["state"] = "retired"
        self.assertEqual(recovery.active_owner(self.board, "product-audit"), self.owner)
        self.owner["business_cwd"] = str(self.root / "missing")
        with self.assertRaisesRegex(ValueError, "cwd missing"):
            recovery.active_owner(self.board, "product-audit")

    def test_old_sent_receipt_is_not_current_activity(self):
        self.assertEqual(self.activity(), "inspect_activity")
        self.observation()
        self.assertEqual(self.activity(), "in_flight")
        for status in ("idle", "completed", "needs_input"):
            self.observation(status)
            self.assertEqual(self.activity(), "resolve_or_resume")

    def test_wrong_run_owner_or_stale_observation_never_waits(self):
        self.observation(run_id="OLD-PRODUCT")
        self.assertEqual(self.activity(), "reconcile_dispatch")
        self.observation(observed_at=(datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat())
        self.assertEqual(self.activity(), "inspect_activity")
        self.observation(observed_at=(datetime.now(timezone.utc) + timedelta(minutes=3)).isoformat())
        self.assertEqual(self.activity(), "inspect_activity")
        self.observation()
        self.proof["task_id"] = "retired-task"
        self.assertEqual(self.activity(), "reconcile_dispatch")

    def test_changed_package_is_rejected(self):
        Path(self.package["path"]).write_text("{}")
        with self.assertRaisesRegex(ValueError, "package changed"):
            recovery.active_owner(self.board, "product-audit")

    def test_progress_preserves_status_outputs_and_gates(self):
        payload = {"schema_version": "2.0", "run_id": "TEST-CURRENT", "events": [],
                   "stages": {"product_audit": {"status": "running", "outputs": ["unchanged"]}},
                   "checkpoint": {"status": "waiting"}}
        lock = self.lock("run-manifest.json", payload)
        evidence = self.lock("checkpoint.json", {"completed_slots": ["synthetic-Q1"]})
        args = argparse.Namespace(manifest=lock["path"], stage="product_audit", message="slot saved",
                                  evidence=evidence["path"])
        state.cmd_update_progress(args)
        result = json.loads(Path(lock["path"]).read_text())
        self.assertEqual(result["stages"]["product_audit"]["status"], "running")
        self.assertEqual(result["stages"]["product_audit"]["outputs"], ["unchanged"])
        self.assertEqual(result["checkpoint"], payload["checkpoint"])
        result["stages"]["product_audit"]["status"] = "completed"
        Path(lock["path"]).write_text(json.dumps(result))
        with self.assertRaisesRegex(ValueError, "running stage"):
            state.cmd_update_progress(args)

    def test_quality_same_candidate_copy_not_same_basename(self):
        source = ".agents/skills/orchestrate-amazon-listing-pipeline/references/quality-gates.md"
        first = self.root / "main" / "quality-gates.md"
        second = self.root / "owner" / "quality-gates.md"
        for path in (first, second):
            path.parent.mkdir()
            path.write_text("synthetic same content")
        digest = hashlib.sha256(first.read_bytes()).hexdigest()
        def manifest(role):
            return {"role": role, "version": "test", "files": [
                {"source": source, "path": "quality-gates.md", "sha256": digest}]}
        main = self.lock("main/package.json", manifest("main"))
        owner = self.lock("owner/package.json", manifest("listing-writing-qa"))
        receipt = {"quality_contract_binding": {"main_manifest": main, "owner_manifest": owner}}
        rules = [{"path": str(second), "sha256": digest}]
        self.assertTrue(recovery.quality_contract_bound(rules, first, receipt))
        bad = manifest("listing-writing-qa")
        bad["version"] = "old"
        receipt["quality_contract_binding"]["owner_manifest"] = self.lock("owner/package.json", bad)
        self.assertFalse(recovery.quality_contract_bound(rules, first, receipt))

    def assignment(self):
        input_lock = self.lock("input.json", {"synthetic": True})
        run = {"run_id": "TEST-CURRENT", "marketplace": "Amazon-US", "input": {
            "product_asin": "B000000001", "locked_path": input_lock["path"], "sha256": input_lock["sha256"]}}
        rules_root = self.root / "separate-rules"
        rules_root.mkdir(exist_ok=True)
        return {"schema": "listing-runtime-assignment/v1", "run_id": "TEST-CURRENT", "role": "product-audit",
                "task_id": "synthetic-task", "host": "local", "dispatch_id": "dispatch-current", "mode": "START",
                "asin": "B000000001", "marketplace": "Amazon-US", "run_manifest": self.lock("run.json", run),
                "business": {"cwd": str(self.root), "git_root": str(self.root), "revision": "business-sha"},
                "rule_source": {"cwd": str(rules_root), "git_root": str(rules_root), "revision": "rules-sha"},
                "package_manifest": self.package, "package_version": "test", "read_locks": [input_lock],
                "write_files": [str(self.root / "new-output.xlsx")]}

    def verify(self, assignment, **kwargs):
        def git(argv, text):
            is_rules = "separate-rules" in argv[2]
            return ((argv[2] if argv[-1] == "--show-toplevel" else
                    "rules-sha" if is_rules else "business-sha") + "\n")
        with patch.object(recovery.subprocess, "check_output", side_effect=git):
            return recovery.verify_assignment(assignment, run_id="TEST-CURRENT", role="product-audit",
                                               task_id="synthetic-task", host="local", **kwargs)

    def test_separate_business_and_rule_roots_are_valid_and_readonly(self):
        assignment = self.assignment()
        self.assertEqual(self.verify(assignment)["status"], "ADMISSION_CHECKED")
        assignment["business"]["revision"] = "stale-sha"
        with self.assertRaisesRegex(ValueError, "revision changed"):
            self.verify(assignment)

    def test_history_access_old_run_and_prep_writes_rejected(self):
        assignment = self.assignment()
        with self.assertRaisesRegex(ValueError, "Read outside"):
            self.verify(assignment, reads=[str(self.root / "old-product.xlsx")])
        assignment["run_id"] = "OLD-PRODUCT"
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            self.verify(assignment)
        assignment["run_id"] = "TEST-CURRENT"
        assignment["mode"] = "PREP"
        with self.assertRaisesRegex(ValueError, "PREP"):
            self.verify(assignment, writes=assignment["write_files"])

    def test_existing_outputs_not_overwritten(self):
        assignment = self.assignment()
        Path(assignment["write_files"][0]).write_text("frozen output")
        with self.assertRaisesRegex(ValueError, "Preserve existing"):
            self.verify(assignment, writes=assignment["write_files"])

    def test_front_review_binds_exact_text_without_minimum_length(self):
        fact = self.lock("facts.json", {"synthetic": True})
        payload = {"title": "Synthetic Product", "item_highlights": "Useful Feature", "front_copy_review": {
            "bullet_count_rationale": "Five distinct buying reasons cover the facts"}}
        for field, limit in (("title", 75), ("item_highlights", 125)):
            text = payload[field]
            payload["front_copy_review"][field] = {"text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "characters": len(text), "remaining_budget": limit - len(text),
                "ordering_rationale": "Current ranked sources", "prefix_review": "Core identity first",
                "remaining_candidates_and_tradeoffs": "No further supported synthetic candidates",
                "buyer_understanding": "Specific understandable benefit",
                "source_refs": [{**fact, "locator": "synthetic fact"}]}
        locks = {str(Path(fact["path"]).resolve()): fact["sha256"]}
        recovery.verify_front_review(payload, locks)
        payload["title"] += " Filler"
        with self.assertRaisesRegex(ValueError, "binding mismatch"):
            recovery.verify_front_review(payload, locks)


if __name__ == "__main__":
    unittest.main()
