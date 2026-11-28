"""M0 development candidate with Case selection ahead of event retrieval."""

from time import perf_counter

from src.common.graph_identifiers import content_hash
from src.common.llm_usage import DEFAULT_MODEL, MeteredClient
from src.common.runtime_input_contract import require_public_path, validate_runtime_graph
from src.eeg.eeg_store import EEGStore
from src.step2_retrieve_and_interpret.execute_model_roles import PIRequestBudget
from src.step2_retrieve_and_interpret.minimal_evidence import case_evidence, make_evidence
from src.step2_retrieve_and_interpret.minimal_pipeline import INVENTORY, execute_selection, model_call


def load_catalog(lookup):
    """PURPOSE: Offer every population-valid Case before event expansion.
    INPUT: One immutable EEG lookup. OUTPUT: Compact model cards and full documented scope bindings.
    """
    projection = lookup.case_graph(event_ids=set(), case_catalog=True)
    validate_runtime_graph(projection)
    evidence, scopes = make_evidence(projection)
    entities = {entity['id']: entity for entity in projection['entity_types']}
    cards = [{
        'id': card['id'], 'name': card['name'],
        'grain': entities[card['id']].get('instance_granularity') or card['meaning'],
        'definition': card['definition'],
        'populations': card['populations'], 'scopes': card['scopes'],
    } for card in evidence['cases']]
    return cards, scopes


def load_case(lookup, case_id):
    """PURPOSE: Retrieve event and attribution facts for a selected Case using indexed links.
    INPUT: Open EEG lookup and ID from the catalog. OUTPUT: Scoped executable graph, model evidence and receipt.
    """
    projection = lookup.case_graph([case_id], include_peers=True, for_pi=True)
    validate_runtime_graph(projection)
    evidence, scopes = make_evidence(projection)
    inventory = {axis: sorted(row['id'] for row in projection.get(axis, [])) for axis in INVENTORY}
    receipt = {'inventory_sha256': content_hash(inventory), 'inventory': inventory, 'evidence': evidence}
    return projection, evidence, scopes, receipt


def interpret(lookup, question, client, model, calls, record):
    """PURPOSE: Resolve intent, Case and events in the original M0 role order.
    INPUT: Public request and lookup, metered client, audit sinks. OUTPUT: Plan and its exact structural evidence.
    """
    cards, scopes = load_catalog(lookup)
    record('case_catalog', cards)
    intent = model_call('minimal_intent', {'original_request': question}, client, model, calls)
    record('intent', intent)
    common = {'original_request': question, 'intent': intent}
    case = model_call('minimal_case', {**common, 'cases': cards}, client, model, calls)
    record('case', case)
    target, scope = case['case_et_id'], case['case_scope_id']
    if case['selection_status'] != 'selected' or target not in scopes or (scope and scope not in scopes[target]):
        return intent, {**case, 'events': []}, {}, {'cases': [], 'events': []}, scopes, None
    projection, evidence, selected_scopes, receipt = load_case(lookup, target)
    record('retrieval', receipt)
    card = next(item for item in evidence['cases'] if item['id'] == target)
    events = model_call('minimal_events', {**common, 'case': case, 'case_evidence': card,
                                         'events': case_evidence(evidence, target)}, client, model, calls)
    return intent, {**case, **events}, projection, evidence, selected_scopes, receipt


def run_m0(database, question, *, index, client, model=DEFAULT_MODEL, checkpoint=None):
    """PURPOSE: Execute the selected M0 design from a public DB and frozen EEG Index.
    INPUT: Public DB, request and existing SDK client. OUTPUT: M0 receipt with actual calls and deterministic output.
    """
    require_public_path(database)
    if not isinstance(index, EEGStore) or not question.strip():
        raise ValueError('A shared EEG index and a nonempty request are required')
    metered = MeteredClient(client)
    metered.pi_request_budget = PIRequestBudget(32, 240_000)
    metered.pi_active = True
    started, calls = perf_counter(), []
    checkpoints = {}

    def record(name, value):
        """PURPOSE: Keep the observed candidate stages available after failure.
        INPUT: Stage key and append-only payload. OUTPUT: Local state plus the optional caller checkpoint.
        """
        checkpoints[name] = value
        if checkpoint is not None:
            checkpoint(name, value)

    with index.open(database) as lookup:
        try:
            intent, initial, projection, evidence, scopes, retrieval = interpret(
                lookup, question, metered, model, calls, record)
        except (ValueError, RuntimeError) as error:
            failed = {'status': 'failed', 'reason': str(error), 'sql': None, 'rows': [], 'pi': None}
            record('initial_error', failed)
            return {'case_catalog': checkpoints.get('case_catalog'), 'retrieval': checkpoints.get('retrieval'),
                    'initial': None, 'initial_seconds': perf_counter() - started,
                    'outcomes': {'M0': failed}, 'calls': calls}
        record('initial', initial)
        initial_seconds = perf_counter() - started
        outcome = execute_selection(database, lookup, projection, evidence, scopes, question, intent, initial)
        record('M0', outcome)
    return {'case_catalog': checkpoints['case_catalog'], 'retrieval': retrieval, 'intent': intent,
            'initial': initial, 'initial_seconds': initial_seconds, 'outcomes': {'M0': outcome}, 'calls': calls}
