"""Iterative request interpretation over an immutable Event Extraction Graph; no oracle access."""

from __future__ import annotations
from src.common.attribution_policy import MAX_ATTRIBUTION_HOPS, bounded_hops, DEFAULT_MAX_REVISIONS
import copy
from src.common.event_definition_eligibility import effective_binding, request_approvals
from src.common.attribution_policy import (
    attribution_adjacency, documented_reference_roles, mentions_role, path_issues, POLICY,
)
import hashlib
import json
import os
import re
from itertools import combinations
from src.common.event_definition_policy import binding_policy
from src.common.prompt_loader import load_prompt
from src.step2_retrieve_and_interpret.validate_case_event_attribution import selectable_objects, _binding_record, assess_binding_attribution
from src.step2_retrieve_and_interpret.retrieve_process_evidence import PIEvidenceRetriever, AUTO_ENCODER, VERSION as RETRIEVAL_VERSION
from src.step2_retrieve_and_interpret.execute_model_roles import (
    UNIFIED_SCHEMA, Step2ContextLimitExceeded, call_role, VERSION, constrained_role_schema,
)
from src.step2_retrieve_and_interpret.event_definition_granularity import choose_event_granularity
from src.step2_retrieve_and_interpret.scope_coverage import check_scope, documented_family_members
from src.step2_retrieve_and_interpret.scope_review_batches import REVIEW_CARD_LIMIT, bounded_replies, review_batches, select_batches
from src.step2_retrieve_and_interpret.progressive_lookup import prepare_cards
from src.common.activity_identity import activity_identity
from src.step2_retrieve_and_interpret.resolve_history_attribution import (
    path_role, role_scope_needs_review, scope_history_paths, verify_path_union,
)
from src.step2_retrieve_and_interpret.unified_interpretation import check_revision, resolve_proposal, semantic_payload
from src.step2_retrieve_and_interpret.verify_activity_requirements import (
    documented_activity_sources, is_source_span, resolve_selection_conflicts, review_card, role_paths, verify_activity,
)


def fingerprint(value):
    """PURPOSE: Detect repeated interpretation states. INPUT: JSON value. OUTPUT: SHA256."""
    original_ids = value.get('selected_candidate_ids', []) if isinstance(value, dict) else []
    if isinstance(value, dict) and 'target_ot_id' in value:
        value = {k: value.get(k) for k in ('target_ot_id', 'activity_scope', 'object_scope')}
        # Selection is a set, and explanatory text does not redefine a case or its scope.
        value['selected_candidate_ids'] = sorted(set(original_ids))
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def available_objects(graph):
    """PURPOSE: Avoid resurrecting physical cases when an explicit selectable catalog is empty.
    INPUT: Runtime EEG. OUTPUT: Valid selectable concepts, or legacy physical objects if no catalog exists.
    """
    source = (graph['entity_types'] if 'entity_types' in graph
              else selectable_objects(graph))
    return [o for o in source if o.get('validation_status', 'valid') == 'valid'
            and o.get('selectable', True) is not False
            and (o.get('key_columns') or
                 any(i.get('unique_probe', {}).get('status') == 'verified'
                     and i.get('columns') for i in o.get('identity_candidates', []))
                 or (o.get('population') or {}).get('status') == 'valid'
                 or o.get('semantic_status')=='supported' and (o.get('population') or {}).get('status')=='unresolved')]


def dictionary_evidence(graph, binding):
    """PURPOSE: Index semantic fields without depending on value_domain alone.
    INPUT: Public DD and binding. OUTPUT: Source-table definition and relevant column records.
    """
    dd = graph.get('data_dictionary') or {}
    names = {binding.get('activity_column'), *binding.get('timestamp_columns', [])}
    tables = [t for t in dd.get('tables', [])
              if t.get('table', t.get('table_name')) == binding.get('source_table')]
    columns = [c for c in dd.get('columns', []) if
               c.get('table', c.get('table_name')) == binding.get('source_table') and
               c.get('column', c.get('name', c.get('column_name'))) in names]
    for table in tables:
        columns.extend(c for c in table.get('columns', []) if c.get('name', c.get('column')) in names)
    return {'tables': [{k: v for k, v in t.items() if k != 'columns'} for t in tables],
            'columns': columns, 'binding_evidence': binding.get('evidence', [])}


def attribution_evidence(graph, binding, target, max_hops=MAX_ATTRIBUTION_HOPS, *, diagnose=True, case_scope=None, for_history=False, binding_paths=None):
    """PURPOSE: Distinguish executed attribution from unverified structural reachability.
    INPUT: Binding, selected OT and graph paths. OUTPUT: pass/fail/unknown with path IDs.
    """
    max_hops = bounded_hops(max_hops)
    if not target:
        return {'status': 'fail', 'reason': 'invalid_target', 'evidence_ids': [], 'paths': []}
    targets = {target['id'], *target.get('member_object_ids', [])}
    if binding_paths is None:
        binding_paths = [p for p in graph.get('attribution_paths', []) if p.get('event_definition_id') == binding['id']]
    paths = {p.get('id'): p for p in [*binding.get('concept_paths', []), *binding_paths]
             if p.get('to') in targets}
    def admissible(p):
        """PURPOSE: Apply the forward-path contract. INPUT: Path record. OUTPUT: True when structurally admissible."""
        return (p.get('cardinality') not in {'M:N', '1:N'}
                and not path_issues(p.get('joins', []), graph.get('relationships', []))
                and (not p.get('joins') or p['joins'][0].get('left_table')==binding.get('source_table'))
                and (not p.get('edge_ids') or p.get('joins')))
    allowed_role = (case_scope or {}).get('step', {}).get('relationship_id')
    review = binding.get('entity_reviews', {}).get(target['id'], {}).get('attribution_paths', {})
    scoped_paths = [p for p in paths.values() if (not p.get('case_role') or
                    (for_history and not allowed_role) or p['case_role']['step']['relationship_id'] == allowed_role)]
    scoped_paths = [p for p in scoped_paths if review.get(p['id'], {}).get('status') != 'incompatible']
    valid = [p for p in scoped_paths if p.get('validation_status') == 'valid'
             and (p.get('case_map', {}).get('validation') or {}).get('passed') is True and admissible(p)]
    if valid:
        return {'status': 'pass', 'verified_for_history': True, 'reason': 'executed_case_mapping',
                'evidence_ids': [p['id'] for p in valid], 'paths': copy.deepcopy(valid)}
    # No in-scope occurrence exists; the attribution rule is fixed by a supported identification rule.
    # Selectable (an empty result is a valid answer) but never reported as an observed mapping.
    confirmed = [p for p in scoped_paths if p.get('validation_status') == 'rule_confirmed_no_occurrences'
                 and admissible(p)]
    if confirmed:
        return {'status': 'pass', 'verified_for_history': True, 'reason': 'rule_confirmed_no_occurrences',
                'observed_mapping': False, 'evidence_ids': [p['id'] for p in confirmed],
                'paths': copy.deepcopy(confirmed)}
    if paths and all(p.get('validation_status') == 'invalid' for p in paths.values()):
        return {'status': 'fail', 'reason': 'invalid_case_mapping',
                'evidence_ids': list(paths), 'paths': list(paths.values())}
    own = binding.get('source_table') in target.get('member_tables', [target.get('anchor_table')])
    keys = target.get('key_columns') or next((i.get('columns') for i in
        target.get('identity_candidates', []) if i.get('unique_probe', {}).get('status') == 'verified'), [])
    if not paths and own and binding.get('source_table') == target.get('anchor_table') and keys:
        return {'status': 'pass', 'verified_for_history': bool(target.get('population', {}).get('status') == 'valid'
                    and binding.get('extraction_status') == 'executable'), 'reason': 'direct_keyed_source_identity',
                'evidence_ids': [target['id']], 'paths': []}
    structural = assess_binding_attribution(graph, binding, target, max_hops=max_hops) if diagnose else None
    return {'status': 'unknown', 'reason': 'executed_case_mapping_not_available',
            'evidence_ids': list(paths), 'paths': list(paths.values()),
            'structural_assessment': structural}


def candidate_catalog(graph, target_id, max_hops=MAX_ATTRIBUTION_HOPS, approvals=None, *, case_scope=None, for_history=False):
    """PURPOSE: Annotate EEG Event definitions by source, semantics and target attribution.
    INPUT: Immutable EG and selected ET. OUTPUT: ID-indexed public evidence records.
    """
    max_hops = bounded_hops(max_hops)
    objects = {o['id']: o for o in available_objects(graph)}
    target = objects.get(target_id, {})
    targets = {target_id, *target.get('member_object_ids', [])}
    # Source provenance and target attribution are separate; neither is a lifecycle membership gate.
    output = {}
    global_paths = {}
    for path in graph.get('attribution_paths', []):
        global_paths.setdefault(path.get('event_definition_id'), []).append(path)
    grouped_associations = {}
    for association in graph.get('event_entity_associations', []):
        grouped_associations.setdefault(association.get('event_definition_id'), []).append(association)
    for binding in graph.get('event_definitions', []):
        approval = (approvals or {}).get(binding['id'])
        binding = effective_binding(binding, target_id, approval)
        row = _binding_record(binding, graph)
        row['dictionary_evidence'] = dictionary_evidence(graph, binding)
        row['source_ot_ids'] = [o['id'] for o in objects.values() if binding.get('source_table')
                               in o.get('member_tables', [o.get('anchor_table')])]
        row['source_member'] = binding.get('source_table') in target.get(
            'member_tables', [target.get('anchor_table')])
        row['attribution'] = attribution_evidence(graph, binding, target, max_hops, case_scope=case_scope,
                                                  for_history=for_history, binding_paths=global_paths.get(binding['id'], []))
        associations = [a for a in grouped_associations.get(binding['id'], []) if a.get('object_concept_id') in targets]
        states = {a.get('lifecycle_membership') for a in associations}
        row['lifecycle_associations'] = copy.deepcopy(associations)
        row['membership'] = ('unknown' if len(states) != 1 else next(iter(states)))
        path_reviews = binding.get('entity_reviews', {}).get(target_id, {}).get('attribution_paths', {})
        reviewed_subject = any(path_reviews.get(p['id'], {}).get('status') == 'supported'
                               and path_reviews[p['id']].get('role') == 'subject'
                               for p in row['attribution']['paths'])
        row['subject_role_supported'] = reviewed_subject or (
            any(a.get('own_event_status') == 'supported' for a in associations)
            if graph.get('entity_model_version') == 'meaning-first-identification-v3' else row['source_member'])
        row['rollup_ids'] = sorted({rid for path in row['attribution'].get('paths',[]) for rid in path.get('rollup_ids',[])}) if row['attribution']['status']=='pass' else []
        row['entity_scope_policy'] = POLICY
        row['binding_policy'] = binding_policy(binding, versioned=bool(graph.get('activity_semantics_version')))
        row['eligible'] = row['binding_policy']['review_eligible']
        if 'candidate_tier' in binding:
            review = binding['entity_reviews'].get(target_id, {})
            row['duplicate_of'] = review.get('duplicate_of')
            tier = binding['candidate_tier']
            row['effective_tier'] = tier
            row['eligible'] = row['eligible'] and (tier == 1 or (tier == 2 and bool(approval)))
        row['semantic_validation'] = row['binding_policy']['checks']['activity_semantics']
        output[binding['id']] = row
    return output


