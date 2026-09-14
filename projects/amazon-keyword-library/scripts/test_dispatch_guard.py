#!/usr/bin/env python3
"""Synthetic control-plane tests only; no live task/provider calls or P1 claims."""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import dispatch_guard as guard
import runtime_contract as runtime
from run_runtime_fixtures import spec as base_spec


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="akw-dispatch-test-")
        self.root = Path(self.temp.name).resolve()
        self.cwd = Path.cwd()
        self.run = "AKW-FIXTURE-DISPATCH-01"
        self.revision = "a" * 40
        self.head_patch = patch.object(guard, "head", return_value=self.revision)
        self.head_patch.start()
        self.root_patch = patch.object(guard, "git_root", side_effect=lambda path: self.target)
        self.root_patch.start()
        self.ledger = self.root / "main" / ".local" / "dispatch-control" / "journal.sqlite3"
        self.receiver = self.root / "receiver" / ".local" / "dispatch-control" / "journal.sqlite3"
        spec = base_spec()
        spec.update(run_id=self.run, revision=self.revision)
        self.contract = runtime.build_contract(spec)
        self.target = self.root / "owner-worktree"
        self.target.mkdir()
        for rule in self.contract["rules"]:
            source = runtime.ROOT / rule["owner"]
            destination = self.target / rule["owner"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        for owner in guard.REUSE_RULES:
            destination = self.target / owner
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(runtime.ROOT / owner, destination)
        self.observed = {"thread_id": "synthetic-task", "host": "local", "cwd": str(self.target),
                         "app_cwd": str(self.target), "git_root": str(self.target),
                         "title": guard.TITLES["sif"], "status": "idle"}
        self.contract_path = self.root / "contract.json"
        runtime.write_json(self.contract_path, self.contract)
        self.preflight = self.root / "preflight.json"
        runtime.write_json(self.preflight, {"schema": runtime.PREFLIGHT_SCHEMA, "providers": {
            p: {"status": "authenticated_mcp" if p in {"sif", "sellersprite"} else "authenticated", "checked_at": "fixture"}
            for p in ("amazon", "sif", "sellersprite")}})
        self.query = self.root / "query-lock.json"
        runtime.write_json(self.query, {"schema": guard.source.QUERY_SCHEMA, "run_id": self.run,
            "marketplace": self.contract["site"], "source_provider": "SIF", "queries": ["SYNTHETIC-ASIN"], "entry_type": "mcp",
            "source_policy": runtime.MCP_ERROR_ONLY_POLICY,
            "query_period": {"kind": "rolling-30-days", "source_label": "Recent 30 days"},
            "filters": {}, "limit_per_asin": 300})
        self.authentication = self.root / "authentication.json"
        runtime.write_json(self.authentication, {"schema": "amazon-keyword-mcp-authentication/v1",
            "run_id": self.run, "task_id": self.observed["thread_id"], "host": self.observed["host"],
            "provider": "SIF", "entry_type": "mcp", "authenticated": True})
        self.access = self.root / "source-access.json"
        runtime.write_json(self.access, {"schema": "amazon-keyword-source-access/v2",
            "run_id": self.run, "task_id": self.observed["thread_id"], "host": self.observed["host"],
            "source_provider": "SIF", "entry_type": "mcp", "query_lock_sha256": runtime.sha256_file(self.query),
            "authentication_evidence": guard.file_record(self.authentication)})
        self.spec = {"run_id": self.run, "run_type": self.contract["run_type"], "revision": self.revision,
                     "execution_mode": "fresh-collection", "role": guard.ROLES["sif"], "stage": "sif",
                     "stage_key": self.contract["stages"]["sif"]["stage_key"],
                     "input_hashes": self.contract["input_hashes"],
                     "target": {k: v for k, v in self.observed.items() if k != "status"},
                     "output_root": str(self.target / ".local" / "runs" / self.run / guard.ROLES["sif"]),
                     "contract": guard.file_record(self.contract_path),
                     "dependency_files": [guard.file_record(p) for p in (self.preflight, self.query, self.access)],
                     "admission": {"status_dir": str(self.root / "status"), "preflight": str(self.preflight),
                                   "query_lock": str(self.query), "source_access": str(self.access)}}

    def tearDown(self):
        os.chdir(self.cwd)
        self.head_patch.stop()
        self.root_patch.stop()
        self.temp.cleanup()

    def reserve(self, spec=None, observed=None):
        return guard.reserve(spec or self.spec, self.run, observed or self.observed, self.ledger)

    def envelope(self):
        return self.reserve()["envelope"]

    def event(self, envelope, status="running", seq=1):
        event = {k: envelope[k] for k in ("dispatch_id", "run_id", "role", "stage_key", "revision", "input_hashes", "output_root")}
        event.update(thread_id=self.observed["thread_id"], status=status, seq=seq, cursor=f"cursor-{seq}")
        return event

    def test_single_dispatch_and_no_duplicate_after_restart(self):
        first = self.reserve()
        self.assertTrue(first["allowed_to_send"])
        duplicate = self.reserve()
        self.assertFalse(duplicate["allowed_to_send"])
        self.assertEqual(first["dispatch_id"], duplicate["dispatch_id"])

    def scan(self):
        return guard.scan_ready({"contract_path": str(self.contract_path),
                                 "status_dir": str(self.root / "status"),
                                 "preflight": str(self.preflight)}, self.run, self.ledger)

    def complete_through(self, last):
        for stage in self.contract["stages"]:
            runtime.write_json(self.root / "status" / f"{stage}.json", {
                "schema": runtime.STATUS_SCHEMA, "stage": stage,
                "stage_key": self.contract["stages"][stage]["stage_key"], "status": "completed",
                "output_sha256": "a" * 64, "evidence_sha256": "b" * 64, "population": {"rows": 2}})
            if stage == last:
                break

    def test_all_parallel_waves_are_scanned_without_omissions(self):
        with guard.journal(self.ledger):
            pass
        for completed, expected in (("core-lock", {"amazon-autocomplete", "sellersprite"}),
                                    ("cleaning", {"word-frequency", "classification"}),
                                    ("classification", {"competition", "trend"})):
            self.complete_through(completed)
            result = self.scan()
            self.assertFalse(result["wait_allowed"])
            self.assertEqual(expected, {r["stage"] for r in result["stages"] if r["action"] == "dispatch"})

    def test_reserved_is_not_sent_and_cannot_allow_wait(self):
        self.reserve()
        self.assertEqual("reconcile_delivery", self.scan()["stages"][0]["action"])
        self.assertFalse(self.scan()["wait_allowed"])

    def test_missing_journal_requires_reconciliation_not_blind_resend(self):
        self.assertEqual("initialize_or_reconcile_ledger", self.scan()["action"])

    def test_sent_one_branch_does_not_hide_unsent_sibling(self):
        self.complete_through("core-lock")
        query = runtime.read_json(self.query)
        query["source_provider"] = "Amazon"
        query["entry_type"] = "web"
        runtime.write_json(self.query, query)
        target = dict(self.spec["target"], title=guard.TITLES["amazon-autocomplete"])
        request = {"contract_path": str(self.contract_path), "stage": "amazon-autocomplete",
                   "target": target, "output_root": self.spec["output_root"], "admission": self.spec["admission"]}
        dispatch = self.reserve(guard.build(request, self.run), dict(target, status="idle"))
        guard.sent(self.ledger, dispatch["dispatch_id"], {"dispatch_id": dispatch["dispatch_id"],
                   "thread_id": target["thread_id"], "response": {"threadId": target["thread_id"]}})
        actions = {r["stage"]: r["action"] for r in self.scan()["stages"]}
        self.assertEqual("in_flight", actions["amazon-autocomplete"])
        self.assertEqual("dispatch", actions["sellersprite"])
        self.assertFalse(self.scan()["wait_allowed"])

    def test_failure_isolates_only_descendants(self):
        with guard.journal(self.ledger):
            pass
        self.complete_through("classification")
        path = self.root / "status" / "word-frequency.json"
        record = runtime.read_json(path)
        record["status"] = "blocked"
        runtime.write_json(path, record)
        actions = {r["stage"]: r["action"] for r in self.scan()["stages"]}
        self.assertEqual("dispatch", actions["competition"])
        self.assertEqual("dispatch", actions["trend"])
        self.assertEqual("blocked", actions["assembly"])

    def test_old_stage_lock_and_duplicate_status_fail_closed(self):
        with guard.journal(self.ledger):
            pass
        self.complete_through("core-lock")
        path = self.root / "status" / "core-lock.json"
        record = runtime.read_json(path)
        record["stage_key"] = "f" * 64
        runtime.write_json(path, record)
        actions = {r["stage"]: r["action"] for r in self.scan()["stages"]}
        self.assertEqual("blocked", actions["sellersprite"])
        runtime.write_json(path.with_name("old-core-lock.json"), record)
        with self.assertRaisesRegex(runtime.ContractError, "duplicate or misnamed"):
            self.scan()

    def test_build_uses_contract_not_hand_copied_hashes(self):
        request = {"contract_path": str(self.contract_path), "stage": "sif", "target": self.spec["target"],
                   "output_root": self.spec["output_root"], "admission": self.spec["admission"]}
        self.assertEqual(guard.build(request, self.run), self.spec)
        with self.assertRaisesRegex(runtime.ContractError, "wrong build Run"):
            guard.build(request, "AKW-OTHER-01")

    def test_role_title_mapping_stays_with_owned_table(self):
        text = (runtime.ROOT / "docs" / "thread-roles.md").read_text()
        for stage, role in guard.ROLES.items():
            self.assertIn(f"| `{role}` | `{guard.TITLES[stage]}` |", text)

    def test_dirty_receiver_rule_fails_even_with_same_head(self):
        rule = self.contract["rules"][0]
        (self.target / rule["owner"]).write_text("drift")
        with self.assertRaisesRegex(runtime.ContractError, "receiver rule"):
            self.reserve()

    def test_not_logged_in_does_not_become_ready(self):
        preflight = runtime.read_json(self.preflight)
        preflight["providers"]["sif"]["status"] = "awaiting_login"
        runtime.write_json(self.preflight, preflight)
        self.spec["dependency_files"] = [guard.file_record(self.preflight)]
        with self.assertRaisesRegex(runtime.ContractError, "login not ready"):
            self.reserve()

    def test_concurrent_reservations_only_one_send(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.reserve(), range(4)))
        self.assertEqual(sum(r["allowed_to_send"] for r in results), 1)

    def test_different_stage_key_same_task_is_busy(self):
        self.reserve()
        changed = copy.deepcopy(self.spec)
        changed["stage_key"] = "b" * 64
        with patch.object(guard, "verify_admission"):
            with self.assertRaisesRegex(runtime.ContractError, "busy"):
                self.reserve(changed)

    def test_cross_run_same_task_is_busy(self):
        self.reserve()
        changed = copy.deepcopy(self.spec)
        changed["run_id"] = "AKW-FIXTURE-OTHER-01"
        changed["output_root"] = str(self.target / ".local" / "runs" / changed["run_id"] / changed["role"])
        with patch.object(guard, "verify_admission"):
            with self.assertRaisesRegex(runtime.ContractError, "busy"):
                guard.reserve(changed, changed["run_id"], self.observed, self.ledger)

    def test_wrong_run_target_role_revision_input_and_directory(self):
        tests = [("run_id", "AKW-OTHER-01"), ("role", guard.ROLES["cleaning"]),
                 ("revision", "b" * 40), ("output_root", str(self.root / "wrong")),
                 ("input_hashes", {k: "c" * 64 for k in self.spec["input_hashes"]})]
        for field, value in tests:
            with self.subTest(field=field):
                changed = copy.deepcopy(self.spec)
                changed[field] = value
                with self.assertRaises(runtime.ContractError):
                    self.reserve(changed)
        for field in ("thread_id", "host", "title", "cwd"):
            with self.subTest(target=field):
                changed = dict(self.observed, **{field: "wrong"})
                with self.assertRaises(runtime.ContractError):
                    self.reserve(observed=changed)

    def test_dependency_hash_and_contract_hash_checked(self):
        self.preflight.write_text("{}")
        with self.assertRaisesRegex(runtime.ContractError, "hash"):
            self.reserve()
        self.contract_path.write_text("{}")
        with self.assertRaisesRegex(runtime.ContractError, "hash"):
            self.reserve()

    def test_receiver_double_accept_cannot_execute_twice(self):
        envelope = self.envelope()
        os.chdir(self.target)
        self.assertTrue(guard.accept(envelope, self.run, self.observed, self.receiver)["execute"])
        self.assertFalse(guard.accept(envelope, self.run, self.observed, self.receiver)["execute"])

    def test_receiver_wrong_actual_cwd(self):
        envelope = self.envelope()
        os.chdir(self.root)
        with self.assertRaisesRegex(runtime.ContractError, "process cwd"):
            guard.accept(envelope, self.run, self.observed, self.receiver)

    def test_receiver_rejects_changed_envelope(self):
        envelope = self.envelope()
        envelope["output_root"] = str(self.root)
        with self.assertRaisesRegex(runtime.ContractError, "digest"):
            guard.accept(envelope, self.run, self.observed, self.receiver)

    def test_delta_duplicate_stale_and_conflict(self):
        envelope = self.envelope()
        event = self.event(envelope)
        self.assertTrue(guard.observe(self.ledger, self.run, event)["changed"])
        self.assertFalse(guard.observe(self.ledger, self.run, event)["changed"])
        later = dict(event, seq=3, cursor="cursor-3")
        self.assertFalse(guard.observe(self.ledger, self.run, later)["changed"])
        stale = dict(event, seq=2, cursor="cursor-2")
        self.assertFalse(guard.observe(self.ledger, self.run, stale)["changed"])
        with self.assertRaisesRegex(runtime.ContractError, "conflicting"):
            guard.observe(self.ledger, self.run, dict(later, status="blocked"))

    def test_login_and_error_are_never_suppressed(self):
        envelope = self.envelope()
        self.assertTrue(guard.observe(self.ledger, self.run, self.event(envelope))["changed"])
        self.assertTrue(guard.observe(self.ledger, self.run, self.event(envelope, "awaiting_login", 2))["changed"])
        self.assertTrue(guard.observe(self.ledger, self.run, self.event(envelope, "blocked", 3))["changed"])
        with self.assertRaisesRegex(runtime.ContractError, "terminal"):
            guard.observe(self.ledger, self.run, self.event(envelope, "running", 4))

    def test_wrong_run_return_not_silently_ignored(self):
        envelope = self.envelope()
        event = self.event(envelope)
        event["run_id"] = "AKW-OTHER-01"
        with self.assertRaisesRegex(runtime.ContractError, "wrong event run"):
            guard.observe(self.ledger, self.run, event)

    def test_completion_requires_current_output_and_population(self):
        envelope = self.envelope()
        event = self.event(envelope, "completed")
        with self.assertRaisesRegex(runtime.ContractError, "population"):
            guard.observe(self.ledger, self.run, event)
        wrong = self.root / "old-result.txt"
        wrong.write_text("synthetic")
        event.update(population={"rows": 1}, gaps=[], verification="owner_checks_completed", artifacts=[guard.file_record(wrong)])
        with self.assertRaisesRegex(runtime.ContractError, "outside"):
            guard.observe(self.ledger, self.run, event)

    def test_successful_completion_checks_real_hash_and_releases_target(self):
        envelope = self.envelope()
        output = Path(envelope["output_root"])
        output.mkdir(parents=True)
        artifact = output / "synthetic-result.json"
        runtime.write_json(artifact, {"fixture": True, "rows": 2})
        event = self.event(envelope, "completed_with_gaps")
        event.update(population={"rows": 2}, gaps=["synthetic missing value"],
                     verification="owner_checks_completed", artifacts=[guard.file_record(artifact)])
        self.assertTrue(guard.observe(self.ledger, self.run, event)["changed"])
        self.assertFalse(guard.observe(self.ledger, self.run, event)["changed"])
        changed = copy.deepcopy(self.spec)
        changed["stage_key"] = "b" * 64
        with patch.object(guard, "verify_admission"):
            self.assertTrue(self.reserve(changed)["allowed_to_send"])

    def test_artifact_hash_drift_prevents_completion(self):
        envelope = self.envelope()
        output = Path(envelope["output_root"])
        output.mkdir(parents=True)
        artifact = output / "synthetic-result.json"
        artifact.write_text("first")
        event = self.event(envelope, "completed")
        event.update(population={"rows": 1}, gaps=[], verification="owner_checks_completed", artifacts=[guard.file_record(artifact)])
        artifact.write_text("changed")
        with self.assertRaisesRegex(runtime.ContractError, "hash"):
            guard.observe(self.ledger, self.run, event)

    def test_explicit_resume_preserves_identity_and_sequence(self):
        envelope = self.envelope()
        guard.observe(self.ledger, self.run, self.event(envelope, "blocked", 2))
        proof = self.root / "resume.json"
        runtime.write_json(proof, {"dispatch_id": envelope["dispatch_id"], "thread_id": self.observed["thread_id"],
                                  "tool_call_id": "synthetic-call", "observed_task_status": "idle", "outcome": "resume_existing",
                                  "execution_stopped": True, "authorize_resume": True})
        result = guard.reconcile(self.ledger, self.run, envelope["dispatch_id"], guard.file_record(proof))
        self.assertTrue(result["resume_existing"])
        self.assertFalse(result["allowed_to_send"])
        self.assertTrue(guard.observe(self.ledger, self.run, self.event(envelope, "running", 3))["changed"])

    def test_closed_dispatch_cannot_be_reopened_by_late_identical_progress(self):
        envelope = self.envelope()
        event = self.event(envelope)
        guard.observe(self.ledger, self.run, event)
        proof = self.root / "close.json"
        runtime.write_json(proof, {"dispatch_id": envelope["dispatch_id"], "thread_id": self.observed["thread_id"],
                                  "tool_call_id": "synthetic-call", "observed_task_status": "idle",
                                  "outcome": "closed", "execution_stopped": True})
        guard.reconcile(self.ledger, self.run, envelope["dispatch_id"], guard.file_record(proof))
        with self.assertRaisesRegex(runtime.ContractError, "terminal"):
            guard.observe(self.ledger, self.run, dict(event, seq=2, cursor="late"))

    def test_uncertain_delivery_never_resends(self):
        envelope = self.envelope()
        proof = self.root / "reconcile.json"
        runtime.write_json(proof, {"dispatch_id": envelope["dispatch_id"], "thread_id": self.observed["thread_id"],
                                  "tool_call_id": "synthetic-call", "observed_task_status": "idle", "outcome": "unknown"})
        with self.assertRaisesRegex(runtime.ContractError, "no automatic resend"):
            guard.reconcile(self.ledger, self.run, envelope["dispatch_id"], guard.file_record(proof))
        self.assertFalse(self.reserve()["allowed_to_send"])

    def test_proven_not_sent_gets_only_one_retry_authorization(self):
        envelope = self.envelope()
        proof = self.root / "reconcile.json"
        runtime.write_json(proof, {"dispatch_id": envelope["dispatch_id"], "thread_id": self.observed["thread_id"],
                                  "tool_call_id": "synthetic-call", "observed_task_status": "idle",
                                  "outcome": "definitely_not_sent", "business_executed": False})
        self.assertTrue(guard.reconcile(self.ledger, self.run, envelope["dispatch_id"], guard.file_record(proof))["allowed_to_send"])
        with self.assertRaises(runtime.ContractError):
            guard.reconcile(self.ledger, self.run, envelope["dispatch_id"], guard.file_record(proof))
        receipt = {"dispatch_id": envelope["dispatch_id"], "thread_id": self.observed["thread_id"], "tool_call_id": "synthetic-call-2"}
        self.assertEqual(guard.sent(self.ledger, envelope["dispatch_id"], receipt)["state"], "sent")

    def test_send_receipt_can_use_actual_available_response(self):
        envelope = self.envelope()
        receipt = {"dispatch_id": envelope["dispatch_id"], "thread_id": self.observed["thread_id"],
                   "response": {"threadId": self.observed["thread_id"]}}
        self.assertEqual(guard.sent(self.ledger, envelope["dispatch_id"], receipt)["state"], "sent")

    def test_cli_build_and_wrong_ledger_fail_closed(self):
        request = self.root / "request.json"
        runtime.write_json(request, {"contract_path": str(self.contract_path), "stage": "sif", "target": self.spec["target"],
                                    "output_root": self.spec["output_root"], "admission": self.spec["admission"]})
        command = [sys.executable, str(runtime.ROOT / "scripts" / "dispatch_guard.py")]
        output = subprocess.run(command + ["build", "--run", self.run, "--input", str(request)],
                                cwd=self.root, capture_output=True, text=True)
        # The fixture directory is deliberately not a Git checkout. CLI must
        # now reject it before trying receiver rule files or any reservation.
        self.assertEqual(output.returncode, 2, output.stdout + output.stderr)
        output = subprocess.run(command + ["reserve", "--run", self.run, "--input", str(request),
                                           "--ledger", str(self.ledger)], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(output.returncode, 2)
        self.assertIn("fixed current-worktree journal", output.stdout)
        self.assertFalse(self.ledger.exists())

    def test_independent_task_not_blocked_by_other_target(self):
        self.envelope()
        changed = copy.deepcopy(self.spec)
        changed["target"]["thread_id"] = "synthetic-independent-task"
        changed["stage_key"] = "b" * 64
        observed = dict(self.observed, thread_id="synthetic-independent-task")
        with patch.object(guard, "verify_admission"):
            self.assertTrue(self.reserve(changed, observed)["allowed_to_send"])

    def test_reuse_branch_does_not_require_fresh_upstream_stages(self):
        changed = copy.deepcopy(self.spec)
        changed.update(stage="assembly", role=guard.ROLES["assembly"], execution_mode="recent-library-reuse")
        changed["target"]["title"] = guard.TITLES["assembly"]
        changed["output_root"] = str(self.target / ".local" / "runs" / self.run / changed["role"])
        contract = {k: changed[k] for k in ("run_id", "run_type", "revision", "input_hashes", "execution_mode")}
        contract.update(schema="amazon-keyword-recent-library-reuse/v1", qa_mode="full-regression",
                        rule_owner_hashes={owner: runtime.sha256_file(runtime.ROOT / owner) for owner in guard.REUSE_RULES})
        runtime.write_json(self.contract_path, contract)
        changed["contract"] = guard.file_record(self.contract_path)
        changed["stage_key"] = guard.digest({"contract": changed["contract"]["sha256"], "stage": "assembly", "executor": guard.VERSION})
        receipt = self.root / "reuse-review.json"
        runtime.write_json(receipt, {"run_id": self.run, "stage": "assembly", "contract_file_sha256": changed["contract"]["sha256"],
                                    "ready": True, "evidence_files": changed["dependency_files"]})
        changed["admission"] = {"receipt": guard.file_record(receipt)}
        observed = dict(self.observed, title=guard.TITLES["assembly"])
        with patch.object(runtime, "ready_for_stage", side_effect=AssertionError("fresh graph called")):
            self.assertTrue(self.reserve(changed, observed)["allowed_to_send"])

    def test_root_preflight_rejects_app_root_as_business_root(self):
        changed = copy.deepcopy(self.spec)
        changed["target"]["cwd"] = str(self.root)
        with self.assertRaisesRegex(runtime.ContractError, "business root"):
            self.reserve(changed, dict(changed["target"], status="idle"))

    def test_source_query_lock_is_mandatory_before_build(self):
        request = {"contract_path": str(self.contract_path), "stage": "sif", "target": self.spec["target"],
                   "output_root": self.spec["output_root"], "admission": {"status_dir": str(self.root / "status"),
                   "preflight": str(self.preflight)}}
        with self.assertRaisesRegex(runtime.ContractError, "query lock"):
            guard.build(request, self.run)

    def test_checkpoint_rejects_foreign_run_after_accept(self):
        envelope = self.envelope()
        os.chdir(self.target)
        guard.accept(envelope, self.run, self.observed, self.receiver)
        allowed = Path(envelope["output_root"]) / "checkpoint.json"
        allowed.parent.mkdir(parents=True)
        runtime.write_json(allowed, {"fixture": True})
        foreign = self.target / ".local" / "runs" / "AKW-FOREIGN-01" / "old.json"
        runtime.write_json(foreign, {"fixture": True})
        self.assertEqual(guard.checkpoint(envelope, self.run, self.observed, self.receiver,
                         [{"mode": "read", "path": str(allowed)}])["checkpoint"], "verified")
        for mode in ("read", "write"):
            with self.assertRaises(runtime.ContractError):
                guard.checkpoint(envelope, self.run, self.observed, self.receiver,
                                 [{"mode": mode, "path": str(foreign)}])
        with self.assertRaisesRegex(runtime.ContractError, "wrong current Run"):
            guard.checkpoint(envelope, "AKW-FOREIGN-01", self.observed, self.receiver,
                             [{"mode": "read", "path": str(foreign)}])

    def test_checkpoint_never_accepts_reserved_or_unfinished_login_state(self):
        envelope = self.envelope()
        os.chdir(self.target)
        with self.assertRaisesRegex(runtime.ContractError, "active dispatch"):
            guard.checkpoint(envelope, self.run, self.observed, self.ledger,
                             [{"mode": "read", "path": str(self.query)}])

    def test_actual_mcp_send_wrapper_is_not_a_planned_task_list(self):
        envelope = self.envelope()
        receipt = {"dispatch_id": envelope["dispatch_id"], "thread_id": self.observed["thread_id"],
                   "response": {"content": [{"type": "text", "text": json.dumps({"threadId": self.observed["thread_id"]})}]}}
        self.assertEqual(guard.sent(self.ledger, envelope["dispatch_id"], receipt)["state"], "sent")
        receipt["response"] = {"planned_tasks": [self.observed["thread_id"]]}
        with self.assertRaisesRegex(runtime.ContractError, "actual tool response"):
            guard.sent(self.ledger, envelope["dispatch_id"], receipt)

    def test_cli_reserve_output_collision_leaves_no_ledger(self):
        folder = self.root / ".local" / "runs" / self.run
        spec_path = folder / "spec.json"
        observed_path = folder / "observed.json"
        runtime.write_json(spec_path, self.spec)
        runtime.write_json(observed_path, self.observed)
        ledger = self.root / ".local" / "dispatch-control" / "journal.sqlite3"
        result = subprocess.run([sys.executable, str(runtime.ROOT / "scripts" / "dispatch_guard.py"),
            "reserve", "--run", self.run, "--input", str(spec_path), "--observed", str(observed_path),
            "--ledger", str(ledger), "--out", str(spec_path)], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("separate envelope path", result.stdout)
        self.assertFalse(ledger.exists())
        self.assertEqual(runtime.read_json(spec_path), self.spec)

    def test_autocomplete_completion_does_not_accept_memory_only_population(self):
        self.complete_through("core-lock")
        query = runtime.read_json(self.query)
        query.update(source_provider="Amazon", entry_type="web", queries=[f"synthetic input {i}" for i in range(75)])
        runtime.write_json(self.query, query)
        target = dict(self.spec["target"], title=guard.TITLES["amazon-autocomplete"])
        request = {"contract_path": str(self.contract_path), "stage": "amazon-autocomplete", "target": target,
                   "output_root": self.spec["output_root"], "admission": self.spec["admission"]}
        envelope = self.reserve(guard.build(request, self.run), dict(target, status="idle"))["envelope"]
        proof = Path(envelope["output_root"]) / "source-evidence.json"
        runtime.write_json(proof, {"run_id": self.run, "records": [{"input": q} for q in query["queries"][:10]]})
        record = guard.file_record(proof)
        event = self.event(envelope, "completed_with_gaps")
        event.update(population={"inputs": 75, "events": 0}, gaps=[], verification="owner_checks_completed",
                     source_evidence=record, artifacts=[record])
        with self.assertRaisesRegex(runtime.ContractError, "matrix population incomplete"):
            guard.observe(self.ledger, self.run, event)

    def test_sif_primary_binds_target_task_and_host_without_exception_approval(self):
        authentication = runtime.read_json(self.authentication)
        proof = runtime.read_json(self.access)
        request = {"contract_path": str(self.contract_path), "stage": "sif", "target": self.spec["target"],
                   "output_root": self.spec["output_root"], "admission": self.spec["admission"]}
        guard.build(request, self.run)
        for field in ("task_id", "host"):
            # Even mutually matching foreign proof/auth files cannot be wrapped
            # as this target's authentication by a current-Run query lock.
            foreign_auth = dict(authentication, **{field: "synthetic-other"})
            runtime.write_json(self.authentication, foreign_auth)
            foreign_proof = dict(proof, **{field: "synthetic-other"}, authentication_evidence=guard.file_record(self.authentication))
            runtime.write_json(self.access, foreign_proof)
            with self.subTest(field=field), self.assertRaisesRegex(runtime.ContractError, "bind current Run/target Task/host"):
                guard.build(request, self.run)

    def test_new_sif_dispatch_rejects_web_login_as_mcp_authentication(self):
        preflight = runtime.read_json(self.preflight)
        preflight["providers"]["sif"]["status"] = "authenticated_web"
        runtime.write_json(self.preflight, preflight)
        self.spec["dependency_files"] = [guard.file_record(p) for p in (self.preflight, self.query, self.access)]
        with self.assertRaisesRegex(runtime.ContractError, "preflight entry"):
            self.reserve()

    def test_mcp_to_web_fallback_relocks_stage_and_preserves_old_dispatch(self):
        original = self.envelope()
        original_hash = guard.file_record(self.contract_path)
        web_query = self.root / "web-query.json"
        query = runtime.read_json(self.query)
        query["entry_type"] = "web"
        runtime.write_json(web_query, query)
        auth = runtime.read_json(self.authentication)
        auth.update(schema="amazon-keyword-web-authentication/v1", entry_type="web")
        auth_path = self.root / "web-auth.json"
        runtime.write_json(auth_path, auth)
        raw = self.root / "failure-raw.json"
        runtime.write_json(raw, {"fixture": "MCP transport unavailable"})
        failure_path = self.root / "failure.json"
        runtime.write_json(failure_path, {"schema": "amazon-keyword-mcp-error/v1", "run_id": self.run,
            "task_id": self.observed["thread_id"], "host": self.observed["host"], "provider": "SIF",
            "entry_type": "mcp", "is_error": True, "error_code": "transport_error", "query_lock_sha256": runtime.sha256_file(self.query),
            "evidence": [guard.file_record(raw)]})
        notice_path = self.root / "login-notice.json"
        runtime.write_json(notice_path, {"schema": "amazon-keyword-web-login-notice/v1", "run_id": self.run,
            "task_id": self.observed["thread_id"], "host": self.observed["host"], "provider": "SIF", "login_requested": True})
        web_access = self.root / "web-access.json"
        access = runtime.read_json(self.access)
        access.update(entry_type="web", query_lock_sha256=runtime.sha256_file(web_query),
                      authentication_evidence=guard.file_record(auth_path), reason="mcp_error",
                      primary_query_lock=guard.file_record(self.query), mcp_error_evidence=guard.file_record(failure_path),
                      completed_queries=[], login_notice=guard.file_record(notice_path))
        runtime.write_json(web_access, access)
        web_preflight = self.root / "web-preflight.json"
        preflight = runtime.read_json(self.preflight)
        preflight["providers"]["sif"]["status"] = "authenticated_web"
        runtime.write_json(web_preflight, preflight)
        request = {"contract_path": str(self.contract_path), "stage": "sif", "target": self.spec["target"],
                   "output_root": self.spec["output_root"], "admission": dict(self.spec["admission"],
                       query_lock=str(web_query), source_access=str(web_access), preflight=str(web_preflight))}
        with self.assertRaisesRegex(runtime.ContractError, "new query-addressed stage lock"):
            guard.build(request, self.run)
        new_spec = dict(base_spec(), run_id=self.run, revision=self.revision)
        new_spec["locks"]["sif_query_lock_sha256"] = runtime.sha256_file(web_query)
        next_contract = runtime.build_contract(new_spec)
        next_path = self.root / "web-contract.json"
        runtime.write_json(next_path, next_contract)
        request["contract_path"] = str(next_path)
        spec = guard.build(request, self.run)
        self.assertNotEqual(spec["stage_key"], original["stage_key"])
        with self.assertRaisesRegex(runtime.ContractError, "busy/unresolved"):
            self.reserve(spec)
        close = self.root / "close.json"
        runtime.write_json(close, {"dispatch_id": original["dispatch_id"], "thread_id": self.observed["thread_id"],
                                  "tool_call_id": "synthetic-call", "observed_task_status": "idle",
                                  "outcome": "closed", "execution_stopped": True})
        guard.reconcile(self.ledger, self.run, original["dispatch_id"], guard.file_record(close))
        self.assertTrue(self.reserve(spec)["allowed_to_send"])
        self.assertEqual(guard.file_record(self.contract_path), original_hash)

    def test_new_dispatch_cannot_choose_missing_or_web_first_policy(self):
        for policies in ({}, {"sif_competitor": "web-first"}):
            with self.subTest(policies=policies), self.assertRaisesRegex(runtime.ContractError, "MCP-first"):
                runtime.build_contract(dict(base_spec(), source_policies=policies))
        legacy = copy.deepcopy(self.contract)
        legacy.pop("source_policies")
        legacy["contract_version"] = "runtime-contract/1.2.0"
        runtime.compute_stage_keys(legacy)
        legacy["contract_sha256"] = guard.digest({k: v for k, v in legacy.items() if k != "contract_sha256"})
        runtime.verify_contract(legacy)  # Historical hash algorithm remains readable.
        runtime.write_json(self.contract_path, legacy)
        self.spec.update(contract=guard.file_record(self.contract_path), stage_key=legacy["stages"]["sif"]["stage_key"])
        with self.assertRaisesRegex(runtime.ContractError, "new dispatch reservations"):
            self.reserve()
        request = {"contract_path": str(self.contract_path), "stage": "sif", "target": self.spec["target"],
                   "output_root": self.spec["output_root"], "admission": self.spec["admission"]}
        with self.assertRaisesRegex(runtime.ContractError, "new dispatch builds"):
            guard.build(request, self.run)

    def test_legacy_locked_web_envelope_remains_verifiable(self):
        legacy = copy.deepcopy(self.contract)
        legacy.pop("source_policies")
        legacy["contract_version"] = "runtime-contract/1.2.0"
        runtime.compute_stage_keys(legacy)
        legacy["contract_sha256"] = guard.digest({k: v for k, v in legacy.items() if k != "contract_sha256"})
        runtime.write_json(self.contract_path, legacy)
        query = runtime.read_json(self.query)
        query.pop("source_policy")
        query["entry_type"] = "web"
        runtime.write_json(self.query, query)
        self.spec.update(contract=guard.file_record(self.contract_path), stage_key=legacy["stages"]["sif"]["stage_key"],
                         dependency_files=[guard.file_record(p) for p in (self.preflight, self.query)])
        envelope = dict(self.spec, schema=guard.VERSION)
        envelope["dispatch_id"] = guard.digest(envelope)
        guard.validate(envelope, self.run, self.observed)

    def test_send_errors_are_rejected_in_all_result_wrappers(self):
        envelope = self.envelope()
        task_id = self.observed["thread_id"]
        error = {"threadId": task_id, "error": "synthetic send failure"}
        is_error = {"threadId": task_id, "isError": True}
        cases = [error, is_error, {"structuredContent": error}, {"structuredContent": is_error},
                 {"content": [{"type": "text", "text": json.dumps(error)}]},
                 {"content": [{"type": "text", "text": json.dumps(is_error)}]},
                 {"threadId": task_id, "content": [{"type": "text", "error": "synthetic failure"}]},
                 {"threadId": task_id, "content": [{"type": "text", "text": json.dumps({"structuredContent": error})}]}]
        for response in cases:
            receipt = {"dispatch_id": envelope["dispatch_id"], "thread_id": task_id,
                       "tool_call_id": "synthetic-call", "response": response}
            with self.subTest(response=response), self.assertRaisesRegex(runtime.ContractError, "reported an error"):
                guard.sent(self.ledger, envelope["dispatch_id"], receipt)
            with guard.journal(self.ledger) as db:
                self.assertEqual(guard.load_job(db, envelope["dispatch_id"])[0], "reserved")

    def test_send_structured_response_supports_success_but_rejects_target_conflicts(self):
        envelope = self.envelope()
        task_id = self.observed["thread_id"]
        receipt = {"dispatch_id": envelope["dispatch_id"], "thread_id": task_id}
        for response in ({"threadId": task_id, "structuredContent": {"threadId": "synthetic-other"}},
                         {"structuredContent": {"threadId": task_id}, "content": [{"type": "text", "text": json.dumps({"threadId": "synthetic-other"})}]}):
            with self.subTest(response=response), self.assertRaisesRegex(runtime.ContractError, "conflicting actual send response"):
                guard.sent(self.ledger, envelope["dispatch_id"], dict(receipt, response=response))
        result = guard.sent(self.ledger, envelope["dispatch_id"],
                            dict(receipt, response={"structuredContent": {"threadId": task_id, "isError": False}}))
        self.assertEqual(result["state"], "sent")


if __name__ == "__main__":
    unittest.main(verbosity=2)
