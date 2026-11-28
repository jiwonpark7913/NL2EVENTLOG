"""Independent domain fixtures for the shared Minimal PI and one-review branches."""

import json

import pytest

from src.eeg.eeg_store import EEGStore, write_index
from src.step2_retrieve_and_interpret.minimal_pipeline import run_minimal
from test_pipeline_runtime import RequirementScenarioClient
from test_v2_index_and_recovery import fixture
from test_v2_occurrence_construction import build


def index_fixture(tmp_path, graph):
    """PURPOSE: Bind a public development graph to the normal indexed entry point.
    INPUT: Writable fixture directory and runtime EEG. OUTPUT: Read-only EEGStore handle.
    """
    index_path = tmp_path / 'candidate-index.sqlite'
    write_index(index_path, graph, 'independent-development')
    return EEGStore(index_path, 'independent-development')


def scripted_plan(case_name, activities, *, review=None, selection_status='selected', scope=None, mode='explicit'):
    """PURPOSE: Script selector outputs without placing expected rows in prompts.
    INPUT: Development Case name, card-to-event selection and optional review.
    OUTPUT: Model-shaped SDK double with observable role order.
    """
    def intent(payload):
        """PURPOSE: Retain the original wording in the intent. INPUT: Request payload. OUTPUT: Free-text intent."""
        return {'objective': payload['original_request'], 'case_intent': case_name,
                'activity_intent': payload['original_request'], 'activity_mode': mode}

    def choose_case(payload):
        """PURPOSE: Choose a real test case card. INPUT: Retrieved cards. OUTPUT: Actual Case and scope IDs."""
        card = next(item for item in payload['cases'] if item['name'].casefold() == case_name.casefold())
        scope_id = next(item['id'] for item in card['scopes'] if item['role'] == scope) if scope else ''
        return {'selection_status': 'selected', 'case_et_id': card['id'], 'case_scope_id': scope_id, 'reason': ''}

    def choose_events(payload):
        """PURPOSE: Choose existing pairs or an explicit failure. INPUT: Case event cards. OUTPUT: Flat selection."""
        return {'selection_status': selection_status, 'events': activities(payload['events']), 'reason': ''}

    return RequirementScenarioClient({'minimal_intent': intent, 'minimal_case': choose_case,
                                      'minimal_events': choose_events, 'minimal_review': review or retain})


def retain(payload):
    """PURPOSE: Confirm a shared Initial PI. INPUT: Review payload. OUTPUT: Unmodified selection."""
    return payload['proposed_pi']


def pairs(cards, predicate, *, role=None):
    """PURPOSE: Construct existing ED/path pairs from a fixture. INPUT: Cards and predicate. OUTPUT: Physical IDs."""
    return [{'event_definition_id': card['id'],
             'path_id': next(path['id'] for path in card['paths'] if role is None or path['role'] == role)}
            for card in cards if predicate(card)]


def test_order_correct_plan_is_shared_without_exclusion_quotes(tmp_path):
    """PURPOSE: Preserve a correct order PI through both branches.
    INPUT: Documented approval DB and scripted existing ED/AP pair. OUTPUT: Identical SQL and rows with four logical calls.
    """
    db, _, _, graph = fixture(tmp_path)

    def select(cards):
        """PURPOSE: Select approval once for both requirements. INPUT: Offered cards. OUTPUT: Existing pair."""
        events = pairs(cards, lambda card: card['activity'] == 'Approved')
        assert len(events) == 1
        return events + events

    client = scripted_plan('Order', select)
    marks = {}
    result = run_minimal(db, 'Show approvals and use those same approvals to measure release, for each order.',
                         index=index_fixture(tmp_path, graph), client=client,
                         checkpoint=lambda label, value: marks.setdefault(label, value))
    expected_roles = ['minimal_intent', 'minimal_case', 'minimal_events', 'minimal_review']
    assert [role['role'] for role in result['calls']] == expected_roles
    assert marks['review_input']['proposed_pi'] == marks['initial']
    assert marks['review_input']['evidence'] == marks['retrieval']['evidence']
    assert result['outcomes']['M0']['status'] == result['outcomes']['M1']['status'] == 'accepted', result
    assert result['outcomes']['M0']['sql'] == result['outcomes']['M1']['sql']
    assert len(result['outcomes']['M0']['rows']) == 2
    assert result['outcomes']['M0']['rows'] == result['outcomes']['M1']['rows']


def case_key(row):
    """PURPOSE: Decode the fixture's typed Case identity. INPUT: One event row. OUTPUT: Scalar key as text."""
    return str(json.loads(row['case_id'])[2][0][1])


