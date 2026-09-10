#!/usr/bin/env python3
"""Preflight the one-workbook input contract using only the Python standard library."""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any
from xml.etree import ElementTree as ET


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")

REQUIRED_SHEETS = {
    "新品基础信息": ["ASIN", "产品类型", "产品人群画像", "使用场景", "用途", "核心卖点", "市场选择"],
    "新品基础配置": ["产品尺寸参数", "产品包装参数", "包含配件/组件", "卖点"],
    "竞品对标ASIN": ["价格竞品", "颜色竞品", "尺寸竞品", "材质竞品", "风格竞品"],
}
MARKET_HEADERS = ["ASIN", "父体ASIN", "是否启用", "采样用途", "备注"]
LOGIN_HEADERS = ["服务", "账户别名", "凭据引用", "登录方式", "说明"]
LOGIN_METHODS = {"浏览器已保存凭据", "本机密码管理器"}
FORBIDDEN_SECRET_HEADERS = {
    "密码",
    "password",
    "passwd",
    "secret",
    "cookie",
    "token",
    "验证码",
    "otp",
}
MARKETPLACE_ROUTES = {
    "Amazon-US": {
        "domain": "amazon.com",
        "postal_code": "10001",
        "shopping_assistant": "Alexa for Shopping",
        "prompt_language": "English",
    },
    "Amazon-DE": {
        "domain": "amazon.de",
        "postal_code": "80539",
        "shopping_assistant": "Rufus",
        "prompt_language": "German",
    },
}
MARKETPLACE_ALIASES = {
    "amazon-us": "Amazon-US",
    "amazon us": "Amazon-US",
    "us": "Amazon-US",
    "amazon.com": "Amazon-US",
    "amazon-de": "Amazon-DE",
    "amazon de": "Amazon-DE",
    "de": "Amazon-DE",
    "amazon.de": "Amazon-DE",
}


def canonical(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\u3000", " ").replace("／", "/")
    text = re.sub(r"\s+", "", text)
    return text


def normalize_asin(value: Any) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"[\s\u200b\ufeff]+", "", text).upper()


def split_asins(value: Any) -> list[str]:
    text = "" if value is None else str(value)
    parts = re.split(r"[\s,，;；、/]+", text)
    return [normalize_asin(part) for part in parts if normalize_asin(part)]


def column_index(cell_ref: str) -> int:
    letters = re.match(r"[A-Za-z]+", cell_ref)
    if not letters:
        return 0
    result = 0
    for char in letters.group(0).upper():
        result = result * 26 + (ord(char) - ord("A") + 1)
    return result - 1


