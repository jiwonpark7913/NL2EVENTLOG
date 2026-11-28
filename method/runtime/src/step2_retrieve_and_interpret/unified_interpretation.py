"""Joint semantic interpretation over a projection of the existing EEG."""

from dataclasses import dataclass

from src.common.attribution_policy import mentions_role
from src.step1_understand.describe_business_entities_and_events import entry
from src.step2_retrieve_and_interpret.verify_activity_requirements import paths_by_role, review_card


@dataclass(frozen=True)
class UnifiedPolicy:
    """Experimental controls sharing one PI schema, independent of the baseline arm."""

    guided: bool = True
    compact: bool = True
    verification: str = 'conditional'
    replay: dict | None = None


def activity_id(definition):
    """PURPOSE: Reference one registered business activity. INPUT: Existing ED. OUTPUT: Activity ID or legacy ED ID."""
    return definition.get('canonical_activity_id') or definition['id']


def semantic_payload(question, objects, definitions, scopes, catalogs, graph, compact):
    """PURPOSE: Render all existing ET and ED candidates with their semantic attribution alternatives.
    INPUT: Full eligible Case catalog, annotations, and verbosity condition. OUTPUT: Gold-free role input.
    """
    entities = []
    for et, obj in sorted(objects.items()):
        card = dict(entry(obj), instance_granularity=obj.get('instance_granularity'),
                    can_anchor_case=(obj.get('population') or {}).get('status') == 'valid')
        entities.append(card)
    activities = {}
    for ed, definition in sorted(definitions.items()):
        event = entry(definition, True)
        meaning = definition.get('activity_semantics') or {}
        key = activity_id(definition)
        group = activities.setdefault(key, dict(id=key, name=event['name'], meaning=event['meaning'], definitions=[]))
        projections = []
        physical = {}
        for (target, scope_id), catalog in catalogs.items():
            row = catalog[ed]
            attribution = row['attribution']
            if attribution['status'] != 'pass':
                continue
            if scope_id:
                candidates = [path for path in attribution['paths']
                              if (path.get('case_role') or {}).get('step', {}).get('relationship_id') == scope_id]
                if not candidates:
                    continue
                row = dict(row, attribution=dict(attribution, paths=candidates))
            roles = sorted(paths_by_role(row))
            projection = dict(case_et_id=target, roles=roles or ['direct'],
                              own_event=bool(row['source_member'] or row['subject_role_supported']),
                              executable=row['eligible'])
            if scope_id:
                projection['case_scope_id'] = scope_id
            projections.append(projection)
            if not compact:
                evidence = review_card(event, definition, row)
                scope_key = target if not scope_id else f'{target}/{scope_id}'
                physical[scope_key] = {k: evidence[k] for k in ('role_projections','direct_case_mapping')
                                       if evidence[k]}
        pairing = definition.get('timestamp_pairing') or {}
        time_policy = next((item.get('occurrence_time_policy') for item in graph.get('event_entity_associations', [])
                            if item.get('event_definition_id') == ed and item.get('occurrence_time_policy')), {})
        card = dict(id=ed, phase=pairing.get('phase'), time_meaning=time_policy.get('semantic_role'),
                    carrier_meaning=meaning.get('code_meaning'), attribution=projections)
        if not compact:
            sample = next((catalog[ed] for catalog in catalogs.values()), None)
            if sample:
                extra = review_card(event, definition, sample)
                card.update({k: extra[k] for k in ('source','occurrence_time','dictionary_evidence','source_context')
                             if extra[k]})
            card['role_evidence_by_case'] = physical
        group['definitions'].append(card)
    return dict(original_request=question, entity_types=entities,
                case_scopes=[{k:v for k,v in card.items() if not compact or k != 'reference_table'} for card in scopes],
                activities=list(activities.values()),
                event_families=[{k: family[k] for k in ('id','label','phase','member_event_definition_ids',
                                'broad_event_definition_id') if k in family}
                                for family in graph.get('event_families', [])])