def healthcare(tmp_path):
    """PURPOSE: Build an independent multi-table healthcare fixture.
    INPUT: Temp directory. OUTPUT: Lab specimen occurrences, actual/expected clocks and a Visit Case EEG.
    """
    return build(tmp_path, """
        CREATE TABLE visits(id INTEGER PRIMARY KEY, admitted_at TEXT);
        CREATE TABLE lab_orders(id INTEGER PRIMARY KEY, visit_id INTEGER NOT NULL REFERENCES visits(id));
        CREATE TABLE specimens(id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES lab_orders(id),
            received_at TEXT, tested_at TEXT, scheduled_at TEXT);
        INSERT INTO visits VALUES (10,'2025-03-01 08:00:00'),(20,'2025-03-02 08:00:00');
        INSERT INTO lab_orders VALUES (1,10),(2,20);
        INSERT INTO specimens VALUES
          (31,1,'2025-03-01 09:00:00','2025-03-01 10:00:00','2025-03-01 15:00:00'),
          (32,2,'2025-03-02 09:00:00','2025-03-02 10:00:00','2025-03-02 15:00:00');
        """, {
        'visits': {'readable_name': 'Visit', 'definition': 'One clinical visit business entity.',
                   'columns': {'admitted_at': {'definition':'Actual patient admission time.'}}},
        'lab_orders': {'readable_name': 'Lab Order', 'definition': 'Lab orders for a clinical visit.',
                       'columns': {'visit_id': {'definition':'Clinical visit that ordered the lab test.'}}},
        'specimens': {'readable_name': 'Specimen', 'definition':'Specimen received and tested on a lab order.',
                      'columns': {'received_at': {'definition':'Actual time that the specimen was received.'},
                                  'tested_at': {'definition':'Actual time that the specimen was tested.'},
                                  'scheduled_at': {'definition':'Planned time for specimen testing.'}}},
    })


def specimen_phases(cards):
    """PURPOSE: Supply the two requested actual phases. INPUT: Case cards. OUTPUT: Receive/test EDs and existing paths."""
    return pairs(cards, lambda card: card['source_table'] == 'specimens'
                 and any(phase in card['clock_id'] for phase in ('received_at', 'tested_at')))


def test_healthcare_uses_two_actual_events_and_multihop_attribution(tmp_path):
    """PURPOSE: Join specimen events across Lab Order to Visit without case-specific runtime logic.
    INPUT: Independent healthcare database and one multi-event request. OUTPUT: Four actual rows, no planned clock.
    """
    db, graph = healthcare(tmp_path)
    client = scripted_plan('Clinical Visit', specimen_phases)
    result = run_minimal(db, 'For each visit, extract specimen processing from receipt through actual testing.',
                         index=index_fixture(tmp_path, graph), client=client)
    output = result['outcomes']['M0']
    assert output['status'] == 'accepted', (output['reason'], output.get('structural'))
    assert {(case_key(row), row['timestamp_raw_column']) for row in output['rows']} == {
        ('10', 'received_at'), ('10', 'tested_at'), ('20', 'received_at'), ('20', 'tested_at')}
    assert len(output['rows']) == 4
    assert set(result['outcomes']['M1']['pi']['selected_event_definition_ids']) == {
        item['event_definition_id'] for item in result['initial']['events']}
    assert any(len(path['joins']) == 2 for path in graph['attribution_paths'] if
               path['id'] in {p['path_id'] for p in result['initial']['events']})


@pytest.mark.parametrize('wrong_initial', [True, False], ids=['correction', 'harmful_review'])
def test_review_can_help_or_harm_a_structurally_executable_log(tmp_path, wrong_initial):
    """PURPOSE: Measure review deltas against actual deterministic rows on one common proposal.
    INPUT: Healthcare process with both relevant and irrelevant available events. OUTPUT: Observed correction or harm.
    """
    db, graph = healthcare(tmp_path)

    def choose(cards):
        """PURPOSE: Produce the selected scenario. INPUT: Cards. OUTPUT: Two specimen phases or the admission clock."""
        return (pairs(cards, lambda card: card['source_table'] == 'visits')
                if wrong_initial else specimen_phases(cards))

    def review(payload):
        """PURPOSE: Swap the event choice without changing Case. INPUT: Shared evidence. OUTPUT: Replacement PI."""
        case = payload['proposed_pi']['case_et_id']
        scoped = [{**e, 'paths': [p for p in e['paths'] if p['case_et_id'] == case]}
                  for e in payload['evidence']['events']]
        scoped = [e for e in scoped if e['paths']]
        events = (specimen_phases(scoped) if wrong_initial
                  else pairs(scoped, lambda card: card['source_table'] == 'visits'))
        return {**payload['proposed_pi'], 'events': events}

    client = scripted_plan('Clinical Visit', choose, review=review)
    result = run_minimal(db, 'Show specimen receipt and testing for each visit.',
                         index=index_fixture(tmp_path, graph), client=client)
    outcomes = result['outcomes']
    assert result['review']['changed']
    assert all(branch['status'] == 'accepted' for branch in outcomes.values())
    wrong, right = (('M0', 'M1') if wrong_initial else ('M1', 'M0'))
    assert {row['source_table'] for row in outcomes[wrong]['rows']} == {'visits'}
    assert {row['timestamp_raw_column'] for row in outcomes[right]['rows']} == {'received_at', 'tested_at'}
    assert len(outcomes[right]['rows']) == 4


