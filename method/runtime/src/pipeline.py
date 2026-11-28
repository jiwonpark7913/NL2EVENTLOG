"""Run Understand, Retrieve & Interpret, and Execute."""

from functools import partial
from time import perf_counter

from src.common.attribution_policy import DEFAULT_MAX_REVISIONS, MAX_ATTRIBUTION_HOPS
from src.common.llm_usage import DEFAULT_MODEL, MeteredClient
from src.eeg.eeg_store import EEGStore
from src.common.runtime_measurements import process_io, summarize_usage
from src.common.runtime_input_contract import require_public_path, validate_runtime_graph
from src.common.graph_identifiers import content_hash
from src.pipeline_stages import build_current_graph, pipeline_manifest
from src.step1_understand.eeg_configuration import DbuConfig
from src.step2_retrieve_and_interpret.pipeline import interpret_process_request
from src.step2_retrieve_and_interpret.execute_model_roles import PIRequestBudget
from src.step2_retrieve_and_interpret.recover_source_knowledge import GAPS, recover_source_graph
from src.step3_execute.materialize_extraction_specification import build_extraction_specification
from src.step3_execute.retrieve_extraction_bindings import retrieve_subgraph
from src.step3_execute.verify_execution_dependencies import (
    CONTRACT_VERSION, execution_dependencies, freeze_execution_contract,
)
from src.step3_execute.pipeline import compact_repair_result, run_repair_pipeline


def run_pipeline(database, dictionary, question, *, client, model=DEFAULT_MODEL,
                 graph=None, config=None, response_cache=None,
                 max_revisions=DEFAULT_MAX_REVISIONS, max_candidates=3,
                 semantic_top_k=10, evidence_retrieval=None, few_shot=True, recovery_enabled=True,
                 indexed=True, rates_per_million=None, retrieval_mode="graph", pi_mode="sequential",
                 max_pi_calls=32, max_pi_input_tokens=240_000, paired_pi_controls=False):
    """PURPOSE: Build or reuse EEG, interpret a request and execute the verified PI.
    INPUT: Read-only SQLite path, public DD path/mapping, natural-language request,
           SDK-compatible client, optional EEG/config/cache and bounded PI review settings.
           Paired controls align the initial inventory, fallback scope and independent review.
    OUTPUT: Graph, PI/query, retrieval, ES, execution, verification and stage manifest.
            Unresolved PI remains explicit; provider calls and EEG cache writes may occur.
    """
    if paired_pi_controls and (not isinstance(graph, EEGStore) or retrieval_mode != 'graph'):
        raise ValueError('Paired PI requires the same existing progressive EEG index')
    if pi_mode not in {'sequential', 'unified'}:
        raise ValueError('unknown PI mode')
    from src.step2_retrieve_and_interpret.unified_interpretation import UnifiedPolicy
    unified = UnifiedPolicy(verification='independent') if pi_mode == 'unified' else None
    return _run_pipeline(
        database, dictionary, question, client=client, model=model, graph=graph, config=config,
        response_cache=response_cache, max_revisions=max_revisions, max_candidates=max_candidates,
        semantic_top_k=semantic_top_k, evidence_retrieval=evidence_retrieval, few_shot=few_shot,
        indexed=indexed, recover_gaps=recovery_enabled, rates_per_million=rates_per_million,
        retrieval_mode=retrieval_mode, defer_case=unified is None and not paired_pi_controls,
        paired_pi_controls=paired_pi_controls, max_pi_calls=max_pi_calls, max_pi_input_tokens=max_pi_input_tokens,
        interpret=partial(interpret_process_request, recovery_enabled=recovery_enabled, database=database, unified=unified,
                          paired_pi_controls=paired_pi_controls))


