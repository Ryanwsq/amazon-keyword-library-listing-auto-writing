"""Synthetic planner tests; no task or browser calls."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import dispatch_plan as planner
import pipeline_state as state


class DispatchPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.input = self.root / "input.xlsx"
        self.input.write_bytes(b"synthetic input")
        self.manifest = {"schema_version": "2.0", "run_id": "TEST-PLAN-01",
                         "input": {"locked_path": str(self.input), "sha256": state.sha256_file(self.input)},
                         "stages": {s: {"status": "pending", "outputs": []} for s in state.STAGES},
                         "login_sessions": state.build_login_sessions("Amazon-DE")}
        for session in self.manifest["login_sessions"]["requirements"]:
            session["status"] = "authenticated_web"
        for stage in ("preflight", "login_gate"):
            self.manifest["stages"][stage]["status"] = "completed"
        self.board = {"schema": "listing-dispatch-board/v1", "run_id": "TEST-PLAN-01", "jobs": {}}

    def tearDown(self):
        self.temp.cleanup()

    def plan(self):
        return planner.plan(self.manifest, self.board, "full_pipeline")

    def actions(self):
        return {r["node"]: r["action"] for r in self.plan()["nodes"]}

    def test_initial_four_branches_dispatch_together(self):
        result = self.plan()
        self.assertEqual({"product_audit", "market_insights", "pain_points", "keyword_library"},
                         {r["node"] for r in result["nodes"] if r["action"] == "dispatch"})
        self.assertFalse(result["wait_allowed"])

    def test_per_stage_login_does_not_wait_for_unrelated_sessions(self):
        self.manifest["login_gate_policy"] = "per-stage-20260914"
        self.manifest["stages"]["login_gate"]["status"] = "running"
        for session in self.manifest["login_sessions"]["requirements"]:
            if session["provider"] != "amazon":
                session["status"] = "pending"
        actions = self.actions()
        for node in ("product_audit", "market_insights", "pain_points", "keyword_library"):
            self.assertEqual(actions[node], "dispatch")

    def test_recovery_requires_single_active_owner_before_dispatch(self):
        self.manifest["runtime_repairs_version"] = "20260914"
        self.assertEqual(self.actions()["product_audit"], "bind_owner")
        self.assertFalse(self.plan()["wait_allowed"])

    def test_new_planner_stale_send_requires_actual_observation(self):
        self.manifest["runtime_repairs_version"] = "20260914"
        package = self.root / "owner-package.json"
        package.write_text(json.dumps({"role": "product-audit", "version": "synthetic"}))
        self.board["role_bindings"] = {"product-audit": [{"state": "active", "task_id": "task", "host": "local",
            "business_cwd": str(self.root), "package_manifest": str(package),
            "package_manifest_sha256": state.sha256_file(package)}]}
        row = next(item for item in self.plan()["nodes"] if item["node"] == "product_audit")
        proof = {k: row[k] for k in ("node", "role", "stage_key")}
        proof.update(run_id=self.manifest["run_id"], state="sent", dispatch_id="dispatch", task_id="task",
                     host="local", response={"threadId": "task"})
        path = self.root / "send.json"
        path.write_text(json.dumps(proof))
        self.board["jobs"]["product_audit"] = {"path": str(path), "sha256": state.sha256_file(path)}
        self.assertEqual(self.actions()["product_audit"], "inspect_activity")
        self.assertFalse(self.plan()["wait_allowed"])

    def test_keyword_send_does_not_hide_three_amazon_branches(self):
        row = next(r for r in self.plan()["nodes"] if r["node"] == "keyword_library")
        proof = {k: row[k] for k in ("node", "role", "stage_key")}
        proof.update(run_id=self.manifest["run_id"], state="sent", dispatch_id="synthetic-dispatch",
                     task_id="synthetic-task", host="local", response={"threadId": "synthetic-task"})
        path = self.root / "receipt.json"
        path.write_text(json.dumps(proof))
        self.board["jobs"]["keyword_library"] = {"path": str(path), "sha256": state.sha256_file(path)}
        self.assertEqual("in_flight", self.actions()["keyword_library"])
        self.assertEqual("dispatch", self.actions()["product_audit"])
        self.assertFalse(self.plan()["wait_allowed"])
        proof["state"] = "reserved"
        path.write_text(json.dumps(proof))
        self.board["jobs"]["keyword_library"]["sha256"] = state.sha256_file(path)
        self.assertEqual("reconcile_dispatch", self.actions()["keyword_library"])

    def test_failure_does_not_block_tag_or_keyword_branch(self):
        self.manifest["stages"]["market_insights"]["status"] = "completed"
        self.manifest["stages"]["product_audit"]["status"] = "failed"
        actions = self.actions()
        self.assertEqual("dispatch", actions["tag_priority"])
        self.assertEqual("dispatch", actions["keyword_library"])
        self.assertEqual("blocked", actions["selling_point_decision"])

    def test_login_gate_and_per_session_invalidation_remain(self):
        self.manifest["stages"]["login_gate"]["status"] = "pending"
        self.assertEqual("blocked", self.actions()["keyword_library"])
        self.manifest["stages"]["login_gate"]["status"] = "completed"
        self.manifest["login_sessions"]["requirements"][0]["status"] = "reauth_required"
        self.assertEqual("blocked", self.actions()["product_audit"])
        self.assertEqual("dispatch", self.actions()["market_insights"])

    def test_keyword_return_never_skips_sku_ready(self):
        self.assertEqual("blocked", self.actions()["sku_keywords"])
        self.manifest["stages"]["keywords"]["status"] = "running"
        self.assertEqual("blocked", self.actions()["sku_keywords"])

    def test_human_copy_and_independent_qa_not_auto_dispatched(self):
        actions = self.actions()
        self.assertEqual("blocked", actions["listing_draft"])
        self.assertEqual("blocked", actions["listing_generation"])
        self.assertEqual("main", next(r for r in self.plan()["nodes"] if r["node"] == "final_qa")["role"])

    def test_intake_roles_are_not_omitted(self):
        for stage in ("product_audit", "market_insights", "tag_priority", "pain_points"):
            self.manifest["stages"][stage]["status"] = "completed"
        self.assertEqual("dispatch", self.actions()["selling_point_intake"])
        self.assertEqual("dispatch", self.actions()["tag_painpoint_intake"])

    def test_old_run_or_changed_artifact_cannot_be_reused(self):
        self.board["run_id"] = "OLD-RUN"
        with self.assertRaisesRegex(ValueError, "identity"):
            self.plan()
        self.board["run_id"] = self.manifest["run_id"]
        self.manifest["stages"]["market_insights"].update(status="completed", outputs=[str(self.input)],
            output_sha256={str(self.input): "a" * 64})
        self.assertEqual("repair_lock", self.actions()["market_insights"])
        self.assertEqual("blocked", self.actions()["tag_priority"])

    def test_downstream_intake_does_not_create_fresh_browser_authority(self):
        result = planner.plan(self.manifest, self.board, "downstream_intake")
        keyword = next(r for r in result["nodes"] if r["node"] == "keyword_library")
        self.assertEqual("blocked", keyword["action"])
        self.assertIn("keyword_source_admission", {r["node"] for r in result["nodes"]})

    def test_completed_descendants_cannot_mask_stale_ancestor(self):
        for name in ("market_insights", "tag_priority", "product_audit", "pain_points", "keywords",
                     "selling_point_decision", "human_checkpoint"):
            self.manifest["stages"][name]["status"] = "completed"
        self.manifest["stages"]["market_insights"].update(outputs=[str(self.input)],
            output_sha256={str(self.input): "a" * 64})
        actions = self.actions()
        for name in ("market_insights", "tag_priority", "selling_point_decision", "human_checkpoint"):
            self.assertEqual("repair_lock", actions[name], name)
        self.assertEqual("completed", actions["product_audit"])
        self.assertEqual("completed", actions["pain_points"])
        self.assertFalse(self.plan()["wait_allowed"])

    def test_sku_completion_must_bind_current_06_bytes(self):
        self.manifest["stages"]["keywords"].update(status="completed", outputs=[str(self.input)],
            output_sha256={str(self.input): "a" * 64})
        self.assertEqual("repair_lock", self.actions()["sku_keywords"])

    def test_actual_send_wrapper_is_supported_but_failure_and_conflicts_are_not(self):
        wrapped = {"content": [{"type": "text", "text": '{"threadId":"synthetic-task"}'}], "isError": False}
        self.assertEqual("synthetic-task", planner.send_target(wrapped))
        self.assertIsNone(planner.send_target({"planned_task_id": "synthetic-task"}))
        with self.assertRaises(ValueError):
            planner.send_target(dict(wrapped, isError=True))
        with self.assertRaises(ValueError):
            planner.send_target(dict(wrapped, threadId="another-task"))

    def test_new_entry_cannot_silently_skip_reuse_but_siblings_still_start(self):
        self.manifest["execution_controls_version"] = "20260911"
        self.manifest["marketplace"] = "Amazon-DE"
        self.manifest["marketplace_route"] = state.MARKETPLACE_ROUTES["Amazon-DE"]
        self.assertEqual("blocked", self.actions()["keyword_library"])
        self.assertEqual("dispatch", self.actions()["market_insights"])
        self.assertEqual("main_action", self.actions()["keyword_entry_request"])
        request = {"protocol_id": "AKW-LISTING-INTERFACE-v1", "listing_run_id": self.manifest["run_id"],
                   "product_context": {"marketplace": self.manifest["marketplace"],
                                       "marketplace_route": self.manifest["marketplace_route"],
                                       "current_fact_sources": [{"path": str(self.input), "sha256": state.sha256_file(self.input)}]},
                   "keyword_entry": {"policy": "recent-library-reuse-first"}, "run_type": "test-validation"}
        path = self.root / "request.json"
        def register():
            path.write_text(json.dumps(request))
            self.board["keyword_request"] = {"path": str(path), "sha256": state.sha256_file(path)}
        register()
        self.assertEqual("dispatch", self.actions()["keyword_library"])
        request["keyword_entry"]["policy"] = "fresh-by-user-request"
        register()
        with self.assertRaisesRegex(ValueError, "explicit user"):
            self.plan()
        request["keyword_entry"]["source"] = {"path": str(self.input), "sha256": state.sha256_file(self.input), "locator": "synthetic user instruction"}
        register()
        self.assertEqual("dispatch", self.actions()["keyword_library"])


if __name__ == "__main__":
    unittest.main()
