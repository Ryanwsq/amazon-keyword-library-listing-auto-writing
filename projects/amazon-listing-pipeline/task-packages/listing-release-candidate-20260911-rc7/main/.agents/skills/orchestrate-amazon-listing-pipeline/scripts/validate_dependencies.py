#!/usr/bin/env python3
"""Validate this exact deployed package; never fall back to global Skills."""
from __future__ import annotations
import argparse
import json
import runpy
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-skills')
    parser.add_argument('--extra-root', action='append', default=[])
    args = parser.parse_args()
    script = Path(__file__).resolve()
    root = next((p for p in script.parents if (p / 'contracts/skill-dependencies.json').is_file()), None)
    errors = []
    if root is None:
        print(json.dumps({'valid': False, 'errors': ['Missing locked dependency contract'], 'global_fallback': False}))
        return 2
    if args.extra_root:
        errors.append('Implicit/extra Skill roots are not permitted for a locked task package')
    if args.project_skills and Path(args.project_skills).resolve() != root / '.agents/skills':
        errors.append('project-skills does not match the locked package')
    try:
        validator = runpy.run_path(str(root / 'scripts/validate_skill_packages.py'))
        report = validator['validate'](root)
        errors.extend(report['errors'])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    result = {'valid': not errors, 'errors': errors, 'searched_roots': [str(root)],
              'global_fallback': False, 'scope': 'declared_local_structure_and_dependencies',
              'keyword_adapter': {'configured': 'sku-usable-keyword-library',
                                  'business_route': 'external_keyword_main_then_independent_sku_task',
                                  'runtime_verified': False},
              'external_runtime_dependencies': {'spreadsheets': 'not_checked',
                                                'Alexa_authentication': 'not_checked',
                                                'task_bindings_and_human_gates': 'not_checked'}}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == '__main__':
    raise SystemExit(main())
