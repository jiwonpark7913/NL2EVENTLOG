"""End-to-end development checks for source verification and three-stage boundaries."""

from copy import deepcopy
import json

from src.eeg.eeg_store import EEGStore, write_index
from src.pipeline import run_pipeline
from src.step1_understand.source_coverage import source_coverage
from src.step3_execute.verify_execution_dependencies import execution_dependencies
from test_pipeline_runtime import RequirementScenarioClient, ScriptedClient
from test_v2_index_and_recovery import event_contract, fixture
from test_v2_occurrence_construction import history_fixture


def test_backward_audit_detects_deleted_claim_projection(tmp_path):
    """PURPOSE: Detect source-supported evidence independently of candidate-accounting success.
    INPUT: Documented source inventory and a graph with a reported source fact removed.
    OUTPUT: The source claim remains and the missing projection is diagnosed.
    """
    _, graph = history_fixture(tmp_path)
    native = graph['dbu_rewrite']
    assert native['source_coverage_claims']
    broken = dict(native, timestamps=[])
    audit = source_coverage(native['source_coverage_claims'], broken, graph)
    assert any(item['status'] == 'clock_discovery_gap' for item in audit['gaps'])
    assert 'clock' in audit['counts']


def test_execute_requires_every_frozen_pi_attribution(tmp_path):
    """PURPOSE: Refuse to materialize an ED when one approved complementary path is absent.
    INPUT: Successful indexed request and its scoped projection with a missing path.
    OUTPUT: Explicit missing-path receipt and three conceptual manifest stages.
    """
    database, dd, config, graph = fixture(tmp_path)
    index = tmp_path / 'final.sqlite'
    write_index(index, graph, 'final')
    result = run_pipeline(database, dd, 'Extract Approved for each order.', graph=EEGStore(index, 'final'),
                          client=ScriptedClient(), config=config, evidence_retrieval=False, recovery_enabled=False)
    manifest = result['manifest']
    assert set(k for k in manifest if k.startswith('step')) == {'step1', 'step2', 'step3'}
    assert manifest['step3']['dependency_closure']['status'] == 'complete'
    information = result['query']['process_information']
    event = information['selected_event_definition_ids'][0]
    query = deepcopy(result['query'])
    query['process_information']['verified_attribution_paths'][event].append('AP:absent')
    report = execution_dependencies(result['graph'], query)
    assert report['status'] == 'incomplete'
    assert any(item.get('id') == 'AP:absent' for item in report['missing'])
    assert len(event_contract(result)) == 2


def unified_reply(payload):
    """PURPOSE: Jointly interpret the same documented order approval requirement in one scripted response.
    INPUT: Canonical request and compact EEG catalog. OUTPUT: Unified PI schema keys.
    """
    case = next(item['id'] for item in payload['entity_types'] if item['name'] == 'Order')
    activity = next(item['id'] for item in payload['activities'] if item['name'] == 'Approved')
    return {'case_et_id': case, 'case_span': 'each order', 'case_scope_id': '', 'process_focus': '',
            'request_mode': 'explicit', 'object_scope': 'own', 'unresolved_requirements': [],
            'selections': [{'span': 'Approved', 'activities': [{'activity_id': activity, 'role': 'direct'}]}]}


def test_unified_parser_ablation_preserves_output_and_independent_review(tmp_path):
    """PURPOSE: Isolate joint interpretation against the sequential parser on the same EEG.
    INPUT: Documented synthetic order approval. OUTPUT: Identical extraction and fewer scripted PI calls.
    """
    database, dd, config, graph = fixture(tmp_path)
    question = 'Extract Approved for each order.'
    clients = {'sequential': ScriptedClient(), 'unified': RequirementScenarioClient({'pi_unified': unified_reply})}
    arms = {mode: run_pipeline(database, dd, question, graph=graph, client=client, config=config,
                              recovery_enabled=False, evidence_retrieval=False, pi_mode=mode)
            for mode, client in clients.items()}
    assert {arm['es']['status'] for arm in arms.values()} == {'accepted'}, {
        mode: arm['query'].get('termination_reason') for mode, arm in arms.items()}
    assert event_contract(arms['sequential']) == event_contract(arms['unified'])
    roles = {mode: [call['response_format']['json_schema']['name'] for call in client.calls]
             for mode, client in clients.items()}
    assert 'semantic_decomposer' in roles['sequential']
    assert 'semantic_decomposer' not in roles['unified']
    assert 'pi_crosscheck' in roles['unified']
    assert len(roles['unified']) < len(roles['sequential'])


