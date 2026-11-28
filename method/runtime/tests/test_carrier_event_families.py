"""Regression tests for carrier partition and discovery-only families."""

from contextlib import closing
from copy import deepcopy
import sqlite3

import pytest

from src.step1_understand.carrier_event_families import apply_carrier_policy
from src.step1_understand.eeg_configuration import DbuConfig
from src.eeg.evidence_graph_storage import read_eeg_layers, write_eeg_layers
from src.step2_retrieve_and_interpret.eeg_delivery import EEGDelivery


@pytest.fixture
def source(tmp_path):
    """PURPOSE: Create a generic composite-key case with repeated timestamps.
    INPUT: Isolated temp directory. OUTPUT: Read-only test DB and a validated graph shape.
    """
    path = tmp_path / 'research.sqlite'
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript("""
            CREATE TABLE observations(
                tenant TEXT, subject TEXT, category TEXT, opened TEXT, closed TEXT, recorded TEXT,
                PRIMARY KEY(tenant, subject)
            ) WITHOUT ROWID;
            INSERT INTO observations VALUES
                ('first','X','A','2025-01-01','2025-01-01','2025-01-02'),
                ('second','X','B','2025-01-01','2025-01-01','2025-01-02'),
                ('first','Y','A','2025-01-01',NULL,'2025-01-02');
        """)
    definitions, paths = [], []
    for eid, column, phase, value, label in (
        ('all-closed','closed','completion',None,'Assessment completed'),
        ('a-closed','closed','completion','A','Optical assessment completed'),
        ('b-closed','closed','completion','B','Acoustic assessment completed'),
        ('opened','opened','start',None,'Assessment started'),
        ('logged','recorded','recording',None,'Record posted'),
    ):
        witness = f'C:observations.{column}'
        typed = value is not None
        definitions.append({
            'id': eid, 'activity': label, 'source_table': 'observations',
            'source_kind': 'row_activity' if typed else 'column_event',
            'activity_column': 'category' if typed else None, 'raw_values': [value] if typed else [],
            'timestamp_columns': [column], 'extraction_status': 'unresolved' if eid=='logged' else 'executable',
            'source_row_key': ['tenant','subject'], 'occurrence_identity_status': 'supported',
            'row_selection': {'kind': 'equals', 'column': 'category', 'value': value} if typed else {'kind':'all_rows'},
            'occurrence_time_source': {'columns': [column], 'json_path': None},
            'timestamp_candidates': [{'kind': 'direct', 'column': column, 'time_role': 'actual'}],
            'semantic_signature': {'interpretation_status':'supported', 'temporal_role':phase,
                                   'evidence_refs':[witness], 'transition':None},
            'activity_semantics': {'status':'supported',
                'citations':[{'evidence_id': f'C:observations.category:code:{value}'}] if typed else []},
            'entity_reviews': {},
        })
        path_sql = (f'SELECT json_array(tenant,subject), json_array(tenant,subject) '
                    f'FROM observations WHERE {column} IS NOT NULL')
        paths.append({
            'id':'path-' + eid, 'event_definition_id':eid, 'to':'case', 'target_table_key_id':'case_key',
            'joins': [], 'validation_status':'valid', 'case_role': {'role': 'subject'},
            'case_map': {'source_event_key_columns':['tenant','subject'], 'case_key_fields':['tenant','subject'],
                         'map_sql':path_sql + (' AND category=?' if typed else ''),
                         'map_parameters':[value] if typed else [], 'validation':{'passed':True}},
        })
    pairs = [{'id':'pair-'+eid, 'binding_pair':['all-closed',eid], 'relationship':'alternative','status':'supported'}
             for eid in ('a-closed','b-closed')]
    pairs += [{'id': 'phase-' + eid, 'binding_pair': ['opened', eid], 'relationship': 'unknown',
               'status': 'candidate'} for eid in ('a-closed', 'b-closed')]
    return path, {'event_definitions':definitions, 'attribution_paths':paths, 'event_definition_pair_relationships':pairs}


