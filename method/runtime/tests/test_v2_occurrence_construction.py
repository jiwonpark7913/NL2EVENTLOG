"""Development fixtures for evidence-first and relational occurrence construction."""

from contextlib import closing
import json
import sqlite3

from src.eeg.eeg_store import EEGStore, write_index
from src.step1_understand.pipeline import build_evidence_graph
from src.step1_understand.eeg_configuration import DbuConfig
from src.step1_understand.project_runtime_evidence_graph import to_runtime_graph
from src.step3_execute.compile_event_log_sql import extract_event_log
from src.step3_execute.materialize_extraction_specification import build_pi_es
from test_pipeline_runtime import ScriptedClient


def build(tmp_path, ddl, dictionary):
    """PURPOSE: Build query-independent EEG from a temporary public development fixture.
    INPUT: SQLite setup SQL and ordinary DD. OUTPUT: DB path and runtime graph.
    """
    database, dd = tmp_path / 'source.sqlite', tmp_path / 'dictionary.json'
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.executescript(ddl)
    dd.write_text(json.dumps(dictionary))
    config = DbuConfig(repair=False, semantic_signatures=False, global_ot_review=False, pairwise_identity_llm=False)
    graph = to_runtime_graph(build_evidence_graph(database, dd, config, ScriptedClient()), database)
    return database, graph


def test_documented_family_member_survives_zero_observations(tmp_path):
    """PURPOSE: Preserve a documented absent code with only its applicable business phase.
    INPUT: Two actual clocks, a posting clock and one documented absent value.
    OUTPUT: Executable completion ED for absent code and no start or posting ED for it.
    """
    _, graph = build(tmp_path, """
        CREATE TABLE task(row_id INTEGER PRIMARY KEY, task_code TEXT,
            started_at TEXT, finished_at TEXT, posted_at TEXT);
        INSERT INTO task VALUES (1, 'I', '2025-03-01 10:00:00',
            '2025-03-01 11:00:00', '2025-03-01 12:00:00');
        """, {'task': {'definition': 'Ground handling work orders and completion records.', 'columns': {
            'task_code': {'definition': 'Code for the actual work activity.',
                          'value_domain': {'I': 'Inspection', 'S': {'label': 'Sealing', 'lifecycle_phases': ['complete']}}},
            'started_at': {'definition': 'Actual job start time.'},
            'finished_at': {'definition': 'Actual job completion time.'},
            'posted_at': {'definition': 'Time the record was posted to the system.'}}}})
    definitions = [e for e in graph['event_definitions'] if e.get('raw_values') == ['S']]
    definition, = definitions
    assert definition['extraction_status'] == 'executable'
    assert definition['timestamp_columns'] == ['finished_at']
    assert definition['timestamp_pairing']['timed_rows'] == 0


def history_fixture(tmp_path):
    """PURPOSE: Generate ordered public history with repeated state and rework.
    INPUT: Temporary directory. OUTPUT: Synthetic database and v2 EEG.
    """
    return build(tmp_path, """
        CREATE TABLE work_kind(code TEXT NOT NULL PRIMARY KEY, label TEXT);
        CREATE TABLE state_kind(code TEXT NOT NULL PRIMARY KEY, label TEXT);
        CREATE TABLE work(id INTEGER PRIMARY KEY, kind TEXT NOT NULL REFERENCES work_kind(code));
        CREATE TABLE history(sequence INTEGER PRIMARY KEY, work_id INTEGER NOT NULL REFERENCES work(id),
            state TEXT NOT NULL REFERENCES state_kind(code), happened_at TEXT);
        INSERT INTO work_kind VALUES ('C', 'Cabin cleaning'), ('R', 'Refuelling');
        INSERT INTO state_kind VALUES ('A', 'Started'), ('B', 'Completed'), ('D', 'Reopened');
        INSERT INTO work VALUES (11, 'C'), (22, 'R');
        INSERT INTO history VALUES
            (1, 11, 'A', '2025-01-01 09:00:00'), (2, 11, 'B', '2025-01-01 10:00:00'),
            (3, 11, 'B', '2025-01-01 10:01:00'), (4, 11, 'D', '2025-01-01 11:00:00'),
            (5, 11, 'B', '2025-01-01 12:00:00'), (6, 22, 'A', '2025-01-01 09:00:00'),
            (7, 22, 'B', '2025-01-01 10:00:00'), (8, 11, 'B', '2025-01-01 12:01:00');
        """, {
        'work_kind': {'columns': {'label': {'definition': 'Work category name.'}}},
        'state_kind': {'columns': {'label': {'definition': 'Business state name.'}}},
        'work': {'readable_name': 'Work', 'definition': 'One work business entity.',
                 'columns': {'kind': {'definition': 'Type code of the work.'}}},
        'history': {'definition': 'Ordered observations of current work state.',
                    'state_history': {'state_column': 'state', 'occurrence_column': 'happened_at',
                                      'partition_by': ['work_id'], 'order_by': ['sequence'],
                                      'context': {'path': [['work_id']], 'column': 'kind'}},
                    'columns': {'state': {'definition': 'Code for the recorded state activity.'},
                                'happened_at': {'definition': 'Time of the physical action.'}}}})


