"""Discover typed state-entry EDs from public history structure and code evidence."""
from copy import deepcopy

from src.common.attribution_policy import forward_adjacency
from src.common.database_io import quote_identifier as qi
from src.common.graph_identifiers import content_hash
from src.common.occurrence_conditions import occurrence_condition_issues, related_rows
from src.step1_understand.detect_and_normalize_timestamps import occurrence_time_policy
from src.step1_understand.resolve_activity_meanings import code_table_evidence, deterministic_meanings


def _context_selector(connection, table, context, tables):
    """PURPOSE: Verify a DD-described path to a terminal carrier.
    INPUT: Read-only DB, source schema, documented path/column and schema catalog.
    OUTPUT: Typed selector shape and endpoint table, or None.
    """
    if not isinstance(context, dict) or not isinstance(context.get('path'), list):
        return None
    references = [{'id': 'history_fk:' + content_hash([source.name, fk]),
                   'kind': 'declared', 'child_table': source.name, **fk}
                  for source in tables.values() for fk in source.foreign_keys]
    adjacency = forward_adjacency(references)
    joins, endpoint = [], table.name
    for hop in context['path']:
        matches = [edge for edge in adjacency.get(endpoint, []) if edge['left_columns'] == hop]
        if len(matches) != 1:
            return None
        joins.append(matches[0])
        endpoint = joins[-1]['right_table']
    field = context.get('column')
    lookup = {'kind': 'related_value', 'joins': joins, 'column': field, 'value': ''}
    if occurrence_condition_issues(connection, table.name, lookup):
        return None
    return lookup, endpoint


def _context_meanings(connection, table, context, state, dd, tables, indexes):
    """PURPOSE: Measure physically present contexts and resolve their public business meanings.
    INPUT: Source and optional local state column, DD and schema. OUTPUT: Typed values, selectors and evidence.
    """
    selected = _context_selector(connection, table, context, tables)
    if selected is None:
        return []
    lookup, endpoint = selected
    field = lookup['column']
    from_sql, correlation, terminal = related_rows(lookup, 's0')
    state_expression = f's0.{qi(state)}' if state else 'NULL'
    pairs = connection.execute(f'SELECT DISTINCT {state_expression}, {terminal} FROM {qi(table.name)} s0, '
                               f'{from_sql} WHERE {correlation} AND {terminal} IS NOT NULL')
    codebook = code_table_evidence(connection, tables[endpoint], field, tables, dd)
    documentation = indexes['columns'].get((endpoint, field), {})
    result = []
    for raw_state, raw_context in sorted(pairs, key=repr):
        meaning = deterministic_meanings(documentation, raw_context, codebook)
        if meaning['status'] == 'supported':
            result.append((raw_state, dict(lookup, value=raw_context), meaning))
    return result


def history_definitions(connection, table, history, bindings, timestamps, dd, tables, indexes):
    """PURPOSE: Construct transition definitions with exact source identity and optional related context.
    INPUT: Documented ordered history and the admitted state/clock inventory.
    OUTPUT: Constructed bindings and a discovery diagnostic.
    """
    state, clock = history.get('state_column'), history.get('occurrence_column')
    unit = next((t for t in timestamps if t['columns'] == [clock] and occurrence_time_policy(t)['eligible']), None)
    if not isinstance(state, str) or not unit:
        return [], 'state_history_state_or_clock_unverified'
    partition, order = history.get('partition_by'), history.get('order_by')
    if not all(isinstance(items, list) and all(isinstance(c,str) for c in items)
               for items in (partition,order)):
        return [], 'invalid_state_history_order'
    transition = {'kind': 'state_transition', 'table': table.name, 'column': state,
                  'partition_by': partition, 'order_by': order, 'order_key': list(table.primary_key),
                  'initial_is_transition': history.get('initial_is_transition') is True}
    if issues := occurrence_condition_issues(connection, table.name, transition):
        return [], issues[0]
    contexts = (_context_meanings(connection, table, history['context'], state, dd, tables, indexes)
                if 'context' in history else [(None, None, None)])
    result = []
    table_doc = indexes['tables'][table.name]
    for candidate in bindings:
        if (candidate['alpha']['kind'] != 'value' or candidate['alpha']['column'] != state
                or candidate['ts_id'] != unit['ts_id'] or candidate.get('interpretation_status') != 'supported'):
            continue
        for code, context, meaning in contexts:
            value = candidate['alpha']['value']
            if context and (type(code) is not type(value) or code != value):
                continue
            item = deepcopy(candidate)
            conditions = [transition, *([context] if context else [])]
            item['documented_source_conditions'] = conditions
            item['id'] += ':occurrence:' + content_hash(conditions)[:16]
            item['evidence'].append({'kind': 'state_history', 'ref': table_doc['id'], 'quote': table_doc['definition']})
            if context:
                label = f"{meaning['code_meaning']} {item['alpha']['name']}"
                item['alpha']['name'] = item['activity_label'] = label
                item['carrier_clock_relationship']['label'] = label
                item['carrier_value_semantics']['evidence'].extend(meaning['evidence'])
            result.append(item)
    return result, 'verified_state_history' if result else 'state_or_context_meaning_unresolved'


def related_definitions(connection, table, documentation, bindings, dd, tables, indexes):
    """PURPOSE: Discover events whose row clock is local but whose carrier is on a related table.
    INPUT: Verified local clock candidates and DD describing the related carrier encoding.
    OUTPUT: Scoped definitions anchored to the source occurrence row and a discovery diagnostic.
    """
    clock = documentation.get('occurrence_column')
    template = next((b for b in bindings if b['alpha']['kind'] == 'column'
                     and b.get('interpretation_status') == 'supported'
                     and b.get('occurrence_time_source', {}).get('columns') == [clock]), None)
    if not template:
        return [], 'related_occurrence_clock_unverified'
    contexts = _context_meanings(connection, table, documentation.get('carrier'), None, dd, tables, indexes)
    result = []
    for _, condition, meaning in contexts:
        item = deepcopy(template)
        label = meaning['code_meaning']
        item['alpha']['name'] = item['activity_label'] = label
        item['documented_source_conditions'] = [condition]
        item['id'] += ':occurrence:' + content_hash(condition)[:16]
        item['evidence'].extend({'kind': e['kind'], 'ref': e['id'], 'quote': e['text']}
                               for e in meaning['evidence'])
        result.append(item)
    return result, 'verified_related_occurrences' if result else 'related_carrier_meaning_unresolved'
