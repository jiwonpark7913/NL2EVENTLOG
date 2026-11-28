"""Regression checks for delivery views over the same Step 2 inventory."""

from copy import deepcopy
import unittest

from src.step2_retrieve_and_interpret.eeg_delivery import EEGDelivery
from src.step2_retrieve_and_interpret.execute_model_roles import constrained_role_schema


class DeliveryTests(unittest.TestCase):

    def setUp(self):
        """PURPOSE: Create unrelated and related ED cards. INPUT: Test lifecycle. OUTPUT: Public fixture."""
        self.cards = [{'id': 'E:' + name, 'name': name, 'source': 'tasks', 'time_role': None,
                       'source_context': ['Task execution table.'], 'requirement_ids': ['R1'],
                       'dictionary_evidence': ['Observed occurrence.', 'Observed occurrence.'],
                       'role_projections': [{'path_id': 'AP:' + name, 'role': 'consumer'}]}
                      for name in ('Purchase approval', 'Final decision', 'Shipment', 'Invoice', 'Refund')]
        self.graph = {'event_definitions': [{'id': row['id'],
                        'timestamp_candidates': [{'time_role': 'actual'}]} for row in self.cards],
                      'event_definition_pair_relationships': [{
                          'binding_pair': [self.cards[0]['id'], self.cards[1]['id']], 'status': 'supported'}]}
        self.payload = {'original_request': 'Purchase approval only', 'activities': self.cards,
                        'activity_requirements': [{'id': 'R1', 'span': 'Purchase approval',
                                                  'meaning': 'Purchase approval', 'coverage': 'one'}]}

    def test_layer_keeps_role_schemas_ids_and_evidence(self):
        """PURPOSE: Verify B preserves scope and verbatim evidence. INPUT: Full cards.
        OUTPUT: Identical response schema, shared source explanation and original physical role IDs.
        """
        original = deepcopy(self.payload)
        layer = EEGDelivery(self.graph, 'layer')('pi_events', self.payload)
        self.assertEqual(self.payload, original)
        self.assertEqual(constrained_role_schema('pi_events', layer),
                         constrained_role_schema('pi_events', original))
        self.assertEqual(layer['activities'][0]['role_projections'], self.cards[0]['role_projections'])
        self.assertEqual(layer['activities'][0]['time_role'], 'actual')
        self.assertEqual(layer['activities'][0]['dictionary_evidence'], ['Observed occurrence.'])
        self.assertEqual(layer['source_context_by_table'], {'tasks': ['Task execution table.']})

    def test_query_expands_relations_and_preserves_unresolved_or_collective_scope(self):
        """PURPOSE: Verify C retains linked EDs and falls back without enough evidence.
        INPUT: Specific, ungrounded and collective activity requests. OUTPUT: Expected candidate scopes.
        """
        delivery = EEGDelivery(self.graph, 'query', event_limit=1)
        result = delivery('pi_events', self.payload)
        self.assertEqual([card['id'] for card in result['activities']],
                         [self.cards[0]['id'], self.cards[1]['id']])
        self.assertEqual(delivery.audit[-1]['initial_search_ids'], [self.cards[0]['id']])
        for req, fallback in [
            ({'span': 'Unrepresented', 'meaning': 'Unrepresented', 'coverage': 'one'},
             'no_grounded_match_for_requirement'),
            ({'span': 'Purchase approval', 'meaning': 'Purchase approval', 'coverage': 'all'},
             'retain_complete_activity_family_scope'),
        ]:
            payload = dict(self.payload, activity_requirements=[dict(req, id='R1')])
            result = delivery('pi_events', payload)
            self.assertEqual([card['id'] for card in result['activities']], [card['id'] for card in self.cards])
            self.assertEqual(delivery.audit[-1]['fallback'], fallback)
