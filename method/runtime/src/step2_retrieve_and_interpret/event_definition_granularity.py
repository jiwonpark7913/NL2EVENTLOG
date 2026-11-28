"""Conservative inclusion proofs between executable event definitions."""

import json


def predicate_domains(definition):
    """PURPOSE: Normalize row restrictions with decidable set inclusion.
    INPUT: Event definition with a row selection and documented conjunctive restrictions.
    OUTPUT: Per-column allowed typed values, with None meaning any non-null value, or unknown.
    """
    domains = {}
    pending = [definition.get('row_selection'), *definition.get('documented_source_conditions', [])]
    while pending:
        condition = pending.pop()
        if not condition:
            return None
        kind = condition.get('kind')
        if kind == 'all_rows':
            continue
        if kind == 'and' and condition.get('conditions'):
            pending.extend(condition['conditions'])
            continue
        column = condition.get('column')
        if not column:
            return None
        if kind == 'not_null':
            domains.setdefault(column, None)
            continue
        if kind not in {'equals','in'}:
            return None
        raw = [condition.get('value')] if kind == 'equals' else condition.get('values', [])
        if not raw or any(value is None or not isinstance(value,(str,int,float,bool)) for value in raw):
            return None
        values = {json.dumps(value, ensure_ascii=False) for value in raw}
        previous = domains.get(column)
        domains[column] = values if previous is None else previous & values
        if not domains[column]:
            return None
    return domains


def same_occurrence_grain(left, right):
    """PURPOSE: Require common row identity, clock and compatible occurrence phase.
    INPUT: Two graph definitions. OUTPUT: True when their scalar physical occurrence grain matches.
    """
    clock, key = left.get('occurrence_time_source'), left.get('source_row_key')
    if not clock or not clock.get('columns') or clock.get('json_path') or not key or not left.get('source_table'):
        return False
    if any(b.get('source_kind') not in {'column_event','row_activity'} or
           b.get('occurrence_identity_status') != 'supported' for b in (left,right)):
        return False
    phases = {(b.get('timestamp_pairing') or {}).get('phase') for b in (left,right)} - {None,'unknown'}
    return (left['source_table'] == right.get('source_table') and key == right.get('source_row_key')
            and clock == right.get('occurrence_time_source') and len(phases) <= 1)


def definition_subsumption(identifiers, definitions):
    """PURPOSE: Prove strict inclusion from event grain and row-predicate implication.
    INPUT: Verified candidate IDs and graph definitions. OUTPUT: Broader IDs and covered specializations.
    """
    domains = {eid: predicate_domains(definitions[eid]) for eid in identifiers}
    covers = {}
    for broad, outer in domains.items():
        if outer is None:
            continue
        for narrow, inner in domains.items():
            if inner is None or outer == inner or not outer.keys() <= inner.keys():
                continue
            if not all(values is None or inner[column] is not None and inner[column] <= values
                       for column, values in outer.items()):
                continue
            if same_occurrence_grain(definitions[broad], definitions[narrow]):
                covers.setdefault(broad, set()).add(narrow)
    return covers


def choose_event_granularity(identifiers, definitions, level):
    """PURPOSE: Select the coarsest nonredundant representation at the requested resolution.
    INPUT: Semantically eligible IDs, their graph definitions, and coarse or distinct.
    OUTPUT: Ranked rules with redundant ancestors or descendants removed.
    """
    covered = definition_subsumption(identifiers, definitions)
    remove = set(covered) if level == 'distinct' else {eid for group in covered.values() for eid in group}
    return [eid for eid in identifiers if eid not in remove]
