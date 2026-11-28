"""Sequential semantic interpretation plus a strictly structural extraction boundary."""

from collections import defaultdict
from copy import deepcopy
from time import perf_counter

from src.common.graph_identifiers import content_hash
from src.common.schema_metadata import stable_id
from src.common.llm_usage import DEFAULT_MODEL, MeteredClient
from src.common.runtime_input_contract import require_public_path, validate_runtime_graph
from src.eeg.eeg_store import EEGStore
from src.step2_retrieve_and_interpret.execute_model_roles import PIRequestBudget, call_role
from src.step2_retrieve_and_interpret.minimal_evidence import case_evidence, make_evidence
from src.step2_retrieve_and_interpret.resolve_history_attribution import verify_explicit_path_unions
from src.step3_execute.materialize_extraction_specification import materialize_pi_selection
from src.step3_execute.pipeline import compact_repair_result, run_repair_pipeline
from src.step3_execute.verify_execution_dependencies import (
    bound_execution_dependencies, CONTRACT_VERSION, freeze_execution_contract,
)

INVENTORY = ('entity_types', 'event_definitions', 'attribution_paths', 'event_families')


def model_call(role, payload, client, model, audits):
    """PURPOSE: Make one logical structured role call. INPUT: Public evidence, role schema and metered client.
    OUTPUT: Parsed model response. The unchanged adapter may retry a technical transport or format failure.
    """
    reply, _ = call_role(role, payload, client, model, few_shot=False, audit_sink=audits)
    return reply


def select_initial(question, intent, evidence, client, model, audits, checkpoint):
    """PURPOSE: Select Case before EDs and paths. INPUT: Original request, intent and retrieved cards.
    OUTPUT: One shared Initial PI, including a typed insufficient-evidence outcome.
    """
    common = {'original_request': question, 'intent': intent}
    candidates = [{'id': card['id'], 'activity': card['activity'],
                   'available_cases': sorted({p['case_et_id'] for p in card['paths']})}
                  for card in evidence['events']]
    case = model_call('minimal_case', {**common, 'cases': evidence['cases'], 'activity_index': candidates},
                      client, model, audits)
    checkpoint('case', case)
    selected_case = next((item for item in evidence['cases'] if item['id'] == case['case_et_id']), None)
    if case['selection_status'] != 'selected' or selected_case is None:
        return {**case, 'events': []}
    scope = case['case_scope_id']
    if scope and scope not in {option['id'] for option in selected_case['scopes']}:
        return {**case, 'events': []}
    focused = case_evidence(evidence, case['case_et_id'])
    events = model_call('minimal_events', {**common, 'case': case, 'case_evidence': selected_case, 'events': focused},
                        client, model, audits)
    return {**case, **events}


def structural_view(evidence, scopes, plan, activity_mode):
    """PURPOSE: Resolve the model's claimed IDs against the same retrieved evidence.
    INPUT: Immutable evidence, declared scope options and proposed PI. OUTPUT: Fixed view or concrete structural issues.
    """
    if plan['selection_status'] == 'insufficient_evidence':
        return None, [{'kind': 'model_reported_insufficient_evidence', 'reason': plan['reason']}]
    case = plan['case_et_id']
    scope_id = plan['case_scope_id']
    if case not in scopes:
        return None, [{'kind': 'unavailable_case', 'id': case}]
    if scope_id and scope_id not in scopes[case]:
        return None, [{'kind': 'unavailable_population_scope', 'id': scope_id}]
    offered = {(row['id'], path['id']) for row in case_evidence(evidence, case) for path in row['paths']}
    selected = defaultdict(set)
    issues = []
    for event in plan['events']:
        identifier, path = event['event_definition_id'], event['path_id']
        if (identifier, path) not in offered:
            issues.append({'kind': 'unavailable_event_attribution', 'event': identifier, 'path': path})
        else:
            selected[identifier].add(path)
    if not plan['events']:
        issues.append({'kind': 'empty_event_selection'})
    if issues:
        return None, issues
    paths = {identifier: sorted(ids) for identifier, ids in sorted(selected.items())}
    info = {'case_notion_et_id': case, 'case_scope': scopes[case].get(scope_id),
            'request_mode': activity_mode, 'selected_event_definition_ids': sorted(paths),
            'verified_attribution_paths': paths}
    return {'target_ot_id': case, 'event_definitions': sorted(paths), 'activity_scope': activity_mode,
            'process_information': info}, []


