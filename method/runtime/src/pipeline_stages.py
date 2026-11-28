"""Shared current graph construction and actual-path manifest for API/CLI/demo."""

from src.common.attribution_policy import bounded_hops
from src.step1_understand.pipeline import DbuConfig
from src.common.runtime_input_contract import POLICY_VERSION


def build_current_graph(database, dictionary, *, client, model, max_hops, cache=None, config=None, indexed=False):
    """PURPOSE: Build the same native EEG from path or in-memory public DD.
    INPUT: DB/DD, runtime model/cache and optional explicit Step 1 ablation config.
    OUTPUT: Runtime EEG; temporary serialized DD is deleted and no dataset asset is changed.
    """
    from src.eeg.evidence_graph_cache import load_or_build
    if dictionary is None:
        raise ValueError('The current pipeline requires a public Data Dictionary')
    max_hops=bounded_hops(max_hops)
    config=config or DbuConfig(model=model,max_hops=max_hops)
    graph,_=load_or_build(database,dictionary,client=client,config=config,response_cache=cache,
                         include_native=False, prepare_summary=not indexed, indexed=indexed)
    return graph


def pipeline_manifest(graph, query, *, pv_selector, selector, db_understanding, model,
                      verify_and_repair, max_hops, max_revisions):
    """PURPOSE: Record the executed route rather than inferring it from requested defaults.
    INPUT: Actual stage artifacts and settings. OUTPUT: One canonical per-run manifest.
    """
    view = query.get('process_view') or {}
    return {'version': 'nl2eventlog-three-stage-v2', 'input_contract': POLICY_VERSION, 'model': model,
        'step1': {'name':'Understand', 'method':'EEG Construction','builder': 'native' if graph.get('dbu_rewrite') else 'provided_or_legacy_graph',
                  'entity_model_version': graph.get('entity_model_version'),
                  'entity_build_stages': graph.get('entity_build_stages', []),
                  'semantic_policy_version': graph.get('semantic_policy_version'),
                  'carrier_event_policy': graph.get('carrier_event_policy'),
                  'canonical_activity_policy': graph.get('canonical_activity_policy'),
                  'entity_linking_policy': graph.get('entity_linking_policy'),
                  'requested_mode': db_understanding, 'configuration': graph.get('build_configuration', {}),
                  'llm_audits_ref': 'graph.dbu_llm_calls',
                  'eeg_cache': graph.get('eeg_cache',{}),
                  'actual_build_llm_requests': graph.get('eeg_cache',{}).get('actual_build_llm_requests',0),
                  'input_audit_ref': 'graph.input_contract_audit',
                  'source_coverage': (graph.get('source_coverage') or {}).get('counts', {})},
        'step2': {'name':'Retrieve & Interpret', 'method':'Graph-guided Process Interpretation','output':'Process Information (PI, I_q)',
                  'process_focus':view.get('process_focus'),
                  'case_notion_et_id':(query.get('process_information') or {}).get('case_notion_et_id'),
                  'selector': pv_selector, 'algorithm': 'iterative' if pv_selector == 'llm_graph' else 'legacy_' + pv_selector,
                  'configuration_ref': 'process_interpretation_trace.configuration',
                  'eeg_delivery': (query.get('runtime_policy') or {}).get('eeg_delivery'),
                  'activity_scope': view.get('activity_scope', view.get('request_type')),
                  'object_scope': view.get('object_scope_policy', {'own_only': 'own',
                      'with_descendants': 'desc'}.get(view.get('object_scope'), 'unresolved')),
                  'max_hops': max_hops, 'max_revisions': max_revisions,
                  'status': query.get('status')},
        'step3': {'name':'Execute', 'method':'Specification-driven Event Log Extraction',
                  'selector': selector, 'validator': 'unified_preflight', 'status': 'not_run',
                  'verification_and_repair': {'enabled': verify_and_repair, 'validator': 'unified_full',
                                              'repair': 'witnessed_occurrence_verification_v2', 'status': 'not_run'}}}
