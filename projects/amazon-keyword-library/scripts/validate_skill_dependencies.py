#!/usr/bin/env python3
"""Read-only, project-scoped dependency checks; never load a fallback Skill."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
import sysconfig
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Set, Tuple


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "contracts/skill-dependencies.json"
SCHEMA = "amazon-keyword-skill-dependencies/v1"
PACKAGE_FILES = ("Agent.md", "SKILL.md", "capabilities.yaml", "knowledge/index.md", "evidence/index.md")
TEXT_FILES = {".md", ".py", ".mjs", ".yaml", ".yml", ".json"}
SKIP_DIRS = {".git", ".local", "__pycache__", "node_modules"}
PATH_TOKEN = re.compile(
    r"(?<![\w./-])((?:(?:\.\.?/)+|\.agents/|docs/|knowledge/|references/|scripts/|tests/|contracts/|assets/)"
    r"[^\s`<>|，；、]+?\.(?:md|py|mjs|yaml|yml|json|xlsx|csv|png|zip))(?=$|[\s`#，；、])"
)
BARE_SCRIPT = re.compile(r"(?<![\w./-])([A-Za-z_][\w-]*\.(?:py|mjs))(?=$|[\s`，；、])")
LINK = re.compile(r"\[[^\]]*\]\(([^\s)]+)\)")
INLINE = re.compile(r"`([^`\n]+)`")
ENTRY_NAME = re.compile(r"(?m)^name:\s*[\"']?([a-z0-9-]+)[\"']?\s*$")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def skill_name(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    match = ENTRY_NAME.search(parts[1]) if len(parts) == 3 and not parts[0].strip() else None
    return match.group(1) if match else ""


def documented_references(text: str, topic_index: bool = False) -> Set[Tuple[str, bool]]:
    """Explicit links, source paths and bare scripts; output filenames are not dependencies."""
    result = set()
    for target in LINK.findall(text):
        if not target.startswith(("https://", "http://", "mailto:", "#")):
            result.add((target.split("#", 1)[0], True))
    for span in INLINE.findall(text):
        result.update((match.group(1), False) for match in PATH_TOKEN.finditer(span))
        result.update((match.group(1), False) for match in BARE_SCRIPT.finditer(span))
    if topic_index:
        for line in text.splitlines():
            cells = line.split("|")
            if len(cells) > 2:
                for token in INLINE.findall(cells[1]):
                    if token.endswith(".md"):
                        result.add((token, True))
    return result


def resolve_reference(root: Path, package: Path, source: Path, token: str, link: bool,
                      declared: Set[Path], errors: List[str]) -> Optional[Path]:
    label = source.relative_to(root).as_posix()
    if token.startswith(("../", "./")) or link:
        choices = [source.parent / token]
    elif token.startswith((".agents/", "docs/", "contracts/")):
        choices = [root / token]
    elif token == "knowledge/index.md" or token.startswith("references/"):
        choices = [package / token]
    elif "/" in token:
        choices = [package / token, root / token]
    else:
        choices = [p for p in declared if p.name == token]
    if not choices or any(not inside(p, root) for p in choices):
        errors.append(f"{label}: missing or out-of-scope dependency {token!r}")
        return None
    found = {p.resolve() for p in choices if p.is_file()}
    if len(found) != 1:
        reason = "ambiguous" if found else "missing"
        errors.append(f"{label}: {reason} dependency {token!r}")
        return None
    target = found.pop()
    if target not in declared:
        errors.append(f"{label}: dependency not registered for this package: {target.relative_to(root)}")
    return target


def check_imports(path: Path, root: Path, declared: Set[Path], errors: List[str]) -> None:
    text = path.read_text(encoding="utf-8")
    label = path.relative_to(root).as_posix()
    if path.suffix == ".mjs":
        for token in re.findall(r"(?:from\s*|import\s*\(\s*|import\s*)[\"'](\.[^\"']+)[\"']", text):
            resolve_reference(root, path.parent, path, token, True, declared, errors)
        return
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        errors.append(f"{label}: invalid Python syntax: {exc.msg}")
        return
    stdlib = Path(sysconfig.get_path("stdlib"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                errors.append(f"{label}: relative Python import needs explicit support before admission")
            elif node.module:
                modules.add(node.module.split(".")[0])
    for module in sorted(modules):
        candidates = {p.resolve() for p in (path.parent / (module + ".py"), root / "scripts" / (module + ".py")) if p.is_file()}
        if candidates:
            if len(candidates) != 1 or not candidates.issubset(declared):
                errors.append(f"{label}: ambiguous or unregistered local import {module!r}")
        elif not (module in sys.builtin_module_names or (stdlib / (module + ".py")).is_file()
                  or (stdlib / module / "__init__.py").is_file()
                  or list((stdlib / "lib-dynload").glob(module + ".*"))):
            errors.append(f"{label}: unresolved Python dependency {module!r}; no global fallback")


def audit_dependencies(root: Path = ROOT, additional_skill_roots=()) -> Dict:
    root = root.resolve()
    errors: List[str] = []
    files: Dict[str, str] = {}
    packages = {}
    evidence_counts: Counter = Counter()

    def require(relative) -> Optional[Path]:
        if not isinstance(relative, str) or not relative or "\\" in relative:
            errors.append("invalid dependency path: " + repr(relative))
            return None
        part = PurePosixPath(relative)
        if part.is_absolute() or ".." in part.parts or ":" in relative:
            errors.append("dependency path must be repository-relative: " + relative)
            return None
        path = root / relative
        if not inside(path, root) or not path.is_file():
            errors.append("missing or escaping dependency: " + relative)
            return None
        files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        return path.resolve()

    try:
        manifest_path = require(MANIFEST)
        if manifest_path is None:
            raise ValueError("dependency manifest unavailable")
        data = json.loads(manifest_path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
        if data.get("schema") != SCHEMA:
            raise ValueError("unsupported dependency manifest schema")
        skills = data.get("skills")
        shared = data.get("shared_files")
        if not isinstance(skills, dict) or not skills or not isinstance(shared, list):
            raise ValueError("skills and shared_files are required")
        if any(not isinstance(s, str) for s in shared):
            raise ValueError("shared_files must contain paths")
        if len(shared) != len(set(shared)):
            raise ValueError("duplicate shared dependency")
        for name, spec in skills.items():
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
                raise ValueError("invalid Skill identity: " + name)
            if not isinstance(spec, dict) or spec.get("entry") != f".agents/skills/{name}/SKILL.md":
                raise ValueError("noncanonical Skill entry: " + name)
    except (OSError, UnicodeError, ValueError, TypeError, AttributeError) as exc:
        return {"status": "fail", "errors": errors + [str(exc)], "files": files, "packages": {}, "evidence_counts": {}}

    common = {p for p in (require(s) for s in shared) if p is not None}
    topic_index = root / "knowledge" / "INDEX.md"
    if topic_index.resolve() in common:
        for token, link in sorted(documented_references(topic_index.read_text(encoding="utf-8"), topic_index=True)):
            resolve_reference(root, root, topic_index, token, link, common, errors)
    entries = sorted((root / ".agents" / "skills").glob("*/SKILL.md"))
    actual = {p.parent.name for p in entries}
    if actual != set(skills):
        errors.append(f"Skill inventory differs: missing={sorted(set(skills)-actual)}, unregistered={sorted(actual-set(skills))}")
    seen = {}
    for path in entries:
        if not inside(path, root):
            errors.append("Skill entry escapes repository: " + path.parent.name)
            continue
        name = skill_name(path)
        if name in seen:
            errors.append("duplicate Skill identity: " + name)
        seen[name] = path
        if name != path.parent.name:
            errors.append("Skill name/directory mismatch: " + path.parent.name)
    for extra in additional_skill_roots:
        extra = Path(extra).resolve()
        if not extra.is_dir():
            errors.append("additional Skill root is unavailable")
            continue
        for entry in sorted(extra.glob("*/SKILL.md")):
            name = skill_name(entry)
            if name in skills and entry.resolve() != (root / skills[name]["entry"]).resolve():
                errors.append("duplicate external Skill source: " + name)

    for name, spec in sorted(skills.items()):
        package = root / ".agents" / "skills" / name
        expected_entry = f".agents/skills/{name}/SKILL.md"
        if not isinstance(spec, dict) or spec.get("entry") != expected_entry:
            errors.append("noncanonical Skill entry: " + name)
            continue
        resources = spec.get("resources")
        if not isinstance(resources, list) or any(not isinstance(s, str) for s in resources):
            errors.append("invalid resource list: " + name)
            continue
        if len(resources) != len(set(resources)):
            errors.append("duplicate package resource: " + name)
        required = [f".agents/skills/{name}/{s}" for s in PACKAGE_FILES] + resources
        declared = common | {p for p in (require(s) for s in required) if p is not None}
        # Existing module files travel together; the manifest pins resources so deletion is not hidden.
        for path in sorted(package.rglob("*")):
            if any(part in SKIP_DIRS for part in path.relative_to(package).parts):
                continue
            if path.is_file() or path.is_symlink():
                target = require(path.relative_to(root).as_posix())
                if target is not None:
                    declared.add(target)
        registry = package / "evidence" / "index.md"
        if registry.is_file() and inside(registry, root):
            for line in registry.read_text(encoding="utf-8").splitlines():
                cells = [cell.strip().strip("`") for cell in line.split("|")]
                if len(cells) >= 8 and re.fullmatch(r"case-0[123]-(?:normal|edge-or-error)\.md", cells[1]):
                    state = cells[3]
                    evidence_counts[state] += 1
                    if state in {"candidate", "accepted", "rejected"}:
                        require(f".agents/skills/{name}/evidence/{cells[1]}")
        for path in sorted(declared):
            if path.suffix in {".py", ".mjs"}:
                check_imports(path, root, declared, errors)
            # Current package entrypoints/contracts carry load-bearing local references.
            # Historical case prose is not reinterpreted as a current dependency declaration.
            if path.suffix == ".md" and inside(path, package) and "evidence" not in path.relative_to(package).parts:
                for token, link in sorted(documented_references(path.read_text(encoding="utf-8"))):
                    resolve_reference(root, package, path, token, link, declared, errors)
        packages[name] = {"entry": expected_entry, "files": sorted(p.relative_to(root).as_posix() for p in declared)}

    return {"schema": "amazon-keyword-dependency-audit/v1", "status": "fail" if errors else "pass",
            "errors": sorted(set(errors)), "files": dict(sorted(files.items())), "packages": packages,
            "evidence_counts": dict(sorted(evidence_counts.items()))}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--additional-skill-root", type=Path, action="append", default=[])
    parser.add_argument("--json", action="store_true", help="Print relative-path SHA-256 inventory; never writes a report")
    args = parser.parse_args()
    report = audit_dependencies(args.root, args.additional_skill_root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Skill dependency check {report['status']}: {len(report['packages'])} packages, {len(report['files'])} files.")
        for error in report["errors"]:
            print("- " + error)
        print("Evidence registry states: " + json.dumps(report["evidence_counts"], sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
