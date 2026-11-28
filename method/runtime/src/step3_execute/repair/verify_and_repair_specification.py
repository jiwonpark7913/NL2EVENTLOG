"""Bounded verification and repair of physical ES bindings under a frozen PI."""

from src.common.prompt_loader import load_prompt
from collections import Counter, defaultdict
import copy
import json
import sqlite3
import time
from src.common.llm_usage import experiment_settings
from src.common.runtime_input_contract import require_no_oracle_payload
from src.step3_execute.repair.collect_physical_repair_candidates import collect_repair_candidates, materialize_candidate, refresh_probe_certificates, timestamp_signature, _path_signature
from src.common.validate_extraction_contract import validate_unified
from src.step3_execute.pipeline import execution_validation
from src.step3_execute.compile_event_log_sql import upgrade_es_v4_to_v5
from src.step3_execute.repair.verify_source_row_witnesses import read_witness, verify_changes, check_execution
from src.step3_execute.repair.summarize_event_log_behavior import build_process_summary
from src.common.schema_metadata import database_fingerprint, stable_id, timestamp_columns
DEFAULT_LIMITS = dict(rounds=2, witness_queries=6, per_field=5, candidates=20, timeout_seconds=10)
OPERATIONS = {'path': 'replace_attribution_path', 'timestamp': 'replace_timestamp'}


def diagnose(es, report, graph):
    """PURPOSE: Preserve failed/unknown checks and distinguish physical defects from process signals.
    INPUT: Fixed ES, unified validation and EEG. OUTPUT: Prioritized JSON findings with scoped rule IDs.
    """
    findings = []

    def record(check, severity, rules=(), kind=None, impact=0, **details):
        """PURPOSE: Construct a stable scoped finding. INPUT: Check and measured impact. OUTPUT: Appends one record."""
        scope = sorted(set(rules))
        findings.append(dict(id=stable_id('finding', [check, scope, kind]), check=check, severity=severity,
                             rules=scope, kind=kind, impact=impact, details=details))
    for check in report['checks']:
        if check['status'] == 'fail':
            kind = {'timestamp_binding':'timestamp', 'live_attribution':'path'}.get(check['check'])
            rules = check['evidence_ids'] if kind else []
            impact = sum(report['live_probes'].get(r, {}).get('connection', {}).get('event_rows', 0) for r in rules)
            record(check['check'], 'violation', rules, kind, impact, failure_code=check['failure_code'])
    paths = {p['id']: p for p in (graph or {}).get('attribution_paths', [])}
    definitions = {b['id']: b for b in (graph or {}).get('event_definitions', [])}
    for rule in es.get('event_rules', []):
        source = es.get('event_sources', {}).get(rule.get('source_id'), {})
        attribution = source.get('case_attribution', {})
        path = paths.get(rule.get('attribution_candidate_id') or attribution.get('attribution_candidate_id'))
        if (path and path.get('validation_status') == 'valid' and path.get('event_definition_id') ==
                rule.get('source_event_definition_id') and _path_signature(path.get('joins', [])) != _path_signature(attribution.get('relationship_path', []))):
            record('selected_path_drift', 'violation', [rule['id']], 'path', path_id=path['id'])
        definition = definitions.get(rule.get('source_event_definition_id'), {})
        selected = [t for t in definition.get('timestamp_candidates', []) if t.get('id') and
                    t['id'] == definition.get('ts_id')]
        if selected and timestamp_signature(selected[0]) != timestamp_signature(rule.get('timestamp', {})):
            record('selected_clock_drift', 'violation', [rule['id']], 'timestamp')
    execution = report['execution']
    if execution.get('passed'):
        rows, diagnostics = execution['event_log'], execution['diagnostics']
        labels = set(es.get('process_view', {}).get('target_activities', []))
        summary = build_process_summary(rows, query_id=es.get('id', ''), top_n=10, provenance_limit=0)
        metrics = report['extraction']['metrics']
        population = diagnostics.get('case_population')
        if population is not None:
            members = {r['case_id'] for r in population}
            outside = sum(r['case_id'] not in members for r in rows)
            if outside:
                record('population_escape', 'violation', impact=outside)
            empty = len(members - {r['case_id'] for r in rows})
            metrics.update(case_population_count=len(members), empty_case_count=empty,
                           empty_case_ratio=empty/len(members) if members else None)
            if empty:
                record('empty_cases', 'signal', impact=empty)
        metrics.update(singleton_denominator='cases_with_events', dfg_edges=summary['dfg_edges'],
                       timestamp_ties=summary['timestamp_order_anomalies'])
        observed = {r['activity'] for r in rows}
        missing = labels - observed
        if missing:
            record('zero_activity', 'signal', activities=sorted(missing))
        incident = set()
        by_case = defaultdict(list)
        for r in rows:
            by_case[r['case_id']].append(r)
        repeats = ties = 0
        for trace in by_case.values():
            if len(trace) > 1:
                incident.update(r['activity'] for r in trace)
            repeats += len(trace) - len({r['activity'] for r in trace})
            ties += len(trace) - len({r['timestamp'] for r in trace})
        for code, value in [('repeated_activity', repeats), ('timestamp_tie', ties),
                            ('singleton_cases', summary['singleton_case_count'])]:
            if value:
                record(code, 'signal', impact=value)
        if labels - incident:
            record('isolated_activity', 'signal', activities=sorted(labels - incident))
        for signal in report['extraction'].get('signals', []):
            record(signal['code'], 'violation' if signal['level']=='hard' else 'signal', **{'evidence': signal['evidence']})
        invalid = sum(r.get('activity') in (None, '') for r in rows)
        if invalid:
            record('missing_activity', 'violation', impact=invalid)
        identities = Counter(r.get('source_occurrence_id') for r in rows)
        if identities.get(None):
            record('missing_occurrence_id','violation',impact=identities[None])
        if es.get('es_version')==6 and any(n>1 for n in identities.values()):
            record('duplicate_occurrence','violation',impact=sum(n-1 for n in identities.values()))
    return sorted(findings, key=lambda f: (f['severity'] != 'violation', -f['impact'], f['kind'] != 'path', f['id']))