def execute_selection(database, lookup, projection, evidence, scopes, question, intent, plan):
    """PURPOSE: Validate real dependencies, hydrate selected facts and execute existing Step 3/4.
    INPUT: EEG lookup, shared projection, intent and model selection. OUTPUT: Scorer-compatible receipt with diagnostics.
    """
    started = perf_counter()
    outcome = {'sql': None, 'rows': [], 'source_format': 'nl2eventlog_compiler_v1',
               'proposed_pi': plan, 'pi': None}
    view, issues = structural_view(evidence, scopes, plan, intent['activity_mode'])
    if issues:
        return {**outcome, 'status': 'unresolved', 'reason': 'unbound_selection', 'structural': issues,
                'execution_seconds': perf_counter() - started}
    info = view['process_information']
    paths = {identifier for group in info['verified_attribution_paths'].values() for identifier in group}
    executable = lookup.case_graph([info['case_notion_et_id']], event_ids=info['selected_event_definition_ids'],
                                   path_ids=paths)
    target = next((entity for entity in projection['entity_types'] if entity['id'] == info['case_notion_et_id']), {})
    view['entity_population_contract'] = target.get('population')
    binding = {'process_information': info, 'process_view': view, 'pi_contract_version': CONTRACT_VERSION}
    binding['execution_contract'] = freeze_execution_contract(projection, binding)
    checked = bound_execution_dependencies(executable, binding)
    if checked['missing']:
        return {**outcome, 'status': 'unresolved', 'reason': 'missing_execution_dependencies',
                'structural': checked['missing'], 'execution_seconds': perf_counter() - started}
    unions = verify_explicit_path_unions(executable, database, info)
    conflicts = {event: receipt for event, receipt in unions.items() if receipt['status'] != 'pass'}
    if conflicts:
        return {**outcome, 'status': 'unresolved', 'reason': 'conflicting_attribution_union',
                'structural': conflicts, 'execution_seconds': perf_counter() - started}
    partitions = {event: receipt['partition'] for event, receipt in unions.items() if receipt.get('partition')}
    if partitions:
        info['verified_attribution_partitions'] = partitions
    # Multiple proofs can agree on this frozen database without changing event multiplicity.
    # A single proof covers the union exactly when its cardinality equals the verified union.
    physical_paths = {p['id']: p for p in executable['attribution_paths']}
    equivalent = {}
    for event, receipt in unions.items():
        candidates = info['verified_attribution_paths'][event]
        sizes = [(physical_paths[p].get('case_map') or {}).get('validation', {}).get('matched_source_rows')
                 for p in candidates]
        if receipt.get('repeated_pairs') and all(n == receipt['distinct_pairs'] for n in sizes):
            equivalent[event] = candidates
            info['verified_attribution_paths'][event] = candidates[:1]
    view['fingerprint'] = stable_id('process_view', view)
    outcome.update(pi=info, equivalent_path_proofs=equivalent)
    es = materialize_pi_selection(executable, question, view, intent)
    if es['status'] != 'accepted':
        return {**outcome, 'status': 'failed', 'reason': es.get('reason_code'), 'es': es,
                'structural': [], 'execution_seconds': perf_counter() - started}
    result = run_repair_pipeline(database, view, es, graph=executable)
    execution = result['report'].get('execution', {})
    accepted = result['terminal_status'] == 'accepted' and result['report']['hard_passed'] and execution.get('passed')
    return {**outcome, 'status': 'accepted' if accepted else 'failed', 'reason': result['status'],
            'es': result['es'], 'case': result['es'].get('case'), 'structural': [],
            'sql': execution.get('sql') if accepted else None, 'rows': execution.get('event_log', []) if accepted else [],
            'execution_seconds': perf_counter() - started, 'execution_review': compact_repair_result(result)}