def logistics(tmp_path, equivalent=False):
    """PURPOSE: Expose independent dispatch and receipt roles plus a documented population scope.
    INPUT: Temp directory and optional equivalent destinations. OUTPUT: Independent logistics DB and EEG.
    """
    setup = """
        CREATE TABLE depots(id INTEGER PRIMARY KEY, commissioned_at TEXT);
        CREATE TABLE transfers(id INTEGER PRIMARY KEY,
            sender_id INTEGER NOT NULL UNIQUE REFERENCES depots(id),
            receiver_id INTEGER NOT NULL UNIQUE REFERENCES depots(id),
            dispatched_at TEXT, received_at TEXT);
        INSERT INTO depots VALUES (10,'2025-01-01 00:00:00'),(20,'2025-01-02 00:00:00'),
                                  (30,'2025-01-03 00:00:00');
        INSERT INTO transfers VALUES (1,10,20,'2025-03-01 09:00:00','2025-03-01 10:00:00'),
                                     (2,20,30,'2025-03-02 09:00:00','2025-03-02 10:00:00');
        """
    if equivalent:
        setup = setup.replace('(1,10,20,', '(1,10,10,').replace('(2,20,30,', '(2,20,20,')
    return build(tmp_path, setup, {
        'depots': {'readable_name': 'Depot', 'definition':'One logistics depot business entity.',
                   'columns': {'commissioned_at': {'definition':'Actual commissioning time of the depot.'}}},
        'transfers': {'readable_name': 'Transfer', 'definition':'One package transfer business entity between two depots.',
                      'columns': {'sender_id': {'definition':'Sender depot for this transfer.'},
                                  'receiver_id': {'definition':'Receiver depot for this transfer.'},
                                  'dispatched_at': {'definition':'Actual time that this transfer was dispatched.'},
                                  'received_at': {'definition':'Actual time that this transfer was received.'}}},
    })


def test_logistics_chooses_two_distinct_event_attribution_roles(tmp_path):
    """PURPOSE: Preserve sender and receiver role choices within a single interpreted process.
    INPUT: Logistics transfer fixture. OUTPUT: Correct endpoint Case on each of four events.
    """
    db, graph = logistics(tmp_path)

    def select(cards):
        """PURPOSE: Select both phases with their respective role. INPUT: EEG cards. OUTPUT: Two role-specific paths."""
        return (pairs(cards, lambda c:'dispatched_at' in c['clock_id'], role='sender')
                + pairs(cards, lambda c:'received_at' in c['clock_id'], role='receiver'))

    result = run_minimal(db, 'List dispatches and receipts for each depot, attributed to the sender and receiver respectively.',
                         index=index_fixture(tmp_path, graph), client=scripted_plan('Logistics Depot', select))
    rows = result['outcomes']['M0']['rows']
    assert result['outcomes']['M0']['status'] == 'accepted', result['outcomes']['M0']['reason']
    assert {(case_key(row), int(json.loads(row['source_record_id'])[0]), row['timestamp_raw_column']) for row in rows} == {
        ('10', 1, 'dispatched_at'), ('20', 1, 'received_at'), ('20', 2, 'dispatched_at'), ('30', 2, 'received_at')}


def test_logistics_applies_declared_case_population(tmp_path):
    """PURPOSE: Restrict Cases to receivers under the same deterministic population contract.
    INPUT: Two receiving depots and one sender-only depot. OUTPUT: No sender-only commissioning event.
    """
    db, graph = logistics(tmp_path)
    client = scripted_plan('Logistics Depot', lambda cards:pairs(cards, lambda c:c['source_table']=='depots'), scope='receiver')
    result = run_minimal(db, 'For each depot that receives a transfer, include its commissioning.',
                         index=index_fixture(tmp_path, graph), client=client, review=False)
    output = result['outcomes']['M0']
    assert output['status'] == 'accepted', output['reason']
    assert set(result['outcomes']) == {'M0'} and len(result['calls']) == 3
    assert {case_key(r) for r in output['rows']} == {'20', '30'}
    assert output['es']['case_selection']['role'] == 'receiver'


