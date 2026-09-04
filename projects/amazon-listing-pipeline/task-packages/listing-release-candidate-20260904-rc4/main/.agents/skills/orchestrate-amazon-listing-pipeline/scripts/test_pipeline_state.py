"""Behavioral tests for the copy approval gate; all fixtures stay in temp dirs."""
import argparse
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("pipeline", Path(__file__).with_name("pipeline_state.py"))
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


class CopyGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="listing-copy-test-")
        self.root = Path(self.temp.name)
        self.facts = self.root / "00_锁定输入.xlsx"
        self.cal = self.root / "07_核心卖点决策包.xlsx"
        self.kw = self.root / "06_SKU可用关键词库.xlsx"
        self.extra = self.root / "user-facts.json"
        for path in (self.facts, self.cal, self.kw, self.extra):
            path.write_bytes(("test fixture: " + path.name).encode())
        self.manifest = {
            "schema_version":"2.0", "run_id":"TEST-RUN-A", "updated_at":None,
            "input":{"locked_path":str(self.facts),"sha256":pipeline.sha256_file(self.facts),"product_asin":"B0TEST0001","user_fact_supplements":[{"path":str(self.extra),"sha256":pipeline.sha256_file(self.extra)}]},
            "stages":{s:{"status":"pending","outputs":[],"started_at":None,"ended_at":None,"message":""} for s in pipeline.STAGES},
            "checkpoint":{"status":"confirmed","confirmed_scope":list(pipeline.CALIBRATION_SCOPE),"calibration_file":str(self.cal),"calibration_sha256":pipeline.sha256_file(self.cal)},
            "copy_checkpoint":{"status":"pending"}, "events":[],
        }
        self.manifest["stages"]["human_checkpoint"]["status"]="completed"
        self.manifest["stages"]["keywords"].update(status="completed",outputs=[str(self.kw)],output_sha256={str(self.kw):pipeline.sha256_file(self.kw)})
        self.manifest["stages"]["keyword_allocation"]["status"]="completed"
        self.path=self.root/"run-manifest.json"
        self.draft=self.root/"copy-draft.json"
        self.payload={"run_id":"TEST-RUN-A","asin":"B0TEST0001","revision":"v01","title":"Example Chair","item_highlights":"Defined material supports everyday desk use","bullet_points":["Evidence: "+("A clear supported use description "*25) for _ in range(5)],"source_locks":[{"path":str(p),"sha256":pipeline.sha256_file(p)} for p in (self.facts,self.extra,self.kw,self.cal)]}
        self.draft.write_text(json.dumps(self.payload))
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        pipeline.atomic_write(self.path,self.manifest)

    def confirm(self):
        self.manifest["stages"]["listing_draft"].update(status="completed",outputs=[str(self.draft)],output_sha256={str(self.draft):pipeline.sha256_file(self.draft)})
        self.save()
        with contextlib.redirect_stdout(io.StringIO()):
            pipeline.cmd_confirm_copy(argparse.Namespace(manifest=str(self.path),copy_file=str(self.draft),confirmed_by="User",note="test explicit approval"))
        self.manifest=pipeline.load_manifest(self.path)

    def test_blocks_final_before_copy_approval(self):
        with self.assertRaisesRegex(ValueError,"User must confirm"):
            pipeline.verify_copy_lock(self.manifest)

    def test_force_stage_does_not_bypass_copy_approval(self):
        with self.assertRaisesRegex(ValueError,"User must confirm"):
            pipeline.cmd_set_stage(argparse.Namespace(manifest=str(self.path),stage="listing_generation",status="running",force=True,message=None,output=[]))

    def test_draft_requires_keyword_plan(self):
        self.manifest["stages"]["keyword_allocation"]["status"]="pending"
        self.save()
        with self.assertRaisesRegex(ValueError,"allocation plan must complete"):
            pipeline.cmd_set_stage(argparse.Namespace(manifest=str(self.path),stage="listing_draft",status="running",force=False,message=None,output=[]))

    def test_final_qa_requires_completed_listing(self):
        self.confirm()
        with self.assertRaisesRegex(ValueError,"listing output must complete"):
            pipeline.cmd_set_stage(argparse.Namespace(manifest=str(self.path),stage="final_qa",status="completed",force=True,message=None,output=[]))

    def test_init_defaults_to_version2_without_mutating_input(self):
        before=self.facts.read_bytes()
        target=self.root/"new-run"
        with contextlib.redirect_stdout(io.StringIO()):
            pipeline.cmd_init(argparse.Namespace(input=str(self.facts),run_dir=str(target),run_id="TEST-NEW-RUN",product_asin="B0TEST0001",marketplace="Amazon-DE"))
        created=pipeline.load_manifest(target/"run-manifest.json")
        self.assertEqual("2.0",created["schema_version"])
        self.assertEqual("v2.2",created["writing_rules_version"])
        self.assertEqual("coverage_based_5_to_6",created["bullet_count_policy"])
        self.assertIn("copy_checkpoint",created["stages"])
        self.assertEqual("B0TEST0001",created["input"]["product_asin"])
        self.assertEqual("Amazon-DE",created["marketplace"])
        self.assertEqual(8,len(created["login_sessions"]["requirements"]))
        self.assertEqual(before,self.facts.read_bytes())

    def test_complete_approval_locks_exact_copy_and_sources(self):
        self.confirm()
        pipeline.verify_copy_lock(self.manifest)
        self.assertEqual(7,len(self.manifest["copy_checkpoint"]["confirmed_scope"]))

    def test_project_no_longer_imposes_500_character_bullet_cap(self):
        self.assertGreater(len(self.payload["bullet_points"][0]),500)
        self.confirm()
        pipeline.verify_copy_lock(self.manifest)

    def test_changed_title_invalidates_copy(self):
        self.confirm()
        self.payload["title"]="Changed Chair"
        self.draft.write_text(json.dumps(self.payload))
        with self.assertRaisesRegex(ValueError,"Confirmed copy changed"):
            pipeline.verify_copy_lock(self.manifest)

    def test_changed_keyword_source_blocks_approved_copy(self):
        self.confirm()
        self.kw.write_bytes(b"new keyword source")
        with self.assertRaisesRegex(ValueError,"source changed"):
            pipeline.verify_copy_lock(self.manifest)

    def test_new_draft_cannot_relabel_an_unaccepted_changed_keyword_file(self):
        self.kw.write_bytes(b"unaccepted replacement")
        for item in self.payload["source_locks"]:
            if item["path"]==str(self.kw):item["sha256"]=pipeline.sha256_file(self.kw)
        self.draft.write_text(json.dumps(self.payload))
        with self.assertRaisesRegex(ValueError,"all product fact locks"):
            pipeline.verify_copy_payload(self.manifest,self.draft)

    def test_changed_user_facts_block_approved_copy(self):
        self.confirm()
        self.extra.write_bytes(b"new facts")
        with self.assertRaisesRegex(ValueError,"source changed"):
            pipeline.verify_copy_lock(self.manifest)

    def test_changed_calibration_blocks_approved_copy(self):
        self.confirm()
        self.manifest["checkpoint"]["calibration_sha256"]="different"
        with self.assertRaisesRegex(ValueError,"07 changed"):
            pipeline.verify_copy_lock(self.manifest)

    def test_cross_run_draft_rejected(self):
        self.payload["run_id"]="TEST-RUN-B"
        self.draft.write_text(json.dumps(self.payload))
        with self.assertRaisesRegex(ValueError,"Run_ID mismatch"):
            pipeline.verify_copy_payload(self.manifest,self.draft)

    def test_missing_bullet_rejected(self):
        self.payload["bullet_points"].pop()
        self.draft.write_text(json.dumps(self.payload))
        with self.assertRaisesRegex(ValueError,"exactly five"):
            pipeline.verify_copy_payload(self.manifest,self.draft)

    def test_missing_overlay_lock_rejected(self):
        self.payload["source_locks"]=[x for x in self.payload["source_locks"] if x["path"]!=str(self.extra)]
        self.draft.write_text(json.dumps(self.payload))
        with self.assertRaisesRegex(ValueError,"all product fact locks"):
            pipeline.verify_copy_payload(self.manifest,self.draft)

    def test_reopen_preserves_prior_artifacts_and_history(self):
        self.confirm()
        before=self.draft.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            pipeline.cmd_reopen_copy(argparse.Namespace(manifest=str(self.path),reason="user requested revision"))
        result=pipeline.load_manifest(self.path)
        self.assertEqual(before,self.draft.read_bytes())
        self.assertEqual("confirmed",result["copy_confirmation_history"][0]["status"])
        self.assertEqual("WAITING_COPY_CONFIRMATION",pipeline.derive_overall_status(result))
        with self.assertRaises(ValueError):pipeline.verify_copy_lock(result)

    def test_version1_completed_run_stays_compatible(self):
        legacy=copy.deepcopy(self.manifest)
        legacy["schema_version"]="1.0"
        legacy.pop("copy_checkpoint")
        legacy["stages"].pop("copy_checkpoint")
        legacy["stages"].pop("listing_draft")
        legacy["stages"]["final_qa"]["status"]="completed"
        pipeline.atomic_write(self.path,legacy)
        loaded=pipeline.load_manifest(self.path)
        pipeline.verify_copy_lock(loaded)
        self.assertEqual("COMPLETED",pipeline.derive_overall_status(loaded))
        self.assertNotIn("copy_checkpoint",loaded)

    def test_new_information_confirmation_invalidates_old_final_status(self):
        self.confirm()
        self.manifest["stages"]["selling_point_decision"].update(status="completed", outputs=[str(self.cal)])
        self.manifest["stages"]["final_qa"]["status"]="completed"
        self.save()
        self.cal.write_bytes(b"user updated 07")
        with contextlib.redirect_stdout(io.StringIO()):
            pipeline.cmd_confirm(argparse.Namespace(manifest=str(self.path),calibration_file=str(self.cal),candidate_id="P0-01",statement_zh="Updated statement",direction_en=None,note="user confirmation",confirmed_by="User"))
        result=pipeline.load_manifest(self.path)
        self.assertEqual("pending",result["stages"]["final_qa"]["status"])
        self.assertEqual("pending",result["stages"]["keyword_allocation"]["status"])
        self.assertEqual("WAITING_COPY_CONFIRMATION",pipeline.derive_overall_status(result))
        with self.assertRaises(ValueError):pipeline.verify_copy_lock(result)

    def test_missing_asin_rejected(self):
        self.payload.pop("asin")
        self.draft.write_text(json.dumps(self.payload))
        with self.assertRaisesRegex(ValueError,"product ASIN"):
            pipeline.verify_copy_payload(self.manifest,self.draft)

    def test_wrong_asin_rejected_even_when_run_matches(self):
        self.payload["asin"]="B0TEST0002"
        self.draft.write_text(json.dumps(self.payload))
        with self.assertRaisesRegex(ValueError,"ASIN mismatch"):
            pipeline.verify_copy_payload(self.manifest,self.draft)

    def test_invalid_asin_rejected(self):
        self.payload["asin"]="invalid"
        self.draft.write_text(json.dumps(self.payload))
        with self.assertRaisesRegex(ValueError,"product ASIN"):
            pipeline.verify_copy_payload(self.manifest,self.draft)

    def test_missing_locked_identity_rejected(self):
        self.manifest["input"].pop("product_asin")
        with self.assertRaisesRegex(ValueError,"product ASIN"):
            pipeline.verify_copy_payload(self.manifest,self.draft)

    def test_empty_revision_rejected(self):
        for revision in (None,"", "   ", 1):
            with self.subTest(revision=revision):
                self.payload["revision"]=revision
                self.draft.write_text(json.dumps(self.payload))
                with self.assertRaisesRegex(ValueError,"revision string"):
                    pipeline.verify_copy_payload(self.manifest,self.draft)

    def test_init_bad_identity_does_not_create_run(self):
        target=self.root/"invalid-run"
        with self.assertRaisesRegex(ValueError,"product ASIN"):
            pipeline.cmd_init(argparse.Namespace(input=str(self.facts),run_dir=str(target),run_id="TEST",product_asin=None))
        self.assertFalse(target.exists())

    def test_changed_registered_draft_cannot_be_confirmed(self):
        self.manifest["stages"]["listing_draft"].update(status="completed",outputs=[str(self.draft)],output_sha256={str(self.draft):pipeline.sha256_file(self.draft)})
        self.save()
        before=self.path.read_bytes()
        self.payload["title"]="Changed before user confirmation"
        self.draft.write_text(json.dumps(self.payload))
        with self.assertRaisesRegex(ValueError,"Registered draft SHA-256"):
            pipeline.cmd_confirm_copy(argparse.Namespace(manifest=str(self.path),copy_file=str(self.draft),confirmed_by="User",note=None))
        self.assertEqual(before,self.path.read_bytes())

    def test_changed_approved_copy_cannot_be_directly_reconfirmed(self):
        self.confirm()
        before=self.path.read_bytes()
        self.payload["title"]="Changed after approval"
        self.draft.write_text(json.dumps(self.payload))
        with self.assertRaisesRegex(ValueError,"reopen-copy"):
            pipeline.cmd_confirm_copy(argparse.Namespace(manifest=str(self.path),copy_file=str(self.draft),confirmed_by="User",note=None))
        self.assertEqual(before,self.path.read_bytes())

    def test_identical_confirmation_retry_is_read_only(self):
        self.confirm()
        before=self.path.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            pipeline.cmd_confirm_copy(argparse.Namespace(manifest=str(self.path),copy_file=str(self.draft),confirmed_by="User",note=None))
        self.assertEqual(before,self.path.read_bytes())

    def test_force_cannot_reset_confirmed_copy_stage(self):
        self.confirm()
        for stage in ("listing_draft","copy_checkpoint"):
            with self.subTest(stage=stage), self.assertRaisesRegex(ValueError,"reopen-copy"):
                pipeline.cmd_set_stage(argparse.Namespace(manifest=str(self.path),stage=stage,status="needs_input",force=True,message=None,output=[]))

    def test_force_cannot_refresh_completed_draft_hash(self):
        self.manifest["stages"]["listing_draft"].update(status="completed",outputs=[str(self.draft)],output_sha256={str(self.draft):pipeline.sha256_file(self.draft)})
        self.save()
        with self.assertRaisesRegex(ValueError,"reopen-copy"):
            pipeline.cmd_set_stage(argparse.Namespace(manifest=str(self.path),stage="listing_draft",status="completed",force=True,message=None,output=[str(self.draft)]))

    def test_reopen_then_new_revision_preserves_approved_snapshot(self):
        self.confirm()
        old_payload=copy.deepcopy(self.payload)
        old_bytes=self.draft.read_bytes()
        new_file=self.root/"copy-draft-v02.json"
        self.payload.update(revision="v02",title="Revised Example Chair")
        new_file.write_text(json.dumps(self.payload))
        with contextlib.redirect_stdout(io.StringIO()):
            pipeline.cmd_reopen_copy(argparse.Namespace(manifest=str(self.path),reason="User requested change"))
            pipeline.cmd_set_stage(argparse.Namespace(manifest=str(self.path),stage="listing_draft",status="running",force=False,message=None,output=[]))
            pipeline.cmd_set_stage(argparse.Namespace(manifest=str(self.path),stage="listing_draft",status="completed",force=False,message=None,output=[str(new_file)]))
            pipeline.cmd_confirm_copy(argparse.Namespace(manifest=str(self.path),copy_file=str(new_file),confirmed_by="User",note="User approved v02"))
        result=pipeline.load_manifest(self.path)
        pipeline.verify_copy_lock(result)
        self.assertEqual(old_bytes,self.draft.read_bytes())
        self.assertEqual(old_payload,result["copy_confirmation_history"][0]["copy_snapshot"])
        self.assertEqual("v02",result["copy_checkpoint"]["revision"])


    def use_v22(self, count=6):
        self.manifest["writing_rules_version"] = "v2.2"
        self.payload["writing_rules_version"] = "v2.2"
        self.payload["bullet_points"] = ["Supported use: " + "Evidence and concrete activity. " * 30 for _ in range(count)]
        self.draft.write_text(json.dumps(self.payload))
        self.save()

    def test_v22_six_long_bullets_confirm_all_eight_fields(self):
        self.use_v22()
        self.confirm()
        pipeline.verify_copy_lock(self.manifest)
        self.assertEqual(8, len(self.manifest["copy_checkpoint"]["confirmed_scope"]))
        self.assertEqual("Bullet 6", self.manifest["copy_checkpoint"]["confirmed_scope"][-1])
        self.assertGreater(len(self.payload["bullet_points"][0]), 500)

    def use_coverage_policy(self, count=5):
        self.use_v22(count)
        self.manifest["bullet_count_policy"] = pipeline.BULLET_COUNT_POLICY
        self.payload["bullet_count_policy"] = pipeline.BULLET_COUNT_POLICY
        self.draft.write_text(json.dumps(self.payload))
        self.save()

    def test_coverage_five_or_six_needs_no_separate_count_approval(self):
        for count in (5, 6):
            with self.subTest(count=count):
                self.use_coverage_policy(count)
                pipeline.verify_copy_payload(self.manifest, self.draft)
                self.assertNotIn("bullet_count_approval", self.payload)

    def test_coverage_rejects_under_five_even_with_count_claim(self):
        for count in (0, 1, 2, 3, 4):
            with self.subTest(count=count):
                self.use_coverage_policy(count)
                self.payload["bullet_count_approval"] = {"count":count,"confirmed_by":"User","note":"Cannot lower project minimum"}
                self.draft.write_text(json.dumps(self.payload))
                with self.assertRaisesRegex(ValueError, "at least 5"):
                    pipeline.verify_copy_payload(self.manifest, self.draft)

    def test_coverage_five_still_requires_full_copy_confirmation(self):
        self.use_coverage_policy(5)
        with self.assertRaisesRegex(ValueError, "User must confirm"):
            pipeline.verify_copy_lock(self.manifest)
        self.confirm()
        pipeline.verify_copy_lock(self.manifest)
        self.assertEqual(7, len(self.manifest["copy_checkpoint"]["confirmed_scope"]))
        self.assertEqual("Bullet 5", self.manifest["copy_checkpoint"]["confirmed_scope"][-1])
        self.payload["bullet_points"][0] += " Changed after approval"
        self.draft.write_text(json.dumps(self.payload))
        with self.assertRaisesRegex(ValueError, "Confirmed copy changed"):
            pipeline.verify_copy_lock(self.manifest)

    def test_coverage_six_confirms_all_bullets_without_padding_five(self):
        self.use_coverage_policy(6)
        self.confirm()
        pipeline.verify_copy_lock(self.manifest)
        self.assertEqual(8, len(self.manifest["copy_checkpoint"]["confirmed_scope"]))
        self.assertEqual("Bullet 6", self.manifest["copy_checkpoint"]["confirmed_scope"][-1])

    def test_coverage_above_six_requires_locked_count_approval(self):
        self.use_coverage_policy(7)
        with self.assertRaisesRegex(ValueError, "bullet_count_approval"):
            pipeline.verify_copy_payload(self.manifest, self.draft)
        evidence = self.root / "coverage-count-approval.json"
        evidence.write_text(json.dumps({"count":7,"confirmation":"Test user and target environment support seven"}))
        lock = {"path":str(evidence),"sha256":pipeline.sha256_file(evidence)}
        self.payload["bullet_count_approval"] = {"count":7,"confirmed_by":"User","note":"Explicit extra field confirmation fixture","source_lock":lock}
        self.draft.write_text(json.dumps(self.payload))
        with self.assertRaisesRegex(ValueError, "approval evidence"):
            pipeline.verify_copy_payload(self.manifest, self.draft)
        self.payload["source_locks"].append(lock)
        self.draft.write_text(json.dumps(self.payload))
        self.confirm()
        pipeline.verify_copy_lock(self.manifest)
        self.assertEqual("Bullet 7", self.manifest["copy_checkpoint"]["confirmed_scope"][-1])

    def test_coverage_count_policy_must_match_and_be_supported(self):
        for manifest_policy, payload_policy in ((pipeline.BULLET_COUNT_POLICY, None), (None, pipeline.BULLET_COUNT_POLICY), ("unknown", "unknown")):
            with self.subTest(manifest_policy=manifest_policy, payload_policy=payload_policy):
                self.use_coverage_policy(5)
                self.manifest["bullet_count_policy"] = manifest_policy
                self.payload["bullet_count_policy"] = payload_policy
                self.draft.write_text(json.dumps(self.payload))
                with self.assertRaisesRegex(ValueError, "bullet_count_policy"):
                    pipeline.verify_copy_payload(self.manifest, self.draft)

    def test_v22_nondefault_counts_require_confirmation(self):
        for count in (3, 5, 7):
            with self.subTest(count=count):
                self.use_v22(count)
                with self.assertRaisesRegex(ValueError, "bullet_count_approval"):
                    pipeline.verify_copy_payload(self.manifest, self.draft)

    def test_v22_seven_with_locked_count_approval(self):
        self.use_v22(7)
        evidence = self.root / "count-approval.json"
        evidence.write_text(json.dumps({"count":7,"confirmation":"Test user approves seven supported fields"}))
        lock = {"path":str(evidence),"sha256":pipeline.sha256_file(evidence)}
        self.payload["bullet_count_approval"] = {"count":7,"confirmed_by":"User","note":"Explicit count approval fixture", "source_lock":lock}
        self.payload["source_locks"].append(lock)
        self.draft.write_text(json.dumps(self.payload))
        self.confirm()
        pipeline.verify_copy_lock(self.manifest)
        self.assertEqual("Bullet 7", self.manifest["copy_checkpoint"]["confirmed_scope"][-1])
        evidence.write_text("changed approval")
        with self.assertRaisesRegex(ValueError, "source changed"):
            pipeline.verify_copy_lock(self.manifest)

    def test_v22_count_claim_without_locked_evidence_fails(self):
        self.use_v22(7)
        self.payload["bullet_count_approval"] = {"count":7,"confirmed_by":"User","note":"claimed", "source_lock":{"path":str(self.root/"missing"),"sha256":"a"*64}}
        self.draft.write_text(json.dumps(self.payload))
        with self.assertRaisesRegex(ValueError, "approval evidence"):
            pipeline.verify_copy_payload(self.manifest, self.draft)

    def test_v22_rule_version_mismatch_fails(self):
        self.use_v22()
        self.payload["writing_rules_version"] = "v2.0"
        self.draft.write_text(json.dumps(self.payload))
        with self.assertRaisesRegex(ValueError, "writing_rules_version"):
            pipeline.verify_copy_payload(self.manifest, self.draft)

    def test_v22_title_highlight_exact_limits_and_overflow(self):
        self.use_v22()
        self.payload.update(title="A"*75, item_highlights="B"*125)
        self.draft.write_text(json.dumps(self.payload))
        pipeline.verify_copy_payload(self.manifest, self.draft)
        for field in ("title", "item_highlights"):
            with self.subTest(field=field):
                self.payload[field] += "X"
                self.draft.write_text(json.dumps(self.payload))
                with self.assertRaisesRegex(ValueError, "75/125"):
                    pipeline.verify_copy_payload(self.manifest, self.draft)
                self.payload[field] = self.payload[field][:-1]

    def test_v22_blank_bullet_fails(self):
        self.use_v22()
        self.payload["bullet_points"][-1] = "   "
        self.draft.write_text(json.dumps(self.payload))
        with self.assertRaisesRegex(ValueError, "nonempty bullet_points"):
            pipeline.verify_copy_payload(self.manifest, self.draft)

    def test_legacy_v20_does_not_silently_accept_six(self):
        self.payload["bullet_points"].append("Additional: Supported fact")
        self.draft.write_text(json.dumps(self.payload))
        with self.assertRaisesRegex(ValueError, "Legacy.*five"):
            pipeline.verify_copy_payload(self.manifest, self.draft)


if __name__=="__main__":unittest.main()