def run_minimal(database, question, *, index, client, model=DEFAULT_MODEL, review=True, checkpoint=None):
    """PURPOSE: Run one Minimal PI or paired M0/M1 with one common immutable Initial PI.
    INPUT: Public read-only DB, indexed EEG, model client and optional append-only checkpoint callback.
    OUTPUT: Shared retrieval/initial audit and independent execution receipts. Provider failures retain prior checkpoints.
    """
    require_public_path(database)
    if not isinstance(index, EEGStore) or not question.strip():
        raise ValueError('A shared EEG index and a nonempty request are required')
    metered = MeteredClient(client)
    metered.pi_request_budget = PIRequestBudget(32, 240_000)
    metered.pi_active = True
    started = perf_counter()
    attempts = []
    record_result = checkpoint or (lambda name, data: None)
    with index.open(database) as lookup:
        projection = lookup.request_graph(question, mode='graph', semantic_top_k=10, progressive=True)
        validate_runtime_graph(projection)
        inventory = {field: sorted(row['id'] for row in projection.get(field, [])) for field in INVENTORY}
        evidence, scopes = make_evidence(projection)
        receipt = {'inventory_sha256': content_hash(inventory), 'inventory': inventory, 'evidence': evidence}
        record_result('retrieval', receipt)
        try:
            intent = model_call('minimal_intent', {'original_request': question}, metered, model, attempts)
            record_result('intent', intent)
            initial = select_initial(question, intent, evidence, metered, model, attempts, record_result)
        except (ValueError, RuntimeError) as error:
            failed = {'status': 'failed', 'reason': str(error), 'sql': None, 'rows': [], 'pi': None}
            record_result('initial_error', failed)
            return {'retrieval': receipt, 'initial': None, 'initial_seconds': perf_counter() - started,
                    'outcomes': {arm: failed for arm in (('M0', 'M1') if review else ('M0',))}, 'calls': attempts}
        record_result('initial', initial)
        initial_seconds = perf_counter() - started
        m0 = execute_selection(database, lookup, projection, evidence, scopes, question, intent, initial)
        record_result('M0', m0)
        outcomes = {'M0': m0}
        receipt_review = None
        if review:
            payload = {'original_request': question, 'intent': intent, 'evidence': evidence, 'proposed_pi': deepcopy(initial)}
            record_result('review_input', payload)
            reviewing = perf_counter()
            try:
                revised = model_call('minimal_review', payload, metered, model, attempts)
                before_pairs = {(p['event_definition_id'], p['path_id']) for p in initial['events']}
                after_pairs = {(p['event_definition_id'], p['path_id']) for p in revised['events']}
                changed = before_pairs != after_pairs or any(
                    initial[key] != revised[key] for key in ('selection_status', 'case_et_id', 'case_scope_id')
                )
                receipt_review = {'status': 'completed', 'changed': changed, 'reply': revised}
            except (ValueError, RuntimeError) as error:
                revised = initial
                receipt_review = {'status': 'technical_failure_preserved_initial', 'reason': str(error),
                                  'changed': False}
            receipt_review['seconds'] = perf_counter() - reviewing
            record_result('review', receipt_review)
            outcomes['M1'] = execute_selection(database, lookup, projection, evidence, scopes, question, intent, revised)
            record_result('M1', outcomes['M1'])
    return {'retrieval': receipt, 'intent': intent, 'initial': initial, 'initial_seconds': initial_seconds,
            'review': receipt_review, 'outcomes': outcomes, 'calls': attempts}
