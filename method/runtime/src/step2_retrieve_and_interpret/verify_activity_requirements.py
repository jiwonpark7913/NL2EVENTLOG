"""Validate explicit activity requirements against the selected case and the runtime EEG."""

from src.common.attribution_policy import mentions_role
from src.common.data_dictionary import _documented_code_meanings
from src.step2_retrieve_and_interpret.event_definition_granularity import choose_event_granularity, definition_subsumption


def is_source_span(question, span):
    """PURPOSE: Check a literal request citation. INPUT: Original text and copied phrase. OUTPUT: Exact nonblank match."""
    return bool(span.strip()) and span in question


def requested_roles(requirement, known_roles):
    """PURPOSE: Resolve request qualifiers to documented role labels.
    INPUT: Parsed requirement and eligible graph roles. OUTPUT: Roles supported by literal qualifiers.
    """
    return {role for role in known_roles
            if any(mentions_role(qualifier, role) for qualifier in requirement['qualifiers'])}


def paths_by_role(row):
    """PURPOSE: Index proved role projections of one ED. INPUT: Attribution catalog row. OUTPUT: Role to path IDs."""
    by_role = {}
    for path in row['attribution']['paths']:
        proof = path.get('role_validation') or {}
        role = (proof.get('reference') or {}).get('role')
        if proof.get('status') == 'pass' and role:
            by_role.setdefault(role, []).append(path['id'])
    return by_role


def role_paths(row, requirement, known_roles=(), chosen_path=None, *, proposal=False):
    """PURPOSE: Resolve a verified case role without pooling incompatible projections.
    INPUT: Catalog row, request, known role labels, optional reviewed path ID, and proposal flag.
    OUTPUT: Whether attribution is possible and the executable witness IDs.
    """
    attribution = row['attribution']
    if attribution['status'] != 'pass':
        return False, []
    by_role = paths_by_role(row)
    roles = requested_roles(requirement, set(known_roles) | by_role.keys())
    paths = attribution['paths']
    neutral = {p['id'] for p in paths} - {i for ids in by_role.values() for i in ids}
    if chosen_path is not None:
        admitted = {role for role, ids in by_role.items() if chosen_path in ids}
        if len(admitted) != 1 or (roles and not admitted <= roles):
            return False, []
        if requirement.get('coverage') != 'all' and roles and admitted != roles:
            return False, []
        return True, [chosen_path]
    if by_role:
        compatible = {role: ids for role, ids in by_role.items() if not roles or role in roles}
        if requirement.get('coverage') != 'all' and roles and roles != compatible.keys():
            return False, []
        if len(compatible) == 1 or proposal and compatible:
            return True, sorted(p for ids in compatible.values() for p in ids)
        return False, []
    # A same-case projection can carry a phase qualifier without a distinct reference role.
    direct = all(join['direction'] == 'child_to_parent' for p in paths for join in p.get('joins', []))
    return (not roles or bool(neutral) and direct), sorted(neutral)


def review_card(event, definition, row):
    """PURPOSE: Expose occurrence and case-role evidence to the reviewer.
    INPUT: Event description, definition and ET-relative catalog row. OUTPUT: Compact public card.
    """
    semantics = definition.get('activity_semantics') or {}
    attribution = row['attribution']
    raw_values = definition.get('raw_values') or []
    return dict(event, source=definition.get('source_table'),
                carrier_code=raw_values[0] if len(raw_values) == 1 else None,
                code_meaning=semantics.get('code_meaning'),
                dictionary_evidence=[c['quote'] for c in semantics.get('citations', []) if c.get('quote')][:2],
                occurrence_time=definition.get('occurrence_time_source') or definition.get('timestamp_columns'),
                time_role=(definition.get('timestamp_pairing') or {}).get('time_role'),
                eligible=row['eligible'], case_attribution=attribution['status'],
                direct_case_mapping=attribution['status'] == 'pass' and bool(attribution['paths'])
                and all(j['direction'] == 'child_to_parent' for p in attribution['paths'] for j in p.get('joins', [])),
                verified_case_roles=sorted(paths_by_role(row)) if attribution['status'] == 'pass' else [],
                role_projections=[{'path_id': p['id'], 'role': proof['reference']['role'],
                    'evidence': proof['reference'].get('quote')} for p in attribution['paths']
                    if attribution['status'] == 'pass' and
                    (proof := p.get('role_validation') or {}).get('status') == 'pass'],
                source_context=[t.get('definition') for t in row.get('dictionary_evidence', {}).get('tables', [])
                                if t.get('definition')])


def documented_activity_sources(graph):
    """PURPOSE: Ground missing ED and source-path diagnostics in existing public code descriptions.
    INPUT: Runtime EEG. OUTPUT: Source table, code column and documented values.
    """
    columns = (graph.get('data_dictionary') or {}).get('columns', [])
    return [{'source': col['table'], 'column': col['column'], 'dictionary_id': col.get('id'),
             'code_meanings': meanings}
            for col in columns if (meanings := _documented_code_meanings(col))]

def validate_review_exclusions(question, initial_ids, review, definitions):
    """PURPOSE: Audit removals from one initial Requirement proposal.
    INPUT: Original request, proposed ED IDs, review verdict and EEG definitions.
    OUTPUT: Missing or unsupported removals and malformed exclusion references.
    """
    retained = set(review['event_definition_ids'])
    removed = set(initial_ids) - retained
    exclusions = review.get('exclusions', [])
    cited = [item['event_definition_id'] for item in exclusions]
    valid = set()
    for item in exclusions:
        identifier = item['event_definition_id']
        if identifier not in removed or not is_source_span(question, item['span']) or not item['reason'].strip():
            continue
        if item['kind'] == 'duplicate_occurrence':
            compared = retained | {identifier}
            subsumes = definition_subsumption(compared, definitions) if definitions and compared <= definitions.keys() else {}
            if not any(identifier in subsumes.get(kept, set()) for kept in retained):
                continue
        valid.add(identifier)
    return sorted(removed - valid), len(cited) != len(set(cited)) or bool(set(cited) - removed)


