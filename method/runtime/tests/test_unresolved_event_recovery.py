"""Exercise conditional unresolved-code recovery through the public pipeline."""

from contextlib import closing
from pathlib import Path
import json
import sqlite3
from types import SimpleNamespace

from src.common.llm_usage import DEFAULT_MODEL
from src.pipeline import run_pipeline
from src.step1_understand.eeg_configuration import DbuConfig
from src.eeg.evidence_graph_cache import load_or_build
from src.eeg.evidence_graph_storage import read_eeg_layers
from test_pipeline_runtime import ScriptedClient, scope_judgments


class RecoveryClient(ScriptedClient):
    """Keep the normal PI controller active with repeatable evidence-based replies."""

    select_general = False
    case_span = 'each handling job'
    case_meaning = 'Handling Job'

    def create(self, **kwargs):
        """PURPOSE: Supply reproducible PI replies for the same Case and request span.
        INPUT: Public role payload. OUTPUT: Dict-shaped model reply; the ordinary review leaves this ED missing.
        """
        role = kwargs['response_format']['json_schema']['name']
        if role == 'carrier_evidence':
            return self.reply(kwargs, {'decisions': []})
        if role not in {'semantic_decomposer', 'pi_cases', 'pi_events', 'pi_crosscheck'}:
            return super().create(**kwargs)
        raw = kwargs['messages'][1]['content']
        payload = json.loads(raw.split('\n', 1)[1].rsplit('\n', 1)[0] if raw.startswith('<runtime_data>') else raw)
        if role == 'semantic_decomposer':
            q = payload['original_request']
            span = q.split('. ')[-1].rstrip('.')
            reply = {'activity_scope': 'explicit', 'process_focus': None,
                     'case_requirement': {'span': self.case_span, 'meaning': self.case_meaning},
                     'scope_requirement': {'span': q, 'object_scope': 'own', 'granularity': 'distinct'},
                     'activity_requirements': [{'id': 'R1', 'span': span, 'meaning': span, 'qualifiers': [],
                                                'coverage': 'one', 'granularity': 'distinct'}]}
        elif role == 'pi_cases':
            reply = {'candidates': [{'et': payload['entity_types'][0]['id'], 'mode': 'explicit', 'focus': ''}]}
        elif role == 'pi_events':
            general = [a['id'] for a in payload['activities'] if a['name'] == 'Job Completion']
            reply = {'matches': [{'requirement_id': 'R1', 'event_definition_ids': general}]
                     if self.select_general and general else []}
        else:
            general = [a['id'] for a in payload['activity_review']['candidates'] if a['name'] == 'Job Completion'
                       ] if self.select_general else []
            reply = {'differences': [], 'requirement_reviews': [
                {'requirement_id': r['id'], 'event_definition_ids': general,
                 'semantic_status': 'matched' if general else 'missing',
                 'reviewed_coverage': r['coverage'], 'reviewed_granularity': r['granularity'],
                 'source_attribution_gap': False, 'reason': 'No confirmed activity candidate.'}
                for r in payload['activity_review']['requirements']]}
            if payload['activity_review']['initial_proposals']:
                for verdict in reply['requirement_reviews']:
                    verdict['exclusions'] = []
            if 'complete_tier1_inventory' in payload:
                reply['absent_from_tier1'] = []
        scope_judgments(payload, reply)
        return self.reply(kwargs, reply)

    def reply(self, request, reply):
        """PURPOSE: Capture and return one SDK-shaped offline reply. INPUT: Request and JSON. OUTPUT: Test response."""
        self.calls.append(request)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
            content=json.dumps(reply), refusal=None), finish_reason='stop')], usage=None)