def decision(packet, client, model, selector):
    """PURPOSE: Select only packet-local identifiers under a strict schema and reject invalid citations.
    INPUT: Public request/PI, finding, candidates and witness aliases. OUTPUT: Checked decision and raw response.
    """
    candidates = packet['candidates']
    operations = sorted({c['operation'] for c in candidates.values()})
    evidence = sorted(packet['evidence'])
    def enum(values):
        """PURPOSE: Encode a closed value set. INPUT: Strings and optional null. OUTPUT: JSON schema."""
        if values == [None]:
            return {'type':'null', 'enum':values}
        return {'type': ['string', 'null'] if None in values else 'string', 'enum': values}
    fields = dict(decision=enum(['KEEP','PATCH','UNRESOLVED']), diagnostic_id=enum(['D1']),
                  hypothesis_code=enum([packet['finding']['check']]), operation=enum([*operations, None]),
                  candidate_id=enum([*candidates, None]), evidence_ids={'type':'array','items':enum(evidence)},
                  reason_code=enum([None,'explained','insufficient_evidence','needs_pi_change']))
    schema = dict(type='object', additionalProperties=False, properties=fields, required=list(fields))
    if selector:
        value = selector(copy.deepcopy(packet), copy.deepcopy(schema))
        raw = value
    else:
        require_no_oracle_payload(packet)
        provider = client.with_options(max_retries=0) if hasattr(client, 'with_options') else client
        alternatives = []
        for action in ('PATCH', 'KEEP', 'UNRESOLVED'):
            options = dict(fields, decision=enum([action]))
            if action == 'PATCH':
                options.update(operation=enum(operations), candidate_id=enum(list(candidates)), reason_code=enum([None]))
            else:
                reasons = ['explained'] if action == 'KEEP' else ['insufficient_evidence','needs_pi_change']
                options.update(operation=enum([None]), candidate_id=enum([None]), reason_code=enum(reasons))
            alternatives.append(dict(type='object',additionalProperties=False,properties=options,required=list(options)))
        wire = dict(type='object',additionalProperties=False,properties={'proposal':{'anyOf':alternatives}},
                    required=['proposal'])
        response = provider.chat.completions.create(model=model, **experiment_settings(model),
            messages=[{'role':'system','content':load_prompt('step3_execute', 'choose_evidence_backed_physical_repair')},
                      {'role':'user','content':json.dumps(packet, ensure_ascii=False)}],
            response_format={'type':'json_schema','json_schema':{'name':'step4_decision','strict':True,'schema':wire}})
        raw = response.choices[0].message.content
        try:
            value = json.loads(raw)['proposal']
        except (KeyError, TypeError, ValueError):
            return None, raw
    if not isinstance(value, dict) or set(value) != set(fields):
        return None, raw
    if any(value[k] not in s['enum'] for k,s in fields.items() if 'enum' in s):
        return None, raw
    citations = value['evidence_ids']
    if not isinstance(citations, list) or any(not isinstance(k,str) or k not in evidence for k in citations):
        return None, raw
    if value['decision'] == 'PATCH':
        c = candidates.get(value['candidate_id'])
        if (not c or c['operation'] != value['operation'] or value['reason_code'] is not None or
                set(citations) != set(c['evidence_ids'])):
            return None, raw
    elif value['operation'] is not None or value['candidate_id'] is not None or (
            value['reason_code']=='needs_pi_change' and value['decision']!='UNRESOLVED'):
        return None, raw
    return value, raw