def verify_activity(requirement, review, catalog, selected, definitions=None, *, known_roles=(),
                    verified_review_selection=False, canonical_only=False, question='', initial_ids=()):
    """PURPOSE: Resolve one requirement with independent semantic and executable path checks.
    INPUT: Requirement, semantic verdict, EEG catalog and selection. OUTPUT: Diagnosed requirement status.
    """
    candidates = review['event_definition_ids']
    original_scope = {key: requirement.get(key) for key in ('coverage','granularity')}
    requirement = dict(requirement, coverage=review.get('reviewed_coverage', original_scope['coverage']),
                       granularity=review.get('reviewed_granularity', original_scope['granularity']))
    choices = {item['event_definition_id']: item['path_id'] for item in review.get('role_path_choices', [])}
    known_roles = set(known_roles) | {role for row in catalog.values() for role in paths_by_role(row)}
    semantic = review['semantic_status']
    reasons, valid, paths = [], [], {}
    if semantic == 'missing':
        reasons.append('event_definition_missing')
    elif semantic == 'time_mismatch':
        reasons.extend(['event_definition_missing', 'occurrence_time_mismatch'])
    else:
        blocked_paths, blocked_definitions = False, False
        for identifier in candidates:
            row = catalog[identifier]
            supported, path_ids = role_paths(row, requirement, known_roles, choices.get(identifier))
            eligible = row['eligible'] and all(c['status'] in {'pass', 'not_run'}
                                              for c in row['binding_policy']['checks'].values())
            if supported and eligible:
                valid.append(identifier)
                paths[identifier] = path_ids
            blocked_paths |= not supported
            blocked_definitions |= not eligible
        if not valid:
            if blocked_paths:
                reasons.append('case_attribution_missing')
            if blocked_definitions:
                reasons.append('event_definition_unverified')
    if review['source_attribution_gap'] and not valid and 'case_attribution_missing' not in reasons:
        reasons.append('case_attribution_missing')
    collective = requirement.get('coverage') == 'all'
    if collective and semantic in {'matched', 'ambiguous'}:
        if set(candidates) - set(valid):
            reasons.append('activity_family_not_fully_attributable')
        if definitions is not None and not canonical_only:
            valid = choose_event_granularity(valid, definitions, requirement.get('granularity','coarse'))
        roles = requested_roles(requirement, known_roles)
        if len(roles) > 1:
            covered = {role for identifier in valid for role, ids in paths_by_role(catalog[identifier]).items()
                       if set(ids) & set(paths[identifier])}
            if not roles <= covered and 'activity_family_not_fully_attributable' not in reasons:
                reasons.append('activity_family_not_fully_attributable')
    if ((collective and semantic == 'ambiguous') or
            (not collective and (len(valid) > 1 or (semantic == 'ambiguous' and len(valid) != 1 and not reasons)))):
        reasons.append('ambiguous_candidates')
    added = sorted(set(valid)-set(selected))
    if added and not verified_review_selection:
        reasons.append('matching_definition_not_selected')
    missing_exclusions, invalid_exclusions = validate_review_exclusions(question, initial_ids, review, definitions)
    if missing_exclusions or invalid_exclusions:
        reasons.append('initial_selection_exclusion_unverified')
    if original_scope['coverage'] == 'all' and not collective:
        reasons.append('requested_family_coverage_narrowed')
    verified = bool(valid) and not reasons and (collective or len(valid) == 1)
    return dict(requirement, status='verified' if verified else 'unresolved',
                parsed_scope=original_scope, added_by_independent_review=added if verified else [],
                semantic_status=semantic, reason_codes=reasons,
                reason=review['reason'], candidate_event_definition_ids=candidates,
                exclusions=review.get('exclusions', []), unaccounted_initial_ed_ids=missing_exclusions,
                event_definition_ids=valid if verified else [],
                attribution_path_ids=sorted({p for eid in valid for p in paths[eid]}) if verified else [],
                definition_path_ids={eid: paths[eid] for eid in valid} if verified else {})


def resolve_selection_conflicts(outcomes, warnings, definition_pairs, locked):
    """PURPOSE: Remove jointly invalid matches without dropping independent verified items.
    INPUT: Item results, structural warnings, EEG pairs and verified requirement IDs from an earlier review.
    OUTPUT: Results with conflicting new matches marked unresolved.
    """
    locked_events = {i for item in outcomes if item['id'] in locked for i in item['event_definition_ids']}
    pairs = {p['id']: p['binding_pair'] for p in definition_pairs}
    conflicting = set()
    for warning in warnings:
        identifiers = warning['evidence_ids']
        if warning['kind'] == 'candidate_conflict':
            conflicts = {i for pair_id in identifiers for i in pairs.get(pair_id, [])}
        elif warning['kind'] == 'duplicate_occurrence':
            conflicts = set(identifiers)
        else:
            continue
        conflicting.update(conflicts - locked_events)
    return [dict(item, status='unresolved', reason_codes=['conflicting_event_definitions'],
                 event_definition_ids=[], attribution_path_ids=[], definition_path_ids={}, added_by_independent_review=[])
            if conflicting.intersection(item['event_definition_ids']) else item for item in outcomes]