def resolve_proposal(proposal, question, scopes, definitions, get_catalog):
    """PURPOSE: Ground semantic IDs in the full graph and preserve unresolved request items.
    INPUT: Schema-valid proposal, original request and runtime catalogs. OUTPUT: Parsed compatibility view,
           selector state, requirement results, validated path IDs, and local issues.
    """
    et, mode = proposal['case_et_id'], proposal['request_mode']
    issues, paths, requirements, outcomes, proposals = [], {}, [], [], []
    initial_focus = proposal['process_focus']
    focus = initial_focus if initial_focus in question else ''
    case_span = proposal['case_span']
    if not case_span.strip() or case_span not in question:
        # The proposal identifies its Case by ET. Retain the original request as available evidence.
        case_span = question
    scope_id = proposal['case_scope_id']
    if not scope_id:
        named = [edge for (target, edge), scope in scopes.items()
                 if et == target and mentions_role(case_span, scope['role'])]
        if len(named) == 1:
            scope_id = named[0]
    if scope_id and (et, scope_id) not in scopes:
        issues.append(dict(kind='invalid_case_scope', target='case'))
    if initial_focus and not focus:
        issues.append(dict(kind='invalid_focus_span', target='focus'))
    try:
        catalog = get_catalog(et, scope_id)
    except ValueError as exc:
        if str(exc) != 'unknown_entity_type':
            raise
        issues.append(dict(kind='invalid_case_id', target='case'))
        catalog = {}
    scope = proposal['object_scope'] if mode == 'implicit' else 'unresolved'
    parsed = dict(activity_scope=mode, process_focus=dict(span=focus,meaning=focus) if focus else None,
                  scope_requirement=dict(span=case_span,object_scope=scope,granularity='distinct'),
                  case_requirement=dict(span=case_span,meaning=case_span), activity_requirements=requirements)
    selections = [(item['span'], item['activities']) for item in proposal['selections']]
    selections.extend((span, []) for span in proposal['unresolved_requirements'])
    for index, (span, picks) in enumerate(selections, 1):
        rid = f'R{index}'
        span = span.strip()
        errors = []
        if mode == 'explicit' and (not span or span not in question):
            errors.append('invalid_quote')
        if not picks:
            errors.append('event_definition_missing')
        resolved, roles = {}, set()
        for pick in picks:
            identifier, role = pick['activity_id'], pick['role']
            matches = [ed for ed, definition in definitions.items()
                       if activity_id(definition) == identifier and ed in catalog and catalog[ed]['eligible']
                       and catalog[ed]['attribution']['status'] == 'pass']
            if not matches:
                errors.append('unknown_or_unattributable_activity')
                continue
            selected = {}
            for ed in matches:
                row = catalog[ed]
                by_role = paths_by_role(row)
                if mode == 'implicit' and scope == 'own' and not (row['source_member'] or row['subject_role_supported']):
                    continue
                if role and role != 'direct':
                    compatible = [name for name in by_role if name.casefold() == role.casefold()]
                    if compatible:
                        selected[ed] = by_role[compatible[0]]
                        roles.add(compatible[0])
                elif not by_role:
                    selected[ed] = [path['id'] for path in row['attribution']['paths']]
            if not selected:
                errors.append('missing_or_unverified_role')
            for ed, values in selected.items():
                if not values:
                    errors.append('missing_executable_path')
                    continue
                if ed in resolved or ed in paths:
                    errors.append('duplicate_activity_selection')
                    continue
                resolved[ed] = sorted(set(values))
        paths.update(resolved)
        if errors:
            issues.extend(dict(kind=error,target=rid) for error in dict.fromkeys(errors))
        if mode == 'explicit':
            evidence = span if span in question and span else question
            req = dict(id=rid, span=evidence, meaning=evidence,
                       qualifiers=sorted(role for role in roles if mentions_role(evidence, role)),
                       coverage='all' if len(resolved)>1 else 'one', granularity='distinct')
            requirements.append(req)
            proposals.append(dict(requirement_id=rid,event_definition_ids=sorted(resolved)))
            outcomes.append(dict(req, status='unresolved' if errors else 'verified',
                                 reason='structural_attribution_only', reason_codes=list(dict.fromkeys(errors)),
                                 event_definition_ids=sorted(resolved) if not errors else [],
                                 definition_path_ids=resolved if not errors else {}))
    if not selections:
        issues.append(dict(kind='empty_interpretation',target='selection'))
    state = dict(et=et, mode=mode, focus=focus, scope_id=scope_id, ids=sorted(paths),
                 classifications={}, requirement_proposals=proposals, unified_paths=paths)
    return parsed, state, outcomes if mode == 'explicit' else None, issues


def check_revision(original, revised, issues):
    """PURPOSE: Disallow a conditional edit from replacing unaffected semantic decisions.
    INPUT: Initial/revised schema-valid replies and local issues. OUTPUT: None or a bounded-edit rejection.
    """
    targets = {item['target'] for item in issues}
    fixed = ('case_et_id','case_span','case_scope_id','request_mode','object_scope')
    if 'case' not in targets and any(original[k] != revised[k] for k in fixed):
        raise ValueError('revision_changed_locked_case')
    if 'focus' not in targets and original['process_focus'] != revised['process_focus']:
        raise ValueError('revision_changed_locked_focus')
    for index, selection in enumerate(original['selections'], 1):
        if f'R{index}' not in targets and selection not in revised['selections']:
            raise ValueError('revision_changed_locked_activity')
