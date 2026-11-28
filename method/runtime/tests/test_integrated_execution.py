"""Acceptance tests for the integrated default CLI and verified PI closure."""

from copy import deepcopy
from csv import DictReader
from dataclasses import asdict
import json
import sys

import openai
import pytest

from src.__main__ import main, save_run
from src.eeg.eeg_store import EEGStore, write_index
from src.pipeline import run_pipeline
from src.step1_understand.eeg_configuration import DbuConfig
from src.step3_execute.materialize_extraction_specification import validate_physical_references
from src.step3_execute.verify_execution_dependencies import execution_dependencies
from test_pipeline_runtime import RequirementScenarioClient, ScriptedClient
from test_v2_occurrence_construction import history_fixture

ACTIVITY = 'Cabin cleaning Completed'
QUESTION = f'Extract {ACTIVITY} for each work.'


def explicit_parser(activity, case_span, case_meaning):
    """PURPOSE: Build a scripted parser that preserves request spans.
    INPUT: Activity label and Case span/meaning. OUTPUT: Test role responder.
    """
    def parse(payload):
        """PURPOSE: Return one exact activity requirement. INPUT: Request. OUTPUT: Parsed PI roles."""
        return {'activity_scope': 'explicit', 'process_focus': None,
                'case_requirement': {'span': case_span, 'meaning': case_meaning},
                'scope_requirement': {'span': payload['original_request'], 'object_scope': 'own', 'granularity': 'distinct'},
                'activity_requirements': [{'id': 'R1', 'span': activity, 'meaning': activity,
                                           'qualifiers': [], 'coverage': 'one', 'granularity': 'distinct'}]}
    return parse


def client_for(activity, case_span, case_meaning):
    """PURPOSE: Select a known activity and correct Case when both are visible.
    INPUT: Fixture labels. OUTPUT: Scripted role client exercising the real PI code.
    """
    def case(payload):
        """PURPOSE: Choose the required ET when present. INPUT: Case catalog. OUTPUT: One valid selection."""
        items = payload['entity_types']
        target = next((item for item in items if item['name'].casefold() == case_meaning.casefold()), items[0])
        return {'candidates': [{'et': target['id'], 'mode': 'explicit', 'focus': ''}]}

    def events(payload):
        """PURPOSE: Match the source-backed label. INPUT: Runtime candidates. OUTPUT: Requirement selection."""
        matches = [item['id'] for item in payload['activities'] if item['name'].casefold() == activity.casefold()]
        return {'matches': [{'requirement_id': 'R1', 'event_definition_ids': matches}] if matches else []}

    def review(payload):
        """PURPOSE: Check candidates independently. INPUT: PI verification packet. OUTPUT: Grounded test verdicts."""
        reply = {'differences': []}
        packet = payload.get('activity_review')
        if packet:
            selected = [item['id'] for item in packet['candidates'] if item['name'].casefold() == activity.casefold()]
            reply['requirement_reviews'] = [
                {'requirement_id': r['id'], 'event_definition_ids': selected, 'reason': 'Supported occurrence and source.',
                 'source_attribution_gap': False, 'semantic_status': 'matched' if selected else 'missing',
                 'reviewed_coverage': r['coverage'], 'reviewed_granularity': r['granularity'],
                 **({'exclusions': []} if packet.get('initial_proposals') else {})} for r in packet['requirements']]
        return reply

    return RequirementScenarioClient({'semantic_decomposer': explicit_parser(activity, case_span, case_meaning),
                                      'pi_cases': case, 'pi_events': events, 'pi_crosscheck': review})


@pytest.fixture
def relational_run(tmp_path):
    """PURPOSE: Produce real indexed relational extraction. INPUT: Isolated fixture path. OUTPUT: Complete receipt."""
    database, graph = history_fixture(tmp_path)
    index = tmp_path / 'index.sqlite'
    write_index(index, graph, 'relational')
    return run_pipeline(database, tmp_path / 'dictionary.json', QUESTION,
                        graph=EEGStore(index, 'relational'), client=client_for(ACTIVITY, 'each work', 'Work'))


