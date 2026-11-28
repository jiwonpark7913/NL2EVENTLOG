"""Regression controls for S2 and the common scoped execution contract."""

import json
from contextlib import closing

import httpx

from development.s2.evidence import activity_aware_catalog
from development.s2.runtime import JOINT_ROLE, JOINT_SCHEMA, choose_joint, run
from development.s2.extraction import execute_stage3
from cross_model_evaluation.providers import GeminiSpendGuard, gemini_client
from src.common.claude_client import ClaudeChatClient
from src.common.llm_usage import MeteredClient
from src.step2_retrieve_and_interpret.execute_model_roles import PIRequestBudget
from test_minimal_step2 import build, case_key, index_fixture, logistics, pairs, scripted_plan
from test_pipeline_runtime import RequirementScenarioClient


def synthetic_depots(tmp_path, same_first_case=False):
    """PURPOSE: Model two disjoint sender/receiver pairs. INPUT: Scratch folder. OUTPUT: DB and reusable public EEG."""
    schema = """
        CREATE TABLE depots(id INTEGER PRIMARY KEY, commissioned_at TEXT);
        CREATE TABLE transfers(id INTEGER PRIMARY KEY,
            sender_id INTEGER NOT NULL UNIQUE REFERENCES depots(id),
            receiver_id INTEGER NOT NULL UNIQUE REFERENCES depots(id),
            dispatched_at TEXT);
        INSERT INTO depots VALUES(10,'2025-01-01'),(20,'2025-01-01'),(30,'2025-01-01'),(40,'2025-01-01');
        INSERT INTO transfers VALUES(1,10,20,'2025-03-01'),(2,30,40,'2025-03-02');
    """
    if same_first_case:
        schema = schema.replace('(1,10,20,', '(1,20,20,')
    return build(tmp_path, schema, {
        'depots': {'readable_name':'Depot','definition':'One logistics depot business entity.',
                   'columns':{'commissioned_at':{'definition':'Actual commissioning time.'}}},
        'transfers':{'readable_name':'Transfer','definition':'One package transfer between two depots.',
                     'columns': {'sender_id':{'definition':'Sender depot for this transfer.'},
                                 'receiver_id':{'definition':'Receiver depot for this transfer.'},
                                 'dispatched_at':{'definition':'Actual time that this transfer was dispatched.'}}}
    })


def dispatch_paths(cards):
    """PURPOSE: Select both offered roles of one actual dispatch occurrence. INPUT: Offered cards. OUTPUT: ED/AP IDs."""
    return [{'event_definition_id':card['id'],'path_id':path['id']}
            for card in cards if 'dispatched_at' in card['clock_id']
            for path in card['paths'] if path['role'] in {'sender','receiver'}]


def test_scope_union_checks_the_compiler_population(tmp_path):
    """PURPOSE: Verify corrected and genuine union conflicts. INPUT: Two role paths and optional scope. OUTPUT: Correct disposition."""
    db, graph = synthetic_depots(tmp_path)
    index = index_fixture(tmp_path, graph)
    for scope, expected in [('receiver', 'accepted'), (None, 'unresolved')]:
        client = scripted_plan('Logistics Depot', dispatch_paths, scope=scope)
        result = run(db, 'Show actual dispatches from both transfer perspectives.', index=index, arm='S0',client=client)
        selected = result['outcome']
        assert selected['status'] == expected, selected
        if scope:
            assert [(case_key(r),json.loads(r['source_record_id'])[0]) for r in selected['rows']] == [('20','1'),('40','2')]
            proof, = selected['scoped_attribution_proofs'].values()
            assert proof['distinct_pairs'] == 2 and sorted(proof['scoped_pairs_by_path'].values()) == [0,2]
            assert selected['execution_review']['cost']['extractions'] == 1
        else:
            assert selected['reason'] == 'conflicting_attribution_union'


