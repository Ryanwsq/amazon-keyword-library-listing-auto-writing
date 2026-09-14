import unittest
from check_search_terms import check, word_tokens


class SearchTermsMechanics(unittest.TestCase):
    def test_249_and_250_boundary(self):
        self.assertTrue(check('a' * 249, 249)['mechanical_pass'])
        self.assertIn('byte_limit_exceeded', check('a' * 250, 249)['errors'])

    def test_stricter_limit_is_explicit(self):
        self.assertTrue(check('a' * 199, 199)['mechanical_pass'])
        self.assertFalse(check('a' * 200, 199)['mechanical_pass'])

    def test_no_default_marketplace_limit(self):
        for limit in (None, True, 0, -1, '249'):
            with self.assertRaises(ValueError):
                check('seat', limit)

    def test_german_preserved_and_counted(self):
        result = check('bürostuhl', 249)
        self.assertEqual((result['characters'], result['utf8_bytes_including_spaces']), (9, 10))
        self.assertEqual(word_tokens('BÜROSTUHL Straße'), ['bürostuhl', 'straße'])

    def test_uppercase_does_not_cost_extra_ascii_bytes(self):
        self.assertEqual(check('CHAIR', 249)['utf8_bytes_including_spaces'], 5)
        self.assertIn('not_lowercase', check('CHAIR', 249)['errors'])

    def test_spaces_are_counted(self):
        self.assertEqual(check('computer seat', 249)['utf8_bytes_including_spaces'], 13)
        self.assertFalse(check('computer seat', 12)['mechanical_pass'])

    def test_invalid_separators_and_format(self):
        for text in ('seat  computer', ' seat', 'seat ', 'seat\tcomputer', 'seat\ncomputer',
                     'seat\u00a0computer', 'seat,computer', 'seat-computer', 'seat😀'):
            self.assertFalse(check(text, 249)['mechanical_pass'], text)

    def test_no_mutation_or_silent_normalization(self):
        text = 'bu\u0308rostuhl'
        result = check(text, 249)
        self.assertEqual(result['text'], text)
        self.assertEqual(result['utf8_bytes_including_spaces'], 11)
        self.assertIn('not_nfc', result['errors'])

    def test_duplicate_tokens(self):
        self.assertEqual(check('chair seat chair', 249)['duplicate_st_tokens'], ['chair'])

    def test_front_all_fields_including_ih(self):
        self.assertEqual(check('footrest', 249, ['Gaming Chair', 'Retractable Footrest', 'Mesh'])[
            'front_overlap_tokens'], ['footrest'])

    def test_punctuation_boundary_not_concatenation(self):
        self.assertEqual(word_tokens('gaming, chair'), ['gaming', 'chair'])
        result = check('gaming chair', 249, ['gaming, chair'])
        self.assertEqual(result['front_overlap_tokens'], ['chair', 'gaming'])
        self.assertNotIn('phrase_covered', result)

    def test_no_substring_stemming_or_synonym_removal(self):
        self.assertTrue(check('seat', 249, ['seating'])['mechanical_pass'])
        self.assertTrue(check('tv television', 249)['mechanical_pass'])
        self.assertTrue(check('glass glasses', 249)['mechanical_pass'])

    def test_empty_is_not_automatic_business_success(self):
        result = check('', 249)
        self.assertTrue(result['mechanical_pass'])
        self.assertFalse(result['business_approved'])

    def test_mechanics_do_not_claim_semantic_or_brand_check(self):
        result = check('brandexample best', 249)
        self.assertTrue(result['mechanical_pass'])
        self.assertFalse(result['business_approved'])
        self.assertIn('facts_relevance_prohibited_content', result['unverified'])


if __name__ == '__main__':
    unittest.main()
