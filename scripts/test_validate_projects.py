"""Synthetic path/inventory guard tests, not project business validation."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from validate_projects import INVENTORY, owned_path, read_json, validate_inventory, validate_registry


class ReleaseInventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='workflow-inventory-fixture-')
        self.root = Path(self.tmp.name)
        (self.root / 'migration').mkdir()
        (self.root / 'rule.md').write_text('fixture only')
        self.write_lock()

    def tearDown(self):
        self.tmp.cleanup()

    def write_lock(self):
        value = {'schema': 'amazon-workflow-release-files/v1',
                 'files': {'rule.md': hashlib.sha256((self.root / 'rule.md').read_bytes()).hexdigest()}}
        (self.root / INVENTORY).write_text(json.dumps(value))

    def test_complete_inventory_is_read_only(self):
        before = (self.root / INVENTORY).read_bytes()
        self.assertEqual(validate_inventory(self.root), 1)
        self.assertEqual(before, (self.root / INVENTORY).read_bytes())

    def test_changed_rule_is_blocked(self):
        (self.root / 'rule.md').write_text('changed')
        with self.assertRaises(ValueError):
            validate_inventory(self.root)

    def test_missing_rule_is_blocked(self):
        (self.root / 'rule.md').unlink()
        with self.assertRaises(ValueError):
            validate_inventory(self.root)

    def test_unreviewed_file_is_blocked(self):
        (self.root / 'raw.txt').write_text('synthetic unreviewed fixture')
        with self.assertRaises(ValueError):
            validate_inventory(self.root)

    def test_declared_private_metadata_is_not_a_release_input(self):
        for relative in ('.DS_Store', 'docs/.DS_Store', 'thread-map.local.md', '.codex/config.toml', '.env.local'):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('synthetic local state only')
        self.assertEqual(validate_inventory(self.root), 1)

    def test_private_metadata_cannot_be_added_to_manifest(self):
        (self.root / '.env').write_text('synthetic local state only')
        manifest = json.loads((self.root / INVENTORY).read_text())
        manifest['files']['.env'] = hashlib.sha256((self.root / '.env').read_bytes()).hexdigest()
        (self.root / INVENTORY).write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            validate_inventory(self.root)

    def test_unreviewed_workbook_is_still_blocked(self):
        (self.root / 'unreviewed.xlsx').write_bytes(b'synthetic unreviewed artifact')
        with self.assertRaises(ValueError):
            validate_inventory(self.root)

    def test_traversal_and_absolute_paths_are_blocked(self):
        for relative in ('../x', '/x', 'a/../../x', 'C:\\x', ''):
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                owned_path(self.root, relative)

    def test_symlink_is_blocked_even_when_target_exists(self):
        (self.root / 'link').symlink_to(self.root / 'rule.md')
        with self.assertRaises(ValueError):
            validate_inventory(self.root)

    def test_duplicate_keys_are_blocked(self):
        (self.root / 'duplicate.json').write_text('{"a":1,"a":2}')
        with self.assertRaises(ValueError):
            read_json(self.root / 'duplicate.json')

    def test_missing_project_is_blocked(self):
        (self.root / 'projects.json').write_text(json.dumps({'schema': 'amazon-workflow-projects/v1', 'projects': []}))
        with self.assertRaises(ValueError):
            validate_registry(self.root)


class ProjectRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='workflow-registry-fixture-')
        self.root = Path(self.tmp.name)
        self.rows = []
        for project_id, count in (('amazon-keyword-library', 12), ('amazon-listing-pipeline', 10)):
            project = self.root / 'projects' / project_id
            project.mkdir(parents=True)
            (project / 'AGENTS.md').write_text('Synthetic routing fixture only')
            (project / 'scripts').mkdir()
            (project / 'scripts' / 'validate.py').write_text('raise SystemExit(0)')
            for number in range(count):
                name = project_id + '-fixture-' + str(number)
                skill = project / '.agents' / 'skills' / name
                skill.mkdir(parents=True)
                (skill / 'SKILL.md').write_text('---\nname: ' + name + '\n---\nFixture only')
            row = {'id': project_id, 'path': 'projects/' + project_id, 'entry': 'AGENTS.md',
                   'maintenance_skills': '.agents/skills', 'expected_skill_count': count,
                   'checks': ['scripts/validate.py']}
            if project_id == 'amazon-listing-pipeline':
                (project / 'task-packages').mkdir()
                (project / 'task-packages' / 'registry.json').write_text('{}')
                row['role_registry'] = 'task-packages/registry.json'
            self.rows.append(row)
        self.write_registry()

    def tearDown(self):
        self.tmp.cleanup()

    def write_registry(self):
        (self.root / 'projects.json').write_text(json.dumps({
            'schema': 'amazon-workflow-projects/v1', 'projects': self.rows}))

    def test_two_projects_keep_owned_cwd_and_original_checks(self):
        skills, checks = validate_registry(self.root)
        self.assertEqual(len(skills), 22)
        self.assertEqual(len(checks), 2)
        for project_id, cwd, command in checks:
            self.assertEqual(cwd, self.root / 'projects' / project_id)
            self.assertEqual(Path(command[2]), cwd / 'scripts' / 'validate.py')

    def test_root_business_skill_is_rejected(self):
        entry = self.root / '.agents' / 'skills' / 'ambiguous'
        entry.mkdir(parents=True)
        (entry / 'SKILL.md').write_text('---\nname: ambiguous\n---')
        with self.assertRaises(ValueError):
            validate_registry(self.root)

    def test_wrong_project_path_is_rejected(self):
        self.rows[1]['path'] = self.rows[0]['path']
        self.write_registry()
        with self.assertRaises(ValueError):
            validate_registry(self.root)

    def test_missing_skill_is_rejected(self):
        project = self.root / self.rows[1]['path']
        next((project / '.agents' / 'skills').glob('*/SKILL.md')).unlink()
        with self.assertRaises(ValueError):
            validate_registry(self.root)

    def test_missing_role_registry_is_rejected(self):
        (self.root / self.rows[1]['path'] / self.rows[1]['role_registry']).unlink()
        with self.assertRaises(ValueError):
            validate_registry(self.root)

    def test_cross_project_check_escape_is_rejected(self):
        self.rows[1]['checks'] = ['../amazon-keyword-library/scripts/validate.py']
        self.write_registry()
        with self.assertRaises(ValueError):
            validate_registry(self.root)

    def test_same_authoritative_identity_is_rejected(self):
        first = self.root / self.rows[0]['path'] / '.agents' / 'skills'
        second = self.root / self.rows[1]['path'] / '.agents' / 'skills'
        old = next(second.iterdir())
        duplicate_name = next(first.iterdir()).name
        new = second / duplicate_name
        old.rename(new)
        (new / 'SKILL.md').write_text('---\nname: ' + duplicate_name + '\n---')
        with self.assertRaises(ValueError):
            validate_registry(self.root)


if __name__ == '__main__':
    unittest.main()
