#!/usr/bin/env python3
"""Read-only ST mechanics; caller owns source locks, byte limit and semantic approval."""
import argparse
from collections import Counter
import json
import unicodedata


def word_tokens(text):
    """Comparison copy only; punctuation is a boundary, no stemming or ASCII folding."""
    normalized = unicodedata.normalize('NFC', text).lower()
    return ''.join(c if c.isalnum() or unicodedata.category(c).startswith('M')
                   else ' ' for c in normalized).split()


def check(text, max_bytes, front_texts=()):
    if not isinstance(text, str):
        raise ValueError('text must be a string')
    if type(max_bytes) is not int or max_bytes < 1:
        raise ValueError('caller must supply a verified positive integer byte ceiling')
    if not isinstance(front_texts, (list, tuple)) or not all(isinstance(t, str) for t in front_texts):
        raise ValueError('front_texts must be confirmed fields supplied as a list of strings')
    errors = []
    byte_count = len(text.encode('utf-8'))
    if byte_count > max_bytes:
        errors.append('byte_limit_exceeded')
    if text != unicodedata.normalize('NFC', text):
        errors.append('not_nfc')
    if text != text.lower():
        errors.append('not_lowercase')
    if text != text.strip(' ') or '  ' in text or any(c.isspace() and c != ' ' for c in text):
        errors.append('not_single_ascii_spaces')
    if any(not (c.isalnum() or unicodedata.category(c).startswith('M') or c == ' ') for c in text):
        errors.append('punctuation_or_special_format')
    tokens = word_tokens(text)
    duplicates = sorted(t for t, count in Counter(tokens).items() if count > 1)
    covered = {t for field in front_texts for t in word_tokens(field)}
    front_overlap = sorted(set(tokens) & covered)
    if duplicates:
        errors.append('duplicate_st_tokens')
    if front_overlap:
        errors.append('tokens_already_in_supplied_front_fields')
    return {
        'text': text, 'utf8_bytes_including_spaces': byte_count, 'max_bytes': max_bytes,
        'characters': len(text), 'duplicate_st_tokens': duplicates,
        'front_overlap_tokens': front_overlap, 'errors': errors,
        'mechanical_pass': not errors, 'business_approved': False,
        'scope': 'bytes_format_exact_tokens_only_not_phrase_coverage',
        'unverified': ['marketplace_limit_evidence', 'run_source_identity_and_06_admission',
                       'confirmation_gates_and_dedup_scope', 'facts_relevance_prohibited_content',
                       'word_forms_and_remaining_phrase_meaning', 'amazon_indexing_and_ranking'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--text', required=True)
    parser.add_argument('--max-bytes', required=True, type=int)
    parser.add_argument('--front', action='append', default=[], help='Repeat for each locked front field')
    args = parser.parse_args()
    result = check(args.text, args.max_bytes, args.front)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['mechanical_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
