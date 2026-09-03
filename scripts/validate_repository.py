#!/usr/bin/env python3
"""Validate the standalone Amazon keyword-library repository."""

from __future__ import annotations

import re
import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / ".agents" / "skills"
SELF = Path(__file__).resolve()

REQUIRED_PATHS = {
    Path("AGENTS.md"),
    Path("PROJECT.md"),
    Path("README.md"),
    Path(".gitignore"),
    Path("docs/thread-architecture.md"),
    Path("docs/thread-roles.md"),
    Path("docs/task-routing.md"),
    Path("docs/thread-map.local.example.md"),
    Path("docs/risk-gates.md"),
    Path("docs/skill-package-standard.md"),
    Path("docs/github-branching.md"),
    Path("docs/end-to-end-workflow.md"),
    Path("docs/keyword-judgment-boundaries.md"),
    Path("docs/runtime-optimization-contract.md"),
    Path("docs/dispatch-control-contract.md"),
    Path("contracts/runtime-rule-map.json"),
    Path("contracts/run-spec.example.json"),
    Path("contracts/source-preflight.example.json"),
    Path("knowledge/INDEX.md"),
    Path("knowledge/product-keyword-library.md"),
    Path("knowledge/keyword-decision-log.md"),
    Path("knowledge/keyword-cleaning-case-evidence.md"),
    Path("scripts/runtime_contract.py"),
    Path("scripts/keyword_deterministic_core.py"),
    Path("scripts/run_runtime_fixtures.py"),
    Path("scripts/dispatch_guard.py"),
    Path("scripts/test_dispatch_guard.py"),
}