def test_proven_family_removes_only_broad_projection(source, tmp_path):
    """PURPOSE: Prove coalescence by composite source identity and phase.
    INPUT: Multi-clock and duplicate-timestamp fixture. OUTPUT: Active members, unchanged source IDs and round trip.
    """
    database, graph = source
    canonical = apply_carrier_policy(graph,database)
    assert len(graph['event_definitions']) == 5
    assert [d['id'] for d in canonical['retired_event_definitions']] == ['all-closed']
    assert [r['id'] for r in canonical['event_definitions']] == ['a-closed','b-closed','opened','logged']
    assert canonical['carrier_lifecycle_pair_proofs'] == ['phase-a-closed','phase-b-closed']
    assert all(p['relationship'] == 'lifecycle_pair' for p in canonical['event_definition_pair_relationships'])
    proof, = canonical['carrier_partition_audit']
    assert proof['broad_occurrences'] == proof['union_occurrences'] == 2
    assert proof['overlap_occurrences'] == proof['missing_occurrences'] == 0
    assert proof['replacement_path_ids'] == {'path-all-closed':['path-a-closed','path-b-closed']}
    assert all(e['row_selection'] == graph['event_definitions'][i]['row_selection']
               for i,e in enumerate(canonical['event_definitions'],1))
    path = tmp_path/'layers'
    checksums = write_eeg_layers(path,canonical)
    assert read_eeg_layers(path,checksums)[0] == canonical
    assert DbuConfig().carrier_event_policy == 'integrated'
    with pytest.raises(ValueError, match='only integrated v2'):
        DbuConfig(carrier_event_policy='canonical')


def test_partial_coverage_keeps_broad_ed_and_accounts_for_residue(source):
    """PURPOSE: Preserve timed rows with NULL or unsupported carrier codes.
    INPUT: Expanded fixture with two unresolved values. OUTPUT: Held broad definition and residue counts.
    """
    database, graph = source
    with closing(sqlite3.connect(database)) as db, db:
        db.execute("""INSERT INTO observations VALUES
                      ('first','M',NULL,'2025-01-01','2025-01-01','2025-01-02'),
                      ('first','N','U','2025-01-01','2025-01-01','2025-01-02')""")
    canonical = apply_carrier_policy(graph,database)
    assert not canonical['event_families']
    assert len(canonical['event_definitions']) == 5
    assert canonical['carrier_partition_audit'][0]['residue_reasons'] == {
        'null_carrier':1,'uncovered_carrier':1}


@pytest.mark.parametrize('control', ('role', 'activity', 'transition', 'duplicate-value'))
def test_equivalence_requires_documented_meaning_and_same_role_partition(source, control):
    """PURPOSE: Guard against overlap removal based only on equal timestamps.
    INPUT: One mismatched role, unknown carrier meaning, independent transition or overlapping value.
    OUTPUT: The broad ED remains eligible and the candidate is auditable.
    """
    database, graph = source
    mutant = deepcopy(graph)
    child = mutant['event_definitions'][1]
    if control == 'role':
        mutant['attribution_paths'][1]['case_role'] = {'role': 'reviewer'}
    elif control == 'activity':
        child['activity_semantics'] = {'status': 'unresolved'}
    elif control == 'transition':
        child['semantic_signature']['transition'] = 'a distinct business state change'
    else:
        child['raw_values'].append('B')
    result = apply_carrier_policy(mutant,database)
    assert not result['event_families']
    assert 'all-closed' in {e['id'] for e in result['event_definitions']}


def test_family_exposes_members_without_changing_canonical_labels(source):
    """PURPOSE: Check search metadata preserves selected EDs and labels.
    INPUT: Active carrier partition and eligible event cards. OUTPUT: One discovery-only family.
    """
    database, graph = source
    candidate = apply_carrier_policy(graph,database)
    ids = ('opened','a-closed','b-closed')
    offered = {'activities': [{'id': e['id'], 'name': e['activity']}
                              for e in candidate['event_definitions'] if e['id'] in ids]}
    wire = EEGDelivery(candidate,'layer')('pi_events',offered)
    assert wire['activities'] == offered['activities']
    assert wire['event_families'][0]['member_event_definition_ids'] == ['a-closed','b-closed']
    assert 'common_label' not in wire['event_families'][0]


@pytest.mark.parametrize("fk_column,retired", [("category", True), ("other_category", False)])
@pytest.mark.parametrize("pair_type", [list, tuple])
def test_codebook_citations_obey_same_partition_proof(source, fk_column, retired, pair_type):
    """PURPOSE: Admit scoped codebook evidence under the existing lossless partition proof.
    INPUT: Matching or mismatched declared FK receipt. OUTPUT: Broad retirement only for verified selectors.
    """
    database, graph = source
    for event in graph["event_definitions"]:
        if event["source_kind"] != "row_activity":
            continue
        value = event["raw_values"][0]
        event["activity_semantics"].update(citations=[{"evidence_id": "CT:" + value}], evidence=[{
            "id": "CT:" + value, "kind": "verified_code_table_row",
            "source_table": "observations", "carrier_column": "category",
            "lookup_table": "assessment_types", "lookup_key": "code", "lookup_code": value,
            "lookup_label": event["activity"],
            "foreign_key": {"parent_table": "assessment_types", "columns": [pair_type((fk_column, "code"))]},
        }])
    canonical = apply_carrier_policy(graph, database)
    assert any(e["id"] == "all-closed" for e in canonical["retired_event_definitions"]) is retired
