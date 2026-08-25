"""Regression tests for the package-level trend OOXML auditor."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1] / "scripts" / "audit_trend_ooxml.py"
)
SPEC = importlib.util.spec_from_file_location("audit_trend_ooxml", SCRIPT)
assert SPEC and SPEC.loader
AUDITOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDITOR
SPEC.loader.exec_module(AUDITOR)


CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
</Types>"""

WORKBOOK = """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://purl.oclc.org/ooxml/spreadsheetml/main"
 xmlns:r="http://purl.oclc.org/ooxml/officeDocument/relationships">
  <sheets>
    <sheet name="Monthly Data" sheetId="1" r:id="rId1"/>
    <sheet name="Quarterly Data" sheetId="2" r:id="rId2"/>
  </sheets>
</workbook>"""

WORKBOOK_RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="/xl/worksheets/sheet2.xml"/>
</Relationships>"""

STYLES = """<?xml version="1.0" encoding="UTF-8"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <cellXfs count="2"><xf numFmtId="0"/><xf numFmtId="9"/></cellXfs>
</styleSheet>"""


def worksheet_xml(*, drawing: bool, formulas: bool, percent_values: bool) -> str:
    rows = []
    for row in range(2, 5):
        cells = []
        for column, value in (("B", row * 10), ("C", row * 20)):
            style = "1" if percent_values else "0"
            formula = f"<f>{row}+1</f>" if formulas else ""
            cells.append(
                f'<c r="{column}{row}" s="{style}">{formula}<v>{value}</v></c>'
            )
        rows.append(f'<row r="{row}">{"".join(cells)}</row>')
    drawing_xml = '<drawing r:id="rIdDraw"/>' if drawing else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheetData>{''.join(rows)}</sheetData>{drawing_xml}
</worksheet>"""


def worksheet_rels(drawing_number: int) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rIdDraw" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" Target="../drawings/drawing{drawing_number}.xml"/>
</Relationships>"""


def drawing_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <xdr:twoCellAnchor><xdr:graphicFrame><a:graphic><a:graphicData>
    <c:chart r:id="rIdChart"/>
  </a:graphicData></a:graphic></xdr:graphicFrame></xdr:twoCellAnchor>
</xdr:wsDr>"""


def drawing_rels(chart_number: int, *, broken: bool = False) -> str:
    if broken:
        target = "../charts/missing.xml"
    elif chart_number == 1:
        target = "charts/chart1.xml"
    else:
        target = "../charts/chart2.xml"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rIdChart" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/chart" Target="{target}"/>
</Relationships>"""


def chart_xml(*, monthly: bool) -> str:
    title = "Monthly actual search volume" if monthly else "季度实际搜索量"
    sheet = "Monthly Data" if monthly else "Quarterly Data"
    labels = ["2026-05", "2026-06", "2026-07"] if monthly else ["2025 Q4", "2026 Q1", "2026 Q2"]
    series = []
    for index, column in enumerate(("B", "C")):
        points = "".join(
            f'<c:pt idx="{point}"><c:v>{label}</c:v></c:pt>'
            for point, label in enumerate(labels)
        )
        series.append(f"""
      <c:ser><c:idx val="{index}"/><c:order val="{index}"/>
        <c:tx><c:v>keyword {index + 1}</c:v></c:tx>
        <c:cat><c:strRef><c:f>'{sheet}'!$A$2:$A$4</c:f><c:strCache>{points}</c:strCache></c:strRef></c:cat>
        <c:val><c:numRef><c:f>'{sheet}'!${column}$2:${column}$4</c:f></c:numRef></c:val>
      </c:ser>""")
    body = f"""
  <c:chart><c:title><c:tx><c:rich><a:p><a:r><a:t>{title}</a:t></a:r></a:p></c:rich></c:tx></c:title>
    <c:plotArea><c:lineChart>{''.join(series)}</c:lineChart></c:plotArea>
  </c:chart>"""
    if monthly:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">{body}</c:chartSpace>"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<chartSpace xmlns="http://schemas.openxmlformats.org/drawingml/2006/chart"
 xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">{body}</chartSpace>"""


