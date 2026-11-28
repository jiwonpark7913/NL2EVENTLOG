"""Shared S0/S2 binding, materialization and stage-local publication."""

from collections import Counter
from time import perf_counter

from src.common.database_io import SQL_COUNTER
from src.common.schema_metadata import database_fingerprint, stable_id
from src.common.validate_extraction_contract import validate_unified
from src.step2_retrieve_and_interpret.minimal_pipeline import structural_view
from src.step3_execute.materialize_extraction_specification import materialize_pi_selection
from src.step3_execute.pipeline import compact_repair_result
from src.step3_execute.repair.verify_and_repair_specification import diagnose
from src.step3_execute.verify_execution_dependencies import (
    CONTRACT_VERSION, bound_execution_dependencies, freeze_execution_contract,
)

from development.s2.scoped_union import verify_scoped_unions


def _materialize(graph, question, view, intent, unions):
    """PURPOSE: Build the unchanged compiler's ESpec plus authenticated scoped branch evidence.
    INPUT: Bound view, original graph and scoped union receipts. OUTPUT: Ready or rejected ESpec.
    """
    es = materialize_pi_selection(graph, question, view, intent)
    if es['status'] != 'accepted' or not unions:
        return es
    for rule in es['event_rules']:
        proof = unions.get(rule['source_event_definition_id'], {})
        if proof.get('union_id'):
            # The compiler's topology exemption requires independent proof of a functional union.
            # This proof is scoped and does not replace any path-local coverage certificate.
            rule['decision'].update(partition_id=proof['union_id'], partition_verified_complete=True)
    stable = {key: value for key, value in es.items() if key != 'id'}
    es['id'] = stable_id('es', stable)
    return es


def execute_stage3(database, graph, view, es):
    """PURPOSE: Verify, execute and publish once without selecting another physical or semantic premise.
    INPUT: Read-only DB, validated dependency graph, frozen PI and deterministic ESpec.
    OUTPUT: Compatible terminal receipt and diagnostics, with no candidate search or LLM.
    """
    if es['database_fingerprint'] != database_fingerprint(database):
        return {'status': 'failed', 'reason': 'database_snapshot_changed', 'sql': None, 'rows': []}
    started = perf_counter()
    cost = Counter(extractions=0, sql_statements=0, witness_queries=0, llm_calls=0)
    token = SQL_COUNTER.set(cost)
    try:
        report = validate_unified(es, process_view=view, graph=graph, database=database, phase='full')
        findings = diagnose(es, report, graph)
    finally:
        SQL_COUNTER.reset(token)
    execution = report['execution']
    current = es['database_fingerprint'] == database_fingerprint(database)
    violations = [item for item in findings if item['severity'] == 'violation']
    accepted = current and report['hard_passed'] and execution['passed'] and not violations
    reason = ('not_needed' if accepted else 'database_snapshot_changed' if not current else
              'needs_step2_revision' if report['next_action'] == 'needs_step2_revision' else 'repair_unresolved')
    review = compact_repair_result({'report': report, 'findings': findings,
                                   'status': 'validated' if accepted else 'validation_failed',
                                   'terminal_status': 'accepted' if accepted else 'failed',
                                   'validated_repair': False, 'repair_entered': False, 'attempts': [],
                                   'cost': {**cost, 'elapsed_seconds': perf_counter() - started}})
    return {'status': 'accepted' if accepted else 'failed', 'reason': reason,
            'rows': execution['event_log'] if accepted else [], 'sql': execution['sql'] if accepted else None,
            'execution_review': review}


def execute_selection(database, lookup, projection, evidence, scopes, question, intent, plan):
    """PURPOSE: Bind delivered IDs and run shared deterministic Stage 3.
    INPUT: Public DB, exact graph and model-selected Case/scope/ED paths. OUTPUT: Auditable extraction receipt.
    """
    started = perf_counter()
    outcome = {'status': 'unresolved', 'sql': None, 'rows': [], 'source_format': 'nl2eventlog_compiler_v1',
               'proposed_pi': plan, 'pi': None, 'structural': []}
    view, issues = structural_view(evidence, scopes, plan, intent['activity_mode'])
    if issues:
        return {**outcome, 'reason': 'unbound_selection', 'structural': issues,
                'execution_seconds': perf_counter() - started}
    info = view['process_information']
    case_id = info['case_notion_et_id']
    selected = info['verified_attribution_paths']
    paths = {identifier for group in selected.values() for identifier in group}
    executable = lookup.case_graph([case_id], event_ids=info['selected_event_definition_ids'], path_ids=paths)
    view['entity_population_contract'] = next(e['population'] for e in projection['entity_types'] if e['id'] == case_id)
    binding = {'process_information': info, 'process_view': view, 'pi_contract_version': CONTRACT_VERSION}
    binding['execution_contract'] = freeze_execution_contract(projection, binding)
    checked = bound_execution_dependencies(executable, binding)
    if checked['missing']:
        return {**outcome, 'reason': 'missing_execution_dependencies', 'structural': checked['missing'],
                'execution_seconds': perf_counter() - started}
    unions = verify_scoped_unions(executable, database, info)
    conflicts = {ed: proof for ed, proof in unions.items() if proof['status'] != 'pass'}
    if conflicts:
        reasons = {proof['status'] for proof in conflicts.values()}
        reason = ('conflicting_attribution_union' if 'cross_path_case_conflict' in reasons
                  else 'invalid_attribution_union' if 'invalid_path_union' in reasons
                  else 'documented_multiple_case_assignments_unsupported')
        return {**outcome, 'reason': reason, 'structural': conflicts,
                'execution_seconds': perf_counter() - started}
    equivalent = {}
    for ed, proof in unions.items():
        if proof.get('equivalent_paths'):
            equivalent[ed] = proof['equivalent_paths']
            selected[ed] = equivalent[ed][:1]
    view['fingerprint'] = stable_id('process_view', view)
    es = _materialize(executable, question, view, intent, unions)
    outcome.update(pi=info, es=es, equivalent_path_proofs=equivalent)
    if unions:
        outcome['scoped_attribution_proofs'] = unions
    if es['status'] != 'accepted':
        return {**outcome, 'status': 'failed', 'reason': es.get('reason_code'),
                'execution_seconds': perf_counter() - started}
    extracted = execute_stage3(database, executable, view, es)
    return {**outcome, **extracted, 'case': es['case'], 'execution_seconds': perf_counter() - started}