def _run_pipeline(database, dictionary, question, *, client, interpret, model=DEFAULT_MODEL,
                  graph=None, config=None, response_cache=None,
                  max_revisions=DEFAULT_MAX_REVISIONS, max_candidates=3,
                  semantic_top_k=10, evidence_retrieval=None, few_shot=True, indexed=False, recover_gaps=False,
                  rates_per_million=None, retrieval_mode="graph", defer_case=False, max_pi_calls=32,
                  max_pi_input_tokens=240_000, paired_pi_controls=False):
    """PURPOSE: Execute the shared stages with an explicit PI interpreter.
    INPUT: Runtime settings and interpreter callable; experiments may inject a historical interpreter.
    OUTPUT: Complete stage results and an execution manifest.
    """
    require_public_path(database)
    if client is None:
        raise ValueError("Process interpretation requires an LLM client")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("A nonempty natural-language request is required")
    config = config or DbuConfig(model=model)
    if config.model != model:
        raise ValueError("EEG configuration model must match the pipeline model")
    started = perf_counter()
    io_before = process_io()
    metered = MeteredClient(client)
    if graph is None:
        graph = build_current_graph(database, dictionary, client=metered, model=model,
                                    max_hops=MAX_ATTRIBUTION_HOPS, cache=response_cache, config=config, indexed=indexed)
    metered.pi_request_budget = PIRequestBudget(max_pi_calls, max_pi_input_tokens)
    build_calls = len(metered.requests)
    understand_seconds = perf_counter() - started
    options = dict(client=metered, model=model, response_cache=response_cache, max_revisions=max_revisions,
                   max_candidates=max_candidates, semantic_top_k=semantic_top_k,
                   evidence_retrieval=evidence_retrieval, few_shot=few_shot, interpret=interpret,
                   rates_per_million=rates_per_million, paired_pi_controls=paired_pi_controls)
    lookup_stats = {}
    if isinstance(graph, EEGStore):
        with graph.open(database) as lookup:
            started_lookup = perf_counter()
            scoped_graph = lookup.request_graph(
                question, mode=retrieval_mode, semantic_top_k=semantic_top_k,
                defer_unanchored=defer_case, progressive=retrieval_mode == 'graph')
            lookup_stats['initial_retrieval_seconds'] = perf_counter() - started_lookup
            if paired_pi_controls:
                lookup_stats['initial_inventory_sha256'] = content_hash({
                    field: sorted(item['id'] for item in scoped_graph.get(field, []))
                    for field in ('entity_types', 'event_definitions', 'attribution_paths', 'event_families')
                })
            result = _run_scoped(database, question, scoped_graph, lookup=lookup, recover_gaps=recover_gaps, **options)
            lookup_stats.update(lookup.stats)
        index = scoped_graph['eeg_cache'].get('index', {})
        lookup_stats.update(index)
    else:
        result = _run_scoped(database, question, graph, **options)
    io_after = process_io()
    result['manifest']['measurements'] = {
        'wall_seconds': perf_counter() - started, 'lookup': lookup_stats,
        'process_io_delta': {key: io_after[key] - io_before[key] for key in io_before.keys() & io_after.keys()},
        'provider_usage': summarize_usage(metered.requests, rates_per_million),
        'understand_seconds': understand_seconds,
        'construction_usage': summarize_usage(metered.requests[:build_calls], rates_per_million),
        'request_usage': summarize_usage(metered.requests[build_calls:], rates_per_million),
    }
    return result


