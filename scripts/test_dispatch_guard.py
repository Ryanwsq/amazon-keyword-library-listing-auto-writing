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
                         "title": guard.TITLES["sif"], "status": "idle"}
        self.contract_path = self.root / "contract.json"
        runtime.write_json(self.contract_path, self.contract)
        self.preflight = self.root / "preflight.json"
        runtime.write_json(self.preflight, {"schema": runtime.PREFLIGHT_SCHEMA, "providers": {
            p: {"status": "authenticated", "checked_at": "fixture"} for p in ("sif", "sellersprite")}})
        self.spec = {"run_id": self.run, "run_type": self.contract["run_type"], "revision": self.revision,
                     "execution_mode": "fresh-collection", "role": guard.ROLES["sif"], "stage": "sif",
                     "stage_key": self.contract["stages"]["sif"]["stage_key"],
                     "input_hashes": self.contract["input_hashes"],
                     "target": {k: v for k, v in self.observed.items() if k != "status"},
                     "output_root": str(self.target / ".local" / "runs" / self.run / guard.ROLES["sif"]),
                     "contract": guard.file_record(self.contract_path),
                     "dependency_files": [guard.file_record(self.preflight)],
                     "admission": {"status_dir": str(self.root / "status"), "preflight": str(self.preflight)}}

    def tearDown(self):
        os.chdir(self.cwd)
        self.head_patch.stop()
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
        self.assertEqual(output.returncode, 0, output.stdout + output.stderr)
        self.assertEqual(json.loads(output.stdout), self.spec)
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
