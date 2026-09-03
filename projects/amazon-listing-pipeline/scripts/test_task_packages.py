#!/usr/bin/env python3
"""Package boundary tests on disposable copies; never run Amazon business work."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from task_packages import digest, encode, validate, validate_plain_frontmatter

ROOT = Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='listing-package-test-')
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / 'task-packages', self.root / 'task-packages')
        self.registry_file = self.root / 'task-packages/registry.json'
        self.registry = json.loads(self.registry_file.read_text())

    def tearDown(self):
        self.temp.cleanup()

    def package(self, role):
        entry = next(r for r in self.registry['roles'] if r['id'] == role)
        return self.root / entry['path']

    def assert_invalid(self):
        result = validate(self.root, check_sources=False)
        self.assertFalse(result['valid'], result)

    def test_intact_deployment(self):
        result = validate(self.root, check_sources=False)
        self.assertTrue(result['valid'], result)
        self.assertEqual(result['roles'], 10)
        self.assertEqual(result['business_run'], 'not_executed')

    def test_missing_contract(self):
        path = self.package('sku-keywords') / '.agents/skills/sku-usable-keyword-library/references/decision-boundaries.md'
        path.unlink()
        self.assert_invalid()

    def test_changed_business_rule(self):
        path = self.package('sku-keywords') / '.agents/skills/sku-usable-keyword-library/SKILL.md'
        path.write_text(path.read_text().replace('不复判', '可以复判'))
        self.assert_invalid()

    def test_changed_sample_asset(self):
        path = self.package('tag-priority') / '.agents/skills/prioritize-amazon-insight-tags/assets/golden-tag-priority-workbook.xlsx'
        path.write_bytes(path.read_bytes() + b'corruption')
        self.assert_invalid()

    def test_wrong_role_manifest(self):
        shutil.copyfile(self.package('painpoint-frequency') / 'package-manifest.json',
                        self.package('painpoint-phrasing') / 'package-manifest.json')
        self.assert_invalid()

    def test_wrong_version_even_if_manifest_hash_refreshed(self):
        role = next(r for r in self.registry['roles'] if r['id'] == 'product-audit')
        path = self.package('product-audit') / 'package-manifest.json'
        manifest = json.loads(path.read_text()); manifest['version'] = 'wrong-version'
        path.write_bytes(encode(manifest)); role['manifest_sha256'] = digest(path.read_bytes())
        self.registry_file.write_bytes(encode(self.registry))
        self.assert_invalid()

    def test_undeclared_skill_rejected(self):
        path = self.package('sku-keywords') / '.agents/skills/unexpected/SKILL.md'
        path.parent.mkdir(); path.write_text('---\nname: unexpected\n---\n')
        self.assert_invalid()

    def test_symlink_escape_rejected(self):
        path = self.package('sku-keywords') / 'Agent.md'
        outside = self.root / 'foreign.md'; outside.write_bytes(path.read_bytes())
        path.unlink(); path.symlink_to(outside)
        self.assert_invalid()

    def run_dependencies(self, *args):
        script = self.package('main') / '.agents/skills/orchestrate-amazon-listing-pipeline/scripts/validate_dependencies.py'
        return subprocess.run([sys.executable, '-B', str(script), *args], cwd=self.root,
                              capture_output=True, text=True)

    def test_dependency_entry_from_unrelated_cwd(self):
        result = self.run_dependencies()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertFalse(data['global_fallback'])
        self.assertFalse(data['keyword_adapter']['runtime_verified'])

    def test_no_extra_global_fallback(self):
        result = self.run_dependencies('--extra-root', str(self.root / 'fake-global-skills'))
        self.assertNotEqual(result.returncode, 0)

    def test_no_wrong_keyword_adapter(self):
        result = self.run_dependencies('--keyword-skill', 'some-category-keyword-library')
        self.assertNotEqual(result.returncode, 0)

    def test_missing_local_skill_not_hidden_by_discovery(self):
        path = self.package('main') / 'dependencies/skills/alexa-painpoint-frequency/SKILL.md'
        path.unlink()
        result = self.run_dependencies()
        self.assertNotEqual(result.returncode, 0)

    def test_frontmatter_requires_description(self):
        self.assertTrue(validate_plain_frontmatter('---\nname: sample\n---\n', 'sample'))

    def test_frontmatter_richer_yaml_is_not_guessed(self):
        self.assertTrue(validate_plain_frontmatter('---\nname: sample\ndescription: |\n  text\n---\n', 'sample'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