def candidates_for_finding(registry, finding, current):
    """PURPOSE: Group equivalent physical choices affecting one selected definition and field.
    INPUT: Query registry, finding, current normalized ES. OUTPUT: Distinct in-scope candidate groups.
    """
    choices = defaultdict(list)
    seen = set()
    existing_paths = {(r.get('source_event_definition_id'), r.get('attribution_candidate_id'))
                      for r in current.get('event_rules', [])}
    for c in registry['candidates'].values():
        if finding['severity']=='signal' and (c['event_definition_id'],c.get('path_id')) in existing_paths and c['kind']=='path':
            continue
        if c['status'] != 'eligible' or (finding['kind'] and c['kind'] != finding['kind']):
            continue
        if finding['rules'] and c['rule_id'] not in finding['rules']:
            continue
        if finding['details'].get('path_id') and c.get('path_id') != finding['details']['path_id']:
            continue
        rule = next(r for r in current['event_rules'] if r['id']==c['rule_id'])
        source = current['event_sources'][rule['source_id']]
        field = c.get('path') if c['kind']=='path' else timestamp_signature(c['timestamp'])
        key = stable_id('physical_choice', [c['event_definition_id'], c['kind'], field,
                       source.get('case_attribution',{}).get('entity_instance_map_id'),
                       source['table'], source.get('row_condition'), rule.get('timestamp_pairing'), c['semantic_basis'],
                       rule.get('timestamp') if c['kind']=='timestamp' else source['case_attribution'].get('relationship_path')])
        if (key, c['rule_id']) not in seen:
            choices[key].append(c)
            seen.add((key, c['rule_id']))
    return [choices[k] for k in sorted(choices)]


