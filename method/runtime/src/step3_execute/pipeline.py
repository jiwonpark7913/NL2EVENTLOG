"""Fixed-Process-View validation, failure localization, and targeted ES repair."""

from __future__ import annotations
import copy
import statistics
import time
import hashlib
from pathlib import Path
from src.common.database_io import SQL_COUNTER
from collections import Counter, defaultdict
from src.step3_execute.compile_event_log_sql import ESValidationError, downgrade_es_v5_to_v4, extract_event_log, compile_es, upgrade_es_v4_to_v5, validate_es as compiler_validate, selected_definition_issues
from src.common.schema_metadata import stable_id, database_fingerprint
REQUIRED_RULE_SLOTS = ('source', 'event_identity', 'activity', 'timestamp', 'case_attribution')
from src.common.llm_usage import DEFAULT_MODEL


def _issue(code, level, target, message, **evidence):
    """PURPOSE: Create one machine-readable validation or diagnostic signal.
    INPUT: Stable code, hard/diagnostic level, repair target, message and evidence fields.
    OUTPUT: Normalized issue dictionary; no side effects.
    """
    return {'code': code, 'level': level, 'repair_target': target, 'message': message,
            'evidence': evidence}


def structural_validation(process_view, es, *, validated_replacements=None):
    """PURPOSE: Check fixed Process View coverage and v5 source/rule completeness.
    INPUT: Immutable Process View, v4/v5 ES and optional source replacement mapping.
    OUTPUT: Hard issues; neither Process View nor ES is modified.
    """
    issues = []
    validated_replacements = validated_replacements or {}
    try:
        normalized = upgrade_es_v4_to_v5(es) if es.get('es_version') == 4 else copy.deepcopy(es)
        expanded = downgrade_es_v5_to_v4(normalized)
    except (ESValidationError, KeyError, TypeError, ValueError) as error:
        return {'passed': False, 'missing_activities': [], 'extra_activities': [],
                'issues': [_issue('source_contract_invalid', 'hard', 'source',
                                  'ES cannot be normalized to the v5 source contract.',
                                  error=str(error))]}
    if not process_view or normalized.get('process_view') != process_view:
        issues.append(_issue('process_view_mutated', 'hard', 'none',
                             'Repair cannot revise or replace the upstream Process View.'))
        return {'passed': False, 'issues': issues}
    definitions = selected_definition_issues(normalized)
    if definitions is not None:
        # PI-selected Event definition IDs decide membership; labels are attached only as evidence.
        requested = {event_definition_id: item.get('conceptual_activity_label')
                     for item in process_view.get('activity_provenance', [])
                     for event_definition_id in item.get('event_definition_ids', [])}
        realized = {str(rule.get('source_event_definition_id')): rule.get('label')
                    for rule in normalized.get('event_rules', [])}
        missing, extra = definitions['missing'], definitions['extra']
        if missing:
            issues.append(_issue('activity_missing', 'hard', 'rule',
                                 'PI-selected Event definitions are absent from ES.', event_definition_ids=missing,
                                 activities=sorted({requested.get(item) or item for item in missing})))
        if extra:
            issues.append(_issue('activity_extra', 'hard', 'rule',
                                 'ES contains Event definitions the PI did not select.', event_definition_ids=extra,
                                 activities=sorted({realized.get(item) or item for item in extra})))
        if definitions['unidentified_rules'] or definitions['selection_mismatch']:
            issues.append(_issue('definition_contract_invalid', 'hard', 'none',
                                 'Event rules and the PI selection cannot be matched by Event definition ID.',
                                 rule_ids=definitions['unidentified_rules'],
                                 selection_mismatch=definitions['selection_mismatch']))
    else:
        targets = set(process_view.get('target_activities', []))
        labels = [rule.get('label') for rule in normalized.get('event_rules', [])]
        grounded = {label for label in labels if label}
        missing, extra = sorted(targets - grounded), sorted(grounded - targets)
        if missing:
            issues.append(_issue('activity_missing', 'hard', 'rule',
                                 'Process View activities are absent from ES.', activities=missing))
        if extra:
            issues.append(_issue('activity_extra', 'hard', 'rule',
                                 'ES contains activities outside the fixed Process View.', activities=extra))
    source_by_rule = {rule['id']: rule.get('source_id')
                      for rule in [*normalized.get('event_rules', []),
                                   *normalized.get('selection_rules', [])]}
    for rule in [*expanded.get('event_rules', []), *expanded.get('selection_rules', [])]:
        absent = [slot for slot in REQUIRED_RULE_SLOTS if not rule.get(slot)]
        if absent:
            issues.append(_issue('grounding_incomplete', 'hard', 'rule',
                                 'Required materialized rule slots are absent.',
                                 rule_id=rule.get('id'), slots=absent))
            continue
        activity_kind = rule['activity'].get('kind')
        source_condition = rule.get('source_condition', {})
        if activity_kind in ('row_activity_value', 'code_mapping', 'column') and not rule['activity'].get('column'):
            issues.append(_issue('encoding_inconsistent', 'hard', 'rule',
                                 'Row activity encoding has no carrier column.', rule_id=rule.get('id')))
        if activity_kind == 'constant' and source_condition.get('kind') == 'in':
            issues.append(_issue('encoding_inconsistent', 'hard', 'rule',
                                 'Column event is paired with a row-value carrier filter.', rule_id=rule.get('id')))
        attribution = rule['case_attribution']
        if not attribution.get('anchor') or not attribution.get('local_event_key'):
            issues.append(_issue('case_attribution_incomplete', 'hard', 'source',
                                 'Event Source attribution lacks anchor or local key.',
                                 source_id=source_by_rule.get(rule.get('id'))))
        source_id = source_by_rule.get(rule.get('id'))
        if source_id in validated_replacements:
            issues.append(_issue('case_multiplicity_policy_violated', 'hard', 'source',
                                 'Single-case policy is violated and a validated source replacement exists.',
                                 source_id=source_id,
                                 current_max_cases_per_event=rule.get('data_validation', {})
                                 .get('connection', {}).get('max_cases_per_event')))
    return {'passed': not issues, 'missing_activities': missing, 'extra_activities': extra,
            'issues': issues}