def test_saved_unresolved_values_recover_only_positive_explicit_requests(tmp_path):
    """PURPOSE: Verify storage, projection, Case/SQL materialization and conservative abstention.
    INPUT: Small job DB with known A, undocumented B and shared actual-vs-recording clocks.
    OUTPUT: Exact B row for confirmed selectors and zero recovery for unlabeled or excluded requests.
    """
    database = tmp_path / 'database.sqlite'
    with closing(sqlite3.connect(database)) as db, db:
        db.executescript("""
            CREATE TABLE jobs(job_id TEXT PRIMARY KEY NOT NULL, job_code TEXT NOT NULL,
                              started_at TEXT, finished_at TEXT, posted_at TEXT);
            INSERT INTO jobs VALUES
              ('a1','A','2025-01-01 10:00:00','2025-01-01 10:10:00','2025-01-01 10:20:00'),
              ('b1','B','2025-01-01 11:00:00','2025-01-01 11:10:00','2025-01-01 11:20:00');
        """)
    dictionary = {'name': 'RecoveryFixture', 'timezone': 'UTC', 'tables': [{
        'table': 'jobs', 'definition': 'Ground handling work orders and completion records.',
        'columns': [
            {'name': 'job_id', 'definition': 'Handling job identifier.'},
            {'name': 'job_code', 'definition': 'Work type code.', 'code_meanings': {'A': 'Inspection'}},
            {'name': 'started_at', 'definition': 'Actual job start time.'},
            {'name': 'finished_at', 'definition': 'Actual job completion time.'},
            {'name': 'posted_at', 'definition': 'Time the record was posted to the system.'},
        ]}]}
    client = RecoveryClient()
    config = DbuConfig(repair=False, semantic_signatures=False, global_ot_review=False, pairwise_identity_llm=False)
    graph, _ = load_or_build(database, dictionary, client=client, config=config, directory=tmp_path / 'cache',
                             prepare_summary=True)
    directory = Path(graph['eeg_cache']['directory'])
    manifest = json.loads((directory / 'manifest.json').read_text())
    assert 'unresolved_event_evidence' in json.loads((directory / 'metadata.json').read_text())['runtime']
    graph, _ = read_eeg_layers(directory, manifest['artifacts'])
    evidence = graph['unresolved_event_evidence']
    assert {(r['value'], r['raw_clock_phase']) for r in evidence['pairs']} == {('B', 'start'), ('B', 'complete')}
    ids = {b['id'] for b in graph['event_definitions']}
    assert not ids.intersection(pair['candidate_id'] for pair in evidence['pairs'])

    cases = [
        ("Extract completed jobs for each handling job where job_code = 'B'.", 'B completed'),
        ("B means calibration. Extract calibration completion for each handling job.", 'calibration completed'),
        ("Extract calibration completion for each handling job.", None),
        ("Extract completed jobs for each handling job except job_code = 'B'.", None),
        ("Extract posted records for each handling job where job_code = 'B'.", None),
        ("Extract completed jobs for each handling job where job_code = 'B' or job_code = 'A'.", None),
        ("Extract the first completed job for each handling job where job_code = 'B'.", None),
    ]
    for question, label in cases:
        output = run_pipeline(database, dictionary, question, graph=graph, client=client, model=DEFAULT_MODEL,
                              evidence_retrieval=False)
        pi = output['query']
        events = output['execution'].get('event_log', [])
        if label:
            assert pi['status'] == 'ready', (pi['process_view_validation'], [(r.get('role'), r.get('rejection'), r.get('error')) for r in pi['process_interpretation_trace']['model_calls']], pi['process_interpretation_trace']['unresolved_event_recovery'])
            assert output['es']['status'] == 'accepted', output['verification']
            assert [(row['source_record_id'], row['activity']) for row in events] == [('["b1"]', label)]
            assert output['verification']['status'] == 'not_needed'
        else:
            assert not events
            assert not pi['process_information'].get('recovered_event_decisions')
        assert {b['id'] for b in graph['event_definitions']} == ids

    client.select_general = True
    question, label = cases[0]
    result = run_pipeline(database, dictionary, question, graph=graph, client=client, evidence_retrieval=False)
    events = result["execution"]["event_log"]
    assert [(row["source_record_id"], row["activity"]) for row in events] == [('["b1"]', label)]
    assert result["query"]["process_view_termination_reason"] == "explicit_carrier_recovery"


def test_single_row_clock_recovery_without_general_ed_and_with_toggle(tmp_path):
    """PURPOSE: Recover one typed code under a single proved actual row clock.
    INPUT: One known and one undocumented scan code using the same clock. OUTPUT: Correct SQL only when enabled.
    """
    database = tmp_path / "scans.sqlite"
    with closing(sqlite3.connect(database)) as db, db:
        db.executescript("""
            CREATE TABLE scans(scan_id TEXT PRIMARY KEY NOT NULL, scan_code TEXT, scanned_at TEXT);
            INSERT INTO scans VALUES
              ('s1', 'B101', '2025-01-01 10:00:00'), ('s2', 'B204', '2025-01-01 11:00:00');
        """)
    dictionary = {"name": "ScanFixture", "tables": [{"table": "scans", "definition": "Physical scan activity records.",
        "columns": [{"name": "scan_id", "definition": "Unique scan identifier."},
                    {"name": "scan_code", "definition": "Code identifying the type of scan activity.",
                     "value_domain": {"B101": "Bag accepted"}},
                    {"name": "scanned_at", "definition": "Time of the physical scan."}]}]}
    config = DbuConfig(repair=False, semantic_signatures=False, global_ot_review=False, pairwise_identity_llm=False)
    client = RecoveryClient()
    client.case_span, client.case_meaning = "each scan", "Individual Scan"
    graph, _ = load_or_build(database, dictionary, client=client, config=config,
                             directory=tmp_path / "cache", prepare_summary=True)
    assert all(event["source_kind"] == "row_activity" for event in graph["event_definitions"])
    pending, = graph["unresolved_event_evidence"]["pairs"]
    assert pending["value"] == "B204" and pending["raw_clock_action"] == "scan" and pending["raw_clock_phase"] is None
    requests = [
        ("Extract scans with scan_code = 'B204' for each scan.", "B204 scan"),
        ("B204 means bag loading scan. Extract bag loading scans for each scan.", "bag loading scan"),
        ("Extract bag loading scans for each scan.", None),
    ]
    response_cache = {}
    for question, expected_label in requests:
        outcomes = {}
        for enabled in (False, True):
            outcomes[enabled] = run_pipeline(database, dictionary, question, graph=graph, client=client,
                model=DEFAULT_MODEL, evidence_retrieval=False, response_cache=response_cache, recovery_enabled=enabled)
        assert not outcomes[False]["execution"].get("event_log")
        found = outcomes[True]["execution"].get("event_log", [])
        assert [(r["source_record_id"], r["activity"], r["timestamp_raw_column"]) for r in found] == (
            [('["s2"]', expected_label, "scanned_at")] if expected_label else [])
    assert not any(e.get("raw_values") == ["B204"] for e in graph["event_definitions"])