def test_progressive_lookup_expands_from_requirement_spans(tmp_path):
    """PURPOSE: Discover a Case outside the initial scope using a partial requirement's literal ED alias.
    INPUT: Indexed canonical EEG, narrowed provisional Case scope and verbatim span.
    OUTPUT: Graph expansion with the matching ET, full family inventory and no model calls.
    """
    database, _, _, graph = fixture(tmp_path)
    index = tmp_path / 'progressive.sqlite'
    write_index(index, graph, 'progressive')
    with EEGStore(index, 'progressive').open(database) as lookup:
        provisional = lookup.case_graph([])
        result, receipt = lookup.expand_requirements(provisional, ['include Approved items'])
        assert receipt['status'] == 'expanded'
        assert any(event['activity_label'] == 'Approved' for event in result['event_definitions'])


def test_source_audit_rechecks_pair_missing_from_original_enumeration(tmp_path):
    """PURPOSE: Recover a source-proved pair before attribution without invoking a model.
    INPUT: Documented code/clock source and a simulated missing pair in the original matrix.
    OUTPUT: Deterministically restored ED and explicit recheck receipt.
    """
    from src.step1_understand.classify_table_event_sources import classify_tables
    from src.step1_understand.eeg_configuration import DbuConfig
    from src.step1_understand.pipeline import load_inputs
    from src.step1_understand.profile_table_values import profile_tables
    from src.step1_understand.source_coverage import reconsider_missing_pairs
    from test_v2_occurrence_construction import build

    database, graph = build(tmp_path, """
        CREATE TABLE jobs(key INTEGER PRIMARY KEY, code TEXT NOT NULL, completed_at TEXT);
        INSERT INTO jobs VALUES (1, 'I', '2025-03-01 11:00:00');
        """, {'jobs': {'definition': 'One job operation per row.', 'columns': {
            'code': {'definition': 'Code for the physical activity.', 'value_domain': {'I': 'Inspection'}},
            'completed_at': {'definition': 'Time of the physical action.'}}}})
    tables, dictionary, _ = load_inputs(database, tmp_path / 'dictionary.json')
    native = graph['dbu_rewrite']
    expected, = [claim for claim in native['source_coverage_claims'] if claim['kind'] == 'carrier_event']
    times = native['timestamps']
    config = DbuConfig()
    profiles = profile_tables(database, tables, config.sample_size)
    states = classify_tables(tables, times, dictionary)
    bindings, traces, receipt = reconsider_missing_pairs(
        database, tables, profiles, dictionary, times, states, config,
        [expected], [], {'jobs': {'carrier_timestamp_matrix': []}})
    assert len(bindings) == 1 and bindings[0]['interpretation_status'] == 'supported'
    assert traces['jobs']['carrier_timestamp_matrix'][0]['value'] == 'I'
    assert receipt[0]['added_definition_ids'] == [bindings[0]['id']]


def test_pi_request_budget_stops_before_an_extra_call(tmp_path):
    """PURPOSE: Stop PI at the request budget without approving a partial extraction.
    INPUT: Existing approval EEG and one-call allowance. OUTPUT: One actual call and unresolved status.
    """
    database, dd, config, graph = fixture(tmp_path)
    client = ScriptedClient()
    result = run_pipeline(database, dd, 'Extract Approved for each order.', graph=graph, client=client,
                          config=config, evidence_retrieval=False, recovery_enabled=False, max_pi_calls=1)
    assert len(client.calls) == 1
    assert result['manifest']['step2']['request_budget']['exhausted'] == 'pi_call_budget_exhausted'
    assert result['query']['status'] != 'ready'
    assert not result['execution']


