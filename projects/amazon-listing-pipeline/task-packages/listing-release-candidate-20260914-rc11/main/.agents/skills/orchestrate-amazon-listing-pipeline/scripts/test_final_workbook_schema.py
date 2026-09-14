"""Synthetic matrices; no real business workbook is created or rewritten."""
import unittest

import final_workbook_schema as layout


class FinalSchemaTests(unittest.TestCase):
    def test_fixed_fourteen_and_base_ten_sheets(self):
        for phase, count in (("base", 10), ("final", 14)):
            matrix = layout.scaffold(phase)
            self.assertEqual(count, len(matrix))
            self.assertEqual([], layout.check_rows(matrix, phase))

    def test_collapsed_headers_fail_before_render_or_copy(self):
        for sheet, count in (("标题与亮点", 4), ("五点与Search Terms", 4), ("图片方案", 8), ("A+方案", 8), ("规则校验", 4)):
            matrix = layout.scaffold("base")
            matrix[sheet][0] = matrix[sheet][0][:count]
            self.assertTrue(any(sheet in error for error in layout.check_rows(matrix, "base")))

    def test_sheet_order_and_extra_or_missing_fields_fail(self):
        matrix = layout.scaffold("final")
        matrix["标题与亮点"][0][3:5] = reversed(matrix["标题与亮点"][0][3:5])
        self.assertTrue(layout.check_rows(matrix))
        matrix = layout.scaffold("final")
        matrix["new-sheet"] = []
        self.assertTrue(layout.check_rows(matrix))

    def test_declared_optional_and_audit_columns_stay_allowed(self):
        matrix = layout.scaffold("final")
        matrix["标签优先级展示"][0].pop()
        matrix["卖点与配置优先级展示"][0].append("来源")
        matrix["痛点频率与重要级展示"][0].append("稳定ID")
        self.assertEqual([], layout.check_rows(matrix))

    def test_header_cannot_be_hidden_after_body(self):
        matrix = layout.scaffold("base")
        matrix["标题与亮点"] = [[] for _ in range(10)] + matrix["标题与亮点"]
        self.assertTrue(layout.check_rows(matrix, "base"))

    def test_schema_is_projection_of_existing_owning_documents(self):
        refs = layout.CONTRACT.parent
        # Works in maintenance source; role snapshots rebase knowledge to package root.
        skill = refs.parent
        project = skill.parents[2]
        presentation = project / "knowledge-base" / "final-workbook-presentation.md"
        content = (refs / "stage-listing-generation.md").read_text() + presentation.read_text()
        for item in layout.specifications("final"):
            if item["headers"]:
                self.assertIn("｜".join(item["headers"]), content)


if __name__ == "__main__":
    unittest.main()