def implicit_events(catalog, scope=None):
    """PURPOSE: Select precisely supported EEG events with verified unique attribution to the chosen ET.
    INPUT: ET-relative catalog; deprecated scope argument is ignored for implicit recorded history.
    OUTPUT: Sorted selected IDs and exclusion diagnostics, never a claim of normative lifecycle completeness.
    """
    selected, excluded = [], []
    for bid,row in sorted(catalog.items()):
        support = row['binding_policy']
        if row.get('duplicate_of'):
            excluded.append(bid + ':duplicate_of:' + row['duplicate_of'])
        elif row.get('effective_tier', 1) != 1 or not support.get('history_supported', False):
            excluded.append(bid + ':event_support_unresolved_or_rejected')
        elif row['attribution']['status'] != 'pass' or not row['attribution'].get('verified_for_history', False):
            excluded.append(bid + ':attribution_not_executed_or_not_unique')
        else:
            selected.append(bid)
    return selected, excluded


def validate_requirement_evidence(question, item, field):
    """PURPOSE: Validate a copied phrase and independent plain-language meaning.
    INPUT: Original request, item containing span and meaning, and audit field name.
    OUTPUT: Specific rejection strings with the affected field.
    """
    errors = []
    if not is_source_span(question, item['span']):
        errors.append(f'invalid_requirement_span_or_meaning:{field}.span must be a literal request phrase; received {item["span"][:160]!r}')
    if not item['meaning'].strip():
        errors.append(f'invalid_requirement_span_or_meaning:{field}.meaning must not be blank')
    return errors


def validate_requirements(question, requirements):
    """PURPOSE: Reject invented spans, ambiguous IDs and implicit activity enumeration.
    INPUT: Original request and independent decomposition. OUTPUT: List of contract violations.
    """
    errors = []
    activities = requirements['activity_requirements']
    if [r['id'] for r in activities] != ['R' + str(i + 1) for i in range(len(activities))]:
        errors.append('requirement_ids_must_be_unique_ordered_R1_Rn')
    errors.extend(validate_requirement_evidence(question, requirements['case_requirement'], 'case_requirement'))
    for item in activities:
        errors.extend(validate_requirement_evidence(question, item, item['id']))
    scope_span = requirements['scope_requirement']['span']
    if not is_source_span(question, scope_span):
        errors.append('invalid_scope_span:scope_requirement.span must be a literal request phrase')
    if requirements['activity_scope']=='explicit' and requirements['scope_requirement']['object_scope']=='attributable_history':
        errors.append('attributable_history_is_implicit_only')
    if requirements['scope_requirement']['object_scope'] in {'own','desc'} and not scope_span:
        errors.append('legacy_scope_requires_source_span')
    focus=requirements.get('process_focus')
    if focus is not None and (not isinstance(focus,dict) or not is_source_span(question, focus.get('span', '')) or not str(focus.get('meaning','')).strip()):
        errors.append('invalid_process_focus_span_or_meaning')
    if requirements['activity_scope'] == 'implicit' and activities:
        errors.append('implicit_requirements_must_be_empty')
    if requirements['activity_scope'] == 'explicit' and not activities:
        errors.append('explicit_requirements_empty')
    return errors


def check(name, status, reason, evidence_ids=(), *, basis='deterministic', blocking=True):
    """PURPOSE: Serialize one honest validation result.
    INPUT: Four-state judgment, evidence and provenance. OUTPUT: Diagnostic record.
    """
    return {'check': name, 'status': status, 'reason': reason, 'evidence_ids': list(evidence_ids),
            'basis': basis, 'blocking': blocking}


def validate_state(graph, state, requirements, catalog, review=None, *, case_review=None, structural_only=False, implicit_inventory=None, resolved_pairs=()):
    """PURPOSE: Validate references and structure independently from semantic model judgments.
    INPUT: PI state, independent requirements, annotated graph and optional semantic review.
    OUTPUT: Checks with pass/fail/unknown/not_run, mappings and final readiness.
    """
    selected = set(state['selected_candidate_ids'])
    explicit = state['activity_scope'] == 'explicit'
    known = selected & set(catalog)
    checks = [check('ot_existence', 'pass' if state['target_ot_id'] in {
        o['id'] for o in available_objects(graph)} else 'fail', 'selectable_ot', [state['target_ot_id']]),
        check('candidate_existence', 'pass' if selected <= set(catalog) else 'fail',
              'stable_EG_ids_only', selected - set(catalog)),
        check('pi_consistency', 'pass' if state['activity_scope'] == requirements['activity_scope']
              else 'fail', 'independent_activity_scope_agreement'),
        check('nonempty_events', 'pass' if selected or not explicit else 'fail', 'no_supported_events' if not selected else 'events_selected')]
    for bid in sorted(known):
        attribution = catalog[bid]['attribution']
        checks.append(check('case_attribution', attribution['status'], attribution['reason'],
                            [bid, *attribution['evidence_ids']]))
        for name, state_check in catalog[bid]['binding_policy']['checks'].items():
            checks.append(check(name, state_check['status'], state_check['reason'],
                state_check['evidence_ids'], blocking=state_check['status'] != 'not_run'))
        if not catalog[bid]['eligible']:
            checks.append(check('candidate_eligibility', 'fail', 'rejected_graph_candidate', [bid]))
    selected_object = next((o for o in available_objects(graph) if o['id'] == state['target_ot_id']), {})
    population = selected_object.get('population')
    if population is not None:
        checks.append(check('entity_population_resolution', 'pass' if population.get('status') == 'valid' else 'unknown',
            'complete_canonical_entity_population_required', [state['target_ot_id'], *([population['id']] if population.get('id') else [])]))
    scope = requirements['scope_requirement']['object_scope']
    if explicit:
        source_only = bool(re.search(r'only.*(?:directly recorded|source table|direct source)|(?:directly recorded|source table).*only',
            requirements['scope_requirement'].get('span',''), re.I))
        conflict = source_only and any(not catalog[b]['source_member'] for b in known)
        checks.append(check('object_scope', 'fail' if conflict else 'pass',
                            'explicit_scope_conflicts_with_selection' if conflict else
                            'named_activities_allow_attributable_related_sources', known))
        checks.append(check('implicit_completeness', 'not_run', 'explicit_request', blocking=False))
    else:
        expected, uncertainties = implicit_events(catalog, state['object_scope'])
        if implicit_inventory is not None:
            expected = implicit_inventory
        status = 'pass' if (selected <= set(expected) if requirements.get('process_focus') else selected == set(expected)) else 'fail'
        checks.append(check('implicit_recorded_history', status,
                            'supported_attributable_subset_for_focus' if requirements.get('process_focus') else 'all_supported_events_with_executed_unique_attribution', expected))
        checks.append(check('implicit_excluded_candidates', 'not_run', ';'.join(uncertainties), blocking=False))
        checks.append(check('object_scope', 'pass' if state['object_scope'] == ('process_focus' if requirements.get('process_focus') else 'attributable_history') else 'fail',
                            'implicit_support_and_attribution_scope'))
    pair_evidence = False
    for pair in graph.get('event_definition_pair_relationships', []):
        if set(pair.get('binding_pair', [])) <= known and len(pair.get('binding_pair', [])) == 2:
            pair_evidence = True
            relation = pair.get('relationship')
            status = ('fail' if relation == 'alternative' and pair.get('status') == 'supported'
                      else 'pass' if relation in {'independent', 'complementary', 'lifecycle_pair'}
                      and pair.get('status') == 'supported' else 'unknown')
            if status == 'unknown' and relation == 'unknown' and pair['id'] in resolved_pairs:
                status, relation = 'pass', 'independently_verified_distinct_occurrences'
            checks.append(check('candidate_conflict', status, str(relation), [pair['id']]))
    bindings = {b['id']: b for b in graph.get('event_definitions', [])}
    duplicates = []
    for left, right in combinations(sorted(known), 2):
        a, b = bindings[left], bindings[right]
        if a.get('occurrence_identity_rule_id') and a.get('occurrence_identity_rule_id') == b.get('occurrence_identity_rule_id'):
            duplicates.extend([left, right])
    checks.append(check('duplicate_occurrence', 'fail' if duplicates else
                        'pass' if len(known) <= 1 or pair_evidence else 'unknown',
                        'shared_occurrence_rule' if duplicates else 'no_observed_overlap_not_global_proof',
                        duplicates, blocking=bool(duplicates)))
    if not pair_evidence:
        checks.append(check('candidate_conflict', 'not_run', 'no_pair_evidence', blocking=False))
    mappings = {}
    if structural_only:
        checks = [c for c in checks if c['check'] != 'pi_consistency']
        warnings = [dict(kind=c['check'], reason=c['reason'], evidence_ids=c['evidence_ids'])
                    for c in checks if c['blocking'] and c['status'] != 'pass']
        return {'status': 'unresolved' if warnings else 'valid', 'checks': checks, 'warnings': warnings, 'mappings': {}}
    if not explicit:
        verified_case = bool(case_review and case_review.get('status') in {'confirmed','corrected'} and
                             case_review.get('target_ot_id') == state['target_ot_id'])
        checks.append(check('case_semantics', 'pass' if verified_case else 'unknown',
                            (case_review or {}).get('reason', 'case_notion_not_independently_reviewed'), basis='llm'))
        checks.append(check('semantic_coverage', 'not_run',
                            'implicit_has_no_unknown_activity_checklist', blocking=False))
        if requirements.get('process_focus'):
            valid_review=bool(review and review.get('status')=='confirmed' and not review.get('case_mismatch') and not review.get('scope_conflict') and not review.get('missing_candidate_ids') and not review.get('extra_candidate_ids') and str(review.get('reason','')).strip())
            references_ok=not review or (set(review.get('missing_candidate_ids',[]))<=set(catalog)-selected and set(review.get('extra_candidate_ids',[]))<=selected)
            checks.append(check('process_focus_coverage','pass' if valid_review and references_ok else 'unknown',
                (review or {}).get('reason','focus_not_reviewed'),basis='llm'))
    elif review is None:
        checks.append(check('semantic_coverage', 'not_run', 'review_not_performed', basis='llm'))
    else:
        req_ids = {r['id'] for r in requirements['activity_requirements']}
        reviews = review['requirement_reviews']
        ids = [r['requirement_id'] for r in reviews]
        valid_reviews = set(ids) == req_ids and len(ids) == len(req_ids)
        refs_valid = (set(review['extra_candidate_ids']) <= selected and all(
            set(r['candidate_ids']) <= selected for r in reviews))
        checks.append(check('review_references', 'pass' if valid_reviews and refs_valid else 'fail',
                            'one_review_per_requirement_existing_selected_ids_only'))
        for r in reviews:
            # Bounded retrieval never establishes exhaustive semantic absence.
            status = r['status'] if r['status'] != 'unsupported' else 'missing'
            covered = status == 'covered' and bool(r['candidate_ids']) and bool(r['evidence'].strip())
            checks.append(check('requirement_coverage', 'pass' if covered else 'unknown' if
                                status == 'ambiguous' else 'fail', status + ':' + r['evidence'],
                                [r['requirement_id'], *r['candidate_ids']], basis='llm'))
            if covered:
                mappings[r['requirement_id']] = sorted(set(r['candidate_ids']))
        justified = {b for values in mappings.values() for b in values}
        repeated = [b for b in justified if sum(b in values for values in mappings.values()) > 1]
        checks.append(check('requirement_occurrence_collision', 'unknown' if repeated else 'pass',
                            'distinct_requirements_cannot_silently_share_one_occurrence', repeated))
        extras = set(review['extra_candidate_ids']) | (selected - justified if explicit else set())
        checks.append(check('extra_activity', 'fail' if extras else 'pass',
                            'requirement_justification', extras, basis='llm'))
        checks.append(check('case_semantics', 'fail' if review['case_mismatch'] else 'pass',
                            review['evidence'], [state['target_ot_id']], basis='llm'))
        checks.append(check('scope_semantics', 'fail' if review['scope_conflict'] else 'pass',
                            review['evidence'], basis='llm'))
    passed = all(c['status'] == 'pass' for c in checks if c['blocking'])
    return {'status': 'valid' if passed else 'unresolved', 'checks': checks, 'mappings': mappings,
            'warnings': [{'kind': c['check'], 'reason': c['reason'],
                          'evidence_ids': c['evidence_ids']} for c in checks
                         if c['blocking'] and c['status'] != 'pass'],
            'semantic_validation_basis': 'llm_judgment_not_semantic_proof',
            'review_enabled': True}


