#!/usr/bin/env python3
"""Destructive cases operate only on disposable fixtures, never real Runs."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from validate_skill_packages import sha, validate

ROOT = Path(__file__).resolve().parents[1]
SKILL = 'sku-usable-keyword-library'


class StructureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='listing-structure-test-')
        self.root = Path(self.temp.name) / 'project'
        self.root.mkdir()
        self.contract = json.loads((ROOT / 'contracts/skill-dependencies.json').read_text())
        for record in self.contract['files']:
            destination = self.root / record['path']
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / record['path'], destination)
        (self.root / 'contracts').mkdir(exist_ok=True)
        self.save_contract()

    def tearDown(self):
        self.temp.cleanup()

    def save_contract(self):
        (self.root / 'contracts/skill-dependencies.json').write_text(json.dumps(self.contract))

    def path(self, rel, skill=SKILL):
        return self.root / '.agents/skills' / skill / rel

    def change_json(self, rel, callback, skill=SKILL):
        p = self.path(rel, skill)
        data = json.loads(p.read_text()); callback(data)
        p.write_text(json.dumps(data, ensure_ascii=False))
        # Refresh fixture hashes so semantic structure checks, not just SHA, must reject it.
        key = p.relative_to(self.root).as_posix()
        next(r for r in self.contract['files'] if r['path'] == key)['sha256'] = sha(p.read_bytes())
        self.save_contract()

    def bad(self, token=None):
        result = validate(self.root)
        self.assertFalse(result['valid'], result)
        if token:
            self.assertIn(token, '\n'.join(result['errors']))

    def test_intact(self):
        result = validate(self.root)
        self.assertTrue(result['valid'], result['errors'])
        self.assertEqual(result['skills'], 10)
        self.assertEqual(result['P1'], 'not_executed')

    def test_capability_missing(self):
        self.path('capabilities.yaml').unlink(); self.bad('Missing standard file')

    def test_agent_missing(self):
        self.path('Agent.md').unlink(); self.bad('Missing standard file')

    def test_capability_identity(self):
        self.change_json('capabilities.yaml', lambda d: d['skill'].update(name='wrong-name'))
        self.bad('skill.name mismatch')

    def test_capability_id_reference(self):
        self.change_json('capabilities.yaml', lambda d: d['capabilities'][0].update(id='listing.wrong.execute'))
        self.bad('capability reference')

    def test_capability_permission_missing(self):
        self.change_json('capabilities.yaml', lambda d: d['capabilities'][0].pop('permission'))
        self.bad('capability fields')

    def test_knowledge_scope_missing(self):
        self.change_json('knowledge/catalog.json', lambda d: d[0].update(scope=''))
        self.bad('Incomplete knowledge record')

    def test_knowledge_source_missing(self):
        self.change_json('knowledge/catalog.json', lambda d: d[0].update(source='knowledge-base/missing.md'))
        self.bad('Missing/unregistered knowledge source')

    def test_knowledge_index_not_synced(self):
        self.change_json('knowledge/catalog.json', lambda d: d[0].update(content='not the displayed index'))
        self.bad('index/catalog mismatch')

    def test_evidence_slot_missing(self):
        self.change_json('evidence/cases.json', lambda d: d['cases'].pop())
        self.bad('Three case slots')

    def test_accepted_case_without_file(self):
        self.change_json('evidence/cases.json', lambda d: d['cases'][0].update(status='accepted'))
        self.bad('Missing real candidate/accepted case')

    def test_p1_promoted_without_evidence(self):
        self.change_json('evidence/cases.json', lambda d: d.update(P1='passed'))
        self.bad('Cannot promote incomplete cases')

    def test_same_named_extra_root(self):
        extra = Path(self.temp.name) / 'extra-skills'
        shutil.copytree(self.path(''), extra / SKILL)
        result = validate(self.root, [extra])
        self.assertFalse(result['valid'])
        self.assertIn('Duplicate discovered Skill', '\n'.join(result['errors']))

    def test_incomplete_discovery_directory(self):
        (self.root / '.agents/skills/incomplete').mkdir()
        self.bad('Incomplete directory in discovery root')

    def test_unregistered_resource(self):
        self.path('references/unregistered.md').write_text('unexpected')
        self.bad('Unregistered/missing Skill resource')

    def test_reference_cannot_be_executable(self):
        self.contract['skills'][0]['mode'] = 'reference'; self.save_contract()
        self.bad('Reference copy in discovery root')

    def test_symlink_escape(self):
        p = self.path('Agent.md')
        other = Path(self.temp.name) / 'outside.md'; other.write_bytes(p.read_bytes())
        p.unlink(); p.symlink_to(other)
        self.bad('Unsafe path')

    def test_static_script_dependency_missing(self):
        p = self.path('scripts/test_pipeline_state.py', 'orchestrate-amazon-listing-pipeline')
        p.write_text(p.read_text() + '\nPath(__file__).with_name("missing_implementation.py")\n')
        next(r for r in self.contract['files'] if r['path'] == p.relative_to(self.root).as_posix())['sha256'] = sha(p.read_bytes())
        self.save_contract(); self.bad('Missing static script dependency')

    def test_explicit_reference_missing(self):
        p = self.path('references/decision-boundaries.md')
        p.write_text(p.read_text() + '\n`references/missing-rule.md`\n')
        next(r for r in self.contract['files'] if r['path'] == p.relative_to(self.root).as_posix())['sha256'] = sha(p.read_bytes())
        self.save_contract(); self.bad('Missing explicit source')


if __name__ == '__main__':
    unittest.main(verbosity=2)
