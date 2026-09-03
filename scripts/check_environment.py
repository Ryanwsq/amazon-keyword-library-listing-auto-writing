#!/usr/bin/env python3
"""Local deployment probes only: no credentials, network, package install or business input."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[1]
RESERVED = {'CON', 'PRN', 'AUX', 'NUL'} | {p + str(n) for p in ('COM', 'LPT') for n in range(1, 10)}


def windows_path_issues(paths):
    issues, seen = [], {}
    for value in sorted(paths):
        path = PurePosixPath(value)
        if path.is_absolute() or '..' in path.parts or '\\' in value:
            issues.append('unsafe path: ' + value)
        for index, part in enumerate(path.parts):
            if re.search(r'[<>:"|?*\x00-\x1f]', part) or part.endswith((' ', '.')) or part.split('.')[0].upper() in RESERVED:
                issues.append('Windows-incompatible name: ' + value)
            prefix = '/'.join(path.parts[:index + 1])
            key = prefix.casefold()
            if key in seen and seen[key] != prefix:
                issues.append('case collision: ' + prefix + ' / ' + seen[key])
            seen[key] = prefix
    return sorted(set(issues))


def command(args, cwd=None):
    return subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          encoding='utf-8', errors='replace', timeout=15, check=True).stdout.strip()


def probe_version(name, args, minimum=None):
    if not shutil.which(name):
        return {'ok': False, 'reason': 'not found in task PATH'}
    try:
        output = command([name, *args])
        match = re.search(r'(\d+)\.(\d+)(?:\.(\d+))?', output)
        if not match:
            return {'ok': False, 'reason': 'unrecognized version output'}
        version = tuple(int(x or 0) for x in match.groups())
        return {'ok': minimum is None or version >= minimum, 'version': '.'.join(map(str, version))}
    except (OSError, subprocess.SubprocessError):
        return {'ok': False, 'reason': 'version probe failed or timed out'}


def probe_zip_commands():
    unzip = {'ok': False, 'reason': 'unzip not found in task PATH'}
    zip_cli = {'ok': False, 'reason': 'zip not found in task PATH (assembly fixtures only)'}
    # A synthetic ZIP, never a user artifact; cleaned by TemporaryDirectory.
    with tempfile.TemporaryDirectory(prefix='workflow-zip-probe-') as temporary:
        directory = Path(temporary)
        archive = directory / 'synthetic probe.zip'
        marker = b'synthetic deployment probe only'
        with ZipFile(archive, 'w') as workbook:
            workbook.writestr('probe.txt', marker)
        if shutil.which('unzip'):
            try:
                names = command(['unzip', '-Z1', str(archive)]).splitlines()
                value = command(['unzip', '-p', str(archive), 'probe.txt'])
                unzip = {'ok': names == ['probe.txt'] and value == marker.decode(), 'tested_flags': ['-Z1', '-p']}
            except (OSError, subprocess.SubprocessError):
                unzip = {'ok': False, 'reason': 'unzip listing/extraction flags failed or timed out'}
        if shutil.which('zip'):
            try:
                staging = directory / 'staging'
                staging.mkdir()
                (staging / 'probe.txt').write_bytes(marker)
                zipped = directory / 'fixture.zip'
                command(['zip', '-q', '-r', str(zipped), '.'], cwd=staging)
                with ZipFile(zipped) as value:
                    valid = value.read('probe.txt') == marker
                zip_cli = {'ok': valid, 'tested_flags': ['-q', '-r']}
            except (OSError, subprocess.SubprocessError, KeyError, ValueError, BadZipFile):
                zip_cli = {'ok': False, 'reason': 'zip fixture flags failed or timed out'}
    return unzip, zip_cli


def main():
    try:
        paths = list(json.loads((ROOT / 'migration/release-files.json').read_text(encoding='utf-8'))['files'])
        path_issues = windows_path_issues(paths)
        unzip, zip_cli = probe_zip_commands()
        required = {
            'python': {'ok': sys.version_info >= (3, 11), 'version': '.'.join(map(str, sys.version_info[:3]))},
            'git': probe_version('git', ['--version']),
            'node': probe_version('node', ['--version'], (20, 0, 0)),
            'unzip_for_privacy_audit': unzip,
            'public_windows_names': {'ok': not path_issues, 'issues': path_issues},
        }
        longest = max((len(str(ROOT / path)) for path in paths), default=0)
        warnings = []
        if os.name == 'nt' and longest >= 240:
            warnings.append('Use a shorter clone directory; long-path support differs by executable.')
        if not zip_cli['ok']:
            warnings.append('Assembly regression fixtures require a compatible zip command.')
        ok = all(row['ok'] for row in required.values())
        print(json.dumps({'schema': 'amazon-workflow-environment/v1', 'local_prerequisites_ok': ok,
                          'required': required, 'zip_for_fixtures': zip_cli, 'warnings': warnings,
                          'max_public_relative_path_chars': max(map(len, paths), default=0),
                          'manual_checks_remaining': ['spreadsheet generation/reload/formula/render runtime',
                                                      'owned task bindings and current revision',
                                                      'provider login/auth/permissions/quota'],
                          'external_services': 'not_checked', 'business_run': 'not_executed',
                          'P1': 'not_executed'}, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    except (OSError, ValueError, KeyError) as exc:
        print('Environment probe failed: ' + type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