def test_paired_pi_controls_use_same_index_and_review(tmp_path):
    """PURPOSE: Check paired controls end to end for named activities and implicit history.
    INPUT: Separate development fixture, shared index, scripted independent replies.
    OUTPUT: Equal initial inventories and logs with the expected architecture-specific model roles.
    """
    database, dd, config, graph = fixture(tmp_path)
    index = tmp_path / 'paired-architecture.sqlite'
    write_index(index, graph, 'paired-architecture')
    shared = EEGStore(index, 'paired-architecture')

    def parse(payload):
        """PURPOSE: Preserve an implicit Case and activity scope.
        INPUT: Original request payload. OUTPUT: Verbatim requirement and whole-history scope.
        """
        return {'activity_scope': 'implicit',
                'case_requirement': {'span': 'the full sequence', 'meaning': 'Determine the relevant Case'},
                'scope_requirement': {'span': payload['original_request'],
                                      'object_scope': 'attributable_history', 'granularity': 'coarse'},
                'activity_requirements': [], 'process_focus': None}

    def case(payload):
        """PURPOSE: Propose the fixture Case. INPUT: Entity cards. OUTPUT: Order Case in implicit mode."""
        order = next(et for et in payload['entity_types'] if et['name'].casefold() == 'order')
        return {'candidates': [{'et': order['id'], 'mode': 'implicit', 'focus': ''}]}

    def joint_history(payload):
        """PURPOSE: Propose the equivalent whole history jointly.
        INPUT: Joint EEG catalog. OUTPUT: Case, scope and implicit activity mode.
        """
        order = next(et for et in payload['entity_types'] if et['name'].casefold() == 'order')
        return {'case_et_id': order['id'], 'case_span': 'the full sequence', 'case_scope_id': '',
                'process_focus': '', 'request_mode': 'implicit', 'object_scope': 'attributable_history',
                'unresolved_requirements': [], 'selections': []}

    def check(_):
        """PURPOSE: Verify the fixture independently. INPUT: Review payload. OUTPUT: No differences."""
        return {'differences': []}

    conditions = [
        ('Extract Approved for each order.', ScriptedClient(),
         RequirementScenarioClient({'pi_unified': unified_reply})),
        ('Show the full sequence.',
         RequirementScenarioClient({'semantic_decomposer': parse, 'pi_cases': case, 'pi_crosscheck': check}),
         RequirementScenarioClient({'pi_unified': joint_history, 'pi_crosscheck': check})),
    ]
    for question, sequential, unified in conditions:
        arms = {mode: run_pipeline(database, dd, question, graph=shared, client=client, config=config,
                                  response_cache={}, pi_mode=mode, paired_pi_controls=True)
                for mode, client in {'sequential': sequential, 'unified': unified}.items()}
        assert {arm['terminal_status'] for arm in arms.values()} == {'accepted'}, {
            mode: arm['query'].get('process_view_termination_reason') for mode, arm in arms.items()}
        assert event_contract(arms['sequential']) == event_contract(arms['unified'])
        assert len(event_contract(arms['sequential'])) == 2
        lookups = [arm['manifest']['measurements']['lookup'] for arm in arms.values()]
        assert lookups[0]['initial_inventory_sha256'] == lookups[1]['initial_inventory_sha256']
        assert not any(lookup.get('case_deferred') for lookup in lookups)
        roles = [[call['response_format']['json_schema']['name'] for call in client.calls]
                 for client in (sequential, unified)]
        assert 'semantic_decomposer' in roles[0] and 'pi_unified' in roles[1]
        assert all('pi_crosscheck' in calls for calls in roles)