def legacy_selection(state, requirements, validation, catalog):
    """PURPOSE: Preserve the existing Step 3 PI adapter while exposing new requirement mappings.
    INPUT: Final controller state and diagnostics. OUTPUT: Compatible selection fields.
    """
    mappings = validation.get('mappings', {})
    interpretations = [{'requested_activity_id': r['id'], 'query_expression': r['span'],
                        'occurrence_meaning': r['meaning'], 'qualifiers': r['qualifiers']}
                       for r in requirements['activity_requirements']]
    by_req = {r['id']: r for r in requirements['activity_requirements']}
    selections = []
    for bid in state['selected_candidate_ids']:
        ids = [r for r, values in mappings.items() if bid in values]
        selections.append({'event_definition_id': bid, 'requested_activity_id': ids[0] if ids else '',
                           'requirement_ids': ids,
                           'query_expression': by_req[ids[0]]['span'] if ids else '',
                           'reason': 'independent_coverage_review'})
    return {'target_object_id': state['target_ot_id'],
            'mode': 'selected' if state['activity_scope'] == 'explicit' else 'full',
            'object_scope': {'own': 'own_only', 'desc': 'with_descendants', 'attributable_history': 'attributable_history','process_focus':'process_focus'}.get(state['object_scope'], 'unresolved'),
            'activity_scope': state['activity_scope'], 'scope_policy': state['object_scope'],
            'process_focus': copy.deepcopy(requirements.get('process_focus')),
            'selected_event_definition_ids':list(state['selected_candidate_ids']),
            'event_definition_ids': list(state['selected_candidate_ids']),
            'activity_selections': selections, 'requested_activity_interpretations': interpretations,
            'selected_rollup_ids': sorted({r for bid in state['selected_candidate_ids']
                                          for r in catalog.get(bid, {}).get('rollup_ids', [])}),
            'unresolved_activities': [r['span'] for r in requirements['activity_requirements'] if r['id'] not in mappings],
            'reason': state.get('evidence', ''), 'trace_identity_phrase': requirements['case_requirement']['span']}


def unresolved_interpretation(reason,calls,requirements=None):
    """PURPOSE: Fail closed on unavailable or invalid parsing without breaking downstream PI/ES adapters.
    INPUT: Public diagnostic, actual role-call audits and optional partial parsing.
    OUTPUT: Complete unresolved PI envelope with no case notion or selected Event definitions.
    """
    requirements={**{'activity_scope':'explicit','process_focus':None,'activity_requirements':[],
        'case_requirement':{'span':'','meaning':''},'scope_requirement':{'span':'','object_scope':'unresolved'}},**(requirements or {})}
    state={'target_ot_id':'','activity_scope':requirements['activity_scope'],'object_scope':'unresolved',
        'selected_candidate_ids':[],'evidence':reason}
    validation={'status':'unresolved','checks':[check('request_interpretation','unknown',reason)],
        'warnings':[{'kind':'request_interpretation','reason':reason}],'mappings':{}}
    selection=legacy_selection(state,requirements,validation,{})
    return {'status':'selection_required','terminal_status':'unresolved_semantic','termination_reason':'invalid_parsing',
        'initial_selection':copy.deepcopy(selection),'initial_audit':{'initial_state':state,'model_calls':calls},
        'final_selection':selection,'final_validation':validation,'validations':[validation], 'revisions':[],
        'requirements':requirements,'requirements_version':fingerprint(requirements), 'model_calls':calls,
        'initial_candidates':[],'candidate_interpretations':[],'rejected_initial_candidates':[],
        'selector_contract':'process_information_v1','prompt_versions':{'initial':VERSION,'revision':VERSION},
        'configuration':{'parsing_policy':'single_pass','parsing_verifier_enabled':False},'max_revisions':0,
        'final_selection_version':0,'final_selection_fingerprint':fingerprint(state),
        'parsing_verification':{'status':'not_run','reason':'single_pass_parsing_policy'},
        'event_selection_verifications':[], 'process_information':{'symbol':'I_q','status':'selection_required',
            'case_notion_et_id':None,'request_mode':requirements['activity_scope'],
            'process_focus':requirements.get('process_focus'),'selected_event_definition_ids':[]}}


def structural_reply_target(target, warnings):
    """PURPOSE: Recognize a reference to an issued structural warning.
    INPUT: Reviser target in wire vocabulary and the structural issues sent to that role.
    OUTPUT: Whether the target names a warning; acknowledgement never discharges the check.
    """
    return bool(target) and any(
        target == warning['kind'] or target == warning['reason'] or target in warning.get('evidence_ids', [])
        for warning in warnings if 'target' not in warning
    )


