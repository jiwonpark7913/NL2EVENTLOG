"""Regression guards for generic role scope, attribution and event granularity."""

from copy import deepcopy
import unittest

from src.common.attribution_policy import attribution_adjacency, documented_reference_roles
from src.common.entity_population import validate_population
from src.step2_retrieve_and_interpret.event_definition_granularity import choose_event_granularity, definition_subsumption
from src.step2_retrieve_and_interpret.verify_activity_requirements import verify_activity


class RoleAndGranularityGuards(unittest.TestCase):
    """Exercise role and ED selection without dataset-specific vocabulary."""

    def test_reference_roles_require_distinct_public_documentation(self):
        """PURPOSE: Discover more than two documented sibling roles.
        INPUT: Three distinct named references and their public descriptions.
        OUTPUT: Three roles with separate alternatives, or none with incomplete evidence.
        """
        roles = ('consignor', 'consignee', 'auditor')
        refs = [{'id': role, 'kind': 'declared', 'child_table': 'dispatch', 'parent_table': 'party',
                 'columns': [[role + '_id', 'id']], 'child_key_unique': True} for role in roles]
        dd = {'columns': [{'id': role, 'table': 'dispatch', 'column': role + '_id',
                           'definition': role.title() + ' party for the dispatch.'} for role in roles]}
        result = documented_reference_roles(attribution_adjacency(refs), dd)
        self.assertEqual(set(result), set(roles))
        self.assertEqual({e['relationship_id'] for e in result['auditor']['alternatives']},
                         {'consignor','consignee'})
        dd['columns'].pop()
        self.assertEqual(documented_reference_roles(attribution_adjacency(refs), dd), {})

    def test_roleless_or_foreign_path_cannot_certify_a_log(self):
        """PURPOSE: Keep competing roles fail-closed until a request-grounded witness is selected.
        INPUT: Two real paths and attempted unknown, swapped and verified references.
        OUTPUT: Only one compatible path is certified for the ED.
        """
        def path(role):
            """PURPOSE: Build role evidence. INPUT: Role label. OUTPUT: Minimal verified path."""
            return {'id': role + '_path', 'role_validation': {'status': 'pass', 'reference': {'role': role}}}

        catalog = {'inspection': {'eligible':True, 'binding_policy':{'checks':{}}, 'attribution':{
            'status':'pass', 'paths':[path('consignor'),path('consignee')]}}}
        request = {'coverage':'one','qualifiers':[]}
        review = {'event_definition_ids':['inspection'],'semantic_status':'matched',
                  'source_attribution_gap':False,'reason':'The reported clock matches.'}
        self.assertEqual(verify_activity(request,review,catalog,catalog)['status'],'unresolved')
        for choice in ('fabricated_path', 'consignor_path'):
            qualified = dict(request,qualifiers=['consignee'])
            reply = dict(review,role_path_choices=[{'event_definition_id':'inspection','path_id':choice}])
            self.assertEqual(verify_activity(qualified,reply,catalog,catalog)['status'],'unresolved')
        reply = dict(review,role_path_choices=[{'event_definition_id':'inspection','path_id':'consignee_path'}])
        accepted = verify_activity(dict(request,qualifiers=['consignee']),reply,catalog,catalog)
        self.assertEqual(accepted['definition_path_ids'],{'inspection':['consignee_path']})

    def test_independent_review_can_restore_a_grounded_family_member(self):
        """PURPOSE: Recover a documented occurrence omitted by a narrower first selection.
        INPUT: Two semantic matches and one initial ED, plus an invalid-path control.
        OUTPUT: The corrected activity family and bounded, auditable additions.
        """
        catalog = {eid:{'eligible':True,'binding_policy':{'checks':{}},
                      'attribution':{'status':'pass','paths':[{'id':'path-'+eid}]}}
                   for eid in ('opened','released')}
        parsed = {'id':'R1','span':'processing milestones','coverage':'one','granularity':'coarse','qualifiers':[]}
        review = {'event_definition_ids':list(catalog), 'semantic_status':'matched',
                  'reviewed_coverage':'all','reviewed_granularity':'coarse',
                  'source_attribution_gap':False,'reason':'The request includes both documented phases.'}
        verified = verify_activity(parsed,review,catalog,['opened'],verified_review_selection=True)
        self.assertEqual(verified['event_definition_ids'],['opened','released'])
        self.assertEqual(verified['added_by_independent_review'],['released'])
        self.assertEqual(verified['parsed_scope']['coverage'],'one')
        catalog['released']['attribution']['status']='fail'
        invalid = verify_activity(parsed,review,catalog,['opened'],verified_review_selection=True)
        self.assertEqual(invalid['status'],'unresolved')
        self.assertEqual(invalid['added_by_independent_review'],[])

    def test_review_exclusions_require_relevant_ids_and_literal_evidence(self):
        """PURPOSE: Admit grounded phase exclusions and guard explicit family coverage.
        INPUT: Initial start/completion proposals and valid, fabricated, and narrowing reviews.
        OUTPUT: Correct single activity or a requirement flagged for revision.
        """
        question = 'Include completion of inspection and packing.'
        clause = 'completion of inspection and packing'
        catalog = {eid: {'eligible': True, 'binding_policy': {'checks': {}},
                         'attribution': {'status': 'pass', 'paths': [{'id': eid}]}}
                   for eid in ('start', 'completed')}
        req = {'id': 'R1', 'span': clause, 'qualifiers': [], 'coverage': 'one'}
        exclusion = {'event_definition_id': 'start', 'kind': 'wrong_phase',
                     'span': clause, 'reason': 'The clause requests completion of packing.'}
        review = {'event_definition_ids': ['completed'], 'semantic_status': 'matched',
                  'source_attribution_gap': False, 'reason': 'The completion clock is recorded.',
                  'reviewed_coverage': 'one', 'exclusions': [exclusion]}

        accepted = verify_activity(req, review, catalog, catalog, question=question, initial_ids=catalog)
        self.assertEqual(accepted['event_definition_ids'], ['completed'])

        narrowed = verify_activity(dict(req, coverage='all'), review, catalog, catalog,
                                   question=question, initial_ids=catalog)
        self.assertIn('requested_family_coverage_narrowed', narrowed['reason_codes'])
        self.assertEqual(narrowed['event_definition_ids'], [])

        for change in ({'span': 'completion of packing'}, {'event_definition_id': 'completed'},
                       {'kind': 'duplicate_occurrence'}):
            with self.subTest(change=change):
                bad = dict(review, exclusions=[dict(exclusion, **change)])
                result = verify_activity(req, bad, catalog, catalog, question=question, initial_ids=catalog)
                self.assertIn('initial_selection_exclusion_unverified', result['reason_codes'])
                self.assertEqual(result['event_definition_ids'], [])

    def test_unrestricted_case_population_cannot_replace_frozen_subset(self):
        """PURPOSE: Guard against dropping case scope at materialization or repair.
        INPUT: A valid case ET, scoped frozen PI, then all_cases as a mutant.
        OUTPUT: Exact scope passes and unrestricted replacement fails.
        """
        edge = {'relationship_id':'scope', 'direction':'parent_to_child',
                'left_table':'party','left_columns':['id'],'right_table':'dispatch','right_columns':['receiver'],
                'child_key_unique':True, 'declared':True, 'cardinality':'1:1'}
        scope = {'kind':'reference_role','step':edge,'role':'receiver'}
        member = {'id':'member','representation_id':'key','table':'party','key_columns':['id'],
                  'entity_type_id':'ET:party','identity_scope_id':'party','mapping_kind':'direct_key',
                  'scope':'all_rows','validation':{'status':'pass'}}
        population = {'entity_type_id':'ET:party','status':'valid','maps':[member], 'selection_independent':True}
        es = {'es_version':6, 'case':{'entity_type_id':'ET:party','population':population},
              'case_selection':scope,'process_view':{'process_information':{'case_scope':scope}}}
        self.assertEqual(validate_population(es)['contract_status'],'pass')
        mutant = deepcopy(es)
        mutant['case_selection'] = {'kind':'all_cases'}
        self.assertIn('Case selection differs from the frozen PI role scope',validate_population(mutant)['issues'])

    def test_subsumption_respects_source_key_phase_and_row_predicate(self):
        """PURPOSE: Prove inclusion from physical occurrence and predicate implication.
        INPUT: Broad and narrow filters plus controls with mismatched key and phase.
        OUTPUT: Only the true specialization can be collapsed or chosen as a distinct type.
        """
        base = {'source_table':'observations', 'occurrence_time_source':{'columns':['at']},
                'source_row_key':['id'],'occurrence_identity_status':'supported','source_kind':'row_activity',
                'timestamp_pairing':{'phase':'complete'}}
        definitions = {
            'broad':dict(base,row_selection={'kind':'in','column':'code','values':['A','B']}),
            'narrow':dict(base,row_selection={'kind':'equals','column':'code','value':'A'}),
            'other':dict(base,row_selection={'kind':'equals','column':'code','value':'C'}),
            'phase':dict(base,row_selection={'kind':'equals','column':'code','value':'A'},
                         timestamp_pairing={'phase':'start'}),
            'key':dict(base,row_selection={'kind':'equals','column':'code','value':'A'},source_row_key=['other_id']),
        }
        self.assertEqual(definition_subsumption(definitions,definitions),{'broad':{'narrow'}})
        self.assertEqual(choose_event_granularity(['broad','narrow'],definitions,'coarse'),['broad'])
        self.assertEqual(choose_event_granularity(['broad','narrow'],definitions,'distinct'),['narrow'])


if __name__ == '__main__':
    unittest.main()
