#!/usr/bin/env python3
"""Freeze, build and verify complete, role-scoped local Listing task packages.

The builder never rewrites source rules. Deployments are immutable snapshots;
explicitly authorized source revisions are declared in package maintenance metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit
from validate_skill_packages import make_contract, validate as validate_standard

ORCH = 'orchestrate-amazon-listing-pipeline'
SKILLS = '.agents/skills/'
CHECKER = SKILLS + ORCH + '/scripts/validate_dependencies.py'
IGNORED = {'.DS_Store', '__pycache__'}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode(obj: object) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode()


def files_under(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob('*') if p.is_file()
                  and not any(part in IGNORED for part in p.parts)
                  and p.suffix != '.pyc')


def safe_read(root: Path, relative: str) -> bytes:
    path = root / relative
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Unsafe source/path: ' + relative)
    return path.read_bytes()


def inventory(root: Path) -> list[str]:
    paths = files_under(root / '.agents/skills') + files_under(root / 'knowledge-base')
    paths += [root / 'project-control/listing-writing-iteration-log.md']
    paths += [root / 'docs/skill-package-standard.md', root / 'scripts/validate_skill_packages.py']
    return sorted(set(p.relative_to(root).as_posix() for p in paths))


def spec(root: Path) -> dict:
    return json.loads((root / 'task-package-specs/roles.json').read_text())


def audit_dir(root: Path, version: str) -> Path:
    if not re.fullmatch(r'[a-z0-9-]+', version):
        raise ValueError('Unsafe version')
    return root / 'project-control/task-package-split' / version


def put_new(path: Path, data: bytes) -> None:
    if path.exists():
        if path.read_bytes() == data:
            return
        raise ValueError('Refusing to overwrite: ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def freeze(root: Path) -> dict:
    version = spec(root)['version']
    lock_path = audit_dir(root, version) / 'source-lock.json'
    if lock_path.exists():
        lock = json.loads(lock_path.read_text())
        assert_source_lock(root, lock)
        return lock
    locked = [{'path': p, 'sha256': digest(safe_read(root, p)),
               'bytes': len(safe_read(root, p))} for p in inventory(root)]
    lock = {'schema_version': 1, 'version': version,
            'frozen_at': datetime.now(timezone.utc).isoformat(),
            'source_root': '.', 'publication_status': spec(root)['publication_status'],
            'source_files': locked,
            'excluded': [
                {'path': 'outputs/', 'reason': '历史业务产物保留原位，不作为规则依赖'},
                {'path': 'project-control/archives/', 'reason': '历史版本保留原位；当前规则不回退'},
                {'path': 'project-control/thread-map.yaml', 'reason': '真实本机映射单独备份，不复制进角色包'},
                {'path': '.git/.codex/缓存/凭据', 'reason': '不属于业务规则包，不迁移登录或Git状态'}]}
    put_new(lock_path, encode(lock))
    # Portable candidates never read or copy local task bindings.
    return lock


def assert_source_lock(root: Path, lock: dict) -> None:
    current = inventory(root)
    expected = [r['path'] for r in lock['source_files']]
    if current != expected:
        raise ValueError('Source inventory changed; do not silently refresh the lock')
    for row in lock['source_files']:
        if digest(safe_read(root, row['path'])) != row['sha256']:
            raise ValueError('Locked source changed: ' + row['path'])


def skill_sources(source_paths: list[str], name: str) -> list[str]:
    return [p for p in source_paths if p.startswith(SKILLS + name + '/')]


def selection(root: Path, role: dict, source_paths: list[str]) -> dict[str, str]:
    selected = {}
    def add(paths: list[str]) -> None:
        selected.update({p: p for p in paths})
    if role.get('all_sources'):
        add(source_paths)
    else:
        add(skill_sources(source_paths, role['skill']))
    if role.get('include_knowledge'):
        add([p for p in source_paths if p.startswith('knowledge-base/')])
        add(['project-control/listing-writing-iteration-log.md'])
    if role.get('include_orchestrator_support'):
        add(skill_sources(source_paths, ORCH))
    for name in role.get('dependency_skills', []):
        for p in skill_sources(source_paths, name):
            selected[p] = p
    add(['docs/skill-package-standard.md', 'scripts/validate_skill_packages.py'])
    selected = {('dependencies/skills/' + target[len(SKILLS):]
                 if target.startswith(SKILLS) and target.split('/')[2] != role['skill'] else target): source
                for target, source in selected.items()}
    return dict(sorted(selected.items()))


def rebased_data(root: Path, source: str, target: str, selected: dict[str, str]) -> bytes:
    """Rebase only declared file-reference paths, never business wording or schema."""
    original = safe_read(root, source)
    source_to_target = {s: t for t, s in selected.items()}
    if source.endswith('/knowledge/catalog.json'):
        rows = json.loads(original)
        for row in rows:
            if row['source'] not in source_to_target:
                raise ValueError('Missing knowledge dependency: ' + row['source'])
            row['source'] = source_to_target[row['source']]
        return encode(rows)
    if not source.endswith('.md'):
        return original
    text = original.decode()
    def replace(match):
        raw = match.group(2).strip('<>')
        if raw.startswith('#') or urlsplit(raw).scheme:
            return match.group(0)
        path, sep, fragment = raw.partition('#')
        resolved = (root / source).parent / unquote(path)
        if not resolved.resolve().is_relative_to(root.resolve()):
            raise ValueError('Reference leaves source root: ' + source)
        rel = resolved.resolve().relative_to(root.resolve()).as_posix()
        if rel not in source_to_target:
            if resolved.is_dir():
                return match.group(0)
            raise ValueError('Unpackaged source dependency: ' + rel)
        new = Path(os.path.relpath(source_to_target[rel], Path(target).parent)).as_posix()
        return '[' + match.group(1) + '](' + new + (sep + fragment if sep else '') + ')'
    return re.sub(r'\[([^\]\n]*)\]\(([^)\n]+)\)', replace, text).encode()


def link_target(root: Path, file: Path, raw: str) -> Path | None:
    target = raw.strip().strip('<>')
    if target.startswith('#') or urlsplit(target).scheme:
        return None
    target = unquote(target.split('#', 1)[0])
    if not target:
        return None
    result = (file.parent / target).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError(f'Link escapes package: {file.relative_to(root)} -> {raw}')
    return result


def validate_links(root: Path) -> list[str]:
    errors = []
    for p in files_under(root):
        if p.suffix != '.md':
            continue
        for target in re.findall(r'\[[^\]\n]*\]\(([^)\n]+)\)', p.read_text()):
            try:
                resolved = link_target(root, p, target)
                if resolved is not None and not resolved.exists():
                    errors.append(f'Broken link: {p.relative_to(root)} -> {target}')
            except ValueError as exc:
                errors.append(str(exc))
    return errors


def validate_plain_frontmatter(text: str, expected_name: str) -> list[str]:
    """Fail-closed fallback for these packages' two plain-scalar fields.

    This is not a general YAML parser or a claim that quick_validate.py ran.
    Any richer YAML must be reviewed with a real YAML parser instead.
    """
    match = re.match(r'^---\n(.*?)\n---(?:\n|$)', text, re.S)
    if not match:
        return ['Missing or invalid frontmatter delimiters']
    fields = {}
    for line in match.group(1).splitlines():
        if not line.strip():
            continue
        row = re.fullmatch(r'(name|description): ([^\r\n]+)', line)
        if not row or row.group(1) in fields:
            return ['Unsupported/duplicate YAML field; real YAML parser required']
        value = row.group(2)
        if value[0] in '\"\'[{|>*&!@`' or ': ' in value or ' #' in value:
            return ['Non-plain YAML scalar; real YAML parser required']
        fields[row.group(1)] = value
    if set(fields) != {'name', 'description'}:
        return ['Both name and description are required']
    name, description = fields['name'], fields['description']
    errors = []
    if (name != expected_name or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name)
            or len(name) > 64):
        errors.append('Invalid or mismatched Skill name')
    if not description.strip() or len(description) > 1024 or '<' in description or '>' in description:
        errors.append('Invalid Skill description')
    if description.startswith('[TODO:') or re.search(r'(?m)^\s*\[TODO:[^\n]*\]\s*$', text[match.end():]):
        errors.append('Unfinished Skill scaffold')
    return errors


def section_map(path: str, data: bytes, target: str) -> list[dict]:
    lines = data.decode().splitlines(keepends=True)
    boundaries = [0] + [i for i, line in enumerate(lines) if i > 0 and re.match(r'^#{1,6} ', line)]
    boundaries.append(len(lines))
    return [{'source': path, 'target': target, 'start_line': start + 1, 'end_line': end,
             'sha256': digest(''.join(lines[start:end]).encode())}
            for start, end in zip(boundaries, boundaries[1:]) if end > start]


def generate_role(root: Path, output: Path, role: dict, config: dict, lock: dict) -> dict:
    output.mkdir(parents=True)
    paths = [r['path'] for r in lock['source_files']]
    selected = selection(root, role, paths)
    records, sections = [], []
    for target, source in selected.items():
        original = safe_read(root, source)
        data = rebased_data(root, source, target, selected)
        destination = output / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        records.append({'path': target, 'source': source, 'source_sha256': digest(original),
                        'sha256': digest(data), 'operation': 'declared_reference_rebase' if data != original else 'byte_identical_copy',
                        'classification': ('candidate_template_asset' if 'golden-' in source else
                                           'local_provenance' if source.startswith('project-control/') else
                                           'complete_rule_or_dependency')})
        if target.endswith('.md'):
            sections.extend(section_map(source, data, target))

    own = SKILLS + role['skill'] + '/SKILL.md'
    refs = sorted(p.split('/')[2] for p in selected
                  if p.startswith('dependencies/skills/') and p.endswith('/SKILL.md'))
    rule_files = [r for r in records if r['path'].endswith('.md')]
    knowledge_list = '\n'.join('- [' + r['source'] + '](../' + r['path'] + ')' for r in rule_files)
    role_agent = f"""# {role['title']}