def test_implicit_history_selects_documented_order_events(tmp_path):
    """PURPOSE: Handle an implicit request without requirement cardinalities or quotes.
    INPUT: Order lifecycle and shared review. OUTPUT: Complete supported history with implicit PI mode.
    """
    db, _, _, graph = fixture(tmp_path)
    client = scripted_plan('Order', lambda cards:pairs(cards, lambda c: c['source_table']=='orders'), mode='implicit')
    result = run_minimal(db, 'Show the whole lifecycle for each order.',
                         index=index_fixture(tmp_path, graph), client=client)
    assert result['outcomes']['M0']['status'] == 'accepted'
    assert result['outcomes']['M0']['pi']['request_mode'] == 'implicit'
    assert len(result['outcomes']['M0']['rows']) == 2


@pytest.mark.parametrize('failure', ['missing', 'unknown_ed', 'unknown_path', 'conflicting_paths'])
def test_structural_boundary_rejects_unsupported_plans(tmp_path, failure):
    """PURPOSE: Stop missing and structurally impossible extraction before SQL.
    INPUT: Logistics graph and typed missing, non-EEG, or conflicting path choices. OUTPUT: Unresolved and no published rows.
    """
    db, graph = logistics(tmp_path)

    def invalid(cards):
        """PURPOSE: Build one prohibited plan. INPUT: Retrieved cards. OUTPUT: Invalid or insufficient evidence."""
        if failure == 'missing':
            return []
        if failure == 'unknown_ed':
            return [{'event_definition_id': 'invented', 'path_id': cards[0]['paths'][0]['id']}]
        if failure == 'unknown_path':
            return [{'event_definition_id': cards[0]['id'], 'path_id': 'invented'}]
        return (pairs(cards, lambda c:'dispatched_at' in c['clock_id'], role='sender')
                + pairs(cards, lambda c:'dispatched_at' in c['clock_id'], role='receiver'))

    status = 'insufficient_evidence' if failure == 'missing' else 'selected'
    result = run_minimal(db, 'Show the requested occurrences for each depot.',
                         index=index_fixture(tmp_path, graph), client=scripted_plan('Logistics Depot', invalid, selection_status=status))
    for output in result['outcomes'].values():
        assert output['status'] == 'unresolved'
        assert output['sql'] is None and output['rows'] == []
    if failure == 'conflicting_paths':
        assert result['outcomes']['M0']['reason'] == 'conflicting_attribution_union'


def test_technical_review_failure_preserves_a_valid_initial_plan(tmp_path):
    """PURPOSE: Keep M0 evidence available when a review response fails technically.
    INPUT: Valid order PI and simulated provider failure. OUTPUT: Recorded unavailable review and preserved rows.
    """
    db, _, _, graph = fixture(tmp_path)

    def unavailable(_):
        """PURPOSE: Simulate a missing provider reply. INPUT: Review request. OUTPUT: Transport error."""
        raise RuntimeError('test transport unavailable')

    client = scripted_plan('Order', lambda cards:pairs(cards, lambda c:c['activity']=='Approved'), review=unavailable)
    verdict = run_minimal(db, 'Show Approved for each order.', index=index_fixture(tmp_path, graph), client=client)
    assert verdict['review']['status'] == 'technical_failure_preserved_initial'
    m0, m1 = (verdict['outcomes'][arm] for arm in ('M0', 'M1'))
    assert m0['status'] == m1['status'] == 'accepted'
    assert m0['rows'] == m1['rows']


def test_equivalent_existing_paths_preserve_occurrence_multiplicity(tmp_path):
    """PURPOSE: Deduplicate two proved paths mapping an ED to the same Case.
    INPUT: Two valid depot FKs that agree on every observed transfer. OUTPUT: One row per physical dispatch.
    """
    db, graph = logistics(tmp_path, equivalent=True)

    def select(cards):
        """PURPOSE: Keep both existing proofs. INPUT: Dispatch cards. OUTPUT: Two paths for one ED."""
        return (pairs(cards, lambda c:'dispatched_at' in c['clock_id'], role='sender')
                + pairs(cards, lambda c:'dispatched_at' in c['clock_id'], role='receiver'))

    r = run_minimal(db, 'Return actual dispatches for each depot.', index=index_fixture(tmp_path, graph),
                    client=scripted_plan('Logistics Depot', select))
    assert r['outcomes']['M0']['status'] == 'accepted', r['outcomes']['M0']['reason']
    assert len(r['outcomes']['M0']['rows']) == 2
    assert len(next(iter(r['outcomes']['M0']['equivalent_path_proofs'].values()))) == 2