def test_post_scope_conflict_is_rejected(tmp_path):
    """PURPOSE: Reject a conflict which survives the actual scope. INPUT: One preserved multi-Case mapping. OUTPUT: No SQL."""
    db, graph = logistics(tmp_path)
    client = scripted_plan('Logistics Depot', dispatch_paths, scope='receiver')
    outcome = run(db,'Show dispatches for receiving depots.',index=index_fixture(tmp_path,graph),
                  arm='S0',client=client)['outcome']
    proof, = outcome['structural'].values()
    assert outcome['reason']=='conflicting_attribution_union' and outcome['sql'] is None
    assert proof['multiple_case_occurrences']==1


def test_partially_equivalent_scoped_paths_dedup(tmp_path):
    """PURPOSE: Preserve a genuine shared assignment with a second distinct pair.
    INPUT: Two validated role paths, one overlapping and one scope-excluded. OUTPUT: One row for each distinct assignment.
    """
    db, graph = synthetic_depots(tmp_path,same_first_case=True)
    client = scripted_plan('Logistics Depot',dispatch_paths,scope='receiver')
    outcome = run(db,'Show actual dispatches for both roles of receiving depots.',
                  index=index_fixture(tmp_path,graph),arm='S0',client=client)['outcome']
    assert outcome['status']=='accepted',outcome
    proof, = outcome['scoped_attribution_proofs'].values()
    assert proof['repeated_pairs']==1 and proof['distinct_pairs']==2
    assert len(outcome['rows'])==2


def test_documented_assignment_unsupported_is_distinct_from_conflict(tmp_path):
    """PURPOSE: Preserve the single-Case output contract with a precise refusal. INPUT: Public role authority. OUTPUT: No SQL."""
    db, graph = synthetic_depots(tmp_path)
    graph['data_dictionary']['business_rules'] = [{
        'text':'A dispatch belongs to the sender and receiver depots.',
        'event_attribution':{'source_table':'transfers','case_table':'depots','roles':['sender','receiver'],
                             'occurrence_columns':['dispatched_at'],'multiple_cases':True}}]
    receipt = run(db, 'Show dispatches from both depot perspectives.', index=index_fixture(tmp_path, graph),
                  arm='S0',client=scripted_plan('Logistics Depot',dispatch_paths))
    assert receipt['outcome']['reason'] == 'documented_multiple_case_assignments_unsupported'
    assert not receipt['outcome']['rows'] and receipt['outcome']['sql'] is None


def test_equivalent_paths_and_separate_lifecycle_roles(tmp_path):
    """PURPOSE: Exercise exact-pair dedup and independent attribution across EDs. INPUT: Existing synthetic graph. OUTPUT: Correct rows."""
    db, graph = logistics(tmp_path,equivalent=True)
    index = index_fixture(tmp_path, graph)
    result = run(db,'Show dispatches for both roles.',index=index,arm='S0',client=scripted_plan('Logistics Depot',dispatch_paths))
    out = result['outcome']
    assert out['status']=='accepted' and len(out['rows'])==2
    assert len(next(iter(out['equivalent_path_proofs'].values())))==2

    def two_roles(cards):
        """PURPOSE: Pick distinct roles for distinct definitions. INPUT: Event cards. OUTPUT: Two sets of exact selections."""
        return (pairs(cards,lambda card:'dispatched_at' in card['clock_id'],role='sender')
                + pairs(cards,lambda card:'received_at' in card['clock_id'],role='receiver'))

    result = run(db,'Show dispatch and receipt by the applicable role.',index=index,arm='S0',
                 client=scripted_plan('Logistics Depot',two_roles))
    assert result['outcome']['status']=='accepted' and len(result['outcome']['rows'])==4