def test_legacy_relational_cli_cold_and_warm(tmp_path, monkeypatch):
    """PURPOSE: Preserve legacy CLI acceptance through the explicit historical route.
    INPUT: Ordered history. OUTPUT: Two rows on both cold and warm requests.
    """
    database, _ = history_fixture(tmp_path)
    config = tmp_path / 'config.json'
    config.write_text(json.dumps(asdict(DbuConfig(repair=False, semantic_signatures=False,
                                                 global_ot_review=False, pairwise_identity_llm=False))))
    client = client_for(ACTIVITY, 'each work', 'Work')
    monkeypatch.setattr(openai, 'OpenAI', lambda: client)
    monkeypatch.setenv('NL2EL_EEG_CACHE_DIR', str(tmp_path / 'cache'))
    for name in ('cold', 'warm'):
        output = tmp_path / name
        monkeypatch.setattr(sys, 'argv', ['src', '--method', 'legacy', '--database', str(database), '--dictionary',
                            str(tmp_path / 'dictionary.json'), '--config', str(config),
                            '--question', QUESTION, '--output-dir', str(output)])
        assert main() == 0
        with (output / 'event_log.csv').open() as csv_file:
            assert [json.loads(row['source_record_id']) for row in DictReader(csv_file)] == [['2'], ['5']]
        run = json.loads((output / 'manifest.json').read_text())
        assert run['terminal_status'] == 'accepted'
        assert run['step3']['dependency_closure']['status'] == 'complete'
        assert run['measurements']['lookup']['records_read'] > 0
        assert run['measurements']['construction_usage']['calls'] == (1 if name == 'cold' else 0)


@pytest.mark.parametrize('mutation', ['predicate', 'definition_id'])
def test_relational_validation_rejects_modified_spec(relational_run, mutation):
    """PURPOSE: Protect source definitions after legacy expansion. INPUT: Mutated ESpec. OUTPUT: Rejection."""
    assert relational_run['terminal_status'] == 'accepted'
    graph, spec = relational_run['graph'], deepcopy(relational_run['es'])
    if mutation == 'definition_id':
        spec['event_rules'][0]['source_event_definition_id'] = 'E:not-in-eeg'
    else:
        source = next(iter(spec['event_sources'].values()))
        term = next(term for term in source['row_condition']['conditions'] if term['kind'] == 'related_value')
        term['value'] = 'R'
    checked = validate_physical_references(graph, spec)
    assert not checked['passed']
    assert any('relational predicate differs' in issue for issue in checked['issues'])


@pytest.mark.parametrize('mutation', ['inventory', 'one_path', 'table', 'occurrence_key', 'predicate', 'case', 'role'])
def test_ready_pi_fails_closed_on_missing_execution_evidence(relational_run, mutation):
    """PURPOSE: Check all required evidence. INPUT: Corruption after PI freeze. OUTPUT: Incomplete closure."""
    query, graph = deepcopy(relational_run['query']), deepcopy(relational_run['graph'])
    assert execution_dependencies(graph, query)['status'] == 'complete'
    info = query['process_information']
    target = info['selected_event_definition_ids'][0]
    path_id = info['verified_attribution_paths'][target][0]
    if mutation == 'inventory':
        info.pop('verified_attribution_paths')
        query['process_view']['process_information'].pop('verified_attribution_paths')
    elif mutation == 'one_path':
        graph['attribution_paths'] = [path for path in graph['attribution_paths'] if path['id'] != path_id]
    elif mutation == 'table':
        graph['tables'] = [table for table in graph['tables'] if table['name'] != 'work']
    elif mutation == 'case':
        info['case_notion_et_id'] = 'ET:incorrect'
    elif mutation == 'role':
        next(path for path in graph['attribution_paths'] if path['id'] == path_id)['case_role'] = {'role': 'invented'}
    else:
        ed = next(item for item in graph['event_definitions'] if item['id'] == target)
        if mutation == 'occurrence_key':
            ed.pop('source_row_key')
        else:
            ed['documented_source_conditions'].pop()
    assert execution_dependencies(graph, query)['status'] == 'incomplete'


def test_diagnostic_rows_are_not_published_as_completed_log(relational_run, tmp_path):
    """PURPOSE: Restrict accepted artifacts to verified success. INPUT: Failed receipt with diagnostic rows. OUTPUT: Diagnostic-only CSV."""
    result = deepcopy(relational_run)
    save_run(result, tmp_path)
    result.update(terminal_status='failed', diagnostic_execution=result['execution'], execution={})
    result['es']['status'] = 'validation_failed'
    save_run(result, tmp_path)
    assert not (tmp_path / 'event_log.csv').exists()
    assert not (tmp_path / 'extraction.sql').exists()
    assert (tmp_path / 'diagnostic' / 'rows.csv').is_file()


