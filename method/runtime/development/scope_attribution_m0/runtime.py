"""A versioned M0 candidate that states the Case population contract during Event Selection."""

from pathlib import Path
from time import perf_counter

from development.case_catalog_m0.runtime import load_case, load_catalog
from src.common.llm_usage import DEFAULT_MODEL, MeteredClient
from src.common.runtime_input_contract import require_public_path
from src.eeg.eeg_store import EEGStore
from src.step2_retrieve_and_interpret.execute_model_roles import PIRequestBudget, call_role
from src.step2_retrieve_and_interpret.minimal_evidence import case_evidence
from src.step2_retrieve_and_interpret.minimal_pipeline import execute_selection, model_call

SCOPE_PROMPT = Path(__file__).with_name('event_scope.md')


def event_payload(question, intent, case, evidence, scopes, *, clarify=True):
    """PURPOSE: Keep existing evidence and expose the one bound population scope explicitly.
    INPUT: Original request, saved or live Case and selected graph. OUTPUT: Normal Event Selection payload.
    """
    target, scope_id = case['case_et_id'], case['case_scope_id']
    scope = scopes[target][scope_id] if scope_id else None
    selected = next(item for item in evidence['cases'] if item['id']==target)
    payload={'original_request':question,'intent':intent,'case':case,'case_evidence':selected,
             'events':case_evidence(evidence,target)}
    if clarify:
        payload['selected_case_scope'] = (
            {'id':scope_id,'role':scope['role'],'evidence':scope['evidence']} if scope else None
        )
    return payload


def run_m0(database, question, *, index, client, model=DEFAULT_MODEL, checkpoint=None, replay=None, clarify=True):
    """PURPOSE: Run normal Sequential M0 or replay its saved Intent and Case with only one new event call.
    INPUT: Public DB, question, frozen Index, client, and optional exact saved checkpoints.
    OUTPUT: Catalog/PI/runtime receipt with an auditable M0 result and only newly made calls.
    """
    require_public_path(database)
    if not isinstance(index,EEGStore) or not question.strip():
        raise ValueError('A shared EEG index and a nonempty request are required')
    metered=MeteredClient(client)
    metered.pi_request_budget=PIRequestBudget(32,240_000)
    metered.pi_active=True
    started,calls=perf_counter(),[]
    stages={}

    def record(key,value):
        """PURPOSE: Keep immutable stages available for diagnostics and partial failures.
        INPUT: Stage key and public payload. OUTPUT: Local stage and optional caller record.
        """
        stages[key]=value
        if checkpoint is not None:
            checkpoint(key,value)

    with index.open(database) as lookup:
        try:
            catalog,catalog_scopes=load_catalog(lookup)
            record('case_catalog',catalog)
            if replay is None:
                intent=model_call('minimal_intent',{'original_request':question},metered,model,calls)
                record('intent',intent)
                case=model_call('minimal_case',{'original_request':question,'intent':intent,'cases':catalog},
                                metered,model,calls)
            else:
                intent,case=replay['intent'],replay['case']
                record('intent',intent)
            record('case',case)
            target,scope_id=case['case_et_id'],case['case_scope_id']
            projection,evidence,scopes={}, {'cases':[],'events':[]},catalog_scopes
            initial={**case,'events':[]}
            if case['selection_status']=='selected' and target in scopes and (not scope_id or scope_id in scopes[target]):
                projection,evidence,scopes,retrieval=load_case(lookup,target)
                if replay is not None and retrieval!=replay['retrieval']:
                    raise ValueError('Replayed event evidence differs from its frozen projection')
                record('retrieval',retrieval)
                payload=event_payload(question,intent,case,evidence,scopes,clarify=clarify)
                events,_=call_role('minimal_events',payload,metered,model,few_shot=False,audit_sink=calls,
                    payload_encoding='compact',system_appendix=SCOPE_PROMPT.read_text().strip() if clarify else None)
                initial={**case,**events}
            elif replay is not None:
                raise ValueError('Saved Case and scope are no longer selectable')
        except (ValueError,RuntimeError) as error:
            failed={'status':'failed','reason':str(error),'rows':[],'sql':None,'pi':None}
            record('initial_error',failed)
            return {**stages,'initial':None,'initial_seconds':perf_counter()-started,
                    'outcomes':{'M0':failed},'calls':calls,'shared_upstream':replay is not None}
        record('initial',initial)
        initial_seconds=perf_counter()-started
        outcome=execute_selection(database,lookup,projection,evidence,scopes,question,intent,initial)
        record('M0',outcome)
    return {**stages,'initial_seconds':initial_seconds,'outcomes':{'M0':outcome},'calls':calls,
            'shared_upstream':replay is not None}