def test_s2_exact_roles_and_shared_eligibility(tmp_path):
    """PURPOSE: Check native wire shape and review visibility without an acceptance gate.
    INPUT: Independent logistics DB and four review states. OUTPUT: Two model roles, then an accepted extraction.
    """
    db, graph = logistics(tmp_path)
    target = next(et['id'] for et in graph['entity_types'] if et['name']=='Logistics Depot')
    status_cycle = iter(('supported','incompatible','uncertain'))
    for ed in graph['event_definitions']:
        for path in graph['attribution_paths']:
            if path['to']==target and path['event_definition_id']==ed['id']:
                state = next(status_cycle,None)
                if state:
                    ed.setdefault('entity_reviews', {})[target] = {'attribution_paths': {
                        **ed.get('entity_reviews', {}).get(target, {}).get('attribution_paths', {}),
                        path['id']:{'status':state,'role':'related','reason':'Fixture review',
                                    'citations':[{'id':'fixture','quote':'Role evidence.'}]}}}
    index = index_fixture(tmp_path, graph)
    question = 'Show the activities for each receiving depot.'

    def joint(payload):
        """PURPOSE: Verify available Case capabilities before choosing one. INPUT: Joint wire. OUTPUT: Closed reply."""
        assert payload['original_request']==question and set(payload)=={'original_request','cases'}
        case = next(card for card in payload['cases'] if card['id']==target)
        assert case['connected_activities']
        assert all(len(value)==4 for value in case['connected_activities'])
        scope = next(s['id'] for s in case['scopes'] if s['role']=='receiver')
        return {'intent':{'objective':question,'case_intent':'Depot','activity_intent':question,'activity_mode':'explicit'},
                'case':{'case_et_id':target,'case_scope_id':scope,'selection_status':'selected','reason':''}}

    def event(payload):
        """PURPOSE: Ensure full ED delivery and all four review distinctions. INPUT: Event wire. OUTPUT: Valid direct path."""
        assert payload['original_request']==question and payload['selected_case_scope']['role']=='receiver'
        status = {p['relationship_review']['status'] for e in payload['events'] for p in e['paths']}
        assert status=={'supported','incompatible','uncertain','unreviewed'}
        offered_labels = {e['activity'] for e in payload['events']}
        card = next(c for c in activity_aware_catalog(db,index) if c['id']==target)
        assert offered_labels == {entry[0] for entry in card['connected_activities']}
        return {'selection_status':'selected','events':pairs(payload['events'],lambda c:'commissioned_at' in c['clock_id']),'reason':''}

    result = run(db,question,index=index,arm='S2',client=RequirementScenarioClient({JOINT_ROLE:joint,'minimal_events':event}))
    assert [a['role'] for a in result['calls']]==[JOINT_ROLE,'minimal_events']
    assert result['outcome']['status']=='accepted' and len(result['outcome']['rows'])==2
    assert all(a['status']=='valid_response' for a in result['calls'])


def test_distinct_same_time_occurrences_survive_stage3(tmp_path):
    """PURPOSE: Preserve duplicate-looking business occurrences. INPUT: Two rows with one owner and clock. OUTPUT: Distinct physical IDs."""
    db, graph = build(tmp_path, """
        CREATE TABLE visits(id INTEGER PRIMARY KEY, admitted_at TEXT);
        CREATE TABLE lab_orders(id INTEGER PRIMARY KEY, visit_id INTEGER NOT NULL REFERENCES visits(id));
        CREATE TABLE specimens(id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES lab_orders(id),
            received_at TEXT, tested_at TEXT);
        INSERT INTO visits VALUES (10,'2025-03-01 08:00:00'),(20,'2025-03-02 08:00:00');
        INSERT INTO lab_orders VALUES (1,10),(2,20);
        INSERT INTO specimens VALUES
            (31,1,'2025-03-01 09:00:00','2025-03-01 10:00:00'),
            (33,1,'2025-03-01 09:00:00','2025-03-01 10:00:00'),
            (32,2,'2025-03-02 09:00:00','2025-03-02 10:00:00');
    """, {
        'visits': {'readable_name':'Visit','definition':'One clinical visit business entity.',
                   'columns': {'admitted_at':{'definition':'Actual patient admission time.'}}},
        'lab_orders': {'readable_name':'Lab Order','definition':'Lab orders for a clinical visit.',
                       'columns': {'visit_id':{'definition':'Clinical visit that ordered the lab test.'}}},
        'specimens': {'readable_name':'Specimen','definition':'Specimen received and tested on a lab order.',
                      'columns': {'received_at':{'definition':'Actual time that the specimen was received.'},
                                  'tested_at':{'definition':'Actual time that the specimen was tested.'}}}
    })
    index = index_fixture(tmp_path, graph)
    client = scripted_plan('Clinical Visit',lambda cards:pairs(cards,lambda c:'received_at' in c['clock_id']))
    result = run(db,'Show each actual specimen receipt for the visit.',index=index,arm='S0',client=client)['outcome']
    assert result['status']=='accepted',result
    rows = [row for row in result['rows'] if case_key(row)=='10']
    assert len(rows)==2 and len({r['source_occurrence_id'] for r in rows})==2
    assert len({(r['case_id'],r['activity'],r['timestamp']) for r in rows})==1

    # An actually mutated frozen specification fails closed with no published partial log.
    es = dict(result['es'],case_selection={'kind':'invalid'})
    view = es['process_view']
    with index.open(db) as lookup:
        ids=view['process_information']['verified_attribution_paths']
        projection=lookup.case_graph([view['target_ot_id']],event_ids=list(ids),path_ids={p for group in ids.values() for p in group})
    rejected=execute_stage3(db,projection,view,es)
    assert rejected['status']=='failed' and rejected['rows']==[] and rejected['sql'] is None