def test_case_alias_can_expand_to_another_et(tmp_path):
    """PURPOSE: Retest Case after a provisional prefix conflicts with activity evidence.
    INPUT: Order prefix, separate Archive event; OUTPUT: Successful second Case and distinct expansion receipt.
    """
    from validation.offline_v2 import TokenCountingClient, create_fixture
    from src.step1_understand.pipeline import build_evidence_graph
    from src.step1_understand.project_runtime_evidence_graph import to_runtime_graph

    database, dd, *_ = create_fixture(tmp_path, 1, 0)
    config = DbuConfig(repair=False, semantic_signatures=False, global_ot_review=False, pairwise_identity_llm=False)
    graph = to_runtime_graph(build_evidence_graph(database, dd, config, TokenCountingClient()), database)
    index = tmp_path / 'index.sqlite'
    write_index(index, graph, 'case-conflict')
    activity, span = 'archive 0 registration', 'each order exception'
    client = client_for(activity, span, 'Archive')
    result = run_pipeline(database, dd, f'Extract {activity} for {span}.', graph=EEGStore(index, 'case-conflict'),
                          client=client, recovery_enabled=False, evidence_retrieval=False)
    assert result['terminal_status'] == 'accepted', result['query']['process_view_termination_reason']
    assert result['manifest']['measurements']['lookup']['expanded_other_cases']
    assert {row['source_table'] for row in result['execution']['event_log']} == {'archive_0'}


def test_multihop_occurrence_context_and_ambiguous_fk(tmp_path):
    """PURPOSE: Validate finite declared lookup chains as one predicate.
    INPUT: A clock anchor, two FK hops and an optional duplicate path. OUTPUT: Exact lineage or explicit rejection.
    """
    from src.step1_understand.discover_state_history import _context_selector
    from src.common.database_io import load_inputs
    from test_v2_occurrence_construction import build
    from contextlib import closing
    from src.common.database_io import connect_readonly

    definition = {
        'kinds': {'columns': {'label': {'definition': 'Business activity name.'}}},
        'links': {'columns': {'kind_id': {'definition': 'Type code of the business operation.'}}},
        'actions': {'readable_name': 'Action', 'definition': 'One action business entity.',
                    'columns': {'link_id': {'definition': 'Context link for the action.'}}},
        'ticks': {'definition': 'One row per actual occurrence.',
                  'related_occurrence': {'occurrence_column': 'occurred_at',
                        'carrier': {'path': [['action_id'], ['link_id']], 'column': 'kind_id'}},
                  'columns': {'occurred_at': {'definition': 'Time of the physical action.'}}}}
    ddl = """
        CREATE TABLE kinds(code TEXT PRIMARY KEY NOT NULL, label TEXT);
        CREATE TABLE links(id INTEGER PRIMARY KEY, kind_id TEXT REFERENCES kinds(code));
        CREATE TABLE actions(id INTEGER PRIMARY KEY, link_id INTEGER REFERENCES links(id));
        CREATE TABLE ticks(id INTEGER PRIMARY KEY, occurred_at TEXT,
                           action_id INTEGER REFERENCES actions(id));
        INSERT INTO kinds VALUES ('I', 'Inspection'), ('S', 'Sealing');
        INSERT INTO links VALUES (1, 'I'), (2, 'S');
        INSERT INTO actions VALUES (1,1), (2,2);
        INSERT INTO ticks VALUES (1, '2025-06-01T01:00:00Z', 1), (2, '2025-06-01T02:00:00Z', 2);
    """
    database, graph = build(tmp_path, ddl, definition)
    expected = [ed for ed in graph['event_definitions'] if ed['source_table'] == 'ticks'
                and ed['activity_label'] == 'Inspection']
    assert len(expected) == 1 and len(expected[0]['documented_source_conditions'][0]['joins']) == 2
    index = tmp_path / 'multihop.sqlite'
    write_index(index, graph, 'multihop')
    result = run_pipeline(database, tmp_path / 'dictionary.json', 'Extract Inspection for each action.',
                          graph=EEGStore(index, 'multihop'), client=client_for('Inspection', 'each action', 'Action'))
    assert result['terminal_status'] == 'accepted', (result['query']['process_view_termination_reason'], result['manifest']['step3'])
    assert [json.loads(row['source_record_id']) for row in result['execution']['event_log']] == [['1']]
    executable = deepcopy(result['graph'])
    assert 'links' in {t['name'] for t in executable['tables']}
    executable['relationships'] = [edge for edge in executable['relationships']
                                   if not (edge['left_table'] == 'actions' and edge['right_table'] == 'links')]
    assert execution_dependencies(executable, result['query'])['status'] == 'incomplete'

    # The context selector must abstain when the same source column names two declared targets.
    ambiguous = tmp_path / 'ambiguous'
    ambiguous.mkdir()
    altered = ddl.replace('action_id INTEGER REFERENCES actions(id)', 
        'action_id INTEGER REFERENCES actions(id), FOREIGN KEY(action_id) REFERENCES links(id)')
    db_ambiguous, _ = build(ambiguous, altered, definition)
    schemas, _, _ = load_inputs(db_ambiguous, ambiguous / 'dictionary.json')
    schemas = {schema.name: schema for schema in schemas}
    selector = definition['ticks']['related_occurrence']['carrier']
    with closing(connect_readonly(db_ambiguous)) as connection:
        assert _context_selector(connection, schemas['ticks'], selector, schemas) is None