def execution_key(database, es):
    """PURPOSE: Bind a reusable execution to its DB, specification, and compiler code.
    INPUT: SQLite path and ES. OUTPUT: Stable digest; no SQL execution or writes.
    """
    from src.step3_execute import compile_event_log_sql
    from src.common import entity_population, schema_metadata, timestamp_policy
    paths = [Path(module.__file__) for module in
             (compile_event_log_sql, entity_population, schema_metadata, timestamp_policy)]
    compiler_hash = hashlib.sha256(b''.join(path.read_bytes() for path in paths)).hexdigest()
    return stable_id('execution', [database_fingerprint(database), compiler_hash,
                                   {**es, 'status': 'accepted'}])


def reusable_execution(database, es, execution):
    """PURPOSE: Check the local cache contents and bind them to the current extraction inputs.
    INPUT: DB, ES and an optional previously measured execution. OUTPUT: Matching execution or None.
    """
    if not execution or not execution.get('passed') or execution.get('execution_key') != execution_key(database, es):
        return None
    contents = [execution.get(k) for k in ('sql', 'event_log', 'diagnostics')]
    return execution if execution.get('result_digest') == stable_id('result', contents) else None


def execution_validation(database, es):
    """PURPOSE: Compile and execute ES-derived SQL without repairing SQL text directly.
    INPUT: SQLite database path and ES expected to pass structural validation.
    OUTPUT: Execution report containing SQL/log/diagnostics or a localized hard issue.
    """
    compiler = compiler_validate(es)
    if not compiler['passed']:
        issue = _issue('compiler_contract_invalid', 'hard', 'physical_binding',
                       'ES cannot be compiled deterministically.', compiler_issues=compiler['issues'])
        return {'passed': False, 'issues': [issue], 'sql': None, 'event_log': None, 'diagnostics': None}
    try:
        counter = SQL_COUNTER.get()
        if counter is not None:
            counter.update(['extractions'])
        key = execution_key(database, es)
        sql, rows, diagnostics = extract_event_log(database, es)
        if key != execution_key(database, es):
            raise ValueError('database_snapshot_changed')
        return {'passed': True, 'issues': [], 'sql': sql, 'event_log': rows, 'diagnostics': diagnostics,
                'execution_key': key, 'result_digest': stable_id('result', [sql, rows, diagnostics])}
    except (ESValidationError, KeyError, TypeError, ValueError) as error:
        issue = _issue('sql_execution_failed', 'hard', 'physical_binding',
                       'Deterministic SQL execution failed; repair ES, not generated SQL.',
                       error_type=type(error).__name__, error=str(error))
        return {'passed': False, 'issues': [issue], 'sql': compile_es(es), 'event_log': None, 'diagnostics': None}
    except Exception as error:
        issue = _issue('database_execution_failed', 'hard', 'physical_binding',
                       'Database rejected deterministic SQL.', error_type=type(error).__name__, error=str(error))
        return {'passed': False, 'issues': [issue], 'sql': compile_es(es), 'event_log': None, 'diagnostics': None}