def _run_scoped(database, question, graph, *, client, interpret, model, response_cache,
                max_revisions, max_candidates, semantic_top_k, evidence_retrieval, few_shot,
                lookup=None, recover_gaps=False, rates_per_million=None, paired_pi_controls=False):
    """PURPOSE: Bind scoped PI and the selected executable dependencies to the existing pipeline.
    INPUT: Public source DB, request, scoped graph, existing interpreter and optional index session.
    OUTPUT: Original pipeline contract with immutable request-local EEG projections.
    """
    validate_runtime_graph(graph)
    arguments = dict(client=client, model=model, selector_cache=response_cache,
                     max_revisions=max_revisions, max_candidates=max_candidates, semantic_top_k=semantic_top_k,
                     evidence_retrieval=evidence_retrieval, few_shot=few_shot)
    before = len(client.requests)
    recovery_inputs = []
    recovery_time = 0.0

    budget = client.pi_request_budget
    client.pi_active = True
    graph_lookup = lookup is not None and graph.get('index_scope', {}).get('mode') == 'graph'

    def load_recovery(current, *, charged=False):
        """PURPOSE: Record a scoped candidate read triggered by incomplete native PI.
        INPUT: Immutable graph and whether the lookup was already reserved. OUTPUT: Local candidate/source evidence."""
        nonlocal recovery_time
        if not charged:
            budget.reserve_lookup()
        started = perf_counter()
        scope = current.get('index_scope') or {}
        if scope.get('projection') == 'semantic':
            current = lookup.case_graph(scope['selected_case_ids'], include_peers=True)
        loaded = lookup.recovery_graph(current)
        recovery_time += perf_counter() - started
        recovery_inputs.append(loaded)
        return loaded

    def load_case_definitions(identifiers):
        """PURPOSE: Read Case-attributed EDs after the existing candidate-selection call.
        INPUT: IDs proposed from the case catalog. OUTPUT: Full dependency closure for those Case IDs.
        """
        budget.reserve_lookup()
        started = perf_counter()
        resolved = lookup.case_graph(identifiers, include_peers=True, for_pi=True)
        lookup.stats['case_expansion_seconds'] = perf_counter() - started
        resolved['index_scope'].update(mode='graph', literal_case=False, deferred_cases=True)
        lookup.stats['case_deferred'] = True
        return resolved

    def hydrate_pi_paths(paths):
        """PURPOSE: Load the witnesses required by a multi-path PI check.
        INPUT: Selected semantic path headers. OUTPUT: Hydrated paths in original order.
        """
        if any(path.get('execution_map_id') for path in paths):
            budget.reserve_lookup()
        return lookup.hydrate_paths(paths)

    def case_hints(phrases):
        """PURPOSE: Rank Case cards by grounded activity hints.
        INPUT: Request phrases. OUTPUT: Registry of candidate Case and ED IDs.
        """
        budget.reserve_lookup()
        return lookup.case_hints(phrases)

    can_recover = lookup is not None and recover_gaps
    extra = {'recovery_loader': load_recovery} if can_recover and not graph_lookup else {}
    if lookup is not None and graph.get('index_scope', {}).get('mode') == 'graph':
        extra['path_loader'] = hydrate_pi_paths
        if graph['index_scope'].get('deferred_cases'):
            extra.update(case_definition_loader=load_case_definitions, case_hint_lookup=case_hints)
    query = interpret(question, graph, **arguments, **extra)
    scope = graph.get('index_scope', {})
    first_coverage = query.get('process_interpretation_trace', {}).get('retrieval_coverage', [])
    missing = {identifier for receipt in first_coverage for identifier in receipt['retrieval_gaps']}
    if graph_lookup and missing and scope.get('projection') == 'semantic' and budget.allow_lookup():
        expanded = lookup.case_graph(scope['selected_case_ids'], include_peers=True)
        if missing <= {ed['id'] for ed in expanded['event_definitions']}:
            lookup.stats['expanded_for_missing_evidence'] = True
            lookup.stats['expanded_same_case'] = True
            graph = expanded
            query = interpret(question, graph, **arguments,
                              **({'recovery_loader': load_recovery} if can_recover else {}))
            query['process_interpretation_trace']['initial_retrieval_coverage'] = first_coverage
            missing.clear()

    if graph_lookup and not missing and query.get('status') != 'ready' and not scope.get('exhaustive_cases'):
        info = query.get('process_information') or {}
        spans = [row['span'] for row in info.get('activity_requirement_results', [])
                 if row['status'] != 'verified' and row.get('span') and row['span'] in question]
        if spans and budget.allow_lookup():
            expanded, receipt = lookup.expand_requirements(graph, spans)
            lookup.stats['requirement_lookup'] = receipt
            if expanded is not graph:
                graph = expanded
                lookup.stats['expanded_other_cases'] = True
                query = interpret(question, graph, **arguments, path_loader=hydrate_pi_paths)
        if query.get('status') != 'ready' and budget.allow_lookup():
            # Comparison uses the same projected candidates for both modes at broad retry.
            broader = (lookup.case_graph(include_peers=True, for_pi=True) if paired_pi_controls else
                       lookup.case_graph(event_ids=set(), case_catalog=True))
            if set(broader['index_scope']['selected_case_ids']) - set(graph['index_scope']['selected_case_ids']):
                lookup.stats['expanded_other_cases'] = True
                broader['index_scope'].update(mode='graph', deferred_cases=not paired_pi_controls)
                graph = broader
                deferred_loaders = {} if paired_pi_controls else dict(
                    case_definition_loader=load_case_definitions, case_hint_lookup=case_hints)
                query = interpret(question, graph, **arguments, path_loader=hydrate_pi_paths, **deferred_loaders)
    initial_calls = len(client.requests)
    if graph_lookup and can_recover and not missing and query.get('status') == 'partial':
        if any(set(row.get('reason_codes', ())) & GAPS for row in
               query.get('process_information', {}).get('activity_requirement_results', [])) and budget.allow_lookup():
            query = interpret(question, graph, **arguments, path_loader=hydrate_pi_paths,
                              recovery_loader=load_recovery)
    if lookup is not None:
        lookup.stats['path_execution_maps_read_during_pi'] = lookup.stats.get('path_execution_maps_read', 0)
    pi = query.get('process_information') or {}
    recovery_started = perf_counter()
    recovery = {'native_resolved': query.get('status') == 'ready' and not pi.get('recovered_event_decisions'),
                'triggered': bool(recovery_inputs or pi.get('recovered_event_decisions')),
                'source': {'status': 'not_applicable'}}
    if can_recover and not missing and not budget.exhausted and query.get('status') == 'partial' and any(
            r['status'] != 'verified' and set(r.get('reason_codes', ())) & GAPS
            for r in pi.get('activity_requirement_results', [])) and budget.allow_lookup():
        local = recovery_inputs[-1] if recovery_inputs else load_recovery(graph, charged=True)
        overlay, receipt = recover_source_graph(local, pi)
        recovery.update(triggered=True, source=receipt)
        if overlay is not local:
            revised = interpret(question, overlay, **arguments)
            revised_pi = revised.get('process_information') or {}
            new_selection = set(revised_pi.get('selected_event_definition_ids', [])) & set(receipt['definition_ids'])
            if (revised.get('status') == 'ready' and new_selection and
                    revised_pi.get('case_notion_et_id') == pi.get('case_notion_et_id')):
                query, pi, graph = revised, revised_pi, overlay
                recovery['source']['selected_definition_ids'] = sorted(new_selection)
                recovery['source']['status'] = 'accepted'
            else:
                recovery['source']['status'] = 'pi_recheck_unresolved'
    recovery['succeeded'] = bool(pi.get('recovered_event_decisions') or recovery['source']['status'] == 'accepted')
    recovery['added_provider_usage'] = summarize_usage(client.requests[initial_calls:], rates_per_million)
    recovery['initial_interpretation_calls'] = initial_calls - before
    recovery['elapsed_seconds'] = perf_counter() - recovery_started + recovery_time
    if client.pi_request_budget.exhausted:
        query = {**query, 'status': 'partial', 'termination_reason': client.pi_request_budget.exhausted}
    client.pi_active = False
    execution_graph = graph
    pi = query.get('process_information') or {}
    if lookup is not None and query.get('status') == 'ready' and pi.get('case_notion_et_id'):
        if pi.get('recovered_event_decisions'):
            execution_graph = recovery_inputs[-1] if recovery_inputs else graph
        elif recovery['source']['status'] != 'accepted':
            path_ids = {path for paths in (pi.get('verified_attribution_paths') or {}).values() for path in paths}
            execution_graph = lookup.case_graph([pi['case_notion_et_id']], event_ids=pi['selected_event_definition_ids'],
                                                path_ids=path_ids)
    from src.common.event_definition_eligibility import graph_for_selection
    view = query.get('process_view', {})
    verified_graph = graph_for_selection(execution_graph, view)
    if query.get('status') == 'ready':
        pi_source = (recovery_inputs[-1] if recovery_inputs else graph) if pi.get('recovered_event_decisions') else graph
        verified_pi_graph = graph_for_selection(pi_source, view)
        query['pi_contract_version'] = CONTRACT_VERSION
        query['execution_contract'] = freeze_execution_contract(verified_pi_graph, query)
    dependencies = execution_dependencies(verified_graph, query)
    if dependencies['status'] == 'incomplete':
        retrieval = {'status': 'incomplete', 'missing_dependencies': dependencies['missing']}
        es = {'es_version': 6, 'status': 'selection_required',
              'reason_code': 'missing_execution_dependencies', 'dependency_closure': dependencies}
    else:
        retrieval = retrieve_subgraph(execution_graph, query)
        es = build_extraction_specification(execution_graph, query, retrieval)
    manifest = pipeline_manifest(
        graph, query, pv_selector="llm_graph", selector="deterministic_pi_materializer",
        db_understanding="native", model=model, verify_and_repair=True,
        max_hops=MAX_ATTRIBUTION_HOPS, max_revisions=max_revisions)
    manifest["step3"].update(status=es.get("status"), selector=es.get("selector"),
                             dependency_closure=dependencies,
                             executable_graph_counts={k: len(execution_graph.get(k, []))
                                 for k in ('entity_types', 'event_definitions', 'attribution_paths')})
    manifest["step2"]["semantic_graph_counts"] = {k: len(graph.get(k, []))
                                 for k in ('entity_types', 'event_definitions', 'attribution_paths')}
    manifest['step2']['request_budget'] = vars(client.pi_request_budget).copy()
    manifest['recovery'] = recovery
    query.setdefault("runtime_manifest", {})["pipeline"] = manifest
    verification, execution = None, {}
    terminal_status = {"partial": "partial", "invalid_llm_output": "failed"}.get(query.get("status"), "unresolved")
    if (es.get("status") in {"accepted", "validation_failed"}
            or es.get("build_result", {}).get("next_action") == "verify_or_repair"):
        result = run_repair_pipeline(database, query.get("process_view", {}), es,
                                     graph=execution_graph, retrieval=retrieval, client=client, model=model)
        es = result["es"]
        verification = compact_repair_result(result)
        execution = result["report"].get("execution", {})
        query.update(step3_execution=result["baseline_execution"],
                     physical_verification=verification, execution=execution)
        manifest["step3"]["verification_and_repair"].update(status=result["status"],
                                                          terminal_status=result["terminal_status"])
        if result["terminal_status"] == "accepted" and result["report"]["hard_passed"] and execution.get("passed"):
            terminal_status = "accepted"
        elif result["status"] == "needs_step2_revision":
            terminal_status = "unresolved"
        else:
            terminal_status = "failed"
        if terminal_status != "accepted" and es.get("status") == "accepted":
            es = {**es, "status": "validation_failed", "reason_code": "full_validation_failed"}
    manifest["step3"]["status"] = manifest["status"] = es.get("status")
    manifest["terminal_status"] = terminal_status
    query["extraction_terminal_status"] = terminal_status
    diagnostic = execution if terminal_status != "accepted" else {}
    if diagnostic:
        query["diagnostic_execution"] = diagnostic
        query.pop("execution", None)
        execution = {}
    return {"graph": execution_graph, "semantic_graph": graph, "execution_graph": execution_graph,
            "query": query, "retrieval": retrieval,
            "es": es, "execution": execution, "diagnostic_execution": diagnostic,
            "terminal_status": terminal_status, "verification": verification, "manifest": manifest}