def attach_witnesses(database, graph, current, registry, target, choices, packet, audit, budget, timeout):
    """PURPOSE: Build a bounded decision packet using only independently witnessed candidates.
    INPUT: Frozen ES, scoped choices, round packet, audit and SQL budget. OUTPUT: Alias-to-trial mapping.
    """
    surviving = {}
    for index, group in enumerate(choices, 1):
        candidate = group[0]
        alias, witness, evidence = 'C'+str(index), 'W'+str(index), 'E'+str(index)
        trial = current
        for c in group:
            trial = materialize_candidate(trial,c,registry)
        rule_ids = {c['rule_id'] for c in group}
        unknown_clock = False
        if candidate['kind']=='timestamp' and candidate['semantic_basis']=='selected_event_binding':
            source = current['event_sources'][candidate['source_id']]
            table = next((t for t in graph.get('tables', []) if t['name']==source['table']), {})
            columns = {col['name'] for col in table.get('columns', [])}
            rule = next(r for r in current['event_rules'] if r['id']==candidate['rule_id'])
            unknown_clock = bool(columns and source['encoding']=='row' and
                                 set(timestamp_columns(rule['timestamp'])) - columns)
        sample = read_witness(database,current,trial,rule_ids,sample=True,budget=budget,
                              seconds=timeout,unknown_clock=unknown_clock)
        audit['candidates'][alias] = [c['id'] for c in group]
        witnesses = {}
        for row in sample:
            sides = witnesses.setdefault(row['occ'], {})
            sides.setdefault(row['side'], []).append({k:row[k] for k in ('cid','stamp','label','ref_state')})
        audit['witnesses'][witness] = witnesses
        if not sample and not (target['check'] in {'timestamp_binding','selected_clock_drift','selected_path_drift'}
                               and len(choices) == 1):
            continue
        role_proven = target['check']=='selected_path_drift' and bool(candidate.get('role_evidence'))
        if target['severity']=='signal' and candidate['kind']=='path' and not any(
                r['side']=='old' and r['ref_state']=='unmatched_reference' for r in sample):
            continue
        if target['severity']=='signal' and candidate['kind']=='timestamp' and not any(
                r['side']=='old' and r['stamp'] is None for r in sample):
            continue
        rule = next(r for r in current['event_rules'] if r['id']==candidate['rule_id'])
        source = current['event_sources'][rule['source_id']]
        before_field = rule.get('timestamp') if candidate['kind']=='timestamp' else source['case_attribution']['relationship_path']
        packet['candidates'][alias] = dict(source_table=source['table'], current_field=before_field, operation=OPERATIONS[candidate['kind']],evidence_ids=[witness,evidence],
            definition=candidate['event_definition_id'],rule_ids=sorted(rule_ids),
            field=candidate.get('path',candidate.get('timestamp')), basis=candidate['semantic_basis'])
        packet['evidence'][witness] = witnesses
        packet['evidence'][evidence] = dict(ids=candidate['evidence_ids'],meaning=candidate['semantic_evidence'],
                                            role_evidence=candidate.get('role_evidence', []))
        surviving[alias] = (group,trial,rule_ids,role_proven,unknown_clock)
    return surviving


