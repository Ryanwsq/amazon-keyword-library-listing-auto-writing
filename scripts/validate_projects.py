#!/usr/bin/env python3
"""Read-only registry, release-inventory and original per-project checks; no business I/O."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = 'migration/release-files.json'
SKIP = {'.git', '.local', '.codex', '.codex-tmp', '__pycache__', '.pytest_cache', 'node_modules'}
LOCAL_NAMES = {'.DS_Store', 'Thumbs.db', 'thread-map.local.md', 'thread-map.yaml'}


def private_local_path(relative):
    """Only declared local metadata; never ignore arbitrary unreviewed business files."""
    parts = PurePosixPath(relative).parts
    return any(part in SKIP for part in parts) or any(
        part in LOCAL_NAMES or part == '.env' or part.startswith('.env.') or part.endswith('bindings.local.json')
        for part in parts)


def unique(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError('Duplicate JSON key: ' + key)
        obj[key] = value
    return obj


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique)


def owned_path(root, relative):
    if not isinstance(relative, str) or not relative or '\\' in relative:
        raise ValueError('Invalid relative path')
    parts = PurePosixPath(relative)
    if parts.is_absolute() or '..' in parts.parts or ':' in relative:
        raise ValueError('Escaping relative path: ' + relative)
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Path escapes root: ' + relative)
    if any((root.joinpath(*parts.parts[:n])).is_symlink() for n in range(1, len(parts.parts) + 1)):
        raise ValueError('Symlink is not a publishable owned file: ' + relative)
    return path


def collect_files(root):
    found = {}
    for path in root.rglob('*'):
        rel = path.relative_to(root)
        if private_local_path(rel.as_posix()):
            continue
        if path.is_symlink():
            raise ValueError('Unexpected symlink: ' + rel.as_posix())
        if path.is_file() and rel.as_posix() != INVENTORY:
            found[rel.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


def validate_inventory(root):
    manifest = read_json(root / INVENTORY)
    if manifest.get('schema') != 'amazon-workflow-release-files/v1':
        raise ValueError('Release inventory schema mismatch')
    expected = manifest.get('files')
    if not isinstance(expected, dict) or not expected:
        raise ValueError('Empty release inventory')
    for rel, digest in expected.items():
        owned_path(root, rel)
        if private_local_path(rel):
            raise ValueError('Private local metadata cannot enter release inventory: ' + rel)
        if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError('Invalid file hash: ' + rel)
    actual = collect_files(root)
    missing = sorted(expected.keys() - actual.keys())
    extra = sorted(actual.keys() - expected.keys())
    changed = sorted(k for k in expected.keys() & actual.keys() if expected[k] != actual[k])
    if missing or extra or changed:
        raise ValueError(json.dumps({'missing': missing, 'unreviewed': extra, 'changed': changed}))
    return len(actual)


def validate_registry(root):
    registry = read_json(root / 'projects.json')
    if registry.get('schema') != 'amazon-workflow-projects/v1':
        raise ValueError('Project registry schema mismatch')
    rows = registry.get('projects')
    if not isinstance(rows, list) or {r.get('id') for r in rows} != {'amazon-keyword-library', 'amazon-listing-pipeline'} or len(rows) != 2:
        raise ValueError('Exactly the two approved projects are required')
    if list((root / '.agents' / 'skills').glob('*/SKILL.md')):
        raise ValueError('Business Skills must not be flattened at repository root')
    seen = {}
    checks = []
    for row in rows:
        if row['path'] != 'projects/' + row['id']:
            raise ValueError('Project identity/path mismatch')
        project = owned_path(root, row['path'])
        if not owned_path(project, row['entry']).is_file():
            raise ValueError('Missing project entry: ' + row['id'])
        skills = sorted(owned_path(project, row['maintenance_skills']).glob('*/SKILL.md'))
        if len(skills) != row['expected_skill_count']:
            raise ValueError('Authoritative Skill count mismatch: ' + row['id'])
        for skill in skills:
            text = skill.read_text(encoding='utf-8')
            header = text.split('---', 2)
            match = re.search(r'(?m)^name:\s*[\"\']?([a-z0-9-]+)', header[1] if len(header) == 3 else '')
            if not match or match[1] != skill.parent.name or match[1] in seen:
                raise ValueError('Invalid or colliding authoritative Skill: ' + str(skill.relative_to(root)))
            seen[match[1]] = str(skill.relative_to(root))
        if 'role_registry' in row and not owned_path(project, row['role_registry']).is_file():
            raise ValueError('Missing role registry')
        for command in row['checks']:
            argv = command.split()
            script = owned_path(project, argv[0])
            if not script.is_file() or script.suffix != '.py' or any(a.startswith('-') for a in argv[1:]):
                raise ValueError('Invalid project check entry: ' + command)
            checks.append((row['id'], project, [sys.executable, '-B', str(script), *argv[1:]]))
    return seen, checks


def main():
    try:
        files = validate_inventory(ROOT)
        skills, checks = validate_registry(ROOT)
        for project_id, cwd, command in checks:
            print('CHECK ' + project_id + ': ' + Path(command[2]).name, flush=True)
            result = subprocess.run(command, cwd=cwd, check=False)
            if result.returncode:
                raise ValueError('Original project validation failed: ' + project_id)
        print(json.dumps({'valid': True, 'projects': 2, 'authoritative_skills': len(skills),
                          'release_files': files, 'business_run': 'not_executed', 'P1': 'not_executed'}))
        return 0
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print('BLOCKED: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