def _distribution(values):
    """PURPOSE: Summarize a finite integer distribution without external dependencies.
    INPUT: Sequence of counts.
    OUTPUT: count/min/max/mean/median mapping; empty input returns null extrema.
    """
    if not values:
        return {'count': 0, 'min': None, 'max': None, 'mean': None, 'median': None}
    return {'count': len(values), 'min': min(values), 'max': max(values),
            'mean': sum(values) / len(values), 'median': statistics.median(values)}


def extraction_diagnostics(es, event_log, execution_diagnostics, *, thresholds=None):
    """PURPOSE: Measure suspicious event-log behavior without declaring distributional facts erroneous.
    INPUT: ES, extracted row dictionaries, compiler diagnostics, optional warning thresholds.
    OUTPUT: Metrics and diagnostic-only signals for singleton, coverage, fan-out, nulls and time.
    """
    thresholds = thresholds or {}
    by_case, activity_cases = defaultdict(list), defaultdict(set)
    exact = Counter()
    for row in event_log:
        by_case[row.get('case_id')].append(row)
        activity_cases[row.get('activity')].add(row.get('case_id'))
        exact[(row.get('case_id'), row.get('event_id'), row.get('activity'), row.get('timestamp'))] += 1
    case_count = len(by_case)
    activity_counts = {case: len({row.get('activity') for row in rows}) for case, rows in by_case.items()}
    event_counts = {case: len(rows) for case, rows in by_case.items()}
    singleton_activity = sum(value == 1 for value in activity_counts.values()) / case_count if case_count else None
    singleton_event = sum(value == 1 for value in event_counts.values()) / case_count if case_count else None
    activity_coverage = {activity: len(cases) / case_count if case_count else None
                         for activity, cases in sorted(activity_cases.items())}
    duplicate_rows = sum(count - 1 for count in exact.values())
    null_case_rows = sum(row.get('case_id') is None for row in event_log)
    null_timestamp_rows = sum(row.get('timestamp') is None for row in event_log)
    normalized = upgrade_es_v4_to_v5(es) if es.get('es_version') == 4 else es
    referenced = {rule.get('source_id') for rule in normalized.get('event_rules', [])}
    attribution = {
        source_id: normalized.get('event_sources', {}).get(source_id, {})
        .get('data_validation', {}).get('connection', {})
        for source_id in referenced}
    timestamp_null_pairs = sum(value.get('null_timestamp_pairs', 0) for value in attribution.values())
    source_output_pairs = sum(value.get('output_rows', 0) for value in attribution.values())
    max_fanout = max((value.get('max_cases_per_event', 0) for value in attribution.values()), default=0)
    metrics = {
        'case_count_in_log': case_count,
        'event_count': len(event_log),
        'singleton_activity_ratio': singleton_activity,
        'singleton_event_ratio': singleton_event,
        'events_per_case': _distribution(list(event_counts.values())),
        'activities_per_case': _distribution(list(activity_counts.values())),
        'activity_case_coverage': activity_coverage,
        'exact_duplicate_rows': duplicate_rows,
        'null_case_rows': null_case_rows,
        'null_timestamp_rows': null_timestamp_rows,
        'max_cases_per_source_event': max_fanout,
        'attribution_coverage_by_source': {key: value.get('event_to_case_coverage') for key, value in attribution.items()},
        'attribution_coverage_by_rule': {rule['id']: attribution.get(rule.get('source_id'), {}).get('event_to_case_coverage')
                                         for rule in normalized.get('event_rules', [])},
        'profiled_null_timestamp_ratio': timestamp_null_pairs / source_output_pairs if source_output_pairs else None,
        'dropped_key_rows_by_source': execution_diagnostics.get('dropped_key_rows_by_source', []),
        'dropped_key_rows_by_rule': execution_diagnostics.get('dropped_key_rows_by_rule', []),
        'temporal_plausibility': {'status': 'not_evaluated',
            'reason': 'Observed order alone is not a normative constraint; sourced temporal rules are required.'},
    }
    signals = []
    singleton_limit = thresholds.get('singleton_activity_ratio')
    if singleton_limit is not None and singleton_activity is not None and singleton_activity > singleton_limit:
        signals.append(_issue('singleton_ratio_high', 'diagnostic', 'multi_cause',
                              'Many extracted cases contain one distinct activity.',
                              value=singleton_activity, threshold=singleton_limit))
    coverage_limit = thresholds.get('activity_case_coverage')
    if coverage_limit is not None:
        low = {activity: value for activity, value in activity_coverage.items() if value < coverage_limit}
        if low:
            signals.append(_issue('activity_case_coverage_low', 'diagnostic', 'multi_cause',
                                  'Some activities occur in few extracted cases.', values=low,
                                  threshold=coverage_limit))
    event_min = thresholds.get('events_per_case_min')
    event_max = thresholds.get('events_per_case_max')
    unusual_cases = {case: count for case, count in event_counts.items()
                     if (event_min is not None and count < event_min)
                     or (event_max is not None and count > event_max)}
    if unusual_cases:
        signals.append(_issue('events_per_case_unusual', 'diagnostic', 'multi_cause',
                              'Some cases fall outside configured event-count bounds.',
                              cases=unusual_cases, minimum=event_min, maximum=event_max))
    attribution_limit = thresholds.get('attribution_coverage')
    if attribution_limit is not None:
        low_rules = {key: value.get('event_to_case_coverage') for key, value in attribution.items()
                     if value.get('event_to_case_coverage') is not None
                     and value.get('event_to_case_coverage') < attribution_limit}
        if low_rules:
            signals.append(_issue('case_attribution_coverage_low', 'diagnostic', 'case_attribution',
                                  'Some event rules connect few candidate events to the anchor.',
                                  rules=low_rules, threshold=attribution_limit))
    if duplicate_rows:
        signals.append(_issue('duplicate_rows_observed', 'hard', 'case_attribution',
                              'Exact duplicate event rows survived extraction.', count=duplicate_rows))
    if null_case_rows:
        signals.append(_issue('null_case_in_log', 'hard', 'case_attribution',
                              'Extracted log contains events without a case identifier.',
                              count=null_case_rows))
    if null_timestamp_rows:
        signals.append(_issue('null_timestamp_in_log', 'hard', 'physical_binding',
                              'Extracted log contains events without a timestamp.',
                              count=null_timestamp_rows))
    if max_fanout > thresholds.get('max_cases_per_event', float('inf')):
        signals.append(_issue('fanout_high', 'diagnostic', 'case_attribution',
                              'A source event maps to many cases; N:M may be valid.', value=max_fanout,
                              threshold=thresholds['max_cases_per_event']))
    if timestamp_null_pairs:
        signals.append(_issue('timestamp_nulls_profiled', 'diagnostic', 'physical_binding',
                              'Timestamp-null source pairs were dropped by policy.', count=timestamp_null_pairs))
    return {'metrics': metrics, 'signals': signals,
            'hard_failure': any(signal['level'] == 'hard' for signal in signals)}


