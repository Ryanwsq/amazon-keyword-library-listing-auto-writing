#!/usr/bin/env python3
"""Read-only Listing package structure/dependency validator, no global fallback."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

REQUIRED = ('Agent.md', 'SKILL.md', 'capabilities.yaml', 'knowledge/index.md',
            'knowledge/catalog.json', 'evidence/index.md', 'evidence/cases.json')
AGENT_HEADINGS = ('业务场景', '负责的结果', '使用时机', '可调用能力', '禁止事项与人工升级条件')
SKILL_HEADINGS = ('目标', '输入', '输出', '可调用能力', '执行步骤', '质量标准', '异常处理')
CASES = ('case-01-normal.md', 'case-02-normal.md', 'case-03-edge-or-error.md')
IGNORED = {'.DS_Store', '__pycache__'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def files(root):
    return sorted(p for p in root.rglob('*') if p.is_file()
                  and not any(x in IGNORED for x in p.parts) and p.suffix != '.pyc')


def safe(root, rel):
    p = root / rel
    if Path(rel).is_absolute() or p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):
        raise ValueError('Unsafe path: ' + str(rel))
    if any(q.is_symlink() for q in [p, *p.parents] if q != root.parent and q.is_relative_to(root)):
        raise ValueError('Symlink in path: ' + str(rel))
    return p


def frontmatter(text):
    m = re.match(r'^---\n(.*?)\n---(?:\n|$)', text, re.S)
    if not m:
        raise ValueError('Missing frontmatter')
    result = {}
    for line in m[1].splitlines():
        if not line.strip():
            continue
        row = re.fullmatch(r'(name|description): (.+)', line)
        if not row or row[1] in result:
            raise ValueError('Unsupported frontmatter: full YAML parser required')
        value = row[2]
        if value[0] in '\"\'[{|>*&!@`' or ': ' in value or ' #' in value:
            raise ValueError('Non-plain frontmatter: full YAML parser required')
        result[row[1]] = value
    if set(result) != {'name', 'description'} or not result['description'].strip():
        raise ValueError('name/description required')
    return result


def local_links(root, file):
    for raw in re.findall(r'\[[^\]\n]*\]\(([^)\n]+)\)', file.read_text()):
        raw = raw.strip('<>')
        if raw.startswith('#') or urlsplit(raw).scheme:
            continue
        name = unquote(raw.split('#', 1)[0])
        if not name:
            continue
        p = file.parent / name
        if not p.resolve().is_relative_to(root.resolve()):
            raise ValueError('Link escapes root: ' + str(file.relative_to(root)) + ' -> ' + raw)
        yield safe(root, p.resolve().relative_to(root.resolve()).as_posix())


def code_references(root, file, skill_dir=None):
    """Explicit current source tokens; do not treat historical/run filenames as sources."""
    if file.relative_to(root).as_posix() == 'project-control/listing-writing-iteration-log.md':
        return  # change-log prose records historical artifacts, not runtime source dependencies
    for raw in re.findall(r'(?<!`)`([^`\n]+)`(?!`)', file.read_text()):
        if not re.fullmatch(r'[^ <>*\[\]{}]+\.(?:md|py|json|yaml|yml|xlsx)', raw):
            continue
        if Path(raw).is_absolute() or '://' in raw:
            continue  # historical/provenance source, not a current package dependency
        candidates = [file.parent / raw, root / raw]
        if skill_dir:
            candidates.extend([skill_dir / raw, skill_dir / 'references' / raw])
        found = next((p for p in candidates if p.exists()), None)
        if found:
            if not found.resolve().is_relative_to(root.resolve()):
                raise ValueError('Code source escapes root: ' + raw)
            yield safe(root, found.resolve().relative_to(root.resolve()).as_posix())
        elif raw.startswith(('references/', 'scripts/', 'knowledge-base/', 'assets/', 'contracts/', '.agents/skills/')):
            raise ValueError('Missing explicit source: ' + str(file.relative_to(root)) + ' -> ' + raw)


def static_script_dependencies(path):
    tree = ast.parse(path.read_text(), filename=str(path))
    result = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'with_name':
            if (len(node.args) == 1 and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)
                    and '__file__' in ast.unparse(node.func.value)):
                result.add(path.parent / node.args[0].value)
        if isinstance(node, ast.ImportFrom) and node.module:
            # This repository's sibling implementation imports, never external libraries.
            if node.module in ('task_packages', 'validate_skill_packages'):
                result.add(path.parent / (node.module + '.py'))
    return sorted(result)


def make_contract(root, entries, version, extra_files=()):
    records = []
    for e in entries:
        d = root / e['path']
        records.append({**e, 'required_files': [p.relative_to(root).as_posix() for p in files(d)]})
    selected = {f for e in records for f in e['required_files']}
    selected.update(extra_files)
    for prefix in ('knowledge-base', 'docs'):
        selected.update(p.relative_to(root).as_posix() for p in files(root / prefix))
    log = 'project-control/listing-writing-iteration-log.md'
    if (root / log).is_file():
        selected.add(log)
    # Only direct runtime validators; maintenance/build tooling is not a business dependency.
    selected.add('scripts/validate_skill_packages.py')
    static = []
    for rel in sorted(selected):
        if rel.endswith('.py'):
            for target in static_script_dependencies(root / rel):
                if not target.resolve().is_relative_to(root.resolve()):
                    raise ValueError('Static dependency escapes root')
                target_rel = target.relative_to(root).as_posix()
                selected.add(target_rel)
                static.append({'source': rel, 'target': target_rel})
    return {'schema_version': 2, 'version': version, 'scope': 'local_structure_and_file_dependencies',
            'discovery_roots': ['.agents/skills'], 'skills': records,
            'files': [{'path': p, 'sha256': sha(safe(root, p).read_bytes())} for p in sorted(selected)],
            'static_dependencies': static,
            'external_runtime': {'spreadsheets': 'not_checked', 'Alexa_authentication': 'not_checked',
                                 'Amazon_keyword_main': 'external_independent_task'},
            'business_rule_owner': 'original_skill_and_references', 'P1': 'not_executed'}


def validate(root, additional_roots=()):
    root = root.resolve()
    errors, checked, names, dependency_edges = [], [], set(), 0
    def require(ok, msg):
        if not ok:
            errors.append(msg)
    try:
        contract = json.loads(safe(root, 'contracts/skill-dependencies.json').read_text())
        require(contract['schema_version'] == 2, 'Wrong dependency schema')
        declared = {r['path']: r['sha256'] for r in contract['files']}
        require(len(declared) == len(contract['files']), 'Duplicate file declarations')
        for rel, expected in declared.items():
            p = safe(root, rel)
            require(p.is_file(), 'Missing dependency: ' + rel)
            if p.is_file():
                actual = sha(p.read_bytes())
                require(actual == expected, 'Dependency hash drift: ' + rel)
                checked.append({'path': rel, 'sha256': actual})
        entries = contract['skills']
        expected_discovered = {}
        capability_ids = set()
        for entry in entries:
            name, rel = entry['name'], entry['path']
            require(name not in names, 'Duplicate Skill identity: ' + name)
            names.add(name)
            d = safe(root, rel)
            require(d.name == name, 'Directory/name mismatch: ' + rel)
            if entry['mode'] == 'executable':
                expected_discovered[name] = d.resolve()
                require(rel == '.agents/skills/' + name, 'Execution entry outside declared discovery root')
            else:
                require(rel == 'dependencies/skills/' + name, 'Reference copy in discovery root')
            actual_files = {p.relative_to(root).as_posix() for p in files(d)}
            require(actual_files == set(entry['required_files']), 'Unregistered/missing Skill resource: ' + name)
            for resource in REQUIRED:
                require((d / resource).is_file(), 'Missing standard file: ' + rel + '/' + resource)
            if not all((d / f).is_file() for f in REQUIRED):
                continue
            skill = (d / 'SKILL.md').read_text()
            fm = frontmatter(skill)
            require(fm['name'] == name and len(name) <= 64 and bool(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name)), 'Invalid Skill name: ' + name)
            require(len(fm['description']) <= 1024, 'Description too long: ' + name)
            require('[TODO:' not in skill, 'Unfinished scaffold: ' + name)
            agent = (d / 'Agent.md').read_text()
            for h in AGENT_HEADINGS:
                require('\n## ' + h + '\n' in agent, 'Missing Agent section: ' + name + '/' + h)
            for h in SKILL_HEADINGS:
                require('\n## ' + h + '\n' in skill, 'Missing Skill section: ' + name + '/' + h)
            caps = json.loads((d / 'capabilities.yaml').read_text())  # documented strict YAML1.2 JSON subset
            require(caps['skill']['name'] == name, 'Capability skill.name mismatch: ' + name)
            require(caps['skill']['maturity'] in ('draft', 'verified'), 'Invalid maturity: ' + name)
            require('last_verified' in caps['skill'], 'Missing last_verified: ' + name)
            own_ids = set()
            for cap in caps['capabilities']:
                require(all(k in cap for k in ('id','type','purpose','status','input','output','permission','risk')), 'Missing capability fields: ' + name)
                require(cap['id'] not in capability_ids, 'Duplicate capability ID: ' + cap['id'])
                capability_ids.add(cap['id']); own_ids.add(cap['id'])
                require(cap['type'] in ('api','cli','mcp','manual'), 'Invalid capability type')
                require(cap['status'] in ('planned','verified','unavailable'), 'Invalid capability state')
                require(all(isinstance(cap.get(k), str) and cap[k].strip() for k in ('purpose','input','output','permission','risk')), 'Empty capability scope: ' + name)
            for doc in (agent, skill):
                used = set(re.findall(r'`(listing\.[a-z0-9.-]+)`', doc))
                require(used == own_ids, 'Unregistered or missing capability reference: ' + name)
            catalog = json.loads((d / 'knowledge/catalog.json').read_text())
            index = (d / 'knowledge/index.md').read_text()
            ids = set()
            for row in catalog:
                require(all(row.get(k) for k in ('id','content','source','scope','updated_on','use')), 'Incomplete knowledge record: ' + name)
                require(row['id'] not in ids, 'Duplicate knowledge ID: ' + name)
                ids.add(row['id'])
                target = safe(root, row['source'])
                require(target.is_file() and row['source'] in declared, 'Missing/unregistered knowledge source: ' + row['source'])
                require(all(str(row[k]).replace('|', '／') in index for k in ('id','content','scope','updated_on','use')), 'Knowledge index/catalog mismatch: ' + name)
            require(bool(catalog) and '不确定' in index and '人工确认' in index, 'Missing knowledge uncertainty boundary')
            evidence = json.loads((d / 'evidence/cases.json').read_text())
            evidence_text = (d / 'evidence/index.md').read_text()
            require(evidence['skill'] == name and evidence['maturity'] == caps['skill']['maturity'], 'Evidence identity/state mismatch')
            require(evidence['P1'] in ('not_executed','in_progress','passed','failed'), 'Invalid P1 state')
            require([r['file'] for r in evidence['cases']] == list(CASES), 'Three case slots required: ' + name)
            for case in evidence['cases']:
                require(all(k in case for k in ('type','status','revision','sanitized_reference','acceptance')), 'Incomplete case slot')
                require(case['status'] in ('planned','running','candidate','accepted','rejected'), 'Invalid case registration')
                require(all(str(case[k] if case[k] is not None else '—') in evidence_text for k in ('file','type','status','revision','sanitized_reference','acceptance')), 'Evidence index differs from slots')
                if case['status'] in ('candidate','accepted'):
                    require((d / 'evidence' / case['file']).is_file(), 'Missing real candidate/accepted case: ' + name)
            if caps['skill']['maturity'] == 'verified' or evidence['P1'] == 'passed':
                require(all(c['status'] == 'accepted' and c['acceptance'] == 'accepted' and c['revision'] and c['sanitized_reference'] for c in evidence['cases']), 'Cannot promote incomplete cases: ' + name)
                require(len({c['revision'] for c in evidence['cases']}) == 1, 'Cases use different revisions')
                require(all(c['status'] == 'verified' for c in caps['capabilities']) and bool(caps['skill']['last_verified']), 'Cannot promote unverified capabilities')
        discovered = {}
        for discovery in [root / x for x in contract['discovery_roots']] + [Path(x).resolve() for x in additional_roots]:
            require(discovery.is_dir(), 'Missing discovery root: ' + str(discovery))
            if not discovery.is_dir():
                continue
            for d in sorted(discovery.iterdir()):
                if not d.is_dir() or d.name in IGNORED:
                    continue
                require((d / 'SKILL.md').is_file(), 'Incomplete directory in discovery root: ' + str(d))
                if (d / 'SKILL.md').is_file():
                    n = frontmatter((d / 'SKILL.md').read_text())['name']
                    require(n not in discovered, 'Duplicate discovered Skill: ' + n)
                    discovered[n] = d.resolve()
        require(discovered == expected_discovered, 'Discovery entries differ from unique declared execution entries')
        for rel in declared:
            p = safe(root, rel)
            if not p.is_file():
                continue
            skill_dir = next((root / e['path'] for e in entries if p.is_relative_to(root / e['path'])), None)
            if p.suffix == '.md':
                for target in [*local_links(root, p), *code_references(root, p, skill_dir)]:
                    require(target.exists(), 'Broken source link: ' + rel + ' -> ' + str(target.relative_to(root)))
                    if target.is_file():
                        require(target.relative_to(root).as_posix() in declared or target.relative_to(root).as_posix() in ('contracts/skill-dependencies.json', 'package-manifest.json'), 'Unregistered source link: ' + rel + ' -> ' + str(target.relative_to(root)))
                    dependency_edges += 1
            if p.suffix == '.py':
                for target in static_script_dependencies(p):
                    require(target.is_file(), 'Missing static script dependency: ' + rel)
                    require(target.resolve().is_relative_to(root), 'Static script dependency escapes root')
                    if target.is_file():
                        require(target.relative_to(root).as_posix() in declared, 'Unregistered script dependency')
        for edge in contract['static_dependencies']:
            require(edge['source'] in declared and edge['target'] in declared, 'Static dependency not locked')
    except (OSError, ValueError, KeyError, TypeError, SyntaxError) as exc:
        errors.append(str(exc))
    return {'valid': not errors, 'skills': len(names), 'files_verified': len(checked),
            'dependency_links_checked': dependency_edges, 'global_fallback': False,
            'scope': 'local_structure_names_capabilities_knowledge_evidence_dependencies_and_syntax',
            'P1': 'not_executed', 'business_run': 'not_executed',
            'external_runtime': 'not_checked', 'publication_status': 'LOCAL_ONLY_NOT_APPROVED_FOR_PUBLICATION',
            'errors': errors, 'files': checked}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--additional-skill-root', action='append', default=[])
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    result = validate(args.root, args.additional_skill_root)
    if not args.json:
        result.pop('files')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['valid'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