TEXT_SUFFIXES = {
    ".json",
    ".md",
    ".py",
    ".sh",
    ".text",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

FORBIDDEN_FILENAMES = {
    ".env",
    "id_ed25519",
    "id_rsa",
}

FORBIDDEN_SUFFIXES = {
    ".key",
    ".p12",
    ".pem",
}

SECRET_PATTERNS = {
    "private key block": re.compile(
        "-----BEGIN " + r"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    ),
    "GitHub token": re.compile(r"\bgh" + r"[opusr]_[A-Za-z0-9]{20,}\b"),
    "GitHub fine-grained token": re.compile(
        r"\bgithub_" + r"pat_[A-Za-z0-9_]{20,}\b"
    ),
    "OpenAI-style secret key": re.compile(r"\bsk" + r"-[A-Za-z0-9]{20,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Slack token": re.compile(r"\bxox" + r"[aboprs]-[A-Za-z0-9-]{20,}\b"),
    "absolute macOS user path": re.compile(r"/Users/[A-Za-z0-9._-]+/"),
    "Codex task identifier": re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        re.IGNORECASE,
    ),
}

AGENT_REQUIRED_HEADINGS = {
    "## 业务场景",
    "## 负责的结果",
    "## 使用时机",
    "## 可调用能力",
    "## 禁止事项与人工升级条件",
}

SKILL_REQUIRED_HEADINGS = {
    "## 目标",
    "## 输入",
    "## 输出",
    "## 可调用能力",
    "## 执行步骤",
    "## 质量标准",
    "## 异常处理",
}

EVIDENCE_REQUIRED_HEADINGS = {
    "## 执行环境",
    "## 输入",
    "## 实际执行步骤与能力 ID",
    "## 实际输出",
    "## 质量检查",
    "## 人工修改或失败原因",
    "## 结论",
}

EVIDENCE_INDEX_REQUIRED_HEADINGS = {
    "## Case slots",
    "## Evidence admission rules",
    "## Current status",
}

EVIDENCE_FILENAMES = {
    "case-01-normal.md",
    "case-02-normal.md",
    "case-03-edge-or-error.md",
}

CAPABILITY_REQUIRED_FIELDS = {
    "type",
    "purpose",
    "status",
    "input",
    "output",
    "permission",
    "risk",
}

CAPABILITY_TYPES = {"api", "cli", "mcp", "manual"}
CAPABILITY_STATUSES = {"planned", "verified", "unavailable"}
CAPABILITY_ID_PATTERN = re.compile(
    r"^[a-z][a-z0-9-]*(?:\.[a-z0-9][a-z0-9-]*)+$"
)


def is_ignored(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if path.name == "thread-map.local.md":
        return True
    return any(
        part in {".git", ".local", ".codex", "__pycache__", "node_modules"}
        for part in relative.parts
    )


def parse_frontmatter(path: Path, errors: List[str]) -> Dict[str, str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        errors.append(f"{path.relative_to(ROOT)}: missing opening YAML frontmatter")
        return {}

    try:
        closing = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        errors.append(f"{path.relative_to(ROOT)}: missing closing YAML frontmatter")
        return {}

    metadata: Dict[str, str] = {}
    for line in lines[1:closing]:
        if not line.strip() or line.lstrip().startswith("#") or line.startswith((" ", "\t")):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip("\"'")
    return metadata


def validate_required_paths(errors: List[str]) -> None:
    for relative in sorted(REQUIRED_PATHS):
        if not (ROOT / relative).is_file():
            errors.append(f"missing required workspace file: {relative}")


def validate_required_headings(
    path: Path, required: Set[str], errors: List[str]
) -> str:
    text = path.read_text(encoding="utf-8")
    lines = {line.strip() for line in text.splitlines()}
    for heading in sorted(required):
        if heading not in lines:
            errors.append(f"{path.relative_to(ROOT)}: missing heading {heading!r}")
    return text


def parse_capabilities(
    path: Path, expected_name: str, errors: List[str]
) -> Tuple[str, str, Dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    relative = path.relative_to(ROOT)

    name_match = re.search(r"(?m)^[ ]{2}name:[ ]*([^#\n]+?)\s*$", text)
    maturity_match = re.search(
        r"(?m)^[ ]{2}maturity:[ ]*(draft|verified)\s*$", text
    )
    verified_match = re.search(
        r"(?m)^[ ]{2}last_verified:[ ]*([^#\n]+?)\s*$", text
    )

    package_name = (
        name_match.group(1).strip().strip("\"'") if name_match else ""
    )
    maturity = maturity_match.group(1) if maturity_match else ""
    last_verified = (
        verified_match.group(1).strip().strip("\"'") if verified_match else ""
    )

    if not package_name:
        errors.append(f"{relative}: missing skill.name")
    elif package_name != expected_name:
        errors.append(
            f"{relative}: skill.name {package_name!r} does not match {expected_name!r}"
        )
    if not maturity:
        errors.append(f"{relative}: maturity must be draft or verified")
    if not verified_match:
        errors.append(f"{relative}: missing skill.last_verified")
    elif maturity == "verified" and last_verified.lower() in {"", "null", "none"}:
        errors.append(f"{relative}: verified skill needs last_verified date")

    capabilities: Dict[str, str] = {}
    block_pattern = re.compile(
        r"(?ms)^[ ]{2}- id:[ ]*([^#\n]+?)\s*$\n(.*?)(?=^[ ]{2}- id:|\Z)"
    )
    for match in block_pattern.finditer(text):
        capability_id = match.group(1).strip().strip("\"'")
        body = match.group(2)
        fields = {
            key: value.strip().strip("\"'")
            for key, value in re.findall(
                r"(?m)^[ ]{4}([a-z_]+):[ ]*(.*?)\s*$", body
            )
        }

        if not CAPABILITY_ID_PATTERN.fullmatch(capability_id):
            errors.append(f"{relative}: invalid capability id {capability_id!r}")
        elif capability_id in capabilities:
            errors.append(f"{relative}: duplicate capability id {capability_id!r}")

        missing = CAPABILITY_REQUIRED_FIELDS - fields.keys()
        for field in sorted(missing):
            errors.append(
                f"{relative}: capability {capability_id!r} missing field {field!r}"
            )

        capability_type = fields.get("type", "")
        status = fields.get("status", "")
        if capability_type and capability_type not in CAPABILITY_TYPES:
            errors.append(
                f"{relative}: capability {capability_id!r} has invalid type {capability_type!r}"
            )
        if status and status not in CAPABILITY_STATUSES:
            errors.append(
                f"{relative}: capability {capability_id!r} has invalid status {status!r}"
            )
        capabilities[capability_id] = status

    if not capabilities:
        errors.append(f"{relative}: no capabilities registered")

    return maturity, last_verified, capabilities


def capability_references(text: str) -> Set[str]:
    references: Set[str] = set()
    for value in re.findall(r"`([^`\n]+)`", text):
        if value.rsplit(".", 1)[-1] in {
            "json",
            "md",
            "py",
            "sh",
            "toml",
            "txt",
            "yaml",
            "yml",
        }:
            continue
        if CAPABILITY_ID_PATTERN.fullmatch(value):
            references.add(value)
    return references


def validate_evidence(skill_dir: Path, errors: List[str]) -> None:
    evidence_dir = skill_dir / "evidence"
    for filename in sorted(EVIDENCE_FILENAMES):
        path = evidence_dir / filename
        if not path.is_file():
            errors.append(
                f"{skill_dir.relative_to(ROOT)}: verified skill missing evidence/{filename}"
            )
            continue
        text = validate_required_headings(path, EVIDENCE_REQUIRED_HEADINGS, errors)
        for label in ("工具/版本", "执行日期", "执行人"):
            if re.search(rf"(?m)^- {re.escape(label)}：\s*$", text):
                errors.append(
                    f"{path.relative_to(ROOT)}: execution field {label!r} is empty"
                )
        for heading in sorted(EVIDENCE_REQUIRED_HEADINGS - {"## 执行环境"}):
            section = re.search(
                rf"(?ms)^{re.escape(heading)}\s*$\n(.*?)(?=^## |\Z)", text
            )
            if not section or not section.group(1).strip():
                errors.append(
                    f"{path.relative_to(ROOT)}: evidence section {heading!r} is empty"
                )
        quality = re.search(
            r"(?ms)^## 质量检查\s*$\n(.*?)(?=^## |\Z)", text
        )
        if quality:
            quality_text = quality.group(1)
            if not re.search(r"(?mi)^- \[[xX]\] ", quality_text):
                errors.append(
                    f"{path.relative_to(ROOT)}: verified evidence needs checked quality items"
                )
            if re.search(r"(?m)^- \[ \] ", quality_text):
                errors.append(
                    f"{path.relative_to(ROOT)}: verified evidence has unchecked quality items"
                )


def validate_evidence_index(
    skill_dir: Path, expected_name: str, maturity: str, errors: List[str]
) -> None:
    path = skill_dir / "evidence" / "index.md"
    if not path.is_file():
        errors.append(
            f"{skill_dir.relative_to(ROOT)}: missing evidence/index.md registry"
        )
        return

    text = validate_required_headings(
        path, EVIDENCE_INDEX_REQUIRED_HEADINGS, errors
    )
    relative = path.relative_to(ROOT)

    if f"- Skill: `{expected_name}`" not in text:
        errors.append(
            f"{relative}: registry Skill name does not match {expected_name!r}"
        )
    if maturity and f"- Maturity: `{maturity}`" not in text:
        errors.append(
            f"{relative}: registry Maturity does not match capabilities.yaml"
        )

    for filename in sorted(EVIDENCE_FILENAMES):
        matching_lines = [
            line for line in text.splitlines() if f"`{filename}`" in line
        ]
        if len(matching_lines) != 1:
            errors.append(
                f"{relative}: registry must mention {filename!r} exactly once"
            )
            continue
        row = matching_lines[0]
        if not re.search(
            r"\|\s*(planned|running|candidate|accepted|rejected)\s*\|", row
        ):
            errors.append(
                f"{relative}: {filename!r} needs a valid registry status"
            )
        if maturity == "verified" and not re.search(
            r"\|\s*accepted\s*\|.*\|\s*accepted\s*\|\s*$", row
        ):
            errors.append(
                f"{relative}: verified skill needs accepted registry and acceptance for {filename!r}"
            )


def validate_skills(errors: List[str]) -> Tuple[int, int, int]:
    if not SKILLS_ROOT.is_dir():
        errors.append("missing .agents/skills directory")
        return 0, 0, 0

    skill_roots = [SKILLS_ROOT]

    root_skill_files = sorted(SKILLS_ROOT.glob("*/SKILL.md"))
    if not root_skill_files:
        errors.append("no repository SKILL.md files found")
        return 0, 0, 0

    skill_count = 0
    draft_count = 0
    verified_count = 0
    name_pattern = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

    for skill_root in skill_roots:
        seen_names: Dict[str, Path] = {}
        for skill_file in sorted(skill_root.glob("*/SKILL.md")):
            skill_count += 1
            metadata = parse_frontmatter(skill_file, errors)
            name = metadata.get("name", "")
            description = metadata.get("description", "")
            relative = skill_file.relative_to(ROOT)

            if not name:
                errors.append(f"{relative}: missing frontmatter field 'name'")
            elif not name_pattern.fullmatch(name):
                errors.append(f"{relative}: invalid skill name {name!r}")
            elif name != skill_file.parent.name:
                errors.append(
                    f"{relative}: name {name!r} does not match directory {skill_file.parent.name!r}"
                )
            elif name in seen_names:
                errors.append(
                    f"{relative}: duplicate skill name in the same scope; "
                    f"also used by {seen_names[name].relative_to(ROOT)}"
                )
            else:
                seen_names[name] = skill_file

            if not description:
                errors.append(f"{relative}: missing frontmatter field 'description'")
            elif len(description) < 20:
                errors.append(f"{relative}: description is too short to trigger reliably")
            elif len(description) > 600:
                errors.append(f"{relative}: description exceeds 600 characters")

            skill_dir = skill_file.parent
            agent_file = skill_dir / "Agent.md"
            capabilities_file = skill_dir / "capabilities.yaml"

            if not agent_file.is_file():
                errors.append(f"{skill_dir.relative_to(ROOT)}: missing Agent.md")
                agent_text = ""
            else:
                agent_text = validate_required_headings(
                    agent_file, AGENT_REQUIRED_HEADINGS, errors
                )

            skill_text = validate_required_headings(
                skill_file, SKILL_REQUIRED_HEADINGS, errors
            )

            if not capabilities_file.is_file():
                errors.append(
                    f"{skill_dir.relative_to(ROOT)}: missing capabilities.yaml"
                )
                continue

            maturity, _, capabilities = parse_capabilities(
                capabilities_file, name or skill_dir.name, errors
            )
            validate_evidence_index(
                skill_dir, name or skill_dir.name, maturity, errors
            )
            if maturity == "draft":
                draft_count += 1
            elif maturity == "verified":
                verified_count += 1
            agent_references = capability_references(agent_text)
            skill_references = capability_references(skill_text)
            if not agent_references:
                errors.append(
                    f"{agent_file.relative_to(ROOT)}: no capability IDs referenced"
                )
            if not skill_references:
                errors.append(
                    f"{skill_file.relative_to(ROOT)}: no capability IDs referenced"
                )
            references = agent_references | skill_references

            for capability_id in sorted(references - capabilities.keys()):
                errors.append(
                    f"{skill_dir.relative_to(ROOT)}: referenced capability "
                    f"{capability_id!r} is not registered"
                )
            for capability_id in sorted(capabilities.keys() - references):
                errors.append(
                    f"{capabilities_file.relative_to(ROOT)}: capability "
                    f"{capability_id!r} is never referenced by Agent.md or SKILL.md"
                )

            knowledge_index = skill_dir / "knowledge" / "index.md"
            if knowledge_index.is_file():
                knowledge_text = knowledge_index.read_text(encoding="utf-8")
                if "资料无法确认时" not in knowledge_text:
                    errors.append(
                        f"{knowledge_index.relative_to(ROOT)}: missing uncertainty escalation statement"
                    )

            if maturity == "verified":
                for capability_id in sorted(references):
                    if capabilities.get(capability_id) != "verified":
                        errors.append(
                            f"{skill_dir.relative_to(ROOT)}: verified skill references "
                            f"non-verified capability {capability_id!r}"
                        )
                validate_evidence(skill_dir, errors)

    return skill_count, draft_count, verified_count


def validate_repository_files(errors: List[str]) -> int:
    checked = 0
    root_resolved = ROOT.resolve()

    for path in sorted(ROOT.rglob("*")):
        if is_ignored(path):
            continue

        if path.is_symlink():
            target = path.resolve()
            try:
                target.relative_to(root_resolved)
            except ValueError:
                errors.append(
                    f"{path.relative_to(ROOT)}: symlink escapes repository ({target})"
                )
            continue

        if not path.is_file():
            continue

        relative = path.relative_to(ROOT)
        checked += 1

        if path.name in FORBIDDEN_FILENAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            errors.append(f"{relative}: sensitive filename must not be committed")

        if path.stat().st_size > 1_000_000:
            errors.append(f"{relative}: file exceeds the 1 MB repository limit")

        if path.resolve() == SELF or path.suffix.lower() not in TEXT_SUFFIXES:
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                errors.append(f"{relative}: possible {label}")

    return checked


def validate_keyword_contract_sync(errors: List[str]) -> None:
    """Check critical cross-file invariants introduced by the current contract."""

    required_phrases = {
        Path("AGENTS.md"): {
            "卖家精灵长期副任务都必须在首次官网业务动作前验证登录",
            "同一成功种子不得为交叉验证重复导出",
            "最终交付固定为一个过程文件夹和一个八Sheet最终工作簿",
            "每Run必须在本机忽略目录建立内容寻址运行合同",
        },
        Path(".agents/skills/amazon-keyword-library-operations/references/source-merge-contract.md"): {
            "可选细分核心词",
            "Amazon联想锚点",
            "卖家精灵种子集合",
            "有细分核心词时恰好包含一级核心词和细分核心词",
            "validate-source-merge",
        },
        Path(".agents/skills/amazon-keyword-sellersprite-expansion/references/source-contract.md"): {
            "种子按`一级品类核心大词、产品细分核心词`锁定为两个",
            "首选本长期副任务内置浏览器中的已登录卖家精灵官网及其完整官方导出",
            "同一机械键跨不同种子只保留一个业务行",
            "未登录时副任务只向主任务回传`awaiting_login`",
        },
        Path(".agents/skills/amazon-keyword-category-cleaning/references/workbook-contract.md"): {
            "固定十四列",
            "通用词库资格",
            "目标细分同对象扩展",
            "纳入+不纳入+待复核=Sheet2人口",
            "目标同对象的普通非变物扩展不以显式出现细分核心词/强等价表达或SKU配置一致为纳入硬门",
            "反向抽查同时覆盖Sheet2误放、通用词库资格误纳",
            "validate-cleaning-ledger",
        },
        Path(".agents/skills/amazon-keyword-classification/references/output-contract.md"): {
            "完整保留第二板块十四列",
            "通用词库资格",
            "classify-traffic",
        },
        Path(".agents/skills/amazon-keyword-word-frequency/references/workbook-contract.md"): {
            "通用词库资格=纳入",
            "word-frequency",
        },
        Path(".agents/skills/amazon-keyword-competition-analysis/references/output-contract.md"): {
            "通用词库资格=纳入",
            "确定性核心",
        },
        Path(".agents/skills/amazon-keyword-trend-analysis/references/output-contract.md"): {
            "通用词库资格=纳入",
            "workbook -> 全部worksheet -> 各自全部drawing -> 各自全部chart",
            "2=auditor_failure",
            "manifest/OOXML包声明存在图表或公式而审计得到零",
            "确定性核心",
        },
        Path(".agents/skills/amazon-keyword-final-workbook-assembly/references/workbook-contract.md"): {
            "Fixed 51 fields plus N semantic columns",
            "固定十六列",
            "恰好八个可见Sheet",
            "最终去向=品类相关",
            "通用词库资格=纳入",
            "存在细分核心词时Amazon联想锚点为细分核心词",
            "独立QA产物一经返回即不可变",
            "process manifest不得列出或哈希自身",
            "普通64位SHA-256必须单独分类并放行",
            "Office内部GUID只允许合同脚本中绑定到精确OOXML部件的已知固定值",
            "Runtime preflight",
        },
        Path(".agents/skills/amazon-keyword-quality-validation/references/quality-contract.md"): {
            "14/13/12列",
            "固定51列+N动态列",
            "Gate 2必须验证ASIN代表人口、锚点/种子层级、单次导出与资格人口",
            "Gate 6必须验证二类词Sheet",
            "QA在最终封包前只生成一次最小白名单产物",
            "QA在装配最终封包后只读比较质量目录白名单",
            "Sheet2`通用词库资格=不纳入`、Sheet3和Sheet4反查假阴性",
            "Runtime contract audit",
        },
        Path("docs/end-to-end-workflow.md"): {
            "一至两个卖家精灵种子",
            "每个种子只取得一个成功完整官方导出",
            "未登录时副任务只回传主任务`awaiting_login`",
            "通用词库资格",
            "固定51列加N个动态语义列",
            "最终`二类词`Sheet机械复制",
            "恰好八个可见Sheet",
            "内容寻址`run-contract.json`",
        },
        Path("docs/runtime-optimization-contract.md"): {
            "三来源、固定来源人口、完整短语逐行语义判断",
            "失败只阻断自己的后代",
            "P0和夹具通过不等于P1或实测提速结论",
        },
    }

    for relative, phrases in required_phrases.items():
        path = ROOT / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for phrase in sorted(phrases):
            if phrase not in text:
                errors.append(
                    f"{relative}: current keyword contract missing {phrase!r}"
                )


def validate_runtime_layer(errors: List[str]) -> None:
    """Validate the tracked rule map and deterministic runtime entrypoints."""

    path = ROOT / "contracts" / "runtime-rule-map.json"
    if not path.is_file():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"contracts/runtime-rule-map.json: invalid JSON: {exc}")
        return
    if data.get("schema") != "amazon-keyword-rule-map/v1":
        errors.append("contracts/runtime-rule-map.json: unsupported schema")
    rules = data.get("rules")
    if not isinstance(rules, list) or not rules:
        errors.append("contracts/runtime-rule-map.json: rules must be a non-empty list")
        return
    seen: Set[str] = set()
    valid_stages = {
        "sif",
        "core-lock",
        "amazon-autocomplete",
        "sellersprite",
        "first-board",
        "cleaning",
        "word-frequency",
        "classification",
        "competition",
        "trend",
        "assembly",
        "quality-validation",
    }
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            errors.append(f"contracts/runtime-rule-map.json: rule {index} is not an object")
            continue
        rule_id = rule.get("id")
        owner = rule.get("owner")
        anchor = rule.get("anchor")
        stages = rule.get("stages")
        if not isinstance(rule_id, str) or not rule_id:
            errors.append(f"contracts/runtime-rule-map.json: rule {index} missing id")
        elif rule_id in seen:
            errors.append(f"contracts/runtime-rule-map.json: duplicate rule id {rule_id!r}")
        else:
            seen.add(rule_id)
        if not isinstance(owner, str) or Path(owner).is_absolute() or ".." in Path(owner).parts:
            errors.append(f"contracts/runtime-rule-map.json: {rule_id!r} has invalid owner")
            continue
        owner_path = ROOT / owner
        if not owner_path.is_file():
            errors.append(f"contracts/runtime-rule-map.json: {rule_id!r} owner is missing")
            continue
        if not isinstance(anchor, str) or anchor not in owner_path.read_text(encoding="utf-8"):
            errors.append(f"contracts/runtime-rule-map.json: {rule_id!r} anchor is missing")
        if not isinstance(stages, list) or not stages or set(stages) - valid_stages:
            errors.append(f"contracts/runtime-rule-map.json: {rule_id!r} stages are invalid")

    entrypoints = {
        Path("scripts/dispatch_guard.py"): {"build", "reserve", "sent", "accept", "observe", "reconcile"},
        Path("scripts/runtime_contract.py"): {
            "build",
            "verify",
            "ready",
            "resume",
            "impact",
            "make-status",
        },
        Path("scripts/keyword_deterministic_core.py"): {
            "validate-source-merge",
            "validate-cleaning-ledger",
            "classify-traffic",
            "word-frequency",
            "competition",
            "trend",
        },
    }
    for relative, commands in entrypoints.items():
        script = ROOT / relative
        if not script.is_file():
            continue
        text = script.read_text(encoding="utf-8")
        for command in sorted(commands):
            if command not in text:
                errors.append(f"{relative}: missing runtime command {command!r}")


def main() -> int:
    errors: List[str] = []
    validate_required_paths(errors)
    skill_count, draft_count, verified_count = validate_skills(errors)
    validate_keyword_contract_sync(errors)
    validate_runtime_layer(errors)
    file_count = validate_repository_files(errors)

    if errors:
        print("Repository validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        f"Repository P0 validation passed: {skill_count} skills "
        f"({draft_count} draft, {verified_count} verified), "
        f"{file_count} repository files checked."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
