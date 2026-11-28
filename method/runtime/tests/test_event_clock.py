"""Value-specific actual/planned message clocks must not overwrite global timestamp roles."""

from contextlib import closing
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from test_pipeline_runtime import ScriptedClient

from src.common.event_clock import scoped_event_clock
from src.step1_understand.pipeline import build_evidence_graph
from src.step1_understand.detect_and_normalize_timestamps import occurrence_time_policy
from src.step1_understand.validate_event_review_patches import validate_patch


class ScopedEventClockTests(unittest.TestCase):
    """Check literal public evidence, predicate scope, and planned/receipt exclusion."""

    def test_actual_and_estimated_codes_have_separate_clock_meanings(self):
        """PURPOSE: Distinguish actual and estimated represented times under the same physical clock.
        INPUT: Two literal code definitions and a public represented-message timestamp description.
        OUTPUT: Only the actual value is eligible; shared time metadata remains unchanged.
        """
        carrier = {'id': 'C:messages.kind', 'code_meanings': {
            'ACT': 'actual dispatch', 'EST': 'estimated dispatch'}}
        clock = {'id': 'C:messages.value_at', 'definition': 'Timestamp represented by the message.'}
        timestamp = {'ts_id': 'TS:messages.value_at', 'columns': ['value_at'],
                     'semantic_role': 'unknown', 'role_status': 'unknown'}
        original = deepcopy(timestamp)
        for value, expected in [('ACT', True), ('EST', False)]:
            with self.subTest(value=value):
                binding = {'table': 'messages', 'alpha': {'kind': 'value', 'column': 'kind', 'value': value}}
                scoped = scoped_event_clock(binding, timestamp, carrier, clock)
                self.assertEqual(occurrence_time_policy(scoped)['eligible'], expected)
                self.assertEqual(scoped_event_clock(binding, timestamp), scoped)
                binding['alpha']['value'] = 'unrelated'
                self.assertEqual(scoped_event_clock(binding, timestamp), original)
        self.assertEqual(timestamp, original)

    def test_receipt_clock_or_missing_actual_code_cannot_be_promoted(self):
        """PURPOSE: Prevent code labels from turning unrelated receipt/recording clocks into occurrence time.
        INPUT: Actual code plus receipt prose, or ambiguous code plus represented-clock prose.
        OUTPUT: Original unknown time role; no scoped proof is stored.
        """
        timestamp = {'ts_id': 'TS:messages.received_at', 'columns': ['received_at'],
                     'semantic_role': 'unknown', 'role_status': 'unknown'}
        for meaning, definition in [('actual dispatch', 'Time the message was received.'),
                                    ('dispatch', 'Timestamp represented by the message.')]:
            binding = {'table': 'messages', 'alpha': {'kind': 'value', 'column': 'kind', 'value': 'X'}}
            result = scoped_event_clock(binding, timestamp,
                {'id': 'C:messages.kind', 'code_meanings': {'X': meaning}},
                {'id': 'C:messages.received_at', 'definition': definition})
            self.assertEqual(result, timestamp)
            self.assertNotIn('scoped_clock_evidence', binding)


    def test_code_dictionary_supports_two_actual_endpoints_of_the_same_action(self):
        """PURPOSE: Regress the missing typed start and unstable role of system posting.
        INPUT: Public code list and clock prose over two work rows, then mismatched clock subjects.
        OUTPUT: Both documented phases validate, while posting and unrelated starts do not.
        """
        with TemporaryDirectory() as temporary:
            database = Path(temporary) / 'work.sqlite'
            dictionary = Path(temporary) / 'data_dictionary.json'
            with closing(sqlite3.connect(database)) as db, db:
                db.executescript("""
                    CREATE TABLE work(job_id INTEGER PRIMARY KEY, job_code TEXT NOT NULL,
                                      started_at TEXT NOT NULL, finished_at TEXT NOT NULL, posted_at TEXT NOT NULL);
                    INSERT INTO work VALUES (1, 'A', '2025-01-01 10:00:00', '2025-01-01 10:10:00', '2025-01-01 10:20:00');
                    INSERT INTO work VALUES (2, 'B', '2025-01-01 11:00:00', '2025-01-01 11:10:00', '2025-01-01 11:20:00');
                """)
            columns = {'job_code': {'description': 'A = inspection; B = replenishment.'},
                       'started_at': {'description': 'Actual job start time.'},
                       'finished_at': {'description': 'Actual job completion time.'},
                       'posted_at': {'description': 'Time the record was posted to the system.'}}
            dictionary.write_text(json.dumps({'work': {'columns': columns}}))
            graph = build_evidence_graph(database, dictionary, llm=ScriptedClient()).data
            typed = [event for event in graph['bindings'] if event['alpha']['kind'] == 'value']
            self.assertEqual({(e['alpha']['value'], e['ts_id'], e['extraction_status']) for e in typed},
                             {(code, 'TS:work.' + clock, 'executable')
                              for code in ('A', 'B') for clock in ('started_at', 'finished_at')})
            self.assertEqual(len({e['occurrence_identity_rule_id'] for e in typed}), 4)
            posted = next(unit for unit in graph['timestamps'] if unit['ts_id'] == 'TS:work.posted_at')
            self.assertEqual(posted['semantic_role'], 'recorded_time')

            columns['started_at']['description'] = 'Actual machine start time.'
            dictionary.write_text(json.dumps({'work': {'columns': columns}}))
            graph = build_evidence_graph(database, dictionary, llm=ScriptedClient()).data
            self.assertFalse(any(e['alpha']['kind'] == 'value' and e['ts_id'] == 'TS:work.started_at'
                                 for e in graph['bindings']))

    def test_review_cannot_delete_documented_receipt_or_add_selectorless_event_time(self):
        """PURPOSE: Keep receipt separate and prevent a generic represented-time ED.
        INPUT: Two timestamp units, exact DD excerpts and the two invalid review edits.
        OUTPUT: Independent semantic validation errors for the receipt deletion and generic addition.
        """
        represented = 'Timestamp represented by the message.'
        receipt = 'Time the message was received.'
        context = {
            'table': {'name': 'messages'},
            'timestamps': [
                {'ts_id': 'represented', 'columns': ['value_at'], 'semantic_role': 'unknown'},
                {'ts_id': 'receipt', 'columns': ['received_at'], 'semantic_role': 'business_occurrence',
                 'role_status': 'supported'},
            ],
            'existing_definitions': [{'id': 'received', 'ts_id': 'receipt', 'alpha': {'kind': 'column'}}],
            'evidence': [
                {'id': 'C:messages.value_at', 'table': 'messages', 'column': 'value_at', 'text': represented},
                {'id': 'C:messages.received_at', 'table': 'messages', 'column': 'received_at', 'text': receipt},
            ],
            'carrier_values': {},
        }
        patch = {'confidence': 'high', 'time_role_revisions': [], 'operations': [
            {'operation': 'delete', 'target_definition_id': 'received',
             'citations': [{'evidence_id': 'C:messages.received_at', 'quote': receipt}]},
            {'operation': 'add', 'definition': {
                'kind': 'time_column', 'carrier_column_id': None, 'value': None,
                'activity_name': 'Reported occurrence', 'timestamp_unit_id': 'represented', 'event_kind': 'business',
                'activity_citations': [{'evidence_id': 'C:messages.value_at', 'quote': represented}],
                'time_citations': [{'evidence_id': 'C:messages.value_at', 'quote': represented}],
            }},
        ]}
        self.assertIn('semantic:documented_receipt_occurrence_required', validate_patch(patch, context))
        self.assertIn('semantic:represented_clock_requires_activity_selector', validate_patch(patch, context))
