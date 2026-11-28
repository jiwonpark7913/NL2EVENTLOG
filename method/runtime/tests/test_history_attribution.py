"""Offline regression tests for canonical EDs and scoped multi-role attribution."""

from contextlib import closing
from copy import deepcopy
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import json
import unittest

from src.common.event_definition_eligibility import effective_binding, review_entity_events
from src.common.schema_metadata import database_fingerprint
from src.step2_retrieve_and_interpret.pipeline import finalize_explicit_attribution
from src.step2_retrieve_and_interpret.interpret_and_verify_process import candidate_catalog
from src.step3_execute.materialize_extraction_specification import build_pi_es
from src.step2_retrieve_and_interpret.resolve_history_attribution import role_scope_needs_review, scope_history_paths, verify_path_union


class HistoryAttribution(unittest.TestCase):
    """Use complete physical maps with no AirlineFlow-specific data or rules."""

    def setUp(self):
        """PURPOSE: Prepare three physical projection shapes. INPUT: Temporary directory. OUTPUT: SQLite DB and EEG contracts."""
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.database = Path(directory.name) / 'events.sqlite'
        with closing(sqlite3.connect(self.database)) as connection:
            connection.executescript("""
                CREATE TABLE accounts(id INTEGER PRIMARY KEY);
                INSERT INTO accounts VALUES (1), (2), (3);
                CREATE TABLE notices(id INTEGER PRIMARY KEY, sender INTEGER REFERENCES accounts(id),
                    recipient INTEGER REFERENCES accounts(id), received_at TEXT);
                INSERT INTO notices VALUES (10, 1, 1, '2025-03-01'), (11, 2, 3, '2025-03-01'),
                    (12, 3, NULL, '2025-03-01');
            """)
        self.target = {'id': 'ET:account', 'anchor_table': 'accounts', 'key_columns': ['id'],
                       'population': {'status': 'valid', 'maps': [
                           {'table': 'accounts', 'representation_id': 'O:accounts',
                            'key_columns': ['id'], 'identity_scope_id': 'accounts'}]}}
        self.event = {'id': 'ED:receipt', 'source_table': 'notices', 'activity_label': 'Notice received',
                      'row_selection': {'kind': 'all_rows'}, 'source_row_key': ['id'],
                      'occurrence_identity_rule_id': 'receipt:identity',
                      'occurrence_time_source': {'columns': ['received_at']},
                      'timestamp_candidates': [{'columns': ['received_at']}],
                      'extraction_status': 'executable', 'candidate_tier': 1,
                      'extraction_checks': dict.fromkeys(('activity', 'occurrence', 'time', 'identity'), 'supported'),
                      'activity_semantics': {'status': 'supported', 'occurrence_status': 'supported'},
                      'entity_reviews': {'ET:account': {'time_role': 'non_occurrence'}, 'ET:notice': {'promoted': True}}}
        self.graph = {'database_fingerprint': database_fingerprint(self.database),
                      'entity_types': [self.target], 'event_definitions': [self.event], 'data_dictionary': {}}

    def path(self, role, clause='', count=1, project='notices.id'):
        """PURPOSE: Provide an executable path receipt. INPUT: Known fixture role, scope and count. OUTPUT: Case map evidence."""
        statement = (f'SELECT json_array({project}), json_array(accounts.id) '
                     f'FROM notices JOIN accounts ON notices.{role}=accounts.id {clause}')
        return {'id': role, 'target_table_key_id': 'O:accounts', 'validation_status': 'valid',
                'role_validation': {'status': 'pass', 'reference': {
                    'role': role, 'step': {'relationship_id': role}}},
                'case_map': {'map_sql': statement, 'validation': {
                    'passed': True, 'max_cases_per_source': 1, 'matched_source_rows': count,
                    'attributable_source_rows': count, 'unmatched_source_rows': 0}}}

    def proof(self, *paths):
        """PURPOSE: Validate a union against the fixture DB. INPUT: Path receipts. OUTPUT: Joint proof."""
        return verify_path_union(self.graph, self.database, self.target, self.event, paths)

    def test_legacy_et_clock_veto_cannot_override_canonical_definition(self):
        """PURPOSE: Prevent ET-specific clock rejection or promotion. INPUT: Same ED, disagreeing ET reviews. OUTPUT: Unchanged ED."""
        original = deepcopy(self.event)
        for entity in ('ET:account', 'ET:notice'):
            self.assertIs(effective_binding(self.event, entity), self.event)
        self.assertEqual(self.event, original)
        row = candidate_catalog(self.graph, 'ET:account')[self.event['id']]
        self.assertEqual(row['effective_tier'], 1)
        self.assertTrue(row['binding_policy']['history_supported'])

    def test_relationship_rejection_is_path_local(self):
        """PURPOSE: Suppress only an incompatible path. INPUT: One incompatible and one accepted ET relationship. OUTPUT: Stable ED and one path."""
        approved = self.path('recipient')
        denied = self.path('sender')
        for path in (approved, denied):
            path.update(joins=[], to=self.target['id'], event_definition_id=self.event['id'])
        self.graph['attribution_paths'] = [approved, denied]
        self.event['entity_reviews'][self.target['id']]['attribution_paths'] = {
            'sender': {'status': 'incompatible', 'reason': 'Documented endpoint differs', 'citations': ['DD']},
            'recipient': {'status': 'supported', 'role': 'subject'}}
        row = candidate_catalog(self.graph, self.target['id'], for_history=True)[self.event['id']]
        self.assertTrue(row['binding_policy']['history_supported'])
        self.assertTrue(row['subject_role_supported'])
        self.assertEqual(row['attribution']['evidence_ids'], ['recipient'])

    def test_fresh_entity_review_records_only_grounded_relationship_decisions(self):
        """PURPOSE: Exercise the replacement Step 1 model contract. INPUT: Native ED and literal DD evidence.
        OUTPUT: New path decisions and unchanged occurrence definition.
        """
        event = deepcopy(self.event)
        event.update(ts_id='TS:receipt', table='notices', alpha={'kind': 'column', 'column': 'received_at'})
        evidence = {'id': 'C:notices.recipient:definition', 'table': 'notices', 'column': 'recipient',
                    'text': 'The recipient account receives the notice.'}
        dd = {'semantic_statements': [evidence]}
        recipient = self.path('recipient', count=2)
        recipient.update(to=self.target['id'], event_definition_id=event['id'], joins=[
            {'left_table': 'notices', 'left_columns': ['recipient'],
             'right_table': 'accounts', 'right_columns': ['id']}])
        recipient['case_map']['validation']['source_rows'] = 2
        graph = {'bindings': [event], 'timestamps': [{'ts_id': 'TS:receipt', 'columns': ['received_at']}],
                 'attribution_paths': [recipient], 'concepts': [self.target]}
        original = {key: deepcopy(event[key]) for key in ('activity_label', 'occurrence_time_source', 'row_selection',
                    'source_row_key', 'occurrence_identity_rule_id', 'extraction_checks', 'timestamp_candidates')}

        def reply(**kwargs):
            """PURPOSE: Confirm a path using evidence offered to the ET review. INPUT: SDK request. OUTPUT: Fake response."""
            card = json.loads(kwargs['messages'][1]['content'])['definitions'][0]
            self.assertIn(evidence['id'], card['dictionary_ids'])
            decisions = [{'id': card['id'], 'duplicate_of': '', 'reason': '', 'citations': [],
                          'paths': [{'path_id': 'recipient', 'status': 'supported', 'role': 'subject',
                                     'reason': 'The recipient is the subject of receipt.',
                                     'citations': [{'id': evidence['id'], 'quote': evidence['text']}]}]}]
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({'decisions': decisions})))],
                                   usage=None)

        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=reply)))
        audits = review_entity_events(graph, dd, self.database, client, 'offline-model')
        self.assertEqual(audits[0]['errors'], [])
        review = event['entity_reviews'][self.target['id']]
        self.assertEqual(review['attribution_paths']['recipient']['role'], 'subject')
        self.assertEqual({key: event[key] for key in original}, original)
        physical_paths = deepcopy(graph['attribution_paths'])

        def incomplete_reply(**kwargs):
            """PURPOSE: Simulate transport rejection of a capped output. INPUT: SDK options. OUTPUT: Validation exception."""
            raise ValueError('Claude structured response incomplete: max_tokens')

        def missing_decision(**kwargs):
            """PURPOSE: Simulate a valid schema with missing ED IDs. INPUT: SDK options. OUTPUT: Empty decisions."""
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"decisions":[]}'))],
                                   usage=None)

        for failed_reply in (incomplete_reply, missing_decision):
            with self.subTest(failure=failed_reply.__name__):
                client.chat.completions.create = failed_reply
                failed = review_entity_events(graph, dd, self.database, client, 'offline-model')
                self.assertTrue(failed[0]['errors'])
                self.assertEqual(graph['entity_event_review_status'][self.target['id']]['status'], 'incomplete')
                self.assertNotIn(self.target['id'], event['entity_reviews'])
                self.assertEqual(graph['attribution_paths'], physical_paths)
                self.assertEqual({key: event[key] for key in original}, original)

    def test_explicit_pi_rejects_cross_requirement_case_conflict(self):
        """PURPOSE: Block a ready Explicit PI whose selected SQLite paths attach one occurrence to different Cases.
        INPUT: Same ED with two independently executable role paths. OUTPUT: Unresolved PI and blocked materialization.
        """
        identifier = self.event['id']
        sender = self.path('sender', 'WHERE notices.id=11')
        recipient = self.path('recipient', 'WHERE notices.id=11')
        for path in (sender, recipient):
            path.update(joins=[], to=self.target['id'], event_definition_id=identifier)
        self.graph['attribution_paths'] = [sender, recipient]
        pi = {'request_mode': 'explicit', 'status': 'ready', 'case_notion_et_id': self.target['id'],
              'verified_attribution_paths': {identifier: ['recipient', 'sender']}}
        result = {'status': 'ready', 'process_information': pi,
                  'final_validation': {'status': 'valid', 'warnings': [], 'checks': []}}
        receipt = finalize_explicit_attribution(result, self.graph, self.database)[identifier]
        self.assertEqual(receipt['multiple_case_occurrences'], 1)
        self.assertEqual(result['termination_reason'], 'cross_path_case_conflict')
        self.assertEqual(pi['status'], 'selection_required')
        self.assertNotIn(identifier, pi['verified_attribution_paths'])
        self.assertNotIn('verified_attribution_partitions', pi)
        es = build_pi_es(self.graph, {'status': result['status'], 'process_view': {'process_information': pi}})
        self.assertEqual(es['status'], 'selection_required')

    def test_disjoint_roles_and_equivalent_projections_pass_jointly(self):
        """PURPOSE: Admit a functional union and count redundant pairs. INPUT: Two roles with distinct and shared source pairs. OUTPUT: Passing proof."""
        disjoint = self.proof(self.path('sender', 'WHERE notices.id=12'),
                              self.path('recipient', 'WHERE notices.id=10'))
        self.assertEqual((disjoint['status'], disjoint['source_occurrences']), ('pass', 2))
        self.assertEqual(disjoint['partition']['path_ids'], ['recipient', 'sender'])
        overlap = self.proof(self.path('sender', 'WHERE notices.id=10'),
                             self.path('recipient', 'WHERE notices.id=10'))
        self.assertEqual((overlap['status'], overlap['distinct_pairs'], overlap['repeated_pairs']), ('pass', 1, 1))
        self.assertNotIn('partition', overlap)

    def test_documented_multiple_case_assignment_is_distinct_from_join_conflict(self):
        """PURPOSE: Classify legitimate fanout separately. INPUT: One occurrence with two role-distinct targets. OUTPUT: Conflict or documented multi-Case."""
        sender = self.path('sender', 'WHERE notices.id=11')
        recipient = self.path('recipient', 'WHERE notices.id=11')
        self.assertEqual(self.proof(sender, recipient)['status'], 'cross_path_case_conflict')
        self.graph['data_dictionary']['business_rules'] = [{
            'text': 'A received notice belongs to both the sender account and recipient account.',
            'event_attribution': {'source_table': 'notices', 'case_table': 'accounts',
                                  'roles': ['sender', 'recipient'], 'occurrence_columns': ['received_at'],
                                  'multiple_cases': True}}]
        result = self.proof(sender, recipient)
        self.assertEqual((result['status'], result['evidence_ids']), ('documented_multiple_cases', ['BR:1']))
        invalid = self.path('sender', count=3, project='10')
        self.assertEqual(self.proof(invalid, recipient)['status'], 'invalid_path_union')

    def test_requested_role_and_topic_are_resolved_separately(self):
        """PURPOSE: Scope roles using literal evidence. INPUT: Whole history, explicit role and ambiguous topic. OUTPUT: Full union, selected role, or review."""
        paths = [self.path('sender'), self.path('recipient')]
        attribution = {'paths': paths}
        self.assertEqual(scope_history_paths(attribution, ['complete history']), ('selected', paths))
        self.assertEqual(scope_history_paths(attribution, ['recipient history']), ('selected', paths[1:]))
        self.assertEqual(scope_history_paths(attribution, ['account notices'], focus='notices')[0], 'needs_role_review')
        self.assertTrue(role_scope_needs_review(['not the sender'], ['sender', 'recipient']))
        self.assertEqual(scope_history_paths(attribution, ['not the sender'], review_required=True)[0], 'needs_role_review')
        self.assertEqual(scope_history_paths(attribution, ['not the sender'], review_required=True,
                                           chosen_ids=['recipient']), ('selected', paths[1:]))