def test_history_transition_preserves_rework_and_context(tmp_path):
    """PURPOSE: Prove a relational ED, indexed closure and ordinary PI-to-SQL execution.
    INPUT: Case history with redundant completion, rework and a different work category.
    OUTPUT: Two completion occurrences and a verified reusable attribution path.
    """
    database, graph = history_fixture(tmp_path)
    definition, = [e for e in graph['event_definitions']
                   if e['activity_label'].casefold() == 'cabin cleaning completed']
    assert definition['extraction_status'] == 'executable'
    assert not graph['candidate_ledger']['audit']['missing_projections']
    index = tmp_path / 'index.sqlite'
    write_index(index, graph, 'synthetic')
    with EEGStore(index, 'synthetic').open(database) as lookup:
        scoped = lookup.request_graph('Extract Cabin cleaning Completed for each work.')
        assert definition['id'] in scoped['index_scope']['prioritization_event_ids']
        attribution = next(p for p in scoped['attribution_paths']
                           if p['event_definition_id'] == definition['id'] and p['validation_status'] == 'valid')
        assert attribution['joins'] and lookup.records('join_paths')
        assert attribution['case_map']['validation']['source_rows'] == 2
    case, event, path = attribution['to'], definition['id'], attribution['id']
    pi = {'status': 'ready', 'case_notion_et_id': case, 'selected_event_definition_ids': [event],
          'verified_attribution_paths': {event: [path]}}
    es = build_pi_es(scoped, {'status': 'ready', 'query': 'Extract Cabin cleaning Completed for each work.',
                              'V_q': [], 'process_view': {'target_ot_id': case,
                              'event_definitions': [event], 'process_information': pi,
                              'activity_scope': 'explicit'}})
    assert es['status'] == 'accepted', es
    _, rows, _ = extract_event_log(database, es)
    assert {tuple(json.loads(row['source_record_id'])) for row in rows} == {('2',), ('5',)}


def test_occurrence_clock_can_anchor_a_carrier_on_another_table(tmp_path):
    """PURPOSE: Detect EDs whose occurrence clock and activity are stored separately.
    INPUT: An occurrence table linked to typed business objects and an independent codebook.
    OUTPUT: One typed, executable ED per represented carrier with the anchor table's row key and clock.
    """
    _, graph = build(tmp_path, """
        CREATE TABLE action_kind(code TEXT NOT NULL PRIMARY KEY, title TEXT);
        CREATE TABLE actions(action_id INTEGER PRIMARY KEY, kind TEXT REFERENCES action_kind(code));
        CREATE TABLE ticks(tick_id INTEGER PRIMARY KEY, action_id INTEGER REFERENCES actions(action_id),
                           occurred_at TEXT);
        INSERT INTO action_kind VALUES ('A', 'Inspection'), ('B', 'Sealing');
        INSERT INTO actions VALUES (1, 'A'), (2, 'B');
        INSERT INTO ticks VALUES (1, 1, '2025-01-01 10:00:00'), (2, 2, '2025-01-01 11:00:00');
        """, {'action_kind': {'columns': {'title': {'definition': 'Business activity name.'}}},
              'actions': {'columns': {'kind': {'definition': 'Type code of the business operation.'}}},
              'ticks': {'definition': 'One row per actual occurrence.',
                        'related_occurrence': {'occurrence_column': 'occurred_at',
                                               'carrier': {'path': [['action_id']], 'column': 'kind'}},
                        'columns': {'occurred_at': {'definition': 'Time of the physical action.'}}}})
    definitions = [e for e in graph['event_definitions'] if e['source_table'] == 'ticks']
    assert {e['activity_label'] for e in definitions} == {'Inspection', 'Sealing'}
    assert all(e['extraction_status'] == 'executable' and e['source_row_key'] == ['tick_id']
               and e['documented_source_conditions'][0]['kind'] == 'related_value' for e in definitions)