def select_iterative(question, graph, client, model, cache=None, *, max_hops=MAX_ATTRIBUTION_HOPS,
                     max_revisions=DEFAULT_MAX_REVISIONS, few_shot=True,
                     cross_ot_expansion=True, semantic_top_k=10, max_candidates=3,
                     evidence_retrieval=None, semantic_encoder=AUTO_ENCODER, eeg_delivery=None,
                     independent_initial=False, unified=None, database=None, scope_verification=False,
                     case_definition_loader=None, case_hint_lookup=None, path_loader=None, paired_pi_controls=False):
    """PURPOSE: Select from the EEG and independently check each interpretation.
    INPUT: Raw request, EEG, bounded client, optional joint seed and shared history verification controls.
    OUTPUT: Step 3 PI envelope and per-candidate decision trace, including rejected proposals.
    """
    from src.common.runtime_input_contract import validate_runtime_graph
    from src.step1_understand.describe_business_entities_and_events import entry, eeg_summary
    validate_runtime_graph(graph)
    max_hops = bounded_hops(max_hops)
    if unified and (independent_initial or unified.verification not in {'structural','independent','conditional'}):
        raise ValueError('invalid_unified_policy')
    if max_revisions < 1 or max_candidates < 1:
        raise ValueError('invalid_interpretation_limits')
    budget = min(2, max_revisions)
    if semantic_top_k < 1:
        raise ValueError('invalid_evidence_retrieval_budget')
    if evidence_retrieval is None:
        evidence_retrieval = os.environ.get('NL2EL_PI_EVIDENCE_RETRIEVAL', '1') != '0'
    evidence_reader = (PIEvidenceRetriever(graph, encoder=semantic_encoder)
                       if evidence_retrieval and case_definition_loader is None else None)
    objects = {e['id']: e for e in available_objects(graph)}
    ets = {eid: entry(e) for eid, e in objects.items()}
    references = documented_reference_roles(attribution_adjacency(graph.get('relationships', [])),
                                            graph.get('data_dictionary') or {})
    role_labels = {item['role'] for item in references.values()}
    case_scopes = {}
    for et, obj in objects.items():
        maps = obj.get('population', {}).get('maps', [])
        if len(maps) != 1:
            continue
        for edge_id, role in references.items():
            if role['step']['left_table'] == maps[0]['table']:
                case_scopes[et, edge_id] = {'kind': 'reference_role', 'role': role['role'],
                    'step': role['step'], 'dictionary_id': role['dictionary_id'], 'evidence': role['quote']}
    scope_cards = [{'et': et, 'id': edge_id, 'role': s['role'], 'reference_table': s['step']['right_table'],
                    'evidence': s['evidence']} for (et, edge_id), s in sorted(case_scopes.items())]
    definitions = {e['id']:e for e in graph.get('event_definitions', [])}
    events = {eid:entry(e, True) for eid,e in definitions.items()}
    catalogs, calls, alternatives, revisions = {}, [], [], []
    lookup_coverage = {}
    verified_unions = {}
    scoped_approvals = {}
    context_attempted = False
    parsed = None
    summary = graph.get('revision_summary')
    initial_candidates = []
    rejected_initial = []
    unified_trace = {}
    comparison = None
    reason = 'no_supported_case_notion'

    retries = {}
    failed_role = None
    def ask(role, payload):
        """PURPOSE: Retry malformed role replies. INPUT: Grounded role data. OUTPUT: Validated response."""
        nonlocal failed_role
        for attempt in range(3):
            call_count = len(calls)
            try:
                wire = eeg_delivery(role, payload) if eeg_delivery is not None else payload
                response, audit = call_role(role,wire,client,model,cache,few_shot=few_shot,audit_sink=calls,
                                            schema=constrained_role_schema(role,wire), defer_cache_write=True)
                if role=='pi_cases':
                    candidates = response['candidates']
                    if len({c['et'] for c in candidates})!=len(candidates):
                        raise ValueError('each case ET may appear only once')
                    if any(c['focus'] and c['focus'] not in question for c in candidates):
                        raise ValueError('focus must be empty or an exact request substring')
                    if any(c.get('scope_id') and (c['et'], c['scope_id']) not in case_scopes for c in candidates):
                        raise ValueError('case scope must belong to the selected ET')
                if role=='semantic_decomposer':
                    errors = validate_requirements(question,response)
                    if errors:
                        raise ValueError(', '.join(errors))
                if role == 'pi_revise_requirement':
                    supplied = {r['id'] for r in payload['unresolved_requirements']}
                    available = {card['id'] for card in payload['activities']}
                    ids = [edit['requirement_id'] for edit in response['edits']]
                    if len(ids) != len(set(ids)) or not set(ids) <= supplied:
                        raise ValueError('requirement_revision_must_target_distinct_pending_ids')
                    for edit in response['edits']:
                        errors = validate_requirement_evidence(question, edit, edit['requirement_id'])
                        proposed_ids = edit['event_definition_ids']
                        if errors:
                            raise ValueError(', '.join(errors))
                        if not proposed_ids or len(proposed_ids) != len(set(proposed_ids)) or not set(proposed_ids) <= available:
                            raise ValueError('requirement_revision_requires_distinct_grounded_ed_ids')
                if role == 'pi_events' and payload.get('initial_choice_only'):
                    cards = {a['id']: {p['path_id'] for p in a['role_projections']} for a in payload['activities']}
                    selected = response['selected_events']
                    ids = [item['event_definition_id'] for item in selected]
                    if len(ids) != len(set(ids)) or not set(ids) <= cards.keys() or any(
                            item['path_id'] and item['path_id'] not in cards[item['event_definition_id']] for item in selected):
                        raise ValueError('invalid_independent_selection_or_role_path')
                if role == 'pi_events' and not payload.get('initial_choice_only'):
                    matches = response['matches']
                    if len({m['requirement_id'] for m in matches}) != len(matches):
                        raise ValueError('duplicate requirement IDs')
                    cards = {a['id']: a for a in payload['activities']}
                    for match in matches:
                        ids = match['event_definition_ids']
                        if len(set(ids)) != len(ids) or any(match['requirement_id'] not in cards[i]['requirement_ids'] for i in ids):
                            raise ValueError('invalid event mapping for requirement')
                if role=='pi_focus':
                    decisions = response['decisions']
                    if sorted(x['id'] for x in decisions)!=sorted(a['id'] for a in payload['activities']):
                        raise ValueError('classify every supplied representative exactly once')
                if role=='pi_crosscheck':
                    if 'implicit_role_review' in payload:
                        offered = {card['id']: {p['id']: p['role'] for p in card['paths']}
                                   for card in payload['implicit_role_review']}
                        choices = response['implicit_role_reviews']
                        if len(choices) != len(offered) or {c['event_definition_id'] for c in choices} != offered.keys():
                            raise ValueError('review each ambiguous implicit role exactly once')
                        for choice in choices:
                            paths = offered[choice['event_definition_id']]
                            selected = set(choice['path_ids'])
                            roles = {paths[key] for key in selected if key in paths}
                            if (not selected <= paths.keys() or len(selected) != len(choice['path_ids'])
                                    or selected != {key for key, role in paths.items() if role in roles}
                                    or not choice['reason'].strip()
                                    or selected and not is_source_span(question, choice['span'])):
                                raise ValueError('invalid_implicit_role_choice')
                    if 'implicit_pair_review' in payload:
                        cards = {card['id']: {event['id']: event['evidence'] for event in card['events']}
                                 for card in payload['implicit_pair_review']}
                        verdicts = response['implicit_pair_reviews']
                        if len(verdicts) != len(cards) or {v['pair_id'] for v in verdicts} != cards.keys():
                            raise ValueError('review each ambiguous ED pair exactly once')
                        for verdict in verdicts:
                            evidence = cards[verdict['pair_id']]
                            quotes = verdict['evidence']
                            if not verdict['reason'].strip() or (verdict['decision'] == 'distinct' and (
                                    len(quotes) != 2 or {q['event_definition_id'] for q in quotes} != evidence.keys()
                                    or len({q['quote'] for q in quotes}) != 2
                                    or any(not q['quote'].strip() or not any(q['quote'] in text
                                           for text in evidence[q['event_definition_id']]) for q in quotes))):
                                raise ValueError('ungrounded_distinct_occurrence_decision')
                    if any(not d['reason'].strip() for d in response['differences']):
                        raise ValueError('each difference needs a reason')
                    if 'activity_review' in payload:
                        reviews = response['requirement_reviews']
                        expected = {r['id'] for r in payload['activity_review']['requirements']}
                        if len(reviews) != len(expected) or {r['requirement_id'] for r in reviews} != expected:
                            raise ValueError('review every pending requirement exactly once')
                        for review in reviews:
                            if payload['activity_review'].get('scope_verification'):
                                offered_ids = {a['id'] for a in wire['activity_review']['candidates']}
                                judgments = [entry['event_definition_id'] for entry in review['candidate_decisions']]
                                if len(judgments) != len(offered_ids) or set(judgments) != offered_ids:
                                    raise ValueError('candidate_judgments_must_cover_offered_inventory_once')
                            ids = review['event_definition_ids']
                            if (not review['reason'].strip() or len(set(ids)) != len(ids)
                                    or review['semantic_status'] in {'matched', 'ambiguous'} and not ids
                                    or review['semantic_status'] == 'missing' and ids):
                                raise ValueError('invalid requirement verdict')
                if role == 'pi_crosscheck' and 'activity_review' in payload:
                    offered = set(payload['activity_review'].get('independent_proposal_ids', []))
                    if offered:
                        aligned = [review['aligned_proposal_ids'] for review in response['requirement_reviews']]
                        if set().union(*aligned) != offered or any(len(ids) != len(set(ids)) for ids in aligned):
                            raise ValueError('independent_proposals_must_all_be_aligned')
                    candidates = {a['id']: {p['path_id'] for p in a['role_projections']}
                                  for a in payload['activity_review']['candidates']}
                    for review in response.get('requirement_reviews', []):
                        choices = review.get('role_path_choices', [])
                        identifiers = [choice['event_definition_id'] for choice in choices]
                        if len(identifiers) != len(set(identifiers)) or any(
                                c['event_definition_id'] not in review['event_definition_ids'] or
                                c['path_id'] not in candidates.get(c['event_definition_id'], set()) for c in choices):
                            raise ValueError('unverified_role_path_choice')
                if role=='pi_revise' and response['action']!='abstain':
                    dest = response['et']
                    permitted = (set(payload['selection']['ids']) if response['action']=='keep'
                                 else set(summary['members'][dest]))
                    if len(set(response['ids']))!=len(response['ids']) or not set(response['ids'])<=permitted:
                        raise ValueError('activity alias must belong to proposed ET')
                    if response['focus'] and response['focus'] not in question:
                        raise ValueError('invalid focus span')
                    if response['action']=='keep':
                        current = payload['selection']
                        remaining = payload['differences']
                        if (any(response[k]!=current[k] for k in ('et','mode','focus')) or sorted(response['ids'])!=sorted(current['ids'])
                            or not response['resolutions']
                            or any((x['kind'],x['target']) not in {(d['kind'],d.get('target')) for d in remaining}
                                   and not structural_reply_target(x['target'], remaining) for x in response['resolutions'])
                            or any(not x['span'] or x['span'] not in question for x in response['resolutions'])):
                            raise ValueError('keep requires unchanged selection and grounded resolutions for every semantic difference')
                if cache is not None and not audit['cache_hit']:
                    cache[audit['cache_key']] = copy.deepcopy(response)
                audit['validation'] = 'accepted'
                return response
            except ValueError as exc:
                if len(calls) == call_count:
                    raise
                audit = calls[-1]
                if (cache is not None and audit['cache_hit']
                        and cache.get(audit['cache_key']) == audit.get('parsed_response')):
                    cache.pop(audit['cache_key'], None)
                audit.update(validation='rejected',rejection=str(exc),attempt=attempt+1)
                if retries.get(role,0)>=2:
                    failed_role=role
                    raise ValueError('invalid_llm_output:'+role) from exc
                retries[role]=retries.get(role,0)+1
                payload=dict(payload,previous_rejection=str(exc))
    def catalog(et, scope_id='', *, for_history=False):
        """PURPOSE: Resolve an ET and its optional case scope. INPUT: Grounded IDs. OUTPUT: Annotated ED catalog."""
        if et not in ets:
            raise ValueError('unknown_entity_type')
        key = (et, scope_id, for_history)
        if key not in catalogs:
            catalogs[key] = candidate_catalog(graph, et, max_hops, scoped_approvals.get(et),
                                              case_scope=case_scopes.get((et, scope_id)), for_history=for_history)
            rows = catalogs[key]
            indexed_catalog = {item['id'] for item in graph.get('candidate_lookup_catalog', [])}
            lookup_coverage.setdefault(key, {'case': et, 'scope': scope_id, 'history': for_history,
                'available': sorted(i for i, row in rows.items() if row['eligible'] and row['attribution']['status'] == 'pass'),
                'cataloged': sorted(rows), 'index_catalog': sorted(indexed_catalog),
                'retrieval_gaps': sorted((indexed_catalog - rows.keys()) |
                                         set(graph.get('family_lookup_gaps', []))),
                'proposal': [], 'expanded_detail': [], 'reviewed': {}})
        if for_history and lookup_coverage[key]['retrieval_gaps']:
            raise ValueError('scope_missing_retrieval')
        return catalogs[key]

    def implicit_inventory(rows, object_scope=None):
        """PURPOSE: Select a nonredundant ED inventory for implicit history or own lifecycle.
        INPUT: Case-relative ED catalog. OUTPUT: IDs eligible for the parsed scope.
        """
        supported = implicit_events(rows)[0]
        scope = object_scope if object_scope is not None else (parsed or {}).get('scope_requirement', {}).get('object_scope')
        if scope != 'own':
            return supported
        own = [i for i in supported if rows[i]['source_member'] or rows[i]['subject_role_supported']]
        if graph.get('canonical_activity_policy'):
            return own
        return choose_event_granularity(own, definitions,
                                        (parsed or {}).get('scope_requirement', {}).get('granularity','coarse'))

    def history_paths(state, choices=None):
        """PURPOSE: Resolve and validate the selected path union per implicit ED.
        INPUT: Current state and optional Independently Verified path choices.
        OUTPUT: Separate per-ED path receipts, without changing the ED inventory.
        """
        et, scope_id = state['et'], state['scope_id']
        rows = catalog(et, scope_id, for_history=True)
        spans = state['history_scope_spans']
        receipt = {}
        for eid in state['ids']:
            mode, paths = scope_history_paths(rows[eid]['attribution'], spans, focus=state['focus'],
                                              chosen_ids=(choices or {}).get(eid),
                                              review_required=state['history_scope_needs_review'])
            ids = tuple(sorted(path['id'] for path in paths))
            if mode == 'needs_role_review' or eid in (choices or {}) and not ids:
                receipt[eid] = dict(status='needs_role_review', path_ids=list(ids))
            else:
                key = et, eid, ids
                if key not in verified_unions:
                    if path_loader is not None and len(paths) > 1:
                        paths = path_loader(paths)
                    verified_unions[key] = verify_path_union(graph, database, objects[et], definitions[eid], paths)
                receipt[eid] = verified_unions[key]
        return receipt

    def selection(case, proposed=None, *, independently=False):
        """PURPOSE: Validate IDs and compute the mode-specific selection.
        INPUT: Selected ET/mode/focus and optional revised IDs. During independent seeding no parse is available.
        OUTPUT: Validated selection state and, for independent explicit picks, candidate role paths.
        """
        et, mode, focus = (case[k] for k in ('et','mode','focus'))
        if (focus and focus not in question) or mode not in ('explicit','implicit'):
            raise ValueError('invalid_mode_or_focus')
        scope_id = case.get('scope_id', '')
        if not independently:
            named = [edge for (target, edge), scope in case_scopes.items() if target == et and
                     mentions_role(parsed['case_requirement']['span'], scope['role'])]
            if len(named) == 1 and not (
                    mode == 'implicit' and role_scope_needs_review([parsed['case_requirement']['span']], role_labels)):
                scope_id = named[0]
            if mode == parsed['activity_scope'] == 'implicit' and parsed.get('process_focus'):
                focus = parsed['process_focus']['span']
        rows = catalog(et, scope_id, for_history=mode == 'implicit' and (not unified or paired_pi_controls))
        allowed = {i for i,r in rows.items() if r['eligible'] and r['attribution']['status']=='pass'}
        supported = implicit_inventory(rows, case['object_scope'] if independently else None)
        classifications = {}
        requirements, paths = [], {}
        payload = {'original_request':question, 'case':ets[et], 'focus':focus}
        history_scope_spans = []
        history_scope_needs_review = False
        if mode == 'implicit':
            if parsed and (not unified or paired_pi_controls):
                history_scope_spans = [parsed['case_requirement']['span'], parsed['scope_requirement']['span']]
                if focus and focus not in history_scope_spans:
                    history_scope_spans.append(focus)
                scoped = case_scopes.get((et, scope_id))
                if scoped:
                    history_scope_spans.append(scoped['role'])
                requested_roles = {label for label in role_labels
                                   if any(mentions_role(span, label) for span in history_scope_spans)}
                history_scope_needs_review = role_scope_needs_review(history_scope_spans, requested_roles)
                if requested_roles and not history_scope_needs_review:
                    supported = [i for i in supported if not (
                        {path_role(p).get('role') for p in rows[i]['attribution']['paths']} - {None}
                        and not any(path_role(p).get('role') in requested_roles or not path_role(p)
                                    for p in rows[i]['attribution']['paths']))]
            allowed = set(supported)
        if proposed is not None and (len(proposed)!=len(set(proposed)) or not set(proposed)<=allowed):
            raise ValueError('invalid_or_unattributable_definition')
        if mode == 'implicit' and not focus:
            ids = supported
        elif mode == 'implicit':
            groups = {}
            for i in supported:
                key = activity_identity(definitions[i]) if scope_verification else (
                    definitions[i].get('canonical_activity_id') or events[i]['name'].casefold() or i)
                groups.setdefault(key, []).append(i)
            if proposed is None:
                cards = [dict(events[g[0]], definitions=[events[i] for i in g]) for g in groups.values()]
                if cards and graph.get('indexed_request'):
                    replies = bounded_replies(cards, lambda chunk: ask('pi_focus', dict(payload, activities=chunk)),
                                              REVIEW_CARD_LIMIT)
                    decisions = [decision for reply in replies for decision in reply['decisions']]
                else:
                    decisions = ask('pi_focus', dict(payload, activities=cards))['decisions'] if cards else []
                by_id = {r['id']:r['decision'] for r in decisions}
                if len(by_id)!=len(decisions) or set(by_id)!={g[0] for g in groups.values()}:
                    raise ValueError('incomplete_focus_classification')
                classifications = {i:by_id[g[0]] for g in groups.values() for i in g}
            else:
                classifications = {i:'INCLUDE' if i in proposed else 'EXCLUDE' for i in supported}
                if any(len({classifications[i] for i in g})!=1 for g in groups.values()):
                    raise ValueError('split_activity_group')
            ids = [i for i,d in classifications.items() if d=='INCLUDE']
        elif independently:
            cards = [review_card(events[i], definitions[i], rows[i]) for i in sorted(allowed)]
            selected = ask('pi_events', dict(payload, activities=cards, initial_choice_only=True))['selected_events'] if cards else []
            ids = [item['event_definition_id'] for item in selected]
            paths = {item['event_definition_id']: item['path_id'] for item in selected if item['path_id']}
        else:
            requirements = parsed['activity_requirements']
            if proposed is not None:
                ids = proposed
            elif requirements:
                cards = [dict(review_card(events[i], definitions[i], rows[i]),
                              requirement_ids=[r['id'] for r in requirements if role_paths(rows[i], r, role_labels, proposal=True)[0]])
                         for i in sorted(allowed)]
                selection_payload = dict(payload, activity_requirements=requirements,
                                         activities=[card for card in cards if card['requirement_ids']])
                receipt = lookup_coverage[et, scope_id, False]
                if graph.get('index_scope', {}).get('projection') == 'semantic':
                    ordered, detail = prepare_cards(selection_payload['activities'], requirements,
                                                    graph.get('event_families', []), detail_limit=semantic_top_k)
                    selection_payload['activities'] = ordered
                    receipt['expanded_detail'] = detail
                receipt['proposal'] = sorted(card['id'] for card in selection_payload['activities'])
                matches = (select_batches(ask, selection_payload) if graph.get('indexed_request')
                           else ask('pi_events', selection_payload)['matches'])
                ids = sorted({i for match in matches for i in match['event_definition_ids']})
            else:
                ids = []
        if len(ids)!=len(set(ids)) or not set(ids)<=allowed:
            raise ValueError('invalid_or_unattributable_definition')
        state = {'et':et,'mode':mode,'focus':focus,'scope_id':scope_id,'ids':sorted(ids),
                 'classifications':classifications}
        if mode == 'implicit' and (not unified or paired_pi_controls):
            state.update(history_scope_spans=history_scope_spans, history_inventory=supported,
                         history_scope_needs_review=history_scope_needs_review)
            state['history_attribution'] = history_paths(state)
        if independently:
            state.update(independent_object_scope=case['object_scope'], independent_proposal_ids=sorted(ids),
                         independent_role_paths=paths)
        elif mode == 'explicit' and proposed is None and requirements:
            state['requirement_proposals'] = matches
        return state

    def active_requirements(state):
        """PURPOSE: Read accepted per-item edits. INPUT: One case selection state. OUTPUT: Requirements in original ID order."""
        revised = state.get('revised_requirements', {})
        return [revised.get(item['id'], item) for item in parsed['activity_requirements']]

    def structures(state, outcomes=None):
        """PURPOSE: Prepare downstream fields and structural checks using the selection's own mode.
        INPUT: Selection state and optional requirement verdicts. OUTPUT: PI selection and checks.
        """
        scope = ('process_focus' if state['focus'] else 'attributable_history') if state['mode']=='implicit' else 'unresolved'
        req = {'activity_scope':state['mode'],'scope_requirement':{'object_scope':scope,'span':question},
               'case_requirement':{'span':question},'activity_requirements':[],
               'process_focus':{'span':state['focus'],'meaning':state['focus']} if state['focus'] else None}
        if parsed and state['mode'] == parsed['activity_scope'] == 'explicit':
            req = dict(parsed, activity_requirements=active_requirements(state))
        adapted = {'target_ot_id':state['et'],'activity_scope':state['mode'],'object_scope':scope,
                   'selected_candidate_ids':state['ids']}
        rows = catalog(state['et'], state['scope_id'], for_history='history_attribution' in state)
        initial_scope = state.get('independent_object_scope') if parsed is None else None
        if unified and state['mode'] == 'implicit':
            initial_scope = parsed['scope_requirement']['object_scope']
        scoped_inventory = (state['history_inventory'] if 'history_inventory' in state
                            else implicit_inventory(rows, initial_scope) if state['mode'] == 'implicit' else None)
        valid = validate_state(graph, adapted, req, rows, structural_only=True, implicit_inventory=scoped_inventory,
                               resolved_pairs=state.get('history_distinct_pairs', ()))
        if 'history_attribution' in state:
            for identifier, receipt in state['history_attribution'].items():
                status = receipt['status']
                if status != 'pass':
                    valid['warnings'].append(dict(kind='implicit_attribution_unresolved', reason=status,
                                                  evidence_ids=[identifier, *receipt['path_ids']]))
                    valid['status'] = 'unresolved'
            rows = {**rows, **{identifier: dict(rows[identifier], rollup_ids=sorted({
                rollup for path in rows[identifier]['attribution']['paths'] if path['id'] in receipt['path_ids']
                for rollup in path.get('rollup_ids', [])}))
                for identifier, receipt in state['history_attribution'].items()}}
        if outcomes is not None:
            valid['requirement_results'] = outcomes
            valid['mappings'] = {r['id']:r['event_definition_ids'] for r in outcomes if r['status'] == 'verified'}
        final = legacy_selection(adapted,req,valid,rows)
        final['case_scope'] = copy.deepcopy(case_scopes.get((state['et'], state['scope_id'])))
        if outcomes is not None:
            final['activity_requirement_results'] = outcomes
        return final,valid

    def seed_unified():
        """PURPOSE: Obtain one joint PI, then apply the registered verification policy.
        INPUT: Current graph and arm. OUTPUT: Compatibility state and optional local finalization.
        """
        nonlocal parsed, failed_role
        catalog_keys = [(et, '') for et in ets] + list(case_scopes)
        evidence = semantic_payload(question, objects, definitions, scope_cards,
                                    {key: catalog(*key) for key in catalog_keys}, graph, unified.compact)
        unified_trace['coverage'] = {
            'entities': [card['id'] for card in evidence['entity_types']],
            'activities': [card['id'] for card in evidence['activities']],
            'definitions': [d['id'] for card in evidence['activities'] for d in card['definitions']],
            'attributions': {d['id']: d['attribution'] for card in evidence['activities']
                             for d in card['definitions']},
        }
        failed_role = 'pi_unified'
        if unified.replay is None:
            guidance = load_prompt('step2_retrieve_and_interpret', 'guide_unified_interpretation') if unified.guided else ''
            initial, _ = call_role('pi_unified', evidence, client, model, cache, few_shot=False,
                                   audit_sink=calls, schema=UNIFIED_SCHEMA, system_appendix=guidance)
        else:
            from jsonschema import Draft202012Validator
            initial = copy.deepcopy(unified.replay)
            if not Draft202012Validator(UNIFIED_SCHEMA).is_valid(initial):
                raise ValueError('invalid_replayed_unified_contract')
        failed_role = None
        parsed, state, outcomes, issues = resolve_proposal(initial, question, case_scopes, definitions, catalog)
        unified_trace.update(initial_proposal=initial, initial_issues=copy.deepcopy(issues))
        if state['et'] in ets and not any(i['target'] == 'case' for i in issues):
            if paired_pi_controls and state['mode'] == 'implicit' and not any(i['target'] == 'focus' for i in issues):
                proposed = state['ids'] if state['focus'] else None
                state = selection(state, proposed=proposed)
            initial_candidates.append(state)
        if unified.verification == 'independent':
            if not initial_candidates:
                raise ValueError(issues[0]['kind'])
            if any(i['kind'] == 'invalid_focus_span' for i in issues):
                raise ValueError('invalid_focus_span')
            return state, None

        def assess(candidate, results, problems):
            """PURPOSE: Validate the resolved projection. INPUT: Semantic state and item outcomes.
            OUTPUT: Downstream envelope fields, structural checks and revision triggers.
            """
            if candidate['et'] not in ets or any(i['target'] == 'case' for i in problems):
                return None, None, problems
            final, validation = structures(candidate, results)
            checks = []
            for item in validation['warnings']:
                affected = set(item['evidence_ids'])
                targets = [r['id'] for r in results or [] if affected.intersection(r['event_definition_ids'])]
                if item['kind'] in {'entity_population_resolution', 'ot_existence'}:
                    targets = ['case']
                checks.extend(dict(kind=item['kind'], target=target, evidence_ids=item['evidence_ids'])
                              for target in targets or ['selection'])
            return final, validation, problems + checks

        final, validation, issues = assess(state, outcomes, issues)
        if issues and unified.verification == 'conditional':
            attempt = dict(input=dict(initial_proposal=initial, issues=issues), accepted=False,
                           role='pi_unified_revision')
            revisions.append(attempt)
            try:
                amended, _ = call_role('pi_unified_revision', dict(evidence, **attempt['input']), client, model,
                                       cache, few_shot=False, audit_sink=calls, schema=UNIFIED_SCHEMA)
                attempt['output'] = amended
                check_revision(initial, amended, issues)
                repaired_parse, repaired, repaired_outcomes, repaired_issues = resolve_proposal(
                    amended, question, case_scopes, definitions, catalog)
                original_parsed = parsed
                parsed = repaired_parse
                new_final, new_validation, new_issues = assess(repaired, repaired_outcomes, repaired_issues)
                if new_issues:
                    parsed = original_parsed
                    attempt['reason'] = 'unresolved_after_revision'
                    attempt['remaining_issues'] = new_issues
                else:
                    state, final, validation, issues = repaired, new_final, new_validation, []
                    attempt['accepted'] = True
            except ValueError as exc:
                attempt['reason'] = str(exc)
        unified_trace['final_issues'] = issues
        if final is None:
            return state, None
        return state, dict(status='ready' if not issues else 'partial', initial=initial_candidates[0]
                           if initial_candidates else {}, final=final, selection=state, validation=validation,
                           reason='unified_requirements_unresolved' if issues else '',
                           rounds=[{'structural_checks': validation}])

    def implicit_pair_cards(state):
        """PURPOSE: Send unresolved overlap only when canonical occurrences can be distinguished.
        INPUT: Proposed implicit selection. OUTPUT: Pair IDs with ED evidence for existing Independent Verification.
        """
        cards = []
        selected = set(state['ids'])
        for pair in graph.get('event_definition_pair_relationships', []):
            ids = pair['binding_pair']
            if (pair.get('relationship') != 'unknown' or len(ids) != 2 or not set(ids) <= selected
                    or pair['id'] in state.get('history_distinct_pairs', [])):
                continue
            bindings = [definitions[i] for i in ids]
            identities = {binding.get('occurrence_identity_rule_id') for binding in bindings}
            if len(identities) != 2 or None in identities or len({b.get('ts_id') for b in bindings}) != 2:
                continue
            items = []
            for identifier, binding in zip(ids, bindings):
                columns = {binding.get('activity_column'), *binding.get('timestamp_columns', [])} - {None}
                source = binding.get('source_table')
                quotes = {item['text'] for item in (graph.get('data_dictionary') or {}).get('semantic_statements', [])
                          if item.get('table') == source and item.get('column') in columns and item.get('text')}
                if not quotes:
                    break
                items.append({'id': identifier, 'label': events[identifier]['name'],
                              'occurrence_time': binding.get('occurrence_time_source'),
                              'evidence': sorted(quotes)})
            if len(items) == 2:
                cards.append({'id': pair['id'], 'events': items})
        return cards

    def compare(state, locked):
        """PURPOSE: Compare independent semantic outputs.
        INPUT: Selection and verified items for this case. OUTPUT: Differences and per-item verdicts.
        """
        et = next(e for e in available_objects(graph) if e['id']==state['et'])
        activities = []
        for i in sorted(set(state['ids']) | set(state['classifications'])):
            semantics = definitions[i].get('activity_semantics') or {}
            quotes = [c['quote'] for c in semantics.get('citations', []) if c.get('quote')]
            activities.append(dict(events[i], description=events[i]['meaning'] or semantics.get('code_meaning'),
                                   dictionary_evidence=quotes[:2]))
        public_state = {key: value for key, value in state.items() if not key.startswith('history_')}
        described = dict(public_state, entity_type=dict(ets[state['et']],
                         instance_definition=et.get('business_definition') or ets[state['et']]['meaning']),
                         case_scope=case_scopes.get((state['et'], state['scope_id'])), activities=activities)
        requirements = active_requirements(state)
        interpretation = dict(parsed, activity_requirements=requirements)
        review_payload = {'original_request':question, 'selection':described, 'request_interpretation':interpretation}
        rows = catalog(state['et'], state['scope_id'], for_history='history_attribution' in state)
        ambiguous = {identifier for identifier, receipt in state.get('history_attribution', {}).items()
                     if receipt['status'] == 'needs_role_review'}
        if ambiguous:
            review_payload['implicit_role_review'] = [
                {'id': identifier, 'label': events[identifier]['name'],
                 'paths': [{'id': p['id'], 'role': path_role(p).get('role'), 'evidence': path_role(p).get('quote')}
                           for p in rows[identifier]['attribution']['paths']]}
                for identifier in sorted(ambiguous)]
        if 'history_attribution' in state:
            pair_review = implicit_pair_cards(state)
            if pair_review:
                review_payload['implicit_pair_review'] = pair_review
        admissible_scopes = [card for card in scope_cards if card['et'] == state['et']]
        case_is_locked = bool(state.get('revised_requirements'))
        if case_is_locked:
            review_payload['case_is_locked'] = True
        elif admissible_scopes:
            review_payload['case_scope_options'] = admissible_scopes
        explicit = state['mode'] == parsed['activity_scope'] == 'explicit'
        pending = [r for r in requirements if r['id'] not in locked]
        initial_proposals = {m['requirement_id']: m['event_definition_ids']
                             for m in state.get('requirement_proposals', [])}
        revised_proposals = {rid: ids for rid, ids in state.get('revised_proposals', {}).items() if rid not in locked}
        if explicit:
            review_payload['activity_review'] = {'requirements': pending,
                'initial_proposals': [{'requirement_id': r['id'], 'event_definition_ids': initial_proposals[r['id']]}
                                      for r in pending if initial_proposals.get(r['id'])],
                'revised_proposals': revised_proposals,
                'candidates': [review_card(events[i], definitions[i], rows[i])
                               for i in sorted(rows)] if pending else [],
                'documented_sources': documented_activity_sources(graph) if pending else [],
                'scope_verification': scope_verification}
            if graph.get('indexed_request'):
                # Selection IDs resolve to the same cards in activity_review.
                described['activities'] = []
                for card in review_payload['activity_review']['candidates']:
                    if card.get('code_meaning') in (None, card.get('name'), card.get('meaning')):
                        card.pop('code_meaning', None)
                    if card.get('meaning') in ('', card.get('name')):
                        card.pop('meaning', None)
            accounted = {identifier for result in locked.values() for identifier in result.get('aligned_proposal_ids', [])}
            independent_ids = sorted(set(state.get('independent_proposal_ids', [])) - accounted)
            if independent_ids and pending:
                review_payload['activity_review']['independent_proposal_ids'] = independent_ids
                review_payload['activity_review']['independent_role_paths'] = {
                    i: p for i, p in state.get('independent_role_paths', {}).items() if i in independent_ids}
        if evidence_reader is not None:
            search = dict(parsed, activity_requirements=pending) if explicit else parsed
            review_payload['retrieved_evidence'] = evidence_reader.retrieve(
                question, state, search, rows, top_k=semantic_top_k)
            evidence_reader.audits[-1]['phase'] = 'pi_crosscheck'
        if (not context_attempted and state['mode'] == 'explicit' and parsed['activity_scope'] == 'explicit'
                and any(r.get('effective_tier') == 2 and r['attribution']['status'] == 'pass' for r in rows.values())):
            review_payload['complete_tier1_inventory'] = [events[i] for i,r in rows.items()
                if r.get('effective_tier') == 1 and r['attribution']['status'] == 'pass']
        reply = (review_batches(ask, review_payload) if graph.get('indexed_request') and explicit
                 else ask('pi_crosscheck', review_payload))
        differences = reply['differences']
        spans = {x['span'] for x in requirements}
        targets = set(state['ids']) | set(state['classifications']) | {state['et']}
        for d in differences:
            t = d['target']
            if not t or not d['reason'].strip() or (t not in targets and t not in question):
                raise ValueError('invalid_difference_reference')
            if (d['kind']=='unrequested' and (t not in state['ids'] or state['mode']!='explicit') or
                d['kind']=='unmatched' and t not in spans or
                d['kind']=='focus_conflict' and (state['mode']!='implicit' or not (state['focus'] or parsed.get('process_focus'))) or
                d['kind']=='uncertain' and state['classifications'].get(t)!='UNCERTAIN'):
                raise ValueError('invalid_difference_target')
        forced = [('uncertain',i) for i,d in state['classifications'].items() if d=='UNCERTAIN']
        if state['mode']!=parsed['activity_scope']:
            forced.append(('mode_mismatch',state['et']))
        for kind,target in forced:
            if not any(d['kind']==kind and (kind=='mode_mismatch' or d['target']==target) for d in differences):
                differences.append({'kind':kind,'target':target,'reason':kind})
        outcomes = None
        if explicit:
            current = {r['requirement_id']: r for r in reply['requirement_reviews']}
            outcomes = [locked[r['id']] if r['id'] in locked else
                        verify_activity(r, current[r['id']], rows, state['ids'], definitions,
                                        known_roles=role_labels, verified_review_selection=True,
                                        canonical_only=bool(graph.get('canonical_activity_policy')),
                                        question=question,
                                        initial_ids=set(initial_proposals.get(r['id'], ())) |
                                                    set(revised_proposals.get(r['id'], ())) |
                                                    set(current[r['id']].get('aligned_proposal_ids', ())))
                        for r in requirements]
            for outcome in outcomes:
                if scope_verification and outcome['id'] not in locked:
                    verdict = current[outcome['id']]
                    cards = review_payload['activity_review']['candidates']
                    required = documented_family_members(outcome, verdict['event_definition_ids'], cards)
                    receipt = lookup_coverage[state['et'], state['scope_id'], False]
                    offered_ids = {card['id'] for card in cards}
                    missing_retrieval = sorted((set(receipt['available']) - offered_ids) |
                                               set(receipt['retrieval_gaps']))
                    receipt['reviewed'][outcome['id']] = sorted(
                        {item['event_definition_id'] for item in verdict['candidate_decisions']} & offered_ids)
                    coverage = check_scope(question, verdict['candidate_decisions'], cards,
                                           verdict['event_definition_ids'], definitions, required=required,
                                           exhaustive=not missing_retrieval)
                    coverage['missing_retrieval'] = missing_retrieval
                    outcome['scope_coverage'] = coverage
                    codes = ('missing_judgments', 'invalid_judgments', 'duplicate_judgments',
                             'unknown_scope', 'missing_required', 'unsupported_selection', 'missing_retrieval')
                    failures = [code for code in codes if coverage[code]]
                    if failures:
                        outcome.update(status='unresolved', event_definition_ids=[], definition_path_ids={},
                                       attribution_path_ids=[], added_by_independent_review=[])
                        outcome['reason_codes'].extend('scope_' + code for code in failures)
                if outcome['id'] not in locked and 'aligned_proposal_ids' in current[outcome['id']]:
                    outcome['aligned_proposal_ids'] = current[outcome['id']]['aligned_proposal_ids']
        reviewed_scope = reply.get('required_case_scope_id', state['scope_id'])
        if not reviewed_scope and state['scope_id'] and mentions_role(
                parsed['case_requirement']['span'], case_scopes[state['et'], state['scope_id']]['role']):
            reviewed_scope = state['scope_id']
        paths = {item['event_definition_id']: item['path_ids'] for item in reply.get('implicit_role_reviews', [])}
        reviewed_pairs = [item['pair_id'] for item in reply.get('implicit_pair_reviews', []) if item['decision'] == 'distinct']
        return differences, set(reply.get('absent_from_tier1', [])), outcomes, reviewed_scope, paths, reviewed_pairs

    def revise_requirements(state, locked, outcomes):
        """PURPOSE: Revisit only unresolved explicit items for the current case.
        INPUT: Case state, locked verdicts and current outcomes. OUTPUT: Revised proposal for independent re-review.
        """
        rows = catalog(state['et'], state['scope_id'])
        unresolved = [r for r in outcomes if r['id'] not in locked]
        requirements = {r['id']: r for r in active_requirements(state)}
        payload = {'original_request': question, 'case': ets[state['et']],
                   'case_scope': case_scopes.get((state['et'], state['scope_id'])),
                   'unresolved_requirements': [requirements[r['id']] for r in unresolved],
                   'review_findings': unresolved, 'verified_requirement_ids': sorted(locked),
                   'activities': [review_card(events[i], definitions[i], row) for i, row in sorted(rows.items())
                                  if row['eligible'] and row['attribution']['status'] == 'pass']}
        attempt = {'role': 'pi_revise_requirement', 'input': payload, 'accepted': False}
        revisions.append(attempt)
        edits = ask('pi_revise_requirement', payload)
        attempt['output'] = copy.deepcopy(edits)
        if not edits['edits']:
            raise ValueError('revision_abstained')
        original = {m['requirement_id']: m['event_definition_ids'] for m in state.get('requirement_proposals', [])}
        existing = {**original, **state.get('revised_proposals', {})}
        revised = dict(state.get('revised_requirements', {}))
        proposals = dict(state.get('revised_proposals', {}))
        for edit in edits['edits']:
            identifier = edit['requirement_id']
            requirement = {'id': identifier, **{key: edit[key] for key in
                           ('span', 'meaning', 'qualifiers', 'coverage', 'granularity')}}
            candidates = sorted(edit['event_definition_ids'])
            if requirement != requirements[identifier] or candidates != sorted(existing.get(identifier, [])):
                revised[identifier] = requirement
                proposals[identifier] = candidates
        if proposals == state.get('revised_proposals', {}) and revised == state.get('revised_requirements', {}):
            raise ValueError('revision_did_not_resolve_requirement')
        ids = {i for r in locked.values() for i in r['event_definition_ids']}
        ids.update(i for rid, values in {**existing, **proposals}.items() if rid not in locked for i in values)
        return dict(state, ids=sorted(ids), revised_requirements=revised, revised_proposals=proposals)

    def propose_initial():
        """PURPOSE: Generate initial case/event interpretations under the selected input policy.
        INPUT: Current raw request and optional parsed requirements. OUTPUT: Validated states or a role diagnostic.
        """
        nonlocal failed_role, evidence_reader, eeg_delivery, summary
        if not ets:
            raise ValueError(reason)
        limit = min(max_candidates, 3)
        payload = {'original_request': question, 'entity_types': list(ets.values()),
                   'max_candidates': limit, 'case_scopes': scope_cards}
        if independent_initial:
            payload['initial_choice_only'] = True
        else:
            payload['request_interpretation'] = parsed
        if case_hint_lookup is not None and parsed and parsed.get('activity_requirements'):
            phrases = [item[key] for item in parsed['activity_requirements'] for key in ('span', 'meaning')]
            hints = case_hint_lookup(phrases)
            if hints:
                payload['entity_types'] = sorted(payload['entity_types'],
                                                 key=lambda item: item['id'] not in hints)
                payload['attributable_activity_hints'] = {i: ids for i, ids in hints.items() if i in ets}
        cases = ask('pi_cases', payload)['candidates']
        if not 0 < len(cases) <= limit or len({c['et'] for c in cases}) != len(cases):
            raise ValueError('ambiguous_or_invalid_cases')
        if case_definition_loader is not None:
            identifiers = sorted({case['et'] for case in cases})
            if not set(identifiers) <= objects.keys():
                raise ValueError('unknown_case_notion')
            loaded = case_definition_loader(identifiers)
            validate_runtime_graph(loaded)
            graph.clear()
            graph.update(loaded)
            definitions.update({item['id']: item for item in loaded['event_definitions']})
            events.update({identifier: entry(item, True) for identifier, item in definitions.items()})
            summary = graph.get('revision_summary')
            if evidence_retrieval:
                evidence_reader = PIEvidenceRetriever(graph, encoder=semantic_encoder)
            if eeg_delivery is not None:
                delivery = type(eeg_delivery)(graph, eeg_delivery.mode)
                delivery.audit = eeg_delivery.audit
                eeg_delivery = delivery
        for case in cases:
            try:
                initial_candidates.append(selection(case, independently=independent_initial))
            except (KeyError, ValueError, TypeError) as exc:
                rejected_initial.append(dict(case=case, reason=str(exc), failed_role=failed_role))
                if len(cases) == 1:
                    raise
                failed_role = None
        if not initial_candidates:
            failed_role = rejected_initial[-1]['failed_role']
            raise ValueError(rejected_initial[-1]['reason'])

    chosen = None
    distinct = {}
    try:
        if independent_initial:
            try:
                propose_initial()
            except (KeyError, ValueError, TypeError) as error:
                initial_failure = (str(error), failed_role)
                failed_role = None
            else:
                initial_failure = None
        if unified:
            _, local = seed_unified()
            if unified.verification != 'independent':
                chosen = local
                if local:
                    alternatives.append(local)
                elif unified_trace.get('final_issues'):
                    reason = unified_trace['final_issues'][0]['kind']
        else:
            parsed = ask('semantic_decomposer', {'original_request': question})
            if parsed['activity_scope'] == 'explicit':
                budget = 1
            if independent_initial:
                if initial_failure:
                    failure, failed_role = initial_failure
                    raise ValueError(failure)
            else:
                propose_initial()
        if unified and (unified.verification != 'independent' or parsed['activity_scope'] == 'explicit'):
            budget = 1
        review_initials = initial_candidates if not unified or unified.verification == 'independent' else []
        for initial in review_initials:
            state = initial
            history = {'initial':initial,'rounds':[],'kept':[]}
            alternatives.append(history)
            first_revision=len(revisions)
            try:
                seen = {fingerprint(state)}
                resolved = set()
                locked = {}
                scope_revised = False
                while True:
                    unambiguous = False
                    if (not paired_pi_controls and 'history_attribution' in state
                            and parsed['activity_scope'] == 'implicit' and not state['focus']):
                        # One literal ET match and a clean structural/path proof permit deterministic inclusion.
                        span = parsed['case_requirement']['span']
                        matches = [eid for eid, card in ets.items()
                                   if any(mentions_role(span, name) for name in (card['name'], card['name'] + 's'))]
                        unambiguous = (matches == [state['et']] and len(initial_candidates) == 1
                                       and not state['scope_id'] and not state['history_scope_needs_review']
                                       and not implicit_pair_cards(state) and not any(receipt['status'] == 'needs_role_review'
                                                   for receipt in state['history_attribution'].values()))
                    if unambiguous:
                        differences, absent, outcomes, reviewed_scope, roles, reviewed_pairs = [], set(), None, state['scope_id'], {}, []
                    else:
                        differences, absent, outcomes, reviewed_scope, roles, reviewed_pairs = compare(state, locked)
                    if reviewed_pairs:
                        state = dict(state, history_distinct_pairs=reviewed_pairs)
                    if roles:
                        state = dict(state, history_attribution=history_paths(state, roles))
                    if reviewed_scope != state['scope_id']:
                        if scope_revised:
                            raise ValueError('case_scope_unresolved')
                        scope_revised = True
                        locked = {}
                        state = selection(dict(state, scope_id=reviewed_scope))
                        continue
                    if outcomes is not None:
                        accepted_state = dict(state, ids=sorted({i for r in outcomes for i in r['event_definition_ids']}))
                        final, validation = structures(accepted_state, outcomes)
                        if validation['warnings']:
                            outcomes = resolve_selection_conflicts(outcomes, validation['warnings'],
                                graph.get('event_definition_pair_relationships', []), locked)
                            accepted_state['ids'] = sorted({i for r in outcomes for i in r['event_definition_ids']})
                            final, validation = structures(accepted_state, outcomes)
                        verified = {r['id']: r for r in outcomes if r['status'] == 'verified'}
                        case_ok = not differences and not any(c['blocking'] and c['status'] != 'pass'
                            and c['check'] == 'ot_existence' for c in validation['checks'])
                        if case_ok:
                            locked = verified
                            state = dict(state, ids=sorted(set(state['ids']) | set(accepted_state['ids'])))
                            history['partial'] = {'final': final, 'validation': validation, 'selection': accepted_state}
                        differences.extend({'kind':'unmatched', 'target':r['id'], 'reason':r['reason'],
                                            'reason_codes':r['reason_codes']}
                                           for r in outcomes if r['status'] != 'verified')
                    else:
                        accepted_state = state
                        final, validation = structures(state)
                    pending = [d for d in differences if (d['kind'],d['target']) not in resolved]
                    issues = pending + validation['warnings']
                    history['rounds'].append({'selection':state,'differences':differences,'structural_checks':validation})
                    if not issues:
                        history.update(status='ready',final=final,validation=validation,selection=accepted_state)
                        break
                    physical_issue = next((item['reason'] for item in validation['warnings']
                                           if item['kind'] == 'implicit_attribution_unresolved'
                                           and item['reason'] != 'needs_role_review'), None)
                    if physical_issue and not pending:
                        history.update(status='selection_required', reason=physical_issue)
                        break
                    if outcomes is not None and case_ok and not context_attempted and absent:
                        et = state['et']
                        missing = [r['span'] for r in outcomes
                                   if 'event_definition_missing' in r['reason_codes'] and r['span'] in absent]
                        approved, receipt = request_approvals(question, missing, dict(ets[et], id=et),
                            definitions, catalog(et, state['scope_id']), client, model, cache)
                        if receipt:
                            calls.append(receipt)
                            context_attempted = True
                        if approved:
                            scoped_approvals[et] = approved
                            catalogs.pop((et, state['scope_id'], False))
                            state = {**state, **selection(state, sorted(set(state['ids']) | set(approved)))}
                            continue
                    if len(revisions)>=budget:
                        history.update(status='selection_required',reason='revision_budget_exhausted')
                        break
                    if outcomes is not None and case_ok and any(r['id'] not in locked for r in outcomes):
                        state = revise_requirements(state, locked, outcomes)
                        key = fingerprint(state)
                        if key in seen:
                            raise ValueError('repeated_state')
                        seen.add(key)
                        resolved.clear()
                        revisions[-1]['accepted'] = True
                        continue
                    if not summary and graph.get('indexed_request'):
                        from src.eeg.eeg_store import EEGLookup
                        EEGLookup.attach_summary(graph)
                        summary = graph['revision_summary']
                    if not summary or 'members' not in summary:
                        raise ValueError('prepared_eeg_summary_required')
                    et_aliases = summary['et_aliases']
                    current_et = next((a for a,v in et_aliases.items() if v==state['et']),None)
                    if not current_et:
                        raise ValueError('summary_et_missing')
                    current_members = summary['members'][current_et]
                    aliases = {eid:a for a,ids in current_members.items() for eid in ids}
                    # Only current selections absent from the verified inventory receive removal-only references.
                    aliases.update({i:'X'+str(n) for n,i in enumerate(sorted((set(state['ids'])|set(state['classifications']))-aliases.keys()),1)})
                    aliases[state['et']] = current_et
                    alias_ids = sorted({aliases[i] for i in state['ids']})
                    wire_state = dict(state,et=current_et,ids=alias_ids,allowed_by_et={e:list(m) for e,m in summary['members'].items()},classifications={
                        aliases[i]:v for i,v in state['classifications'].items()})
                    wire_issues = [dict(d,target=aliases.get(d['target'],d['target'])) if 'target' in d
                                   else dict(d,evidence_ids=[aliases.get(i,i) for i in d.get('evidence_ids',[])]) for d in issues]
                    payload = {'original_request':question,'selection':wire_state,'differences':wire_issues,'eeg_summary':summary['paragraph']}
                    if outcomes is not None:
                        pending_ids = {d['target'] for d in pending if d['kind'] == 'unmatched'}
                        changing_case = any(d['kind'] == 'case_mismatch' for d in pending)
                        payload['unresolved_requirements'] = [r for r in parsed['activity_requirements']
                                                              if changing_case or r['id'] in pending_ids]
                        payload['verified_ids'] = sorted({aliases[i] for r in locked.values() for i in r['event_definition_ids']})
                        payload['selection'].pop('requirement_proposals', None)
                    if evidence_reader is not None:
                        evidence_aliases = {identifier:alias for alias,identifier in et_aliases.items()}
                        evidence_aliases.update({eid:alias for members in summary['members'].values()
                                                 for alias,ids in members.items() for eid in ids})
                        evidence_aliases.update(aliases)
                        payload['retrieved_evidence'] = evidence_reader.retrieve(
                            question, state, dict(parsed, activity_requirements=payload['unresolved_requirements'])
                            if outcomes is not None else parsed, catalog(state['et'], state['scope_id']), issues=issues,
                            aliases=evidence_aliases, top_k=2*semantic_top_k if outcomes is not None else semantic_top_k)
                        evidence_reader.audits[-1]['phase'] = 'pi_revise'
                    attempt = {'input':payload,'accepted':False}
                    revisions.append(attempt)
                    proposal = ask('pi_revise',payload)
                    attempt['output'] = copy.deepcopy(proposal)
                    if proposal['action']!='abstain':
                        dest = proposal['et']
                        choices = proposal['ids']
                        if dest not in et_aliases:
                            raise ValueError('invalid_or_unattributable_alias')
                        selected = []
                        for a in choices:
                            previous = [i for i in state['ids'] if aliases[i]==a] if dest==current_et else []
                            selected.extend(previous if proposal['action']=='keep' else summary['members'][dest][a])
                        resolutions = []
                        for x in proposal['resolutions']:
                            matches = [d for d in pending if d['kind']==x['kind'] and aliases.get(d['target'],d['target'])==x['target']]
                            if not matches:
                                if structural_reply_target(x['target'],wire_issues):
                                    # Structural checks run again against the revised selection.
                                    continue
                                raise ValueError('invalid_keep_target')
                            resolutions.extend(dict(x,target=d['target']) for d in matches)
                        proposal = dict(proposal,et=et_aliases[dest],ids=selected,resolutions=resolutions)
                    if proposal['action']=='abstain':
                        raise ValueError('revision_abstained')
                    if outcomes is not None and proposal['action'] == 'keep':
                        raise ValueError('revision_did_not_resolve_requirement')
                    if outcomes is not None and proposal['et'] != state['et'] and not any(
                            d['kind'] == 'case_mismatch' for d in pending):
                        raise ValueError('revision_cannot_replace_verified_case')
                    if proposal['et'] == state['et']:
                        proposal['scope_id'] = state['scope_id']
                        proposal['ids'] = sorted(set(proposal['ids']) |
                            {i for r in locked.values() for i in r['event_definition_ids']})
                    else:
                        locked = {}
                    trial = state if proposal['action']=='keep' else selection(proposal,proposal['ids'])
                    if outcomes is not None and trial['et'] == state['et'] and trial['mode'] == 'explicit':
                        if trial['ids'] == state['ids']:
                            raise ValueError('revision_did_not_resolve_requirement')
                    if fingerprint(trial)==fingerprint(state) and (proposal['resolutions'] or proposal['action']=='keep'):
                        keys = {(x['kind'],x['target']) for x in proposal['resolutions']}
                        if any(not x['span'].strip() or x['span'] not in question for x in proposal['resolutions']):
                            raise ValueError('invalid_keep_evidence')
                        resolved.update(keys)
                        history['kept'].extend(proposal['resolutions'])
                        attempt['accepted'] = True
                        if {(d['kind'],d['target']) for d in pending} - keys:
                            continue
                        if validation['warnings']:
                            history.update(status='selection_required',reason='structural_failure')
                        else:
                            history.update(status='ready',final=final,validation=validation,selection=accepted_state)
                        break
                    else:
                        state = trial
                        key = fingerprint(state)
                        if key in seen:
                            raise ValueError('repeated_state')
                        seen.add(key)
                        resolved.clear()
                    attempt['accepted'] = True
            except (KeyError, ValueError, TypeError) as exc:
                history.update(status='selection_required',reason=str(exc),failed_role=failed_role)
                if len(revisions)>first_revision and not revisions[-1]['accepted']:
                    revisions[-1]['reason']=str(exc)
                    last_role = revisions[-1].get('role', 'pi_revise')
                    if 'output' not in revisions[-1] and calls and calls[-1]['role'] == last_role:
                        revisions[-1]['output'] = calls[-1].get('parsed_response', calls[-1].get('invalid_response'))
                failed_role=None
        ready = [h for h in alternatives if h.get('status')=='ready']
        for candidate in ready:
            final = candidate['final']
            identity = (final['target_object_id'], candidate['selection']['scope_id'], frozenset(final['event_definition_ids']))
            distinct.setdefault(identity, candidate)
        if not distinct and any(h.get('reason')=='revision_budget_exhausted' for h in alternatives):
            reason = 'revision_budget_exhausted'
        elif len(distinct)==1:
            chosen = next(iter(distinct.values()))
        elif len(distinct)>1:
            reason = 'request_ambiguity'
            comparison = ask('interpretation_comparator', {
                'original_request': question, 'requirements': parsed,
                'interpretations': [dict(h['selection'],
                                         status=h['status'], final_validation=h['validation'],
                                         entity_type=ets[h['final']['target_object_id']],
                                         activities=[events[i] for i in h['final']['event_definition_ids']])
                                    for h in distinct.values()]})
            if comparison['decision']=='select' and comparison['reason_kind']=='supported_interpretation' and comparison['reason'].strip():
                matches = [h for h in distinct.values()
                           if comparison['target_ot_id']==h['final']['target_object_id']
                           and sorted(comparison['selected_candidate_ids'])==h['final']['event_definition_ids']]
                if len(matches)==1:
                    chosen = matches[0]
        elif alternatives:
            reason = alternatives[-1]['reason']
            failed_role=alternatives[-1].get('failed_role')
    except (KeyError, ValueError, TypeError, Step2ContextLimitExceeded) as exc:
        reason = 'scope_context_budget_exhausted' if isinstance(exc, Step2ContextLimitExceeded) else str(exc)
        if calls and not failed_role and not any(c.get("rejection")==reason for c in calls): calls[-1].update(validation="rejected",rejection=reason)
    if not chosen and not distinct:
        partial_by_case = {}
        for candidate in alternatives:
            partial = candidate.get('partial')
            if partial:
                target = partial['selection']['et']
                retained = partial_by_case.get(target)
                if retained is None or len(partial['validation']['mappings']) > len(retained['validation']['mappings']):
                    partial_by_case[target] = dict(partial, initial=candidate['initial'],
                        rounds=candidate['rounds'], reason=candidate.get('reason'), status='partial')
        if len(partial_by_case) == 1:
            chosen = next(iter(partial_by_case.values()))
        elif partial_by_case:
            reason = 'request_ambiguity'
    result = unresolved_interpretation(reason,calls,parsed)
    if initial_candidates:
        result['initial_audit']['initial_state'] = (chosen or {}).get('initial',initial_candidates[0])
    result.update(retrieval_coverage=list(lookup_coverage.values()),
        request_parsing=parsed, requirements=parsed or result['requirements'],
        interpretation_comparison=comparison,
        requirements_version=fingerprint(parsed), termination_reason=reason,
        initial_candidates=initial_candidates,rejected_initial_candidates=rejected_initial,candidate_interpretations=alternatives,revisions=revisions,
        revision_count=len(revisions),final_selection_version=len(revisions),max_revisions=budget,
        candidate_count=len(initial_candidates),selector_contract='independent_eeg_crosscheck_v3',
        cross_check={'candidates':alternatives,'revisions':revisions,'llm_calls':sum(
            not c['cache_hit'] and c.get('status_detail')!='context_limit_exceeded_not_sent' for c in calls)},
        configuration={'review_enabled':True,'max_revisions':budget,
                       'evidence_retrieval':bool(evidence_retrieval),'semantic_top_k':semantic_top_k,
                       **({'initial_selection_policy': 'independent_request_and_eeg'} if independent_initial else {})},
        evidence_retrieval={'version':RETRIEVAL_VERSION,'enabled':bool(evidence_retrieval),
                            'searches':evidence_reader.audits if evidence_reader is not None else []})
    if unified:
        result['configuration'].update(unified=unified_trace, guided=unified.guided, compact=unified.compact,
                                       verification_policy=unified.verification,
                                       review_enabled=unified.verification == 'independent')
        result['selector_contract'] = 'unified_process_information_v1'
        result['prompt_versions']['initial'] = 'interpret-unified-v1'
    if initial_candidates:
        result['initial_selection'] = structures((chosen or {}).get('initial',initial_candidates[0]))[0]
    if not chosen and alternatives:
        last = alternatives[-1]['rounds']
        if last:
            result['validations'] = [r['structural_checks'] for r in last]
            final_check = copy.deepcopy(last[-1]['structural_checks'])
            final_check['status'] = 'unresolved'
            final_check['warnings'].extend(last[-1]['differences'])
            result['final_validation'] = final_check
    if chosen:
        state = chosen['selection']
        final = chosen['final']
        status = chosen['status']
        validation = copy.deepcopy(chosen['validation'])
        if status == 'partial':
            validation['status'] = 'partial'
        result.update(status=status, terminal_status='validated' if status == 'ready' else 'partial',
            termination_reason='validation_complete' if status == 'ready' else chosen['reason'] or reason,
            final_validation=validation,final_selection=final,final_selection_fingerprint=fingerprint(state),
            validations=[r['structural_checks'] for r in chosen['rounds']])
        if state['mode']=='implicit':
            result['implicit_selection_audit'] = {
                'excluded_candidates': implicit_events(catalog(state['et'], state['scope_id'],
                                                               for_history='history_attribution' in state))[1],
                'attribution': state.get('history_attribution', {})}
        if state['mode'] == 'explicit' and scoped_approvals.get(state['et']):
            result['process_information']['tier2_approvals'] = {
                i:a for i,a in scoped_approvals[state['et']].items() if i in state['ids']}
        result['process_information'].update(status=status,case_notion_et_id=state['et'],request_mode=state['mode'],
            process_focus=final['process_focus'],selected_event_definition_ids=state['ids'],
            case_requirement=(parsed or {}).get('case_requirement'), activity_requirements=active_requirements(state),
            case_scope=final['case_scope'],
            case_population_policy='reference_role' if final['case_scope'] else 'all_identifiable_entities_in_selected_ET')
        if state['mode'] == 'explicit':
            result['process_information']['activity_requirement_results'] = final.get('activity_requirement_results', [])
            path_ids = {i: set() for i in state['ids']}
            for item in result['process_information']['activity_requirement_results']:
                for identifier in item['event_definition_ids']:
                    path_ids[identifier].update(item.get('definition_path_ids', {}).get(identifier, []))
            result['process_information']['verified_attribution_paths'] = {
                identifier: sorted(ids) for identifier, ids in path_ids.items()}
        elif unified and state.get('unified_paths') and set(state['ids']) <= state['unified_paths'].keys():
            result['process_information']['verified_attribution_paths'] = {
                i: state['unified_paths'][i] for i in state['ids']}
        elif 'history_attribution' in state:
            result['process_information']['verified_attribution_paths'] = {
                identifier: receipt['path_ids'] for identifier, receipt in state['history_attribution'].items()
                if receipt['status'] == 'pass'}
            partitions = {identifier: receipt['partition'] for identifier, receipt in state['history_attribution'].items()
                          if receipt['status'] == 'pass' and receipt.get('partition')}
            if partitions:
                result['process_information']['verified_attribution_partitions'] = partitions
        else:
            rows = catalog(state['et'], state['scope_id'])
            result['process_information']['verified_attribution_paths'] = {
                i: sorted(path['id'] for path in rows[i]['attribution']['paths']) for i in state['ids']
            }
    if not chosen and alternatives and 'status' not in alternatives[-1]:
        alternatives[-1].update(status='selection_required',reason=reason)
    if revisions and not revisions[-1]['accepted']:
        revisions[-1].setdefault('reason',reason)
        if 'output' not in revisions[-1] and calls[-1]['role']=='pi_revise':
            revisions[-1]['output'] = calls[-1].get('invalid_response')
    result['cross_check'].update(retries=retries,failed_role=failed_role)
    if failed_role and not chosen:
        result.update(status='invalid_llm_output',terminal_status='invalid_llm_output',termination_reason='invalid_llm_output:'+failed_role)
        result['process_information']['status']='invalid_llm_output'
    result['cross_check'].update(status=result['status'],reason=result['termination_reason'])
    return result