def localize_repair(structural, execution, extraction, retrieval=None):
    """PURPOSE: Map validation signals to bounded ES repair targets and candidate search order.
    INPUT: Three validation reports and optional retrieval candidate inventory.
    OUTPUT: Ordered actions; diagnostic-only signals never become automatic edits alone.
    """
    retrieval = retrieval or {}
    issues = [*structural.get('issues', []), *execution.get('issues', []),
              *extraction.get('signals', [])]
    replacement_inventory = retrieval.get('validated_replacement_candidates', {})
    actions = []
    source_codes = {'duplicate_rows_observed', 'case_multiplicity_policy_violated',
                    'case_attribution_incomplete', 'case_attribution_coverage_low',
                    'source_contract_invalid', 'compiler_contract_invalid'}
    rule_codes = {'activity_missing', 'activity_extra', 'null_timestamp_in_log',
                  'timestamp_nulls_profiled', 'encoding_inconsistent', 'grounding_incomplete'}
    for issue in issues:
        target = ('source' if issue['code'] in source_codes else
                  'rule' if issue['code'] in rule_codes else issue['repair_target'])
        action = {'signal_code': issue['code'], 'repair_target': target,
                  'automatic_eligible': issue['level'] == 'hard' and target != 'none',
                  'requires_candidate_validation': True}
        if issue['code'] == 'activity_missing':
            missing = set(issue['evidence']['activities'])
            residual = [candidate['id'] for activity, values in retrieval.get('residual_rule_candidates', {}).items()
                        if activity in missing for candidate in values]
            alternatives = [candidate['id'] for activity, values in retrieval.get('event_rule_candidates', {}).items()
                            if activity in missing for candidate in values]
            action.update({'activities': sorted(missing),
                           'search_order': ['residual_same_carrier', 'grounding_alternatives', 'bounded_wider_search'],
                           'residual_candidate_ids': sorted(set(residual)),
                           'alternative_candidate_ids': sorted(set(alternatives))})
        elif issue['code'] == 'activity_extra':
            action.update({'activities': issue['evidence']['activities'], 'operation': 'remove_extra_rules'})
        elif target == 'source':
            action['search_order'] = ['alternative_case_path', 'alternative_case_key', 'cardinality_review']
            action['validated_path_candidate_ids'] = list(replacement_inventory.get('paths', []))
        elif target == 'rule':
            action['search_order'] = ['schema_reference', 'timestamp_candidate', 'filter_and_type', 'compiler_bug_review']
            action['validated_timestamp_candidate_ids'] = list(
                replacement_inventory.get('timestamps', []))
        elif issue['repair_target'] == 'multi_cause':
            action.update({'automatic_eligible': False,
                           'search_order': ['activity_coverage', 'source_grounding', 'case_attribution', 'timestamp_filter']})
        actions.append(action)
    return {'actions': actions, 'automatic_action_count': sum(a['automatic_eligible'] for a in actions),
            'process_view_repair_allowed': False}


