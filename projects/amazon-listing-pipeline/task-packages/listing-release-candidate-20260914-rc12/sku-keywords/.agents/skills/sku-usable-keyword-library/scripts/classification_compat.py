"""Read-value compatibility only: no SKU decision, I/O, repair, rank calculation or READY.

verified_evidence must be a caller's record of an actual source review. This
pure function cannot prove that review occurred; a boolean assertion is not a
record. The caller must check original file hash, row/Keyword_ID and values.
"""
import math
import re

TIERS = {'F1': '核心大词', 'F2': '二级词', 'F3': '中流量词',
         'F4': '中长尾词', 'F5': '长尾词'}
ABA_MISSING = '关键词ABA排名缺失'
NORMAL_STATES = (None, '', '搜索量缺失', '没有搜索量')


def blank(value):
    return value is None or (type(value) is str and value == '')


def finite_number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def same_raw(left, right):
    if blank(left) and blank(right):
        return True  # reader null/empty-string equivalence, not source rewriting
    return finite_number(left) and finite_number(right) and left == right


def check_review_record(row, evidence):
    if not isinstance(evidence, dict):
        raise ValueError('Missing actual source-review record; boolean is not evidence')
    kid = row.get('Keyword_ID')
    if not kid or evidence.get('keyword_id') != kid:
        raise ValueError('Evidence Keyword_ID mismatch')
    for name in ('source_path', 'source_locator', 'unavailable_reason'):
        if not isinstance(evidence.get(name), str) or not evidence[name].strip():
            raise ValueError('Missing evidence field: ' + name)
    source_hash = evidence.get('source_sha256')
    if not isinstance(source_hash, str) or not re.fullmatch(r'[0-9a-f]{64}', source_hash):
        raise ValueError('Missing or malformed source hash')
    if 'raw_aba' not in evidence or not same_raw(row['ABA月排名'], evidence['raw_aba']):
        raise ValueError('Evidence raw ABA mismatch')
    if evidence.get('raw_classification_status') != ABA_MISSING:
        raise ValueError('Evidence classification status mismatch')
    if 'raw_traffic_layer' not in evidence or not blank(evidence['raw_traffic_layer']):
        raise ValueError('Evidence traffic-layer mismatch')
    if finite_number(row['ABA月排名']) and row['ABA月排名'] == 0:
        if evidence.get('source_zero_confirmed') is not True:
            raise ValueError('Source zero is not explicitly verified as original and unavailable')


def resolve_classification(row, verified_evidence=None):
    """Return a classification/ledger view without modifying the input row.

    Raising ValueError stops the affected output for upstream clarification.
    Success is not keyword admission: existing SKU/text/spelling gates remain.
    """
    if not isinstance(row, dict) or not {'流量层', 'ABA月排名'}.issubset(row):
        raise ValueError('Required source field missing')
    layer, aba = row['流量层'], row['ABA月排名']
    status = row.get('分类状态')
    if not blank(aba) and not finite_number(aba):
        raise ValueError('ABA must be a finite source number or a real missing value')
    if finite_number(aba) and (aba < 0 or 0 < aba < 1):
        raise ValueError('Invalid ABA source number; ask upstream, do not repair')
    if type(layer) is str and layer in TIERS:
        if not finite_number(aba) or aba < 1 or status not in NORMAL_STATES:
            raise ValueError('ABA/status/traffic-layer conflict')
        classification, state = TIERS[layer], 'mapped'
    elif blank(layer):
        if status != ABA_MISSING or not (blank(aba) or aba == 0):
            raise ValueError('Unexplained blank layer or conflicting ABA missing status')
        check_review_record(row, verified_evidence)
        classification, state = None, 'allowed_missing_aba'
    else:
        raise ValueError('Undefined traffic layer; do not create another tier')
    return {'keyword_classification': classification, 'compatibility_status': state,
            'source_values': {'Keyword_ID': row.get('Keyword_ID'), 'ABA月排名': aba,
                              '分类状态': status, '流量层': layer}}
