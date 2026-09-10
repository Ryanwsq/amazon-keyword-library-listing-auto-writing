"""Synthetic boundary tests; not row-level SKU judgment or a production validation."""
import copy
import unittest

from classification_compat import ABA_MISSING, TIERS, resolve_classification


def missing_row(aba=None, layer=None, status=ABA_MISSING):
    return {'Keyword_ID': 'FIXTURE-1', 'ABA月排名': aba, '流量层': layer,
            '分类状态': status, '最终去向': '品类相关', '英文关键词': 'sample chair'}


def evidence(row):
    # These are fixtures of caller-verified records, NOT verification of real files.
    return {'keyword_id': row['Keyword_ID'], 'source_path': 'fixture-source.json',
            'source_sha256': 'a' * 64, 'source_locator': 'records/FIXTURE-1',
            'unavailable_reason': 'synthetic unavailable ABA fixture',
            'raw_aba': row['ABA月排名'], 'raw_classification_status': row['分类状态'],
            'raw_traffic_layer': row['流量层']}


class ClassificationCompatibilityTests(unittest.TestCase):
    def test_existing_five_tiers_are_mapped_not_recomputed(self):
        for tier, label in TIERS.items():
            with self.subTest(tier=tier):
                row = missing_row(12000000, tier, '')
                self.assertEqual(resolve_classification(row)['keyword_classification'], label)

    def test_valid_legacy_tier_does_not_require_status_column(self):
        row = missing_row(1, 'F1', '')
        del row['分类状态']
        self.assertEqual(resolve_classification(row)['keyword_classification'], '核心大词')

    def test_search_volume_states_do_not_override_valid_tier(self):
        for status in ('搜索量缺失', '没有搜索量', '', None):
            with self.subTest(status=status):
                self.assertEqual(resolve_classification(missing_row(10, 'F2', status))['keyword_classification'], '二级词')

    def test_null_and_reader_empty_string_with_review_record(self):
        for aba in (None, ''):
            for layer in (None, ''):
                with self.subTest(aba=aba, layer=layer):
                    row = missing_row(aba, layer)
                    result = resolve_classification(row, evidence(row))
                    self.assertIsNone(result['keyword_classification'])
                    self.assertEqual(result['source_values']['ABA月排名'], aba)

    def test_source_zero_requires_explicit_review(self):
        row = missing_row(0)
        with self.assertRaises(ValueError):
            resolve_classification(row, evidence(row))
        reviewed = evidence(row)
        reviewed['source_zero_confirmed'] = True
        result = resolve_classification(row, reviewed)
        self.assertEqual(result['source_values']['ABA月排名'], 0)
        self.assertIsNone(result['keyword_classification'])

    def test_no_evidence_or_boolean_is_not_a_source_review(self):
        for record in (None, True, False, {}, {'verified': True}):
            with self.subTest(record=record), self.assertRaises(ValueError):
                resolve_classification(missing_row(), record)

    def test_evidence_identity_and_raw_values_must_match(self):
        for key, value in (('keyword_id', 'OTHER'), ('raw_aba', 0),
                           ('raw_classification_status', ''), ('raw_traffic_layer', 'F1'),
                           ('source_sha256', 'wrong'), ('source_path', ''),
                           ('source_locator', ''), ('unavailable_reason', '')):
            row = missing_row()
            record = evidence(row)
            record[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                resolve_classification(row, record)

    def test_missing_raw_aba_key_is_not_null_evidence(self):
        row = missing_row()
        record = evidence(row)
        del record['raw_aba']
        with self.assertRaises(ValueError):
            resolve_classification(row, record)

    def test_placeholders_errors_booleans_and_illegal_numbers_rejected(self):
        for aba in ('N/A', '—', '#N/A', ' ', '0', '12', True, False, -1,
                    float('nan'), float('inf'), -float('inf'), 0.5):
            row = missing_row(aba)
            with self.subTest(aba=aba), self.assertRaises(ValueError):
                resolve_classification(row, evidence(row))

    def test_missing_state_is_exact_not_trimmed_or_split(self):
        for status in (None, '', '关键词ABA排名缺失 ', '关键词ABA排名缺失｜搜索量缺失',
                       '关键词ABA排名缺失;搜索量缺失', '搜索量缺失'):
            row = missing_row(status=status)
            with self.subTest(status=status), self.assertRaises(ValueError):
                resolve_classification(row, evidence(row))

    def test_valid_rank_and_missing_state_conflict(self):
        for layer in (None, 'F1'):
            row = missing_row(10, layer)
            with self.subTest(layer=layer), self.assertRaises(ValueError):
                resolve_classification(row, evidence(row))

    def test_missing_rank_with_assigned_tier_conflicts(self):
        for aba in (None, '', 0):
            row = missing_row(aba, 'F2')
            with self.subTest(aba=aba), self.assertRaises(ValueError):
                resolve_classification(row, evidence(row))

    def test_undefined_layer_not_repaired(self):
        for layer in ('F6', ' f1', 'F1 ', '核心大词', ' ', 1, []):
            row = missing_row(layer=layer)
            with self.subTest(layer=layer), self.assertRaises(ValueError):
                resolve_classification(row, evidence(row))

    def test_required_fields_and_exception_keyword_id(self):
        for key in ('流量层', 'ABA月排名', 'Keyword_ID'):
            row = missing_row()
            record = evidence(row)
            del row[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                resolve_classification(row, record)

    def test_no_mutation_and_no_sku_or_text_admission(self):
        for keyword in ('sample chair', 'gamming chair', 'chair+desk', 'chair 300', 'chair,'):
            row = missing_row()
            row.update(英文关键词=keyword, 月搜索量=None, SKU事实匹配='不通过', 拼写规则结果='拼写待确认')
            before = copy.deepcopy(row)
            result = resolve_classification(row, evidence(row))
            self.assertEqual(row, before)
            self.assertEqual(set(result), {'keyword_classification', 'compatibility_status', 'source_values'})
            self.assertNotIn('Sheet1输出资格', result)


if __name__ == '__main__':
    unittest.main()
