"""Exercise one scoped population across direct and role-specific Event Definition paths."""

import json

import pytest

from development.case_catalog_m0.runtime import run_m0 as baseline
from development.scope_attribution_m0.runtime import run_m0
from test_minimal_step2 import case_key, index_fixture, logistics, pairs, scripted_plan


QUESTION = ('For each depot that received a transfer, show its commissioning and actual dispatches '
            'assigned to their sending depot.')


@pytest.mark.parametrize('role,expected_dispatches', [
    ('sender',{('20',2)}),
    ('receiver',{('20',1),('30',2)}),
])
def test_population_restriction_and_event_role_are_independent(tmp_path,role,expected_dispatches):
    """PURPOSE: Show that the global receiver population does not replace the dispatch role.
    INPUT: Two receiving depots, one sender-only depot and two offered dispatch paths.
    OUTPUT: Direct commissioning is filtered identically, while the path changes dispatch assignments.
    """
    database,graph=logistics(tmp_path)

    def select(cards):
        """PURPOSE: Exercise the direct event alongside one chosen role path.
        INPUT: Public ED cards. OUTPUT: Actual commissioning and dispatch selections.
        """
        return (pairs(cards,lambda card:'commissioned_at' in card['clock_id'])
                + pairs(cards,lambda card:'dispatched_at' in card['clock_id'],role=role))

    client=scripted_plan('Logistics Depot',select,scope='receiver')
    receipt=run_m0(database,QUESTION,index=index_fixture(tmp_path,graph),client=client)
    assert [call['role'] for call in receipt['calls']]==['minimal_intent','minimal_case','minimal_events']
    last=receipt['calls'][-1]['prompt']
    payload=json.loads(last['user'].split('\n',1)[1].rsplit('\n',1)[0])
    assert payload['selected_case_scope']['role']=='receiver'
    assert payload['selected_case_scope']['id']==receipt['case']['case_scope_id']
    assert 'event-specific relationship' in last['system']
    roles={p['role'] for card in payload['events'] if 'dispatched_at' in card['clock_id']
           for p in card['paths']}
    assert {'sender','receiver'}<=roles
    output=receipt['outcomes']['M0']
    assert output['status']=='accepted'
    assert {case_key(row) for row in output['rows'] if row['timestamp_raw_column']=='commissioned_at'}=={'20','30'}
    assert {(case_key(row),int(json.loads(row['source_record_id'])[0])) for row in output['rows']
            if row['timestamp_raw_column']=='dispatched_at'}==expected_dispatches


def test_replay_shares_intent_case_and_retrieval_and_preserves_unrestricted_case(tmp_path):
    """PURPOSE: Change only the Event Selection representation on the saved upstream checkpoints.
    INPUT: An unrestricted Logistics Depot baseline. OUTPUT: Identical SQL and rows with one new role call.
    """
    database,graph=logistics(tmp_path)
    index=index_fixture(tmp_path,graph)
    stages={}

    def direct(cards):
        """PURPOSE: Select the direct Case clock. INPUT: Public cards. OUTPUT: Commissioning ED/path pair."""
        return pairs(cards,lambda c:'commissioned_at' in c['clock_id'])

    original=baseline(database,'Show commissioning for every logistics depot.',index=index,
                      client=scripted_plan('Logistics Depot',direct),
                      checkpoint=lambda stage,value:stages.setdefault(stage,value))
    fixed={name:stages[name] for name in ('intent','case','retrieval')}
    candidate=run_m0(database,'Show commissioning for every logistics depot.',index=index,
                     client=scripted_plan('Logistics Depot',direct),replay=fixed)
    assert [call['role'] for call in candidate['calls']]==['minimal_events']
    assert all(candidate[name]==value for name,value in fixed.items())
    encoded=candidate['calls'][0]['prompt']['user']
    assert json.loads(encoded.split('\n',1)[1].rsplit('\n',1)[0])['selected_case_scope'] is None
    before,after=(r['outcomes']['M0'] for r in (original,candidate))
    assert (before['sql'],before['rows'])==(after['sql'],after['rows'])
    assert len(after['rows'])==3