def manifest() -> dict:
    return {
        "population": {"actual": 2},
        "formula_count": 12,
        "charts": {
            "count": 2,
            "monthly": {
                "metric": "actual monthly search volume",
                "source_range": "'Monthly Data'!A1:C4",
                "series": 2,
                "percentage_series": 0,
            },
            "quarterly": {
                "metric": "actual quarterly search volume",
                "source_range": "'Quarterly Data'!A1:C4",
                "series": 2,
                "percentage_series": 0,
            },
        },
    }


def build_fixture(
    path: Path,
    *,
    drawings: bool = True,
    formulas: bool = True,
    quarterly_percent: bool = False,
    broken_chart_relationship: bool = False,
) -> None:
    parts = {
        "[Content_Types].xml": CONTENT_TYPES,
        "xl/workbook.xml": WORKBOOK,
        "xl/_rels/workbook.xml.rels": WORKBOOK_RELS,
        "xl/styles.xml": STYLES,
        "xl/worksheets/sheet1.xml": worksheet_xml(
            drawing=drawings, formulas=formulas, percent_values=False
        ),
        "xl/worksheets/sheet2.xml": worksheet_xml(
            drawing=drawings,
            formulas=formulas,
            percent_values=quarterly_percent,
        ),
        "xl/drawings/charts/chart1.xml": chart_xml(monthly=True),
        "xl/charts/chart2.xml": chart_xml(monthly=False),
    }
    if drawings:
        for number in (1, 2):
            parts[f"xl/worksheets/_rels/sheet{number}.xml.rels"] = worksheet_rels(number)
            parts[f"xl/drawings/drawing{number}.xml"] = drawing_xml()
            parts[f"xl/drawings/_rels/drawing{number}.xml.rels"] = drawing_rels(
                number, broken=broken_chart_relationship and number == 2
            )
    with zipfile.ZipFile(path, "w") as archive:
        for name, value in parts.items():
            archive.writestr(name, value)


class TrendOoxmlAuditTests(unittest.TestCase):
    def audit(self, manifest_data=None, **fixture_options):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        workbook = Path(temporary.name) / "fixture.xlsx"
        build_fixture(workbook, **fixture_options)
        return AUDITOR.audit_workbook(workbook, manifest_data or manifest())

    def test_traverses_every_sheet_and_mixed_chart_namespace(self):
        result = self.audit()
        self.assertEqual(result["status"], "pass", json.dumps(result, indent=2))
        self.assertEqual(result["formula_count"], 12)
        self.assertEqual(len(result["worksheets"]), 2)
        self.assertEqual({chart["role"] for chart in result["charts"]}, {"monthly", "quarterly"})
        self.assertEqual([chart["series_count"] for chart in result["charts"]], [2, 2])

    def test_rejects_percentage_formatted_quarterly_series(self):
        result = self.audit(quarterly_percent=True)
        self.assertEqual(result["status"], "business_failure")
        self.assertTrue(
            any("percentage-formatted" in item for item in result["business_failures"])
        )

    def test_rejects_series_outside_locked_actual_volume_range(self):
        locked_manifest = manifest()
        locked_manifest["charts"]["monthly"]["source_range"] = "'Monthly Data'!A1:B4"
        result = self.audit(manifest_data=locked_manifest)
        self.assertEqual(result["status"], "business_failure")
        self.assertTrue(
            any("outside manifest source_range" in item for item in result["business_failures"])
        )

    def test_zero_results_against_manifest_are_auditor_failure(self):
        result = self.audit(drawings=False, formulas=False)
        self.assertEqual(result["status"], "auditor_failure")
        failures = "\n".join(result["auditor_failures"])
        self.assertIn("resolved zero charts", failures)
        self.assertIn("resolved zero formulas", failures)

    def test_broken_chart_relationship_is_auditor_failure(self):
        result = self.audit(broken_chart_relationship=True)
        self.assertEqual(result["status"], "auditor_failure")
        self.assertTrue(
            any("chart target is missing" in item for item in result["auditor_failures"])
        )


if __name__ == "__main__":
    unittest.main()
