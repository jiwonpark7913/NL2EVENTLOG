"""Exercise the new M0 entry point against existing independent public fixtures."""

import json

from development.case_catalog_m0.runtime import run_m0
from test_minimal_step2 import healthcare, index_fixture, logistics, pairs, scripted_plan, specimen_phases


def test_catalog_then_case_scoped_multihop_lookup(tmp_path):
    """PURPOSE: Bind an indexed Visit after browsing population metadata alone.
    INPUT: Independent healthcare fixture and a scripted role client. OUTPUT: Three roles and four correct events.
    """
    db, graph = healthcare(tmp_path)
    client = scripted_plan('Clinical Visit', specimen_phases)
    checkpoint = {}
    receipt=run_m0(db,'For each clinical visit, show actual specimen receipt and testing.',
                   index=index_fixture(tmp_path,graph),client=client,
                   checkpoint=lambda k,v:checkpoint.setdefault(k,v))
    assert list(checkpoint) == ['case_catalog','intent','case','retrieval','initial','M0']
    assert [x['role'] for x in receipt['calls']] == ['minimal_intent','minimal_case','minimal_events']
    payload=json.loads(receipt['calls'][1]['prompt']['user'].split('\n',1)[1].rsplit('\n',1)[0])
    assert set(payload)=={'original_request','intent','cases'}
    assert {row['id'] for row in receipt['case_catalog']}=={
        row['id'] for row in graph['entity_types'] if (row.get('population') or {}).get('status')=='valid'}
    roles=receipt['outcomes']['M0']
    assert roles['status']=='accepted' and len(roles['rows'])==4
    assert {x['timestamp_raw_column'] for x in roles['rows']}=={'received_at','tested_at'}


def test_catalog_preserves_documented_population_scope(tmp_path):
    """PURPOSE: Preserve Case population independently of a direct event path.
    INPUT: Independent logistics fixture and receiver scope. OUTPUT: Commissioning only for receiving depots.
    """
    db, graph = logistics(tmp_path)

    def select(cards):
        """PURPOSE: Choose the direct commissioning fact. INPUT: Depot EDs. OUTPUT: Existing ED/path pairs."""
        return pairs(cards,lambda card:'commissioned_at' in card['clock_id'])

    client=scripted_plan('Logistics Depot',select,scope='receiver')
    receipt=run_m0(db,'Show commissioning for each logistics depot that received a transfer.',
                   index=index_fixture(tmp_path,graph),client=client)
    outcome=receipt['outcomes']['M0']
    assert outcome['status']=='accepted' and len(outcome['rows'])==2
    assert outcome['pi']['case_scope']['role']=='receiver'
    assert {x['timestamp_raw_column'] for x in outcome['rows']}=={'commissioned_at'}