def verify_and_repair(database, view, es, graph, retrieval, thresholds, client, model, selector,
                      baseline, limits, cost, *, legacy_selector=None):
    """PURPOSE: Bound diagnosis, source witnesses, guarded trials and atomic publication.
    INPUT: Frozen query context, optional baseline/selector, configurable caps and cost counters.
    OUTPUT: Final verified state or original state plus complete round audit and explicit termination.
    """
    limits = {**DEFAULT_LIMITS, **(limits or {})}
    if set(limits) != set(DEFAULT_LIMITS) or any(type(v) is not int or v < 0 for v in limits.values()):
        raise ValueError('invalid_step4_budget')
    snapshot = database_fingerprint(database)
    graph_digest = stable_id('eeg', graph) if graph is not None else None
    initial = validate_unified(es, process_view=view, database=database, graph=graph, phase='full',
                               retrieval=retrieval, thresholds=thresholds, baseline_execution=baseline)
    current = upgrade_es_v4_to_v5(es) if es.get('es_version') == 4 else es
    report = initial
    findings = diagnose(current, report, graph)
    initial_findings = copy.deepcopy(findings)
    attempts, history, rejected = [], [], set()
    baseline_log = baseline or initial['execution']
    if (baseline_log.get('skipped') and initial['next_action'] != 'needs_step2_revision'
            and current.get('case') and current.get('event_rules')):
        baseline_log = execution_validation(database, dict(current, status='accepted'))
    initial_log = baseline_log
    def finish(status, reason=None, *, revision=False):
        """PURPOSE: Publish only a fully accepted state. INPUT: Terminal decision. OUTPUT: Compatible result and audit."""
        changed = status=='accepted' and bool(history)
        final_es, final_report = (current, report) if changed else (es, initial)
        if database_fingerprint(database) != snapshot:
            status, reason, changed, final_es, final_report = 'unresolved','database_snapshot_changed',False,es,initial
        final_report = dict(final_report)
        if status!='accepted':
            final_report.update(hard_passed=False,status='repair_required')
        if not changed and not initial_log.get('skipped') and not final_report['execution'].get('passed'):
            final_report['execution'] = initial_log
        if changed:
            final_es = copy.deepcopy(final_es)
            final_es.update(status='accepted',reason_code=None)
            final_es['repair_history'] = [*es.get('repair_history', []), *history]
            final_es.pop('id',None)
            final_es['id'] = stable_id('es',final_es)
        compatible = ('needs_step2_revision' if revision else 'repaired' if changed else
                      'not_needed' if status=='accepted' else 'repair_unresolved')
        return dict(status=compatible, terminal_status=status,
                    input_state={'database_snapshot':snapshot, 'eeg_digest':graph_digest,
                                 'es_id':es.get('id'), 'pi_fingerprint':view.get('fingerprint'),
                                 'execution_key':initial_log.get('execution_key')},
                    execution_state=('success' if final_report['execution'].get('passed') else
                                     'not_run' if final_report['execution'].get('skipped') else 'failed'), requires_step2_revision=revision,
                    validated_repair=changed, repair_entered=bool(attempts), es=final_es, report=final_report,
                    baseline_execution=initial_log, initial_report=initial, initial_findings=initial_findings,
                    findings=findings if changed else initial_findings, attempts=attempts,
                    llm_review={'calls':cost['llm_calls']}, baseline_reused=baseline is not None,
                    patch={'candidate_ids':[i for h in history for i in h['candidate_ids']]} if changed else None,
                    unresolved_actions=[{'reason':reason}] if reason else [], search_budget_exhausted=status=='budget_exhausted')
    if initial['next_action']=='needs_step2_revision':
        return finish('unresolved','needs_pi_change',revision=True)
    for iteration in range(limits['rounds'] + 1):
        violations = [f for f in findings if f['severity']=='violation']
        ready = report['hard_passed'] and not violations
        if not graph or not current.get('event_rules') or not current.get('case'):
            return finish('accepted' if ready else 'unresolved', None if ready else 'physical_evidence_unavailable')
        if not findings or (history and ready):
            return finish('accepted' if ready else 'unresolved', None if ready else 'required_check_unverified')
        if violations and not any(f['kind'] for f in violations):
            return finish('unresolved', 'no_verified_candidate')
        registry = collect_repair_candidates(graph, current, retrieval, database_snapshot=snapshot)
        # Shape alone never establishes a wrong clock or wrong unique case. Signal witnesses may
        # establish a missed attribution or an independently documented competing occurrence clock.
        target = choices = None
        for finding in (violations or findings):
            if violations and not finding['kind']:
                continue
            eligible = candidates_for_finding(registry, finding, current)
            if finding['severity']=='signal':
                eligible = [g for g in eligible if g[0]['kind']=='path' or
                            g[0]['semantic_basis']=='selected_event_binding']
            if eligible:
                target, choices = finding, eligible
                break
        if not choices:
            return finish('accepted' if ready else 'unresolved',None if ready else 'no_verified_candidate')
        if iteration == limits['rounds']:
            return finish('budget_exhausted','round_limit')
        audit = dict(round=iteration+1, finding=target, candidates={}, witnesses={}, guard_passed=False, passed=False)
        attempts.append(audit)
        if len(choices)>limits['candidates'] or max(Counter((c[0]['rule_id'],c[0]['kind']) for c in choices).values())>limits['per_field']:
            return finish('budget_exhausted','candidate_limit')
        budget = {'used':0,'limit':limits['witness_queries']}
        round_started = time.monotonic()
        cost_before = cost.copy()
        packet = dict(request=es.get('query',''), pi={'case':view.get('target_ot_id') or current['case'].get('entity_type_id'),
                      'selected_definitions':view.get('event_definitions',[]), 'activities':view.get('target_activities',[]),
                      'focus':view.get('process_focus')}, finding={'id':'D1','check':target['check'],'severity':target['severity'],
                      'impact':target['impact'], 'details':target['details'], 'rules':target['rules']},
                      es={'case_table':current['case'].get('table'), 'case_selection':current.get('case_selection'),
                          'activity_source_policy':current.get('activity_source_policy')}, candidates={}, evidence={})
        try:
            surviving = attach_witnesses(database, graph, current, registry, target, choices,
                                         packet, audit, budget, limits['timeout_seconds'])
            audit['packet'] = packet
            if not surviving:
                return finish('accepted' if ready else 'unresolved',None if ready else 'no_supporting_witness')
            chosen = next(iter(surviving))
            deterministic = len(choices)==1 and (choices[0][0]['semantic_basis']=='selected_event_binding' or
                            choices[0][0]['kind']=='path' and target['severity']=='violation')
            if not deterministic:
                if legacy_selector is not None:
                    bundles = [{'candidate_ids':[c['id'] for c in group], 'candidates':copy.deepcopy(group)}
                               for group, _, _, _, _ in surviving.values()]
                    def legacy_decision(packet, schema):
                        """PURPOSE: Adapt legacy enumerated bundle selectors to the witnessed decision contract.
                        INPUT: Reviewed packet and schema. OUTPUT: Evidence-scoped decision for the selected bundle.
                        """
                        ids = legacy_selector(bundles, registry['frozen_pi_contract'])
                        selected = next((k for k in surviving if sorted(ids)==sorted(audit['candidates'][k])),None)
                        return dict(decision='PATCH' if selected else 'UNRESOLVED', diagnostic_id='D1',
                                    hypothesis_code=target['check'], candidate_id=selected,
                                    operation=packet['candidates'][selected]['operation'] if selected else None,
                                    evidence_ids=packet['candidates'][selected]['evidence_ids'] if selected else [],
                                    reason_code=None if selected else 'insufficient_evidence')
                    selector = legacy_decision
                if client is None and selector is None:
                    return finish('unresolved','semantic_choice_unresolved')
                cost['llm_calls'] += 1
                try:
                    answer, raw = decision(packet,client,model,selector)
                except Exception as error:
                    audit.update(decider='model', error_type=type(error).__name__)
                    return finish('unresolved','model_unavailable')
                audit.update(decider='model',raw_response=raw)
                if answer is None:
                    return finish('unresolved','invalid_proposal')
                if answer['decision']!='PATCH':
                    ok = ready and answer['decision']=='KEEP'
                    return finish('accepted' if ok else 'unresolved',None if ok else answer['reason_code'] or 'open_violation',
                                  revision=answer['reason_code']=='needs_pi_change')
                chosen = answer['candidate_id']
            else:
                audit['decider'] = 'deterministic'
            group, trial, rule_ids, role_proven, unknown_clock = surviving[chosen]
            signature = (registry['context_id'],target['id'],tuple(c['id'] for c in group))
            if signature in rejected:
                return finish('unresolved','repeated_proposal')
            audit['selected'] = chosen
            proof = read_witness(database,current,trial,rule_ids,sample=False,budget=budget,seconds=limits['timeout_seconds'],
                                 unknown_clock=unknown_clock)
            if not baseline_log.get('passed') and not deterministic:
                return finish('unresolved','unproved_baseline')
            expected = {}
            audit['diff'] = verify_changes(proof,group[0],baseline_log,{},
                              has_population=bool(current['case'].get('population')),role_proven=role_proven,
                              unknown_clock=unknown_clock,expected_after=expected)
            audit['guard_passed'] = True
            trial = refresh_probe_certificates(database,trial)
            after = validate_unified(trial, process_view=view, graph=graph, database=database, phase='full',
                                     frozen_contract=registry['frozen_pi_contract'],retrieval=retrieval,thresholds=thresholds)
            check_execution(after['execution'], expected['rows'], expected['population'], 'new')
            next_findings = diagnose(trial,after,graph)
            previous = {(f['check'],r) for f in violations for r in (f['rules'] or [None])}
            remaining = {(f['check'],r) for f in next_findings if f['severity']=='violation' for r in (f['rules'] or [None])}
            if remaining - previous or any((target['check'],r) in remaining for r in rule_ids):
                raise ValueError('new_or_persistent_violation')
            if not after['hard_passed'] and (not remaining or not remaining < previous):
                raise ValueError('required_check_unverified')
            audit.update(passed=True, validation=after['checks'])
            history.append(dict(candidate_ids=list(signature[2]),context_id=registry['context_id'],
                                frozen_pi_fingerprint=registry['frozen_pi_contract']['fingerprint'],validated_repair=True))
            current, report, findings, baseline_log = trial, after, next_findings, after['execution']
        except (sqlite3.Error,ValueError,KeyError,TypeError,RuntimeError) as error:
            audit['reason'] = str(error)
            if str(error)=='witness_budget_exhausted':
                return finish('budget_exhausted',str(error))
            if 'selected' not in audit:
                return finish('unresolved',str(error))
            rejected.add(signature)
        finally:
            audit['witness_queries'] = budget['used']
            cost['witness_queries'] += budget['used']
            audit['cost'] = {k:cost[k]-cost_before[k] for k in cost}
            audit['cost']['elapsed_seconds'] = time.monotonic()-round_started
    return finish('budget_exhausted','round_limit')