class XlsxReader:
    def __init__(self, path: Path):
        self.path = path
        self.archive = zipfile.ZipFile(path)
        self.shared_strings = self._load_shared_strings()
        self.sheets = self._load_sheet_paths()

    def close(self) -> None:
        self.archive.close()

    def _load_shared_strings(self) -> list[str]:
        try:
            root = ET.fromstring(self.archive.read("xl/sharedStrings.xml"))
        except KeyError:
            return []
        strings: list[str] = []
        for item in root.findall(f"{{{MAIN_NS}}}si"):
            strings.append("".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t")))
        return strings

    def _load_sheet_paths(self) -> dict[str, str]:
        workbook = ET.fromstring(self.archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(self.archive.read("xl/_rels/workbook.xml.rels"))
        rel_map = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in relationships.findall(f"{{{PKG_REL_NS}}}Relationship")
        }
        result: dict[str, str] = {}
        for sheet in workbook.findall(f".//{{{MAIN_NS}}}sheet"):
            name = sheet.attrib["name"]
            rel_id = sheet.attrib[f"{{{REL_NS}}}id"]
            target = rel_map[rel_id].replace("\\", "/")
            if target.startswith("/"):
                full_path = target.lstrip("/")
            else:
                full_path = str(PurePosixPath("xl") / target)
            result[name] = str(PurePosixPath(full_path))
        return result

    def rows(self, sheet_name: str) -> tuple[list[list[Any]], list[str], list[str]]:
        root = ET.fromstring(self.archive.read(self.sheets[sheet_name]))
        rows: list[list[Any]] = []
        errors: list[str] = []
        merges = [node.attrib.get("ref", "") for node in root.findall(f".//{{{MAIN_NS}}}mergeCell")]
        for row_node in root.findall(f".//{{{MAIN_NS}}}sheetData/{{{MAIN_NS}}}row"):
            row_values: list[Any] = []
            row_number = int(row_node.attrib.get("r", len(rows) + 1))
            for cell in row_node.findall(f"{{{MAIN_NS}}}c"):
                ref = cell.attrib.get("r", f"A{row_number}")
                idx = column_index(ref)
                while len(row_values) <= idx:
                    row_values.append("")
                cell_type = cell.attrib.get("t", "")
                value_node = cell.find(f"{{{MAIN_NS}}}v")
                if cell_type == "inlineStr":
                    value = "".join(node.text or "" for node in cell.iter(f"{{{MAIN_NS}}}t"))
                elif value_node is None:
                    value = ""
                elif cell_type == "s":
                    try:
                        value = self.shared_strings[int(value_node.text or "0")]
                    except (ValueError, IndexError):
                        value = ""
                elif cell_type == "b":
                    value = value_node.text == "1"
                elif cell_type == "e":
                    value = value_node.text or "#ERROR"
                    errors.append(f"{sheet_name}!{ref}={value}")
                else:
                    value = value_node.text or ""
                row_values[idx] = value
            rows.append(row_values)
        return rows, errors, merges


def find_sheet(sheet_names: list[str], expected: str) -> str | None:
    expected_key = canonical(expected)
    for name in sheet_names:
        if canonical(name) == expected_key:
            return name
    return None


def nonempty_rows(rows: list[list[Any]]) -> list[list[Any]]:
    return [row for row in rows if any(canonical(value) for value in row)]


def validate_headers(
    sheet_name: str,
    rows: list[list[Any]],
    expected: list[str],
    errors: list[str],
    warnings: list[str],
) -> bool:
    if not rows:
        errors.append(f"{sheet_name}: 工作表为空")
        return False
    actual = [canonical(value) for value in rows[0]]
    expected_keys = [canonical(value) for value in expected]
    if actual[: len(expected_keys)] != expected_keys:
        errors.append(f"{sheet_name}: 列名或顺序错误；期望 {expected}")
        return False
    if len(actual) > len(expected_keys) and any(actual[len(expected_keys) :]):
        warnings.append(f"{sheet_name}: 存在额外列，额外列不会自动并入固定合同")
    return True


def reject_secret_headers(sheet_name: str, rows: list[list[Any]], errors: list[str]) -> None:
    """Reject spreadsheet columns that invite plaintext credentials or session secrets."""
    if not rows:
        return
    for value in rows[0]:
        header = canonical(value).lower()
        if any(term in header for term in FORBIDDEN_SECRET_HEADERS):
            errors.append(
                f"{sheet_name}: 禁止凭据字段 {value!r}；只允许填写账户别名和本机凭据引用"
            )


def parse_enabled(value: Any) -> bool:
    text = canonical(value).lower()
    if text in {"否", "no", "0", "false", "disabled", "禁用"}:
        return False
    return True


def normalize_marketplace(value: Any) -> str | None:
    text = "" if value is None else str(value).strip()
    if not text:
        return None
    return MARKETPLACE_ALIASES.get(text.lower())


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook")
    parser.add_argument(
        "--marketplace",
        help="optional explicit marketplace assertion; must agree with 新品基础信息.市场选择",
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    path = Path(args.workbook).expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    result: dict[str, Any] = {
        "workbook": str(path),
        "valid": False,
        "errors": errors,
        "warnings": warnings,
        "product_asin": None,
        "benchmark_asins": [],
        "market_asins": [],
        "formal_sample_ready": False,
        "marketplace": None,
        "marketplace_route": None,
        "login_profiles": {},
    }

    if not path.is_file():
        errors.append(f"文件不存在：{path}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2
    if path.suffix.lower() != ".xlsx":
        errors.append("输入必须为 .xlsx 工作簿")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    try:
        reader = XlsxReader(path)
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        errors.append(f"无法读取 XLSX 结构：{exc}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    try:
        sheet_data: dict[str, list[list[Any]]] = {}
        for expected, headers in REQUIRED_SHEETS.items():
            actual_name = find_sheet(list(reader.sheets), expected)
            if actual_name is None:
                errors.append(f"缺少工作表：{expected}")
                continue
            rows, cell_errors, merges = reader.rows(actual_name)
            sheet_data[expected] = rows
            reject_secret_headers(actual_name, rows, errors)
            errors.extend(f"公式/单元格错误：{item}" for item in cell_errors)
            if merges:
                errors.append(f"{actual_name}: 存在合并单元格 {merges}，固定输入区不得合并")
            validate_headers(expected, rows, headers, errors, warnings)

        if "新品基础信息" in sheet_data and len(nonempty_rows(sheet_data["新品基础信息"][1:])) != 1:
            errors.append("新品基础信息: 必须恰好有一条产品记录")
        if "新品基础配置" in sheet_data and len(nonempty_rows(sheet_data["新品基础配置"][1:])) != 1:
            errors.append("新品基础配置: 必须恰好有一条产品记录")

        marketplace_raw = ""
        if "新品基础信息" in sheet_data and len(sheet_data["新品基础信息"]) >= 2:
            row = sheet_data["新品基础信息"][1]
            expected = REQUIRED_SHEETS["新品基础信息"]
            for idx, header in enumerate(expected):
                value = row[idx] if idx < len(row) else ""
                if header != "市场选择" and not canonical(value):
                    errors.append(f"新品基础信息!{header}: 必填值为空")
            own_asin = normalize_asin(row[0] if row else "")
            result["product_asin"] = own_asin or None
            if own_asin and not ASIN_RE.fullmatch(own_asin):
                errors.append(f"新品基础信息!ASIN: 非法 ASIN {own_asin}")
            marketplace_raw = row[6] if len(row) > 6 else ""

        login_name = find_sheet(list(reader.sheets), "登录准备")
        if login_name is None:
            errors.append("缺少工作表：登录准备")
        else:
            rows, cell_errors, merges = reader.rows(login_name)
            reject_secret_headers(login_name, rows, errors)
            errors.extend(f"公式/单元格错误：{item}" for item in cell_errors)
            if merges:
                errors.append(f"登录准备: 存在合并单元格 {merges}，固定输入区不得合并")
            if validate_headers("登录准备", rows, LOGIN_HEADERS, errors, warnings):
                profiles: dict[str, dict[str, Any]] = {}
                for row_number, row in enumerate(rows[1:], start=2):
                    if not any(canonical(value) for value in row):
                        continue
                    service = str(row[0] if row else "").strip()
                    alias = str(row[1] if len(row) > 1 else "").strip()
                    credential_ref = str(row[2] if len(row) > 2 else "").strip()
                    login_method = str(row[3] if len(row) > 3 else "").strip()
                    if service not in {"SIF", "卖家精灵", "Amazon"}:
                        errors.append(f"登录准备!A{row_number}: 未知服务 {service or '<空>'}")
                        continue
                    if service in profiles:
                        errors.append(f"登录准备!A{row_number}: 服务重复 {service}")
                        continue
                    if service in {"SIF", "卖家精灵"}:
                        if not alias:
                            errors.append(f"登录准备!B{row_number}: {service}账户别名不能为空")
                        if not credential_ref:
                            errors.append(f"登录准备!C{row_number}: {service}凭据引用不能为空；禁止填写明文密码")
                        if login_method not in LOGIN_METHODS:
                            errors.append(
                                f"登录准备!D{row_number}: {service}登录方式只允许 {sorted(LOGIN_METHODS)}"
                            )
                    elif login_method != "用户手动":
                        errors.append("登录准备: Amazon登录方式必须为用户手动")
                    profiles[service] = {
                        "account_alias": alias,
                        "credential_ref": credential_ref,
                        "login_method": login_method,
                    }
                for service in ("SIF", "卖家精灵", "Amazon"):
                    if service not in profiles:
                        errors.append(f"登录准备: 缺少服务行 {service}")
                result["login_profiles"] = profiles

        if "新品基础配置" in sheet_data and len(sheet_data["新品基础配置"]) >= 2:
            row = sheet_data["新品基础配置"][1]
            expected = REQUIRED_SHEETS["新品基础配置"]
            for idx, header in enumerate(expected):
                value = row[idx] if idx < len(row) else ""
                if not canonical(value):
                    errors.append(f"新品基础配置!{header}: 必填值为空")

        benchmark_asins: list[str] = []
        if "竞品对标ASIN" in sheet_data:
            rows = sheet_data["竞品对标ASIN"]
            for col_idx, category in enumerate(REQUIRED_SHEETS["竞品对标ASIN"]):
                category_asins: list[str] = []
                for row in rows[1:]:
                    value = row[col_idx] if col_idx < len(row) else ""
                    for asin in split_asins(value):
                        if not ASIN_RE.fullmatch(asin):
                            errors.append(f"竞品对标ASIN!{category}: 非法 ASIN {asin}")
                        else:
                            category_asins.append(asin)
                if not category_asins:
                    errors.append(f"竞品对标ASIN!{category}: 至少需要一个合法 ASIN")
                benchmark_asins.extend(category_asins)
        benchmark_asins = unique(benchmark_asins)
        result["benchmark_asins"] = benchmark_asins

        own_asin = result.get("product_asin")
        if own_asin and own_asin in benchmark_asins:
            errors.append("本品 ASIN 出现在竞品对标集合中")

        input_marketplace = normalize_marketplace(marketplace_raw)
        cli_marketplace = normalize_marketplace(args.marketplace)
        if not canonical(marketplace_raw):
            errors.append("新品基础信息!市场选择: 必须选择 Amazon-US 或 Amazon-DE")
        elif input_marketplace is None:
            errors.append(
                "新品基础信息!市场选择只允许 Amazon-US/Amazon-DE "
                "（兼容 Amazon US、Amazon DE、amazon.com、amazon.de）"
            )
        if args.marketplace and cli_marketplace is None:
            errors.append("--marketplace 只允许 Amazon-US 或 Amazon-DE")
        if input_marketplace and cli_marketplace and input_marketplace != cli_marketplace:
            errors.append("新品基础信息!市场选择与 --marketplace 冲突")
        marketplace = input_marketplace
        if marketplace is not None:
            route = dict(MARKETPLACE_ROUTES[marketplace])
            result["marketplace"] = marketplace
            result["marketplace_route"] = route

        formal_min = 10

        market_asins: list[str] = []
        market_name = find_sheet(list(reader.sheets), "市场竞品ASIN池")
        if market_name:
            rows, cell_errors, merges = reader.rows(market_name)
            errors.extend(f"公式/单元格错误：{item}" for item in cell_errors)
            if merges:
                errors.append(f"市场竞品ASIN池: 存在合并单元格 {merges}")
            if validate_headers("市场竞品ASIN池", rows, MARKET_HEADERS, errors, warnings):
                for row_number, row in enumerate(rows[1:], start=2):
                    if not any(canonical(value) for value in row):
                        continue
                    asin = normalize_asin(row[0] if row else "")
                    if not asin:
                        continue
                    enabled = parse_enabled(row[2] if len(row) > 2 else "")
                    if not enabled:
                        continue
                    if not ASIN_RE.fullmatch(asin):
                        errors.append(f"市场竞品ASIN池!A{row_number}: 非法 ASIN {asin or '<空>'}")
                    else:
                        market_asins.append(asin)
        else:
            market_asins = list(benchmark_asins)
            warnings.append("缺少市场竞品ASIN池，已回退到五类对标竞品去重集合")

        market_asins = unique(market_asins)
        if own_asin and own_asin in market_asins:
            errors.append("本品 ASIN 出现在市场竞品集合中")
        result["market_asins"] = market_asins
        result["formal_sample_ready"] = len(market_asins) >= formal_min
        result["formal_sample_min"] = formal_min
        if len(market_asins) < formal_min:
            warnings.append(
                f"市场竞品仅 {len(market_asins)} 个，少于正式门槛 {formal_min}；标签和痛点只能试算"
            )

    finally:
        reader.close()

    result["valid"] = not errors
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
