"""Regress complete value/clock evaluation after model admission of a carrier."""

from contextlib import closing
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

from test_pipeline_runtime import ScriptedClient

from src.step1_understand.pipeline import build_evidence_graph
from src.step1_understand.review_uncertain_event_definitions import apply_review_decision


class CarrierClient(ScriptedClient):
    """Provide grounded model decisions with the same call contract as the live client."""

    def create(self, **kwargs):
        """PURPOSE: Simulate carrier admission and value interpretation.
        INPUT: Bound metadata requests. OUTPUT: Structured citations, including a deliberately bad one.
        """
        if kwargs['response_format']['json_schema']['name'] != 'carrier_evidence':
            return super().create(**kwargs)
        self.calls.append(kwargs)
        payload = json.loads(kwargs['messages'][1]['content'].split('\n', 1)[1].rsplit('\n', 1)[0])
        decisions = []
        for candidate in payload['candidates']:
            identifier = candidate['id']
            evidence_id = candidate['evidence_ids'][0]
            if payload['task'] == 'event_encoding_identification':
                decision = 'carrier' if candidate['column'] == 'job_code' else 'attribute'
                label, quote = '', payload['evidence'][evidence_id]
            elif payload['task'] == 'carrier_value_semantics':
                decision, (label, quote) = 'supported', {
                    'A': ('inspection', 'A for inspection'),
                    'B': ('calibration', 'B for calibration'),
                    'C': ('guessed meaning', 'C for guessed meaning'),
                }[candidate['raw_value']]
            else:
                continue
            decisions.append({'id': identifier, 'decision': decision, 'label': label,
                              'citations': [{'evidence_id': evidence_id, 'quote': quote}]})
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
            content=json.dumps({'decisions': decisions}), refusal=None))], usage=None)


def test_model_carrier_enters_every_value_and_clock(tmp_path):
    """PURPOSE: Test staged interpretation without a provider call.
    INPUT: Three observed codes, two actual clocks, one recording clock, an attribute code domain.
    OUTPUT: Nine auditable pairs, two unresolved meanings for the uncited code, and four typed EDs.
    """
    database = tmp_path / 'work.sqlite'
    dictionary = tmp_path / 'data_dictionary.json'
    with closing(sqlite3.connect(database)) as db, db:
        db.executescript("""
            CREATE TABLE work(job_id INTEGER PRIMARY KEY, job_code TEXT, aircraft_type TEXT,
                              started_at TEXT, finished_at TEXT, posted_at TEXT);
            INSERT INTO work VALUES
                (1, 'A', 'W', '2025-01-01 10:00:00', '2025-01-01 10:10:00', '2025-01-01 10:20:00'),
                (2, 'B', 'N', '2025-01-01 11:00:00', '2025-01-01 11:10:00', '2025-01-01 11:20:00'),
                (3, 'C', 'N', '2025-01-01 12:00:00', '2025-01-01 12:10:00', '2025-01-01 12:20:00');
        """)
    dictionary.write_text(json.dumps({'work': {'columns': {
        'job_code': {'description': 'Codes include A for inspection and B for calibration. C has no description.'},
        'aircraft_type': {'description': 'Aircraft classification.',
                          'code_meanings': {'W': 'widebody', 'N': 'narrowbody'}},
        'started_at': {'description': 'Actual job start time.'},
        'finished_at': {'description': 'Actual job completion time.'},
        'posted_at': {'description': 'Time the record was posted to the system.'},
    }}}))
    graph = build_evidence_graph(database, dictionary, llm=CarrierClient()).data
    matrix = graph['carrier_timestamp_matrix']
    assert {r['carrier'] for r in matrix} == {'job_code'}
    assert {(r['value'], tuple(r['clock'])) for r in matrix} == {
        (value, (clock,)) for value in 'ABC' for clock in ('started_at', 'finished_at', 'posted_at')}
    assert {r['status'] for r in matrix if r['clock'] == ['posted_at']} == {'excluded'}
    assert {r['status'] for r in matrix if r['value'] == 'C' and r['clock'] != ['posted_at']} == {'unresolved'}
    assert {b['alpha']['name'] for b in graph['bindings'] if b['alpha']['kind'] == 'value'} == {
        'inspection started', 'inspection completed', 'calibration started', 'calibration completed'}


def test_table_review_cannot_delete_a_protected_partition_candidate(tmp_path):
    """PURPOSE: Prevent table review from bypassing partition proof.
    INPUT: A validated candidate and an attempted deletion of its protected ID. OUTPUT: Preserved ED and audit.
    """
    binding = {'id': 'broad'}
    operation = {'operation': 'delete', 'target_definition_id': 'broad', 'citations': []}
    context = {'protected_definition_ids': ['broad'], 'table': {'name': 'work'},
               'existing_definitions': [binding], 'timestamps': [], 'evidence': []}
    decision = {'patch': {'confidence': 'high', 'operations': [operation], 'time_role_revisions': []},
                'context': context, 'audit': {}}
    result, status = apply_review_decision([binding], SimpleNamespace(name='work'), {},
                                          decision, [], {}, tmp_path / 'unused')
    assert result == [binding] and status == 'confirmed_unchanged'
    assert decision['audit']['application']['ignored_protected_operations'] == [operation]


def test_missing_description_retains_meaning_from_linked_codebook(tmp_path):
    """PURPOSE: Preserve code semantics that remain publicly documented after prose removal.
    INPUT: One declared codebook FK, an observed code and an unlabeled source column in public DD.
    OUTPUT: Meaning grounded in the verified codebook row before construction of both actual phases.
    """
    database = tmp_path / 'work.sqlite'
    dictionary = tmp_path / 'data_dictionary.json'
    with closing(sqlite3.connect(database)) as db, db:
        db.executescript("""
            CREATE TABLE codebook(code TEXT PRIMARY KEY, label TEXT);
            CREATE TABLE work(job_id INTEGER PRIMARY KEY, job_code TEXT REFERENCES codebook(code),
                              started_at TEXT, finished_at TEXT);
            INSERT INTO codebook VALUES ('Z', 'Calibration');
            INSERT INTO work VALUES (1, 'Z', '2025-01-01 10:00:00', '2025-01-01 10:10:00');
        """)
    dictionary.write_text(json.dumps({'work': {'columns': {
        'job_code': {'description': 'Code for the actual work activity.'},
        'started_at': {'description': 'Actual job start time.'},
        'finished_at': {'description': 'Actual job completion time.'},
    }}}))
    graph = build_evidence_graph(database, dictionary, llm=CarrierClient()).data
    specialized = [b for b in graph['bindings'] if b['alpha']['kind'] == 'value']
    assert {b['alpha']['name'] for b in specialized} == {'Calibration started', 'Calibration completed'}
    assert all(any(ref['kind'] == 'verified_code_table_row' for ref in b['activity_semantics']['evidence'])
               for b in specialized)