def test_joint_schema_through_both_native_adapters_without_network(tmp_path):
    """PURPOSE: Check actual native serialization and response parsing for the closed joint role.
    INPUT: Two mocked HTTP providers. OUTPUT: Preserved nested replies and one call per provider.
    """
    reply = {'intent':{'objective':'Objective','case_intent':'Case','activity_intent':'Events','activity_mode':'implicit'},
             'case':{'selection_status':'insufficient_evidence','case_et_id':'','case_scope_id':'','reason':'No evidence'}}
    requests = []

    def anthropic(request):
        """PURPOSE: Simulate Claude structured tool output behind its HTTP adapter.
        INPUT: Native request. OUTPUT: Meterable in-memory response.
        """
        body = json.loads(request.content)
        requests.append(body)
        assert body['thinking']=={'type':'adaptive'} and body['output_config']=={'effort':'medium'}
        assert body['tools'][0]['name']==JOINT_ROLE and body['tools'][0]['input_schema']==JOINT_SCHEMA
        return httpx.Response(200,json={'id':'msg_test','model':'claude-haiku-5-5','stop_reason':'tool_use',
            'content':[{'type':'tool_use','name':JOINT_ROLE,'input':reply}],
            'usage':{'input_tokens':100,'output_tokens':30}})

    def google(request):
        """PURPOSE: Simulate Gemini's native JSON-schema response.
        INPUT: generateContent request. OUTPUT: Meterable in-memory response.
        """
        body = json.loads(request.content)
        requests.append(body)
        config = body['generationConfig']
        schema = config.get('responseJsonSchema') or config.get('responseSchema')
        assert set(schema['properties'])=={'intent','case'}
        assert config['thinkingConfig']=={'thinkingLevel':'MINIMAL'} and config['temperature']==0
        return httpx.Response(200,json={'modelVersion':'gemini-3.5-flash-lite',
            'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(reply)}]}}],
            'usageMetadata':{'promptTokenCount':100,'candidatesTokenCount':30}})

    guard = GeminiSpendGuard(tmp_path/'g.json','1.50',tmp_path/'h.json',
                            'paid_cap_permitted', inner=httpx.MockTransport(google))
    with closing(ClaudeChatClient('test',transport=httpx.MockTransport(anthropic))) as claude, closing(
            gemini_client('test',guard)) as gemini:
        for model, client in [('claude-haiku-5-5',claude),('gemini-3.5-flash-lite',gemini)]:
            metered=MeteredClient(client)
            metered.pi_request_budget=PIRequestBudget(32,240_000)
            metered.pi_active=True
            audits=[]
            assert choose_joint('Original request',[],metered,model,audits)==(reply['intent'],reply['case'])
            assert [call['role'] for call in audits]==[JOINT_ROLE]
    assert len(requests)==2
