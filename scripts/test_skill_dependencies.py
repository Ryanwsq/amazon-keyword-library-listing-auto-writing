#!/usr/bin/env python3
"""Synthetic dependency failures only; no business evidence or P1 is produced."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from validate_skill_dependencies import MANIFEST, PACKAGE_FILES, SCHEMA, audit_dependencies


class DependencyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        self.name = "example-keyword-skill"
        self.prefix = ".agents/skills/" + self.name + "/"
        self.package = self.root / self.prefix
        for filename in PACKAGE_FILES:
            self.write(self.prefix + filename, "# Source\n")
        self.write(self.prefix + "SKILL.md", "---\nname: " + self.name + "\ndescription: synthetic test\n---\nRead `references/output-contract.md`.\n")
        self.write(self.prefix + "knowledge/index.md", "Read `../../../../knowledge/rules.md`.\n")
        self.write(self.prefix + "references/output-contract.md", "# Contract\n")
        self.write("knowledge/rules.md", "# Stable fixture rules\n")
        self.registry()
        self.manifest = {"schema": SCHEMA, "shared_files": ["knowledge/rules.md"], "skills": {
            self.name: {"entry": self.prefix + "SKILL.md", "resources": [self.prefix + "references/output-contract.md"]}}}
        self.save()

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def save(self):
        self.write(MANIFEST, json.dumps(self.manifest))

    def registry(self, first="planned"):
        rows = ["| File | Type | Status | Revision | Source | Acceptance |"]
        for n, kind, state in [(1, "normal", first), (2, "normal", "planned"), (3, "edge-or-error", "planned")]:
            rows.append(f"| `case-0{n}-{kind}.md` | {kind} | {state} | pending | pending | pending |")
        self.write(self.prefix + "evidence/index.md", "\n".join(rows))

    def assertFails(self, fragment, **kwargs):
        result = audit_dependencies(self.root, **kwargs)
        self.assertEqual(result["status"], "fail", result)
        self.assertTrue(any(fragment in e for e in result["errors"]), result["errors"])

    def test_valid_and_read_only(self):
        before = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        report = audit_dependencies(self.root)
        self.assertEqual(report["status"], "pass", report["errors"])
        self.assertEqual(report["evidence_counts"], {"planned": 3})
        self.assertEqual(before, {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})
        self.assertTrue(all(not Path(p).is_absolute() and len(h) == 64 for p, h in report["files"].items()))

    def test_missing_knowledge_index(self):
        (self.package / "knowledge/index.md").unlink()
        self.assertFails("knowledge/index.md")

    def test_missing_shared_rules(self):
        (self.root / "knowledge/rules.md").unlink()
        self.assertFails("knowledge/rules.md")

    def test_project_knowledge_index_dead_link(self):
        self.write("knowledge/INDEX.md", "| Topic | Status |\n| `missing.md` | active |\n")
        self.manifest["shared_files"].append("knowledge/INDEX.md")
        self.save()
        self.assertFails("missing.md")

    def test_missing_contract(self):
        (self.package / "references/output-contract.md").unlink()
        self.assertFails("references/output-contract.md")

    def test_missing_registered_asset(self):
        self.manifest["skills"][self.name]["resources"].append(self.prefix + "assets/blank.xlsx")
        self.save()
        self.assertFails("blank.xlsx")

    def test_missing_explicit_relative_reference(self):
        self.write(self.prefix + "knowledge/index.md", "Read `../../../../knowledge/missing.md`.\n")
        self.assertFails("missing.md")

    def test_markdown_cross_package_reference_requires_registration(self):
        self.write("shared/other.md", "# Shared\n")
        self.write(self.prefix + "references/output-contract.md", "[Shared](../../../../shared/other.md)\n")
        self.assertFails("not registered")
        self.manifest["shared_files"].append("shared/other.md")
        self.save()
        self.assertEqual(audit_dependencies(self.root)["status"], "pass")

    def test_explicit_wrong_path_cannot_fallback(self):
        self.write("knowledge/output-contract.md", "# Same basename\n")
        self.write(self.prefix + "SKILL.md", "---\nname: " + self.name + "\n---\nRead `./missing/output-contract.md`.\n")
        self.assertFails("missing dependency")

    def test_runtime_output_is_not_a_source_dependency(self):
        with (self.package / "SKILL.md").open("a", encoding="utf-8") as handle:
            handle.write("Output `quality-manifest.json`, `issues.md`, `<Run_ID>.xlsx`; source runtime remains unchanged.\n")
        self.assertEqual(audit_dependencies(self.root)["status"], "pass")

    def test_ambiguous_script_source(self):
        self.write("scripts/check.py", "pass\n")
        self.write(self.prefix + "scripts/check.py", "pass\n")
        self.manifest["shared_files"].append("scripts/check.py")
        self.save()
        self.write(self.prefix + "references/output-contract.md", "Run `python3 scripts/check.py --verify`.\n")
        self.assertFails("ambiguous dependency")

    def test_symlink_escape(self):
        target = Path(self.temp.name) / "outside.md"
        target.write_text("# Outside\n", encoding="utf-8")
        path = self.package / "references/output-contract.md"
        path.unlink()
        path.symlink_to(target)
        self.assertFails("escaping dependency")

    def test_relative_reference_escape(self):
        self.write(self.prefix + "SKILL.md", "---\nname: " + self.name + "\n---\n[Bad](../../../../../outside.md)\n")
        self.assertFails("out-of-scope")

    def test_manifest_traversal(self):
        self.manifest["shared_files"].append("../outside.md")
        self.save()
        self.assertFails("repository-relative")

    def test_noncanonical_entry(self):
        self.manifest["skills"][self.name]["entry"] = "elsewhere/SKILL.md"
        self.save()
        self.assertFails("noncanonical")

    def test_unregistered_skill(self):
        self.write(".agents/skills/second-skill/SKILL.md", "---\nname: second-skill\n---\n")
        self.assertFails("unregistered=")

    def test_duplicate_frontmatter_identity(self):
        self.write(".agents/skills/second-skill/SKILL.md", "---\nname: " + self.name + "\n---\n")
        self.assertFails("duplicate Skill identity")

    def test_duplicate_external_source_even_when_identical(self):
        external = Path(self.temp.name) / "global-skills"
        path = external / self.name / "SKILL.md"
        path.parent.mkdir(parents=True)
        path.write_bytes((self.package / "SKILL.md").read_bytes())
        self.assertFails("duplicate external Skill source", additional_skill_roots=[external])

    def test_missing_local_entry_cannot_use_external_copy(self):
        external = Path(self.temp.name) / "global-skills"
        path = external / self.name / "SKILL.md"
        path.parent.mkdir(parents=True)
        path.write_bytes((self.package / "SKILL.md").read_bytes())
        (self.package / "SKILL.md").unlink()
        self.assertFails("missing=", additional_skill_roots=[external])

    def test_missing_external_scope_is_not_silently_ignored(self):
        self.assertFails("additional Skill root is unavailable", additional_skill_roots=[Path(self.temp.name) / "missing"])

    def test_accepted_and_candidate_need_files(self):
        for state in ("accepted", "candidate"):
            with self.subTest(state=state):
                self.registry(state)
                self.assertFails("evidence/case-01-normal.md")
        self.write(self.prefix + "evidence/case-01-normal.md", "# Synthetic presence test only\n")
        self.assertEqual(audit_dependencies(self.root)["status"], "pass")

    def test_content_change_changes_digest(self):
        before = audit_dependencies(self.root)
        self.write("knowledge/rules.md", "# Changed fixture\n")
        after = audit_dependencies(self.root)
        self.assertNotEqual(before["files"]["knowledge/rules.md"], after["files"]["knowledge/rules.md"])

    def test_duplicate_manifest_key(self):
        self.write(MANIFEST, '{"schema":"one","schema":"two"}')
        self.assertFails("duplicate JSON key")

    def test_invalid_manifest_shapes(self):
        for bad in (None, [], "not-a-package"):
            with self.subTest(spec=bad):
                self.manifest["skills"][self.name] = bad
                self.save()
                self.assertFails("noncanonical")

    def test_invalid_skill_identity(self):
        self.manifest["skills"]["../escaped"] = self.manifest["skills"].pop(self.name)
        self.save()
        self.assertFails("invalid Skill identity")

    def test_duplicate_resource(self):
        resource = self.manifest["skills"][self.name]["resources"][0]
        self.manifest["skills"][self.name]["resources"].append(resource)
        self.save()
        self.assertFails("duplicate package resource")

    def test_python_local_import(self):
        self.write("scripts/runner.py", "import local_helper\n")
        self.write("scripts/local_helper.py", "pass\n")
        self.manifest["shared_files"].append("scripts/runner.py")
        self.save()
        self.assertFails("unregistered local import")
        self.manifest["shared_files"].append("scripts/local_helper.py")
        self.save()
        self.assertEqual(audit_dependencies(self.root)["status"], "pass")

    def test_missing_python_import_cannot_use_global_environment(self):
        self.write("scripts/runner.py", "import nonexistent_fixture_library\n")
        self.manifest["shared_files"].append("scripts/runner.py")
        self.save()
        self.assertFails("no global fallback")

    def test_node_relative_import(self):
        self.write(self.prefix + "scripts/runner.mjs", 'import {x} from "./missing.mjs";\n')
        self.assertFails("missing.mjs")


if __name__ == "__main__":
    unittest.main(verbosity=2)
