"""Distinguish five independently injected knowledge loss stages."""

from copy import deepcopy

import pytest

from src.step1_understand.candidate_ledger import candidate_key
from validation.knowledge_accounting import knowledge_counts


@pytest.mark.parametrize('removed', ('discovered', 'decided', 'projected', 'retrieved', 'selected'))
def test_locates_first_knowledge_loss(removed):
    """PURPOSE: Show causes remain distinct even when the final selected set is empty.
    INPUT: Independent occurrence fact and a one-fact loss injected at one pipeline boundary.
    OUTPUT: Correct first-loss stage while prior unaffected stages stay positive.
    """
    source = {'table': 'entries', 'timestamp_unit_id': 'timestamp'}
    fact = {'kind': 'column_event', 'source': source, 'case': 'entity'}
    row = {'id': candidate_key(fact['kind'], source), 'decision': 'approved', 'projected_ids': ['event']}
    whole = {'event_definitions': [{'id': 'event', 'extraction_status': 'executable'}],
             'attribution_paths': [{'id': 'path', 'event_definition_id': 'event', 'to': 'entity',
                                    'validation_status': 'valid', 'case_map': {'validation': {'passed': True}}}]}
    request = deepcopy(whole)
    pi = {'selected_event_definition_ids': ['event'], 'verified_attribution_paths': {'event': ['path']}}
    ledger = {'candidates': [row]}
    if removed == 'discovered':
        ledger['candidates'] = []
    elif removed == 'decided':
        row['decision'] = 'unresolved'
    elif removed == 'projected':
        whole['event_definitions'] = []
    elif removed == 'retrieved':
        request['attribution_paths'] = []
    else:
        pi['selected_event_definition_ids'] = []
    counted = knowledge_counts([fact], ledger, whole, request, pi)
    assert counted['first_losses'] == [{'candidate_id': row['id'], 'first_loss': removed}]