角色ID：`{role['id']}`。版本：`{config['version']}`。

## 职责

{role['purpose']}。唯一所属Skill：[{role['skill']}]({own})。

## 边界与加载

完整读取[加载顺序](LOAD_ORDER.md)及[交接边界](contracts/dispatch-and-loading.md)。本包内其他Skill、dependencies/和历史依据只用于输入解释或主任务监督，不授予跨模块执行权。

默认只读初始化；无锁定输入和明确业务启动指令不执行历史Run、不访问Alexa、不输出业务工作簿。主任务保留两道人机确认与最终验收；副任务不代理确认。所属Skill的全部判断、例外、停止与重试规则保持原文。

缺少文件、版本冲突、身份不符或无法解释来源时报告并停止受影响动作；禁止回退全局同名Skill。快照不直接编辑，规则迭代须回权威源经授权再生成新版本。

本批仅结构拆分。历史验收状态留在原Skill和证据中，不新增P1、也不撤销既有业务验收。真实业务输入、工具权限和登录不包含在本包。
"""
    generated = {
        'AGENTS.md': f"# {role['title']}：任务包入口\n\n本目录只绑定角色 `{role['id']}`，不因cwd或相同Skill名称改变职责。先完整读取[Agent.md](Agent.md)和[LOAD_ORDER.md](LOAD_ORDER.md)，再按所属Skill执行。\n\n本包是候选部署快照，不自动授权业务运行或公开发布。包内校验只读；验证输出放主任务批准的包外审计目录。\n",
        'Agent.md': role_agent,
        'LOAD_ORDER.md': f"# 加载顺序\n\n1. 核对明确下发的角色 `{role['id']}`、版本 `{config['version']}` 和 [package-manifest.json](package-manifest.json) 哈希。\n2. 完整读取 [Agent.md](Agent.md) 和 [任务包交接边界](contracts/dispatch-and-loading.md)。\n3. 完整读取所属 [{role['skill']}]({own})。\n4. 按Skill要求完整读取必需reference与知识正文；[知识索引](knowledge-base/index.md)与[规则映射](rules/index.md)只作导航，不代替正文。\n5. 再核对本次锁定输入、来源、Run/SKU及启动授权；没有业务输入时停止在只读READY。\n\n主任务包保留全项目规则用于监督和分发；非所属Skill不在当前任务执行业务。副任务包只包含本角色所需完整材料与明确依赖。证据与结构测试范围见[evidence/index.md](evidence/index.md)。\n",
        'knowledge-base/index.md': '# 完整知识与合同索引\n\n以下文件均在本包内，保留来源正文；不是摘要替代品。各文件适用阶段以所属Skill的读取路由为准；依赖/历史材料不自动变为本模块现行规则。\n\n' + knowledge_list + '\n\n来源、日期、版本、哈希见package-manifest.json及各源文件。无法确认资料时保留不确定并交主任务确认。\n',
        'rules/index.md': '# 判断边界保全索引\n\n完整规则仍在原Skill/reference/知识正文；不得只读取此索引或只匹配Rule ID。\n\n[逐章节来源与哈希](rule-map.json)覆盖复制的Markdown正文，包括前言、条件、例外、失败与停止条款。逐文件字节一致性见[包清单](../package-manifest.json)。\n\n唯一内容适配是总控依赖发现脚本：取消隐式全局回退，改为检查本包完整清单和精确哈希，不改业务判断。其原/新哈希在清单逐项列出。\n',
        'evidence/index.md': '# 本次拆分验证范围\n\n本包保留原业务规则及其原有状态，不以新目录给旧Skill降级或升级。本次仅验证文件、依赖、规则正文保全及现有机械回归。\n\n- 新业务Run：未执行\n- 新真实三案例/P1：未执行\n- 外部工具、登录及后台审核：未验证\n- 结构检查与脚本测试：以主任务本批validation-report和测试日志的实际结果为准\n\n接收整理入口的文件化不代表新建了评分、采集或写作能力。真实案例仍回原Run及已有获准证据，不伪造案例文件。\n',
        'PUBLICATION.md': '# 本地包，不直接公开发布\n\n本批保留完整本地规则、来源说明及适用资产。原文可能包含本机来源路径、历史Run/ASIN示例及讨论依据；标签黄金模板含示例业务数据，只复用版式/公式，不复用事实。\n\n本包尚未脱敏或取得公开发布许可。不要上传GitHub、共享云盘或把本包当纯空模板发布。真实任务ID、设备绑定和接收回执留在项目本地映射。外部工具与登录不随包分发。\n'}
    generated['PUBLICATION.md'] = safe_read(root, 'PUBLICATION.md').decode()
    generated['contracts/dispatch-and-loading.md'] = safe_read(root, 'task-package-specs/dispatch-and-loading.md').decode()
    maintenance = config.get('maintenance')
    if maintenance:
        note = ('本版维护事项：`' + maintenance['id'] + '`；范围：' + maintenance['scope'] +
                '。v1/v2快照及历史业务产物不改；实际差异以维护源和逐文件清单为准，'
                '不把接口兼容修订声称为仅路径改动，不新增业务Run或P1。')
        generated['Agent.md'] = generated['Agent.md'].replace('本批仅结构拆分。', note + '\n\n')
        generated['rules/index.md'] = generated['rules/index.md'].replace(
            '唯一内容适配是总控依赖发现脚本：取消隐式全局回退，改为检查本包完整清单和精确哈希，不改业务判断。其原/新哈希在清单逐项列出。', note)
        generated['evidence/index.md'] += '\n\n' + note + '\n'
    for path, text in generated.items():
        put_new(output / path, text.encode())
        records.append({'path': path, 'sha256': digest(text.encode()), 'operation': 'generated_packaging_metadata'})
    put_new(output / 'rules/rule-map.json', encode(sections))
    records.append({'path': 'rules/rule-map.json', 'sha256': digest(encode(sections)), 'operation': 'generated_complete_section_map'})
    entries = [{'name': role['skill'], 'path': SKILLS + role['skill'], 'mode': 'executable', 'role': role['id']}]
    owners = {r['skill']: r['id'] for r in config['roles']}
    entries += [{'name': name, 'path': 'dependencies/skills/' + name, 'mode': 'reference', 'role': owners[name]} for name in refs]
    contract_path = 'contracts/skill-dependencies.json'
    contract = make_contract(output, entries, config['version'], [r['path'] for r in records])
    put_new(output / contract_path, encode(contract))
    records.append({'path': contract_path, 'sha256': digest(encode(contract)), 'operation': 'generated_dependency_contract'})
    manifest = {'schema_version': 1, 'version': config['version'], 'role': role['id'],
                'title': role['title'], 'kind': role['kind'], 'owned_skills': [role['skill']],
                'reference_skills': refs, 'publication_status': config['publication_status'],
                'original_business_skill_count': 8, 'new_business_run': False,
                'business_rules_changed': role['id'] in (maintenance or {}).get('affected_roles', []),
                'authorized_maintenance': maintenance,
                'files': sorted(records, key=lambda x: x['path'])}
    put_new(output / 'package-manifest.json', encode(manifest))
    errors = validate_links(output)
    errors.extend(validate_standard(output)['errors'])
    if errors:
        raise ValueError('\n'.join(errors))
    return manifest


def build(root: Path) -> dict:
    config = spec(root)
    lock = freeze(root)
    package_root = root / 'task-packages'
    destination = package_root / config['version']
    if destination.exists():
        raise ValueError('Version already exists; validate it or create a new approved version')
    package_root.mkdir(exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.building-', dir=package_root))
    all_manifests = {}
    try:
        for role in config['roles']:
            all_manifests[role['id']] = generate_role(root, staging / role['id'], role, config, lock)
        covered = {r.get('source') for manifest in all_manifests.values() for r in manifest['files']}
        missing = set(inventory(root)) - covered
        if missing:
            raise ValueError('Source coverage gap: ' + repr(sorted(missing)))
        assert_source_lock(root, lock)
        staging.rename(destination)
    except Exception:
        print('Incomplete staging retained for inspection: ' + str(staging))
        raise
    registry = {'schema_version': 1, 'version': config['version'],
                'publication_status': config['publication_status'],
                'source_lock': (audit_dir(root, config['version']) / 'source-lock.json').relative_to(root).as_posix(),
                'roles': []}
    for role in config['roles']:
        path = destination / role['id']
        registry['roles'].append({'id': role['id'], 'title': role['title'], 'skill': role['skill'],
                                  'kind': role['kind'], 'path': path.relative_to(root).as_posix(),
                                  'manifest_sha256': digest((path / 'package-manifest.json').read_bytes())})
    # Promote only fully validated new snapshots; the previous registry is retained.
    put_new(audit_dir(root, config['version']) / 'registry.json', encode(registry))
    prior = package_root / 'registry.json'
    if prior.exists():
        put_new(audit_dir(root, config['version']) / 'registry.before.json', prior.read_bytes())
    fd, temporary = tempfile.mkstemp(prefix='.registry-', dir=package_root)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(encode(registry))
    os.replace(temporary, prior)
    coverage = []
    for row in lock['source_files']:
        uses = [{'role': role, 'target': file['path'], 'operation': file['operation'], 'sha256': file['sha256']}
                for role, manifest in all_manifests.items() for file in manifest['files']
                if file.get('source') == row['path']]
        coverage.append({**row, 'disposition': 'preserved', 'destinations': uses})
    put_new(audit_dir(root, config['version']) / 'file-coverage.json', encode(coverage))
    table = '# 任务包拆分与文件保全清单\n\n原始业务规则保持原位，角色包为只读部署快照；不移动历史Run，不公开发布。\n\n| 原文件 | SHA-256 | 完整副本归属 |\n|---|---|---|\n'
    for row in coverage:
        table += '| `' + row['path'] + '` | `' + row['sha256'] + '` | ' + '、'.join(u['role'] for u in row['destinations']) + ' |\n'
    put_new(audit_dir(root, config['version']) / 'file-coverage.md', table.encode())
    return registry


def validate(root: Path, check_sources: bool = True) -> dict:
    errors = []
    registry_path = root / 'task-packages/registry.json'
    try:
        registry = json.loads(registry_path.read_text())
        lock = json.loads((root / registry['source_lock']).read_text()) if check_sources else None
        if check_sources:
            assert_source_lock(root, lock)
        role_ids, skills = [], []
        covered = set()
        total_files, total_sections = 0, 0
        for role in registry['roles']:
            role_ids.append(role['id']); skills.append(role['skill'])
            package = root / role['path']
            if not package.resolve().is_relative_to(root.resolve()) or package.is_symlink():
                raise ValueError('Unsafe role path')
            raw = safe_read(package, 'package-manifest.json')
            if digest(raw) != role['manifest_sha256']:
                errors.append('Manifest hash drift: ' + role['id'])
            manifest = json.loads(raw)
            if (manifest['role'] != role['id'] or manifest['version'] != registry['version']
                    or manifest['owned_skills'] != [role['skill']]):
                errors.append('Role/version mismatch: ' + role['id'])
            expected = {'package-manifest.json'}
            for entry in manifest['files']:
                expected.add(entry['path']); total_files += 1
                try:
                    data = safe_read(package, entry['path'])
                    if digest(data) != entry['sha256']:
                        errors.append('File hash drift: ' + role['id'] + '/' + entry['path'])
                    if entry.get('source'):
                        covered.add(entry['source'])
                        if check_sources:
                            original = safe_read(root, entry['source'])
                            if digest(original) != entry['source_sha256']:
                                errors.append('Source drift: ' + entry['source'])
                            if entry['operation'] == 'byte_identical_copy' and data != original:
                                errors.append('Non-identical business rule: ' + entry['path'])
                            elif entry['operation'] == 'declared_reference_rebase':
                                mapping = {f['path']: f['source'] for f in manifest['files'] if f.get('source')}
                                if data != rebased_data(root, entry['source'], entry['path'], mapping):
                                    errors.append('Non-path modification: ' + entry['path'])
                            elif entry['operation'] != 'byte_identical_copy':
                                errors.append('Unapproved adaptation: ' + entry['path'])
                except (OSError, ValueError) as exc:
                    errors.append(str(exc))
            actual = {p.relative_to(package).as_posix() for p in files_under(package)}
            if actual != expected:
                errors.append('Undeclared/missing package files: ' + role['id'] + ' ' + repr(sorted(actual ^ expected)))
            sections = json.loads((package / 'rules/rule-map.json').read_text())
            total_sections += len(sections)
            for section in sections:
                lines = (package / section['target']).read_text().splitlines(keepends=True)
                part = ''.join(lines[section['start_line'] - 1:section['end_line']]).encode()
                if digest(part) != section['sha256']:
                    errors.append('Rule section changed: ' + section['target'])
            errors.extend(role['id'] + ': ' + e for e in validate_links(package))
            errors.extend(role['id'] + ': ' + e for e in validate_standard(package)['errors'])
            own_file = package / SKILLS / role['skill'] / 'SKILL.md'
            if not own_file.is_file():
                errors.append('Skill entrypoint mismatch: ' + role['id'])
            else:
                errors.extend(role['id'] + ': ' + e for e in validate_plain_frontmatter(own_file.read_text(), role['skill']))
        if len(role_ids) != 10 or len(set(role_ids)) != 10 or len(set(skills)) != 10:
            errors.append('Expected ten unique role/Skill bindings, including main and two receive-only roles')
        if check_sources and set(inventory(root)) - covered:
            errors.append('Original source files omitted')
        if check_sources:
            errors.extend('canonical: ' + e for e in validate_standard(root)['errors'])
        return {'valid': not errors, 'version': registry['version'], 'roles': len(role_ids),
                'files_verified': total_files, 'sections_verified': total_sections,
                'original_source_files': len(lock['source_files']) if lock else None,
                'source_rules_unchanged': check_sources and not errors,
                'frontmatter_check': 'strict_plain_scalar_fallback; quick_validate.py unavailable without PyYAML',
                'scope': 'structure_full_text_hashes_links_and_explicit_role_bindings',
                'business_run': 'not_executed', 'P1': 'not_executed',
                'publication_status': registry['publication_status'], 'errors': errors}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {'valid': False, 'errors': [str(exc)]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['freeze', 'build', 'validate'])
    parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--deployed-only', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    root = args.project_root.resolve()
    if args.command == 'freeze':
        result = freeze(root)
    elif args.command == 'build':
        result = build(root)
    else:
        result = validate(root, not args.deployed_only)
    if args.report:
        report = args.report.resolve()
        if not report.is_relative_to(root) or report.is_relative_to(root / 'task-packages'):
            raise ValueError('Reports must be under the project, outside immutable packages')
        put_new(report, encode(result))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get('valid', True) else 2


if __name__ == '__main__':
    raise SystemExit(main())