def test_espec_v4_v5_v6_extract_the_same_source_occurrences(relational_run):
    """PURPOSE: Verify reader compatibility through SQL execution.
    INPUT: Equivalent v4 expansion and v5/v6 specs. OUTPUT: Identical Case, source, and timestamp tuples.
    """
    from src.step3_execute.compile_event_log_sql import downgrade_es_v5_to_v4, extract_event_log

    es = relational_run['es']
    database = relational_run['graph']['database']
    legacy_v5 = {**es, 'es_version': 5,
                 'case': {key: value for key, value in es['case'].items() if key != 'population'}}
    for spec in (legacy_v5, es):
        expanded = downgrade_es_v5_to_v4(spec)
        _, original, _ = extract_event_log(database, spec)
        _, round_trip, _ = extract_event_log(database, expanded)
        fields = ('case_id', 'source_record_id', 'source_occurrence_id', 'timestamp')
        assert [tuple(row[key] for key in fields) for row in original] == [
            tuple(row[key] for key in fields) for row in round_trip]
        assert [json.loads(row['source_record_id']) for row in original] == [['2'], ['5']]


def test_source_audit_distinguishes_representation_and_path_gaps(tmp_path):
    """PURPOSE: Keep source-backed ER and projected-path loss visible.
    INPUT: Valid constructed EEG with removed runtime records. OUTPUT: Distinct audit findings.
    """
    from src.step1_understand.source_coverage import source_coverage
    _, graph = history_fixture(tmp_path)
    original = graph['dbu_rewrite']
    claims = original['source_coverage_claims']
    reduced = {**graph, 'entity_types': [], 'attribution_paths': []}
    audit = source_coverage(claims, original, reduced)
    statuses = {item['status'] for item in audit['gaps']}
    assert {'key_without_verified_entity_representation', 'verified_path_not_projected'} <= statuses


def test_context_review_cannot_bypass_request_budget():
    """PURPOSE: Charge the direct review path to the same PI budget.
    INPUT: Exhausted budget and a contextual review packet. OUTPUT: No SDK request and explicit reason.
    """
    from src.common.event_definition_eligibility import review_once
    from src.step2_retrieve_and_interpret.execute_model_roles import PIRequestBudget
    client = ScriptedClient()
    budget = client.pi_request_budget = PIRequestBudget(1, 100000)
    budget.reserve(100)
    results, audit = review_once('tier2_context', {'entity_type': {'id': 'ET:synthetic'},
                                                   'definitions': []}, client, 'gpt-4o-mini')
    assert not results and not client.calls
    assert budget.exhausted == 'pi_call_budget_exhausted'
    assert any(budget.exhausted in error for error in audit['errors'])


def test_unanchored_implicit_history_defers_details_until_case_proposal(tmp_path):
    """PURPOSE: Recover Case and eligible occurrences when both are implicit.
    INPUT: Unanchored whole-history request. OUTPUT: Case-first lookup and all related events.
    """
    from test_v2_index_and_recovery import fixture
    database, dd, config, graph = fixture(tmp_path)
    path = tmp_path / 'implicit.sqlite'
    write_index(path, graph, 'implicit')
    question = 'Show the full sequence.'

    def parse(payload):
        """PURPOSE: Preserve the history request without inventing a named ET.
        INPUT: Original request. OUTPUT: Implicit mode and the verbatim contextual span.
        """
        return {'activity_scope': 'implicit', 'case_requirement': {'span': 'the full sequence', 'meaning': 'Determine the relevant Case'},
                'scope_requirement': {'span': payload['original_request'], 'object_scope': 'attributable_history',
                                      'granularity': 'coarse'},
                'activity_requirements': [], 'process_focus': None}

    def case(payload):
        """PURPOSE: Select the ET from its own evidence. INPUT: Case cards. OUTPUT: Proposed implicit Case."""
        orders = next(et for et in payload['entity_types'] if et['name'].casefold() == 'order')
        return {'candidates': [{'et': orders['id'], 'mode': 'implicit', 'focus': ''}]}

    def check(_):
        """PURPOSE: Confirm the unambiguous fixture interpretation.
        INPUT: Independent review payload. OUTPUT: No structural or applicability differences.
        """
        return {'differences': []}

    client = RequirementScenarioClient({'semantic_decomposer': parse, 'pi_cases': case, 'pi_crosscheck': check})
    result = run_pipeline(database, dd, question, graph=EEGStore(path, 'implicit'), config=config, client=client)
    assert result['terminal_status'] == 'accepted', result['query']['process_view_termination_reason']
    assert result['manifest']['measurements']['lookup']['case_deferred']
    assert {row['activity'] for row in result['execution']['event_log']} == {'Approved'}
    assert len(result['execution']['event_log']) == 2