def run_repair_pipeline(database, process_view, es, *, retrieval=None,
                        validated_candidate_rules=(), validated_replacements=None,
                        thresholds=None, graph=None, candidate_selector=None,
                        client=None, model=DEFAULT_MODEL, baseline_execution=None, limits=None, decider=None):
    """PURPOSE: Verify a fixed PI and repair only witnessed physical ES defects.
    INPUT: Read-only DB, PI, ES, EEG and optional previously executed baseline/decision provider.
    OUTPUT: Compatible caller status plus terminal status, final artifacts, findings and measured cost.
    """
    from src.step3_execute.repair.verify_and_repair_specification import verify_and_repair
    from src.common.runtime_input_contract import require_no_oracle_payload
    from src.common.event_definition_eligibility import graph_for_selection
    graph = graph_for_selection(graph, process_view)
    require_no_oracle_payload(es)
    require_no_oracle_payload(retrieval or {})
    if decider is not None and candidate_selector is not None:
        raise ValueError('Provide one decision provider')
    baseline_execution = reusable_execution(database, es, baseline_execution)
    cost = Counter(extractions=0, sql_statements=0, witness_queries=0, llm_calls=0)
    token = SQL_COUNTER.set(cost)
    started = time.monotonic()
    try:
        result = verify_and_repair(database, process_view, es, graph, retrieval, thresholds,
                                   client, model, decider, baseline_execution, limits, cost,
                                   legacy_selector=candidate_selector)
    finally:
        SQL_COUNTER.reset(token)
    execution = result.get('report', {}).get('execution', {})
    if result.get('report', {}).get('hard_passed') and execution.get('passed'):
        info = (process_view or {}).get('process_information') or {}
        executed = {r.get('source_event_definition_id') for r in result['es'].get('event_rules', [])}
        used = sorted(executed.intersection(info.get('tier2_approvals', {})))
        execution['event_log_metadata'] = {'used_tier2':bool(used), 'tier2_definition_ids':used}
    result['cost'] = {**cost, 'elapsed_seconds': time.monotonic() - started}
    return result


def compact_repair_result(result):
    """PURPOSE: Remove bulky SQL/log payloads while preserving repair audit evidence.
    INPUT: Result returned by run_repair_pipeline or automatic_repair_cycle.
    OUTPUT: JSON-safe audit summary with execution counts, signals, patch and statuses.
    """
    compact = copy.deepcopy({key: value for key, value in result.items() if key not in {'es','baseline_execution'}})
    for report_name in ('report', 'initial_report'):
        report = compact.get(report_name)
        if not report:
            continue
        execution = report.get('execution', {})
        rows = execution.pop('event_log', None)
        execution['event_log_rows'] = len(rows) if rows is not None else None
        execution['sql_generated'] = bool(execution.pop('sql', None))
        diagnostics = execution.get('diagnostics')
        if diagnostics:
            execution['diagnostics'] = {
                'row_count': diagnostics.get('row_count'),
                'identity_conflicts': diagnostics.get('identity_conflicts'),
                'dropped_key_rows_by_source': diagnostics.get('dropped_key_rows_by_source', []),
                'dropped_key_rows_by_rule': diagnostics.get('dropped_key_rows_by_rule', []),
                'compilation_plan': diagnostics.get('sql_package', {}).get('compilation_plan'),
            }
    return compact
