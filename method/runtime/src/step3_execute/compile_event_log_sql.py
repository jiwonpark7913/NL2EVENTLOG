"""ES v5 compiler with explicit Event Source references. Run one read transaction.

Standalone event_log_sql exposes variants, but does not validate them. Consumers
must abort if conflict_sql returns rows, on the same connection and snapshot."""

from __future__ import annotations
import copy
import json
import sqlite3
from contextlib import closing
from src.common.graph_identifiers import normalize_event_definition_references
from src.common.attribution_policy import path_issues, database_path_issues, POLICY
from src.common.database_io import connect_readonly
from src.common.schema_metadata import stable_id, timestamp_columns
from src.common.timestamp_policy import EPOCH_UNITS, binding_timezone, event_time_order
from src.common.sql_identifiers import quote_identifier as qi
from src.common.entity_population import case_expression, source_case, population_cte, validate_population
ES_VERSION = 5
OUTPUT_COLUMNS = ('case_id', 'event_id', 'activity', 'activity_original',
                  'source_event_definition_id', 'source_occurrence_id', 'timestamp',
                  'timestamp_kind', 'timestamp_raw_value', 'timestamp_raw_column',
                  'timestamp_json_path',
                  'timestamp_day', 'timestamp_day_column',
                  'timestamp_clock', 'timestamp_clock_column', 'timestamp_clock_encoding',
                  'timestamp_timezone', 'source_table', 'source_record_id',
                  'object_refs')


class ESValidationError(ValueError):
    pass


def selected_definition_contract(es):
    """PURPOSE: Read current PI materialization contracts and legacy implicit-history receipts consistently.
    INPUT: Normalized ES mapping. OUTPUT: Selected definition IDs and request mode, or None for other ES paths.
    This compatibility adapter does not infer a lifecycle or alter the frozen PI/population.
    """
    contract=es.get('pi_materialization_contract',{})
    if (contract.get('policy')=='validated_selected_event_definitions' and
        contract.get('request_mode') in {'explicit','implicit'} and
        isinstance(contract.get('selected_event_definition_ids'),list)):
        return contract
    legacy=es.get('implicit_history_contract',{})
    if legacy.get('policy')=='supported_and_verified_attributable_recorded_history' and isinstance(legacy.get('selected_event_definition_ids'),list):
        return {'policy':'validated_selected_event_definitions','request_mode':'implicit',
            'selected_event_definition_ids':legacy['selected_event_definition_ids']}
    return None


def selected_definition_issues(es):
    """PURPOSE: Check that ES event rules realize exactly the PI-selected Event definitions, by ID.
    INPUT: Normalized v5/v6 ES; each event rule names its Event definition in source_event_definition_id.
    OUTPUT: None when the ES carries no PI selection contract (legacy label checks apply); otherwise
    missing/extra definition IDs, rules without a definition ID and a Process View/contract
    mismatch flag. Request wording and output activity names are never compared.
    """
    contract = selected_definition_contract(es)
    if contract is None:
        return None
    selected = {str(item) for item in contract['selected_event_definition_ids']}
    rules = es.get('event_rules', [])
    realized = {str(rule['source_event_definition_id']) for rule in rules if rule.get('source_event_definition_id')}
    view_ids = (es.get('process_view') or {}).get('event_definitions')
    return {'missing': sorted(selected - realized), 'extra': sorted(realized - selected),
            'unidentified_rules': sorted(str(rule.get('id')) for rule in rules if not rule.get('source_event_definition_id')),
            'selection_mismatch': view_ids is not None and {str(item) for item in view_ids} != selected}


EMPTY_RESULT_BASIS = 'rule_confirmed_no_occurrences'


def event_to_case_loss(connection):
    """PURPOSE: Judge one Event Source's event-to-case attribution without treating 0/0 as observed success.
    INPUT: Connection probe (event_rows, linked_events, event_to_case_coverage) with an optional
           empty_result_approval recorded when the source was materialized from a rule-confirmed path.
    OUTPUT: None when every observed event reaches a case, or when no event exists and the empty result
            is approved by confirmed rules; otherwise 'event_to_case_loss' or 'unconfirmed_empty_event_source'.
    """
    connection = connection or {}
    if connection.get('event_rows') == 0:
        approval = connection.get('empty_result_approval') or {}
        if approval.get('status') == EMPTY_RESULT_BASIS and not connection.get('linked_events'):
            return None
        return 'unconfirmed_empty_event_source'
    coverage = connection.get('event_to_case_coverage')
    return 'event_to_case_loss' if coverage is None or coverage < 1 else None


def sql_literal(value):
    """PURPOSE: Quote event-condition constants safely for SQLite.
    INPUT: Scalar value or None.
    OUTPUT: Escaped SQL text literal or NULL.
    """
    return 'NULL' if value is None else "'" + str(value).replace("'", "''") + "'"


def _text(alias, column):
    """PURPOSE: Use a common text representation for a bound physical column.
    INPUT: Validated alias and column name.
    OUTPUT: SQL CAST expression; no database access.
    """
    return f'CAST({alias}.{qi(column)} AS TEXT)'


def _json_key(alias, columns):
    """PURPOSE: Encode ordered compound keys without separator collisions.
    INPUT: SQL alias and nonempty ordered key columns.
    OUTPUT: SQLite JSON-array expression; empty key raises ESValidationError.
    """
    if not columns:
        raise ESValidationError('identity/case key has no columns')
    return 'json_array(' + ', '.join(_text(alias, c) for c in columns) + ')'


def _json_timestamp(value, path):
    """PURPOSE: Preserve a JSON timestamp scalar. INPUT: JSON SQL expression and verified path.
    OUTPUT: Decoded string or exact JSON number token.
    """
    path = sql_literal(path)
    return (f"CASE WHEN json_type({value},{path}) IN ('integer','real') "
            f"THEN ({value} -> {path}) ELSE json_extract({value},{path}) END")


def _timestamp(binding, alias):
    """PURPOSE: Preserve the source clock representation. INPUT: Timestamp binding and alias.
    OUTPUT: Raw SQLite value, JSON scalar, or ordered original date/clock components.
    """
    kind = binding['kind']
    if kind == 'json_path':
        return _json_timestamp(f'{alias}.{qi(binding["column"])}', binding['json_path'])
    if kind in ('direct', 'epoch_seconds', 'epoch_ms'):
        return f'{alias}.{qi(binding["column"])}'
    if kind in ('date_clock', 'date_compact_clock', 'compact_date_seconds'):
        day = f'{alias}.{qi(binding["date_column"])}'
        clock = f'{alias}.{qi(binding.get("clock_column") or binding["seconds_column"])}'
        return (f'CASE WHEN {day} IS NOT NULL AND {clock} IS NOT NULL '
                f'THEN json_array({day},{clock}) END')
    raise ESValidationError(f'Unsupported timestamp binding: {kind!r}')


def _timestamp_timezone(value, binding, *, clock_only=False):
    """PURPOSE: Expose the inline source offset or documented timezone. INPUT: Raw SQL value and binding.
    OUTPUT: SQL expression with unknown timezone represented by NULL.
    """
    text = f'trim(CAST(({value}) AS TEXT))'
    extended = (f"substr({text},5,1)='-' AND substr({text},8,1)='-' "
                f"AND substr({text},11,1) IN ('T','t',' ') AND substr({text},12,2) GLOB '[0-2][0-9]'")
    basic = (f"substr({text},1,8) GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]' "
             f"AND substr({text},9,1) IN ('T','t') AND substr({text},10,2) GLOB '[0-2][0-9]'")
    time_present = f"substr({text},3,1)=':'" if clock_only else f"(({extended}) OR ({basic}))"
    choices = [(6, '[+-][0-2][0-9]:[0-5][0-9]'), (5, '[+-][0-2][0-9][0-5][0-9]'),
               (3, '[+-][0-2][0-9]')]
    terms = " ".join(
        f"WHEN substr({text},-{n}) GLOB '{pattern}' "
        f"AND CAST(substr({text},{1-n},2) AS INTEGER)<24 THEN substr({text},-{n})"
        for n, pattern in choices)
    fallback = sql_literal(binding_timezone(binding))
    return (f"CASE WHEN {time_present} THEN CASE WHEN substr({text},-1)='Z' THEN 'Z' "
            f"{terms} ELSE {fallback} END ELSE {fallback} END")


def _timestamp_component_fields(binding, alias):
    """PURPOSE: Project untouched physical timestamp components into the final log.
    INPUT: Validated timestamp binding and SQL source alias.
    OUTPUT: SQL expressions for generic raw/day/clock fields and their provenance.
    Timestamp values are preserved without calendar or timezone conversion.
    """
    kind = binding['kind']
    direct = kind in ('direct', 'epoch_seconds', 'epoch_ms')
    raw_column = binding.get('column') if direct or kind == 'json_path' else None
    day_column = binding.get('date_column')
    clock_column = binding.get('clock_column') or binding.get('seconds_column')
    detected = binding.get('detected_format', binding.get('format'))
    raw_value = _timestamp(binding, alias) if raw_column else 'NULL'
    zone_value = f'{alias}.{qi(clock_column)}' if clock_column else raw_value
    clock_encoding = ('seconds_since_midnight' if 'seconds_column' in binding else
                      'compact_hhmmss' if kind == 'date_compact_clock' else
                      'text' if clock_column else detected if detected in EPOCH_UNITS or detected == 'compact' else None)

    def source_value(column):
        """PURPOSE: Preserve one physical component as text or SQL NULL.
        INPUT: Optional validated source-column name.
        OUTPUT: SQL expression with no date/time normalization.
        """
        return _text(alias, column) if column else 'NULL'

    return {
        'timestamp_kind': sql_literal(kind),
        'timestamp_raw_value': raw_value,
        'timestamp_raw_column': sql_literal(raw_column),
        'timestamp_json_path': sql_literal(binding.get('json_path')) if kind == 'json_path' else 'NULL',
        'timestamp_day': source_value(day_column),
        'timestamp_day_column': sql_literal(day_column),
        'timestamp_clock': source_value(clock_column),
        'timestamp_clock_column': sql_literal(clock_column),
        'timestamp_clock_encoding': sql_literal(clock_encoding),
        'timestamp_timezone': _timestamp_timezone(zone_value, binding, clock_only=bool(clock_column)),
    }


def _from(rule, case, *, left=False):
    """PURPOSE: Build one validated independent source-to-case branch.
    INPUT: Event rule, target case binding and optional LEFT join mode.
    OUTPUT: (FROM/JOIN clauses, case alias); invalid/disconnected/repeated-table paths fail.
    """
    projection = case.get('projection')
    if projection:
        if projection.get('kind') != 'json_array_values' or rule.get('joins') or case['columns'] != ['value']:
            raise ESValidationError('Invalid explicit JSON case projection')
        column = 's0.' + qi(projection['column'])
        value = f"CASE WHEN json_valid({column}) THEN CASE WHEN json_type({column})='array' THEN {column} ELSE '[]' END ELSE '[]' END"
        predicate = 'obj.type = \'text\' AND obj.value LIKE ' + sql_literal(projection['value_pattern'])
        return [f"FROM {qi(rule['source']['table'])} AS s0", f'JOIN json_each({value}) AS obj ON {predicate}'], 'obj'
    current, alias = rule['source']['table'], 's0'
    parts, seen = [f'FROM {qi(current)} AS s0'], {current}
    for n, join in enumerate(rule.get('joins', []), 1):
        a, b = join['left_columns'], join['right_columns']
        if join['left_table'] != current or not a or len(a) != len(b):
            raise ESValidationError('Invalid composite join path')
        if join['right_table'] in seen:
            raise ESValidationError('Repeated-table roles are outside ES v4')
        nxt = f'j{n}'
        condition = ' AND '.join(f'{alias}.{qi(x)}={nxt}.{qi(y)}' for x, y in zip(a, b))
        parts.append(f'{"LEFT JOIN" if left else "JOIN"} {qi(join["right_table"])} AS {nxt} ON {condition}')
        current, alias = join['right_table'], nxt
        seen.add(current)
    if current != case['table']:
        raise ESValidationError('Rule does not reach case table')
    return parts, alias


def _partition_activity_condition(condition, activity_column):
    """PURPOSE: Separate a row-activity value filter from source-level predicates.
    INPUT: Structured condition tree and the validated activity-carrier column.
    OUTPUT: (raw values, remaining condition); missing/duplicate carrier filters raise.
    """
    if condition.get('kind') == 'in' and condition.get('column') == activity_column:
        if not condition.get('values'):
            raise ESValidationError('Row activity filter has no values')
        return list(condition['values']), None
    if condition.get('kind') != 'and' or not condition.get('conditions'):
        raise ESValidationError('Row activity rule must filter its activity column')
    values, remaining = None, []
    for term in condition['conditions']:
        if term.get('kind') == 'in' and term.get('column') == activity_column:
            if values is not None:
                raise ESValidationError('Duplicate row activity filters')
            values = list(term.get('values') or [])
        else:
            remaining.append(copy.deepcopy(term))
    if not values:
        raise ESValidationError('Row activity filter has no values')
    rest = None if not remaining else remaining[0] if len(remaining) == 1 else {'kind': 'and', 'conditions': remaining}
    return values, rest


def _combine_conditions(*conditions):
    """PURPOSE: Combine optional structured predicates without changing their meaning.
    INPUT: Zero or more condition dictionaries or None values.
    OUTPUT: None, one copied predicate, or a flattened conjunction.
    """
    values = [copy.deepcopy(value) for value in conditions if value]
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return {'kind': 'and', 'conditions': values}


def _remove_column_event_filter(condition, timestamp):
    """PURPOSE: Separate a derived column-event non-null filter from source-level predicates.
    INPUT: v4 source condition and the rule timestamp binding.
    OUTPUT: Remaining source predicate; malformed or absent derived filters raise.
    """
    columns = timestamp_columns(timestamp)
    expected = columns[0] if columns else None
    terms = condition.get('conditions', []) if condition.get('kind') == 'and' else [condition]
    removed, remaining = False, []
    for term in terms:
        if not removed and term.get('kind') == 'not_null' and term.get('column') == expected:
            removed = True
        else:
            remaining.append(copy.deepcopy(term))
    if not removed:
        raise ESValidationError('Column event rule must filter its timestamp column')
    return None if not remaining else remaining[0] if len(remaining) == 1 else {
        'kind': 'and', 'conditions': remaining}


def event_source_id(source):
    """PURPOSE: Derive the stable identity of one v5 Event Source.
    INPUT: Source-level physical binding without an embedded ID.
    OUTPUT: Stable content ID over table reading, identity, path, condition and NULL policy.
    """
    payload = {name: copy.deepcopy(source.get(name)) for name in (
        'table', 'encoding', 'activity_column', 'translation_map_id',
        'event_identity', 'row_condition', 'missing_values', 'json_spec',
        'source_priority', 'deduplication')}
    if 'object_references' in source:
        payload['object_references'] = copy.deepcopy(source['object_references'])
    payload['relationship_path'] = copy.deepcopy(
        source.get('case_attribution', {}).get('relationship_path', []))
    mapping = source.get('case_attribution', {}).get('entity_instance_map_id')
    if mapping:
        payload['entity_instance_map_id'] = mapping
    return stable_id('event_source', payload)


def _v4_rule_parts(rule):
    """PURPOSE: Split one concrete v4 rule into a v5 Event Source and Activity Rule.
    INPUT: Valid v4 rule with copied table-level attributes.
    OUTPUT: (source_id, source object, activity-rule object).
    """
    activity = rule['activity']
    discriminator = rule.get('event_identity', {}).get('discriminator', {})
    row = (discriminator.get('kind') == 'row'
           or (activity.get('kind') in {'row_activity_value', 'code_mapping'} and bool(activity.get('column'))))
    pairing = rule.get('timestamp_pairing')
    if row and not pairing and str(discriminator.get('value', '')).startswith('row_event:'):
        pairing = {'occurrence_discriminator': discriminator['value'].removeprefix('row_event:')}
    if row:
        raw_values, row_condition = _partition_activity_condition(
            rule['source_condition'], activity.get('column'))
    else:
        raw_values = []
        row_condition = _remove_column_event_filter(
            rule['source_condition'], rule['timestamp'])
    source = {
        'table': rule['source']['table'],
        'encoding': 'row' if row else 'column',
        'activity_column': activity.get('column') if row else None,
        'translation_map_id': activity.get('translation_map_id'),
        'event_identity': {
            'namespace': rule['event_identity']['namespace'],
            'key_columns': list(rule['event_identity']['key_columns'])},
        'case_attribution': copy.deepcopy(rule.get('case_attribution', {
            'anchor': rule.get('case'), 'relationship_path': rule.get('joins', [])})),
        'row_condition': row_condition,
        'missing_values': copy.deepcopy(rule['missing_values']),
        'data_validation': copy.deepcopy(rule.get('data_validation', {})),
        'object_references': copy.deepcopy(rule.get('object_references', [])),
    }
    source['case_attribution'].setdefault(
        'relationship_path', copy.deepcopy(rule.get('joins', [])))
    source_id = event_source_id(source)
    activity_rule = {
        'id': rule['id'], 'source_id': source_id,
        'source_event_definition_id': (rule.get('source_event_definition_id') or
                              activity.get('source_event_definition_id') or
                              rule.get('grounding_candidate_id') or rule.get('id')),
        'activity_source': copy.deepcopy(
            rule.get('activity_source') or activity.get('activity_source') or {}),
        'activity_label_source': (rule.get('activity_label_source') or
                                  activity.get('activity_label_source') or 'legacy_unspecified'),
        'label': activity.get('label'),
        'canonical_activity_id': activity.get('canonical_activity_id'),
        'raw_values': list(raw_values),
        'timestamp': copy.deepcopy(rule['timestamp']),
        'timestamp_pairing': copy.deepcopy(pairing),
        'eventness': rule.get('eventness'),
        'history_completeness': rule.get('history_completeness'),
        'attribution': rule.get('attribution'),
        'grounding_candidate_id': rule.get('grounding_candidate_id'),
        'attribution_candidate_id': rule.get('attribution_candidate_id'),
        'lifecycle_associations': copy.deepcopy(rule.get('lifecycle_associations', [])),
        **({'eeg_candidate_validation': copy.deepcopy(rule['eeg_candidate_validation'])}
           if 'eeg_candidate_validation' in rule else {}),
        'decision': copy.deepcopy(rule.get('decision')),
        'evidence': copy.deepcopy(rule.get('evidence', [])),
    }
    return source_id, source, {key: value for key, value in activity_rule.items()
                               if value is not None}


def _source_conflicts(event_sources):
    """PURPOSE: Detect incompatible identities within one table-and-encoding namespace.
    INPUT: v5 source mapping.
    OUTPUT: Deterministic conflicts; mixed row/column representations may coexist.

    A mixed-encoded table legitimately has an occurrence namespace for row events and
    separate column events.  Comparing those sources as if they were two definitions of
    the same occurrence rejects a valid ES.  Identity consistency is therefore enforced
    within an encoding family, while alternative case paths remain runtime-validated
    branches.
    """
    by_namespace = {}
    conflicts = []
    for source_id, source in sorted(event_sources.items()):
        namespace = (source.get('table'), source.get('encoding'))
        signature = {
            'json_spec': source.get('json_spec'),
            'event_identity': source.get('event_identity')}
        previous = by_namespace.setdefault(namespace, (source_id, signature))
        if previous[1] != signature:
            differing = [field for field in signature
                         if previous[1].get(field) != signature.get(field)]
            conflicts.append({'code': 'source_conflict', 'table': source.get('table'),
                              'encoding': source.get('encoding'),
                              'source_ids': [previous[0], source_id],
                              'differing_fields': differing})
    return conflicts


def upgrade_es_v4_to_v5(es):
    """PURPOSE: Normalize a stored v4 ES into the explicit Event Source v5 representation.
    INPUT: v4 or already-v5 ES; v4 rule identities/paths must satisfy invariant I2.
    OUTPUT: Deep-copied v5 ES with legacy_id preserved; source conflicts raise.
    """
    if es.get('es_version') in (5, 6):
        return copy.deepcopy(es)
    if es.get('es_version') != 4:
        raise ESValidationError('Only ES v4 can be upgraded to ES v5')
    upgraded = copy.deepcopy(es)
    event_sources = {}
    for collection in ('event_rules', 'selection_rules'):
        converted = []
        for rule in es.get(collection, []):
            source_id, source, activity_rule = _v4_rule_parts(rule)
            if source_id not in event_sources:
                source.setdefault('data_validation', {}).setdefault('scope', 'first_rule')
                event_sources[source_id] = source
            elif event_source_id(event_sources[source_id]) != source_id:
                raise ESValidationError('event_source ID collision')
            converted.append(activity_rule)
        upgraded[collection] = converted
    conflicts = _source_conflicts(event_sources)
    if conflicts:
        raise ESValidationError('source_conflict: ' + json.dumps(conflicts, sort_keys=True))
    legacy_id = es.get('id')
    upgraded['es_version'] = 6 if upgraded.get('case', {}).get('population') else ES_VERSION
    upgraded['event_sources'] = event_sources
    if legacy_id:
        upgraded['legacy_id'] = legacy_id
    upgraded.pop('id', None)
    upgraded['id'] = stable_id('es', upgraded)
    return upgraded


def _v5_rule_to_v4(es, rule):
    """PURPOSE: Expand one v5 Activity Rule for legacy debugging and verified SQL helpers.
    INPUT: v5 ES and a rule whose source_id exists.
    OUTPUT: Semantically equivalent v4 rule with derived filters/discriminator restored.
    """
    source = es['event_sources'][rule['source_id']]
    row = source['encoding'] == 'row'
    timestamp = copy.deepcopy(rule['timestamp'])
    activity = {
        'kind': ('code_mapping' if source.get('translation_map_id') else
                 'row_activity_value') if row else 'constant',
        'label': rule['label'],
        'canonical_activity_id': rule.get('canonical_activity_id'),
        'column': source.get('activity_column'),
        'raw_values': list(rule.get('raw_values', []))}
    activity['source_event_definition_id'] = rule.get('source_event_definition_id')
    activity['activity_source'] = copy.deepcopy(rule.get('activity_source', {}))
    activity['activity_label_source'] = rule.get('activity_label_source')
    if source.get('translation_map_id'):
        activity['translation_map_id'] = source['translation_map_id']
    derived = ({'kind': 'in', 'column': source['activity_column'],
                'values': list(rule.get('raw_values', []))} if row else
               {'kind': 'not_null', 'column': timestamp_columns(timestamp)[0]})
    identity = copy.deepcopy(source['event_identity'])
    identity['discriminator'] = ({'kind': 'row'} if row else {
        'kind': 'constant',
        'value': '|'.join(timestamp_columns(timestamp)) +
                 ('|' + timestamp['json_path'] if timestamp.get('kind') == 'json_path' else '') + '_event'})
    pairing = rule.get('timestamp_pairing') or {}
    if row and (clock := pairing.get('occurrence_discriminator')):
        identity['discriminator'] = {'kind':'constant','value':'row_event:' + clock}
    elif row and (phase := pairing.get('phase')) in {'start','complete'}:
        identity['discriminator'] = {'kind':'constant','value':'row_event:' + phase}
    attribution = copy.deepcopy(source['case_attribution'])
    path = copy.deepcopy(attribution.get('relationship_path', []))
    return {
        'id': rule['id'],
        'grounding_candidate_id': rule.get('grounding_candidate_id'),
        'attribution_candidate_id': rule.get('attribution_candidate_id'),
        'source': {'table': source['table'], 'alias': 's0'},
        'case': copy.deepcopy(source_case(source, es['case'])),
        'case_attribution': attribution,
        'event_identity': identity,
        'activity': activity,
        'timestamp': timestamp,
        **({'timestamp_pairing': copy.deepcopy(pairing)} if pairing else {}),
        'joins': path,
        'source_condition': _combine_conditions(derived, source.get('row_condition')),
        'missing_values': copy.deepcopy(source['missing_values']),
        'eventness': rule.get('eventness'),
        'history_completeness': rule.get('history_completeness'),
        'attribution': rule.get('attribution'),
        'lifecycle_associations': copy.deepcopy(rule.get('lifecycle_associations', [])),
        **({'eeg_candidate_validation': copy.deepcopy(rule['eeg_candidate_validation'])}
           if 'eeg_candidate_validation' in rule else {}),
        'decision': copy.deepcopy(rule.get('decision')),
        'evidence': copy.deepcopy(rule.get('evidence', [])),
        'data_validation': copy.deepcopy(source.get('data_validation', {})),
        'object_references': copy.deepcopy(source.get('object_references', [])),
    }


def downgrade_es_v5_to_v4(es):
    """PURPOSE: Expand v5 sources into v4 rule copies for debugging and old consumers.
    INPUT: v5 or already-v4 ES.
    OUTPUT: Deep-copied v4 ES; SQL-relevant source properties are preserved.
    """
    if es.get('es_version') == 4:
        return copy.deepcopy(es)
    if es.get('es_version') not in (5, 6):
        raise ESValidationError('Only ES v5/v6 can be expanded to ES v4')
    downgraded = copy.deepcopy(es)
    for collection in ('event_rules', 'selection_rules'):
        downgraded[collection] = [_v5_rule_to_v4(es, rule)
                                  for rule in es.get(collection, [])]
    downgraded.pop('event_sources', None)
    downgraded['es_version'] = 4
    downgraded['id'] = es.get('legacy_id', downgraded.get('id'))
    downgraded.pop('legacy_id', None)
    return downgraded


def group_rules_by_source(es, collection='event_rules'):
    """PURPOSE: Form compiler branches directly from explicit source references.
    INPUT: v5 ES and event_rules or selection_rules collection name.
    OUTPUT: Ordered (source_id, source, rules) groups; row groups split by timestamp.
    """
    groups = {}
    for rule in es.get(collection, []):
        source = es['event_sources'][rule['source_id']]
        timestamp_key = json.dumps(rule['timestamp'], sort_keys=True, separators=(',', ':'))
        key = (rule['source_id'], timestamp_key if source['encoding'] in ('row', 'json') else rule['id'])
        groups.setdefault(key, []).append(rule)
    return [(source_id, es['event_sources'][source_id], rules)
            for (source_id, _), rules in groups.items()]


def _activity_expression(activity, alias='s0'):
    """PURPOSE: Compile constant or row-value-to-canonical-label activity output.
    INPUT: Accepted activity binding and source alias.
    OUTPUT: Deterministic SQL expression; incomplete/conflicting mappings raise.
    """
    if activity.get('kind') != 'value_mapping':
        if not activity.get('label'):
            raise ESValidationError('Canonical activity label required')
        return sql_literal(activity['label'])
    mappings = activity.get('mappings') or []
    if not mappings:
        raise ESValidationError('Value-mapped activity has no mappings')
    column = f'{alias}.{qi(activity["column"])}'
    branches = ' '.join('WHEN ' + sql_literal(item['raw_value']) + ' THEN ' + sql_literal(item['label'])
                        for item in mappings)
    return f'CASE {column} {branches} ELSE NULL END'


def _typed_original_expression(activity: dict, alias: str = 's0') -> str:
    """PURPOSE: Serialize the original activity selector without type or delimiter collisions.
    INPUT: Compiled activity rule and validated SQL source alias.
    OUTPUT: Deterministic JSON text for a raw value or structured column source.
    """
    if activity.get('kind') == 'value_mapping':
        column = f'{alias}.{qi(activity["column"])}'
        return f"json_object('type',typeof({column}),'value',{column})"
    source = activity.get('activity_source') or {}
    return sql_literal(json.dumps(source, ensure_ascii=False, sort_keys=True,
                                  separators=(',', ':')))


def _binding_expression(activity: dict, alias: str = 's0') -> str:
    """PURPOSE: Emit the exact Binding ID responsible for each compiled event row.
    INPUT: Constant or value-mapped compiled activity and source alias.
    OUTPUT: SQL literal/CASE expression; missing or conflicting provenance raises.
    """
    if activity.get('kind') != 'value_mapping':
        event_definition_id = activity.get('source_event_definition_id') or 'legacy:unknown-binding'
        return sql_literal(event_definition_id)
    mappings = activity.get('mappings') or []
    if not mappings or any(not item.get('source_event_definition_id') for item in mappings):
        raise ESValidationError('Value mapping has incomplete source_event_definition_id provenance')
    column = f'{alias}.{qi(activity["column"])}'
    branches = ' '.join(
        'WHEN ' + sql_literal(item['raw_value']) + ' THEN ' + sql_literal(item['source_event_definition_id'])
        for item in mappings)
    return f'CASE {column} {branches} ELSE NULL END'


def _condition(rule, *, alias="s0"):
    """PURPOSE: Compile a validated event-defining source predicate.
    INPUT: ES source_condition with in/not_null/equals and bound column.
    OUTPUT: SQL predicate on s0; unsupported operations fail.
    """
    value = rule['source_condition']
    if value['kind'] == 'and' and value.get('conditions'):
        return '(' + ' AND '.join(_condition({'source_condition': term}, alias=alias) for term in value['conditions']) + ')'
    if value['kind'] == 'reference_role':
        from src.common.attribution_policy import role_source_scope_sql
        return role_source_scope_sql(value)
    if value['kind'] == 'state_transition':
        from src.common.occurrence_conditions import transition_sql
        return transition_sql(value, alias)
    if value['kind'] == 'related_value':
        from src.common.occurrence_conditions import related_rows
        from_sql, correlation, terminal = related_rows(value, alias)
        return f"EXISTS (SELECT 1 FROM {from_sql} WHERE {correlation} AND {terminal} = {sql_literal(value['value'])})"
    column = f'{alias}.{qi(value["column"])}'
    if value['kind'] == 'in' and value.get('values'):
        return f'{column} IN ({", ".join(sql_literal(x) for x in value["values"])})'
    if value['kind'] == 'not_null':
        return column + ' IS NOT NULL'
    if value['kind'] == 'equals':
        return column + '=' + sql_literal(value['value'])
    raise ESValidationError('Unsupported source condition')


def _discriminator(rule):
    """PURPOSE: Keep event identity independent of rule IDs and requested activity sets.
    INPUT: ES rule with row or stable column-event discriminator.
    OUTPUT: SQL literal for the physical event discriminator.
    """
    disc = rule['event_identity']['discriminator']
    if disc['kind'] == 'row':
        return "'row_event'"
    if disc['kind'] == 'constant' and disc.get('value'):
        return sql_literal(disc['value'])
    raise ESValidationError('Identity must be a row event or a stable column discriminator')


def _missing(rule, case, case_alias):
    """PURPOSE: Apply explicit drop policies consistently in exported and executed SQL.
    INPUT: Rule, target case and case alias.
    OUTPUT: Non-null SQL predicates; unsupported missing-value policies fail.
    """
    policy = rule['missing_values']
    if any(policy.get(slot) != 'drop' for slot in ('case', 'event_key', 'activity', 'timestamp')):
        raise ESValidationError('ES v4 requires explicit drop policies for every missing slot')
    conditions = [f'{case_alias}.{qi(c)} IS NOT NULL' for c in case['columns']]
    conditions += [f's0.{qi(c)} IS NOT NULL' for c in rule['event_identity']['key_columns']]
    if rule['activity']['kind'] != 'constant':
        conditions.append(f's0.{qi(rule["activity"]["column"])} IS NOT NULL')
    conditions.append(f'({_timestamp(rule["timestamp"], "s0")}) IS NOT NULL')
    return conditions


def _object_reference_expression(rule, case, case_alias):
    """PURPOSE: Compile verified Event-to-Object identities without conflating source rows and cases.
    INPUT: Concrete rule, canonical case and the SQL alias that supplies the case key.
    OUTPUT: SQLite JSON array expression; only ES-declared Object references are emitted.
    """
    aliases = {rule['source']['table']: 's0', case['table']: case_alias}
    for index, join in enumerate(rule.get('joins', []), 1):
        aliases[join['right_table']] = f'j{index}'
    references = list(rule.get('object_references') or [{
        'table': case['table'], 'columns': list(case['columns']),
        'entity_type_name': case.get('entity_type_name') or case['table'],
        'entity_type_id': case.get('entity_type_id'),
        'table_key_id': case.get('table_key_id'),
        'role': 'subject', 'evidence_basis': 'validated_case_attribution'}])
    objects, seen = [], set()
    for reference in references:
        table = reference.get('table')
        columns = list(reference.get('columns') or [])
        alias = aliases.get(table)
        identity = (table, tuple(columns))
        if not alias or not columns or identity in seen:
            continue
        seen.add(identity)
        object_id = (case_expression(case, case_alias) if reference.get('role') == 'subject' and
                     table == case.get('table') and columns == case.get('columns') else None) or _json_key(alias, columns)
        objects.append(
            "json_object(" + ','.join([
                sql_literal('object_type'), sql_literal(reference.get('entity_type_name') or table),
                sql_literal('entity_type_id'), sql_literal(reference.get('entity_type_id')),
                sql_literal('table_key_id'), sql_literal(reference.get('table_key_id')),
                sql_literal('object_id'), f'json({object_id})',
                sql_literal('table'), sql_literal(table),
                sql_literal('role'), sql_literal(reference.get('role') or 'related'),
                sql_literal('evidence_basis'), sql_literal(reference.get('evidence_basis')),
            ]) + ")")
    return 'json_array(' + ','.join(objects) + ')'


def _compile_v4_event_rule(rule, case, *, case_only=False):
    """PURPOSE: Reuse the verified v4 branch SQL builder after explicit v5 materialization.
    INPUT: Expanded concrete rule, case binding and optional case-only flag.
    OUTPUT: Independent SELECT branch with only the required joins.
    """
    parts, alias = _from(rule, case)
    identity, activity = rule['event_identity'], rule['activity']
    key, case_id = _json_key('s0', identity['key_columns']), (case_expression(case, alias) or _json_key(alias, case['columns']))
    conditions = [_condition(rule), *_missing(rule, case, alias)]
    if case_only:
        select = f'SELECT DISTINCT {case_id} AS case_id'
    else:
        event = f'json_array({sql_literal(identity["namespace"])},{key},{_discriminator(rule)})'
        components = _timestamp_component_fields(rule['timestamp'], 's0')
        component_sql = ', '.join(f'{expression} AS {name}' for name, expression in components.items())
        object_refs = _object_reference_expression(rule, case, alias)
        select = (f'SELECT {case_id} AS case_id, {event} AS event_id, '
                  f'{_activity_expression(activity)} AS activity, '
                  f'{_typed_original_expression(activity)} AS activity_original, '
                  f'{_binding_expression(activity)} AS source_event_definition_id, '
                  f'{event} AS source_occurrence_id, {_timestamp(rule["timestamp"], "s0")} AS timestamp, '
                  f'{component_sql}, '
                  f'{sql_literal(rule["source"]["table"])} AS source_table, {key} AS source_record_id, '
                  f'{object_refs} AS object_refs')
    return '\n'.join([select, *parts, 'WHERE ' + ' AND '.join(conditions)])


def _compiler_rule(source, rules, case):
    """PURPOSE: Materialize one v4-shaped compiler branch from a v5 source group.
    INPUT: One Event Source, rules sharing source and timestamp, and canonical case.
    OUTPUT: Concrete branch rule; conflicting raw-to-label mappings raise.
    """
    if not rules:
        raise ESValidationError('Compiler source branch has no rules')
    temp_es = {'event_sources': {rules[0]['source_id']: source}, 'case': case}
    expanded = [_v5_rule_to_v4(temp_es, rule) for rule in rules]
    if source['encoding'] == 'column':
        if len(expanded) != 1:
            raise ESValidationError('Column Event Source must compile one rule per branch')
        expanded[0]['compiled_rule_ids'] = [rules[0]['id']]
        return expanded[0]
    mappings, labels = [], {}
    for rule in rules:
        for raw in rule.get('raw_values', []):
            key = json.dumps(raw, sort_keys=True, ensure_ascii=False)
            if key in labels and labels[key] != rule['label']:
                raise ESValidationError('One raw activity value maps to conflicting labels')
            if key not in labels:
                labels[key] = rule['label']
                mappings.append({'raw_value': raw, 'label': rule['label'],
                                 'source_event_definition_id': rule.get('source_event_definition_id'),
                                 'activity_source': copy.deepcopy(rule.get('activity_source', {})),
                                 'activity_label_source': rule.get('activity_label_source'),
                                 'canonical_activity_id': rule.get('canonical_activity_id')})
    if not mappings:
        raise ESValidationError('Row Event Source rule has no raw activity values')
    branch = expanded[0]
    branch['activity'] = {'kind': 'value_mapping',
                          'column': source['activity_column'],
                          'mappings': sorted(mappings, key=lambda item: str(item['raw_value']))}
    activity_filter = {'kind': 'in', 'column': source['activity_column'],
                       'values': [item['raw_value'] for item in branch['activity']['mappings']]}
    branch['source_condition'] = _combine_conditions(activity_filter, source.get('row_condition'))
    branch['compiled_rule_ids'] = [rule['id'] for rule in rules]
    return branch


def _json_field_expression(spec, *, source_alias='s0', item_alias='j'):
    """PURPOSE: Compile one enumerated JSON-source field selector.
    INPUT: Field spec with exactly one of column, path, or array_index.
    OUTPUT: SQLite expression; malformed/unbound selectors raise ESValidationError.
    """
    if not isinstance(spec, dict):
        raise ESValidationError('JSON field selector must be an object')
    choices = [name for name in ('column', 'path', 'array_index', 'lookup_column') if name in spec]
    if len(choices) != 1:
        raise ESValidationError('JSON field selector needs exactly one binding')
    if choices[0] == 'column':
        return _text(source_alias, spec['column'])
    if choices[0] == 'lookup_column':
        return _text('jl', spec['lookup_column'])
    if choices[0] == 'array_index':
        return f'CAST({item_alias}.key AS TEXT)'
    path = spec['path']
    if not isinstance(path, str) or not path.startswith('$'):
        raise ESValidationError('JSON path must start with $')
    return f'CAST(json_extract({item_alias}.value,{sql_literal(path)}) AS TEXT)'


def _json_activity_expression(rules, spec, *, source_alias='s0', item_alias='j'):
    """PURPOSE: Compile raw JSON/column event types to canonical labels.
    INPUT: Activity rules and source activity selector.
    OUTPUT: Label CASE, raw expression, accepted values and Binding-ID CASE.
    """
    raw_expression = _json_field_expression(
        spec, source_alias=source_alias, item_alias=item_alias)
    labels = {}
    event_definition_ids = {}
    for rule in rules:
        for raw in rule.get('raw_values', []):
            key = json.dumps(raw, ensure_ascii=False, sort_keys=True)
            previous = labels.setdefault(key, (raw, rule['label']))
            if previous[1] != rule['label']:
                raise ESValidationError('One JSON activity value maps to conflicting labels')
            prior_binding = event_definition_ids.setdefault(
                key, (raw, rule.get('source_event_definition_id') or rule.get('id')))
            if prior_binding[1] != (rule.get('source_event_definition_id') or rule.get('id')):
                raise ESValidationError('One JSON activity value maps to conflicting Binding IDs')
    if not labels:
        raise ESValidationError('JSON Activity Rule has no raw values')
    values = [item[0] for _, item in sorted(labels.items())]
    branches = ' '.join(
        f'WHEN {sql_literal(raw)} THEN {sql_literal(label)}'
        for raw, label in (item for _, item in sorted(labels.items())))
    binding_branches = ' '.join(
        f'WHEN {sql_literal(raw)} THEN {sql_literal(event_definition_id)}'
        for raw, event_definition_id in (item for _, item in sorted(event_definition_ids.items())))
    return (f'CASE {raw_expression} {branches} ELSE NULL END', raw_expression, values,
            f'CASE {raw_expression} {binding_branches} ELSE NULL END')


def _compile_json_event_source(source, rules, case, *, case_only=False):
    """PURPOSE: Compile a JSON Event Source using json_each/json_extract deterministically.
    INPUT: Native v5 JSON source, referencing activity rules, conceptual case and case-only flag.
    OUTPUT: Independent SELECT branch; JSON paths come only from validated ES fields.
    """
    spec = source.get('json_spec', {})
    payload = spec.get('payload_column')
    if not payload:
        raise ESValidationError('JSON Event Source has no payload_column')
    array_path = spec.get('array_path')
    from_parts = [f'FROM {qi(source["table"])} s0']
    if array_path:
        if not isinstance(array_path, str) or not array_path.startswith('$'):
            raise ESValidationError('JSON array_path must start with $')
        from_parts.append(
            f'JOIN json_each(s0.{qi(payload)},{sql_literal(array_path)}) j')
    else:
        # A root object is represented as one virtual JSON item. json_each would
        # incorrectly emit one row per property, so bind its value in a one-row subquery.
        from_parts.append(
            f'JOIN (SELECT 0 AS key) ji ON 1=1')
        from_parts.append(
            f'JOIN json_each(json_array(s0.{qi(payload)})) j ON 1=1')
    lookup = spec.get('activity_lookup')
    if lookup:
        source_columns = lookup.get('source_columns', [])
        lookup_columns = lookup.get('lookup_columns', [])
        if not source_columns or len(source_columns) != len(lookup_columns):
            raise ESValidationError('JSON activity_lookup column arity mismatch')
        predicate = ' AND '.join(
            f's0.{qi(left)}=jl.{qi(right)}'
            for left, right in zip(source_columns, lookup_columns))
        from_parts.append(f'JOIN {qi(lookup["table"])} jl ON {predicate}')
    activity, raw_activity, raw_values, source_binding = _json_activity_expression(
        rules, spec.get('activity', {}))
    clock = spec.get('timestamp', {})
    timestamp_spec = {'timezone': spec.get('timezone'), **clock}
    timestamp = _json_field_expression(clock)
    if 'path' in clock:
        timestamp = _json_timestamp('j.value', clock['path'])
    elif 'column' in clock:
        timestamp = f's0.{qi(clock["column"])}'
    elif 'lookup_column' in clock:
        timestamp = f'jl.{qi(clock["lookup_column"])}'
    case_value = _json_field_expression(spec.get('case', {}))
    event_value = _json_field_expression(spec.get('event_id', {'array_index': True}))
    source_keys = source.get('event_identity', {}).get('key_columns', [])
    base_key = _json_key('s0', source_keys)
    identity_fields = spec.get('event_identity_fields')
    identity_values = ([_json_field_expression(item) for item in identity_fields]
                       if identity_fields else [base_key, event_value])
    case_id = f'json_array({case_value})'
    conditions = [f'json_valid(s0.{qi(payload)})', f'{case_value} IS NOT NULL',
                  f'{timestamp} IS NOT NULL', f'{raw_activity} IN (' +
                  ', '.join(sql_literal(value) for value in raw_values) + ')']
    if source.get('row_condition'):
        conditions.append(_condition({'source_condition': source['row_condition']}))
    if case_only:
        select = f'SELECT DISTINCT {case_id} AS case_id'
    else:
        event_id = ('json_array(' + sql_literal(source['event_identity']['namespace']) + ',' +
                    ','.join(identity_values) + ')')
        source_record = f'json_array({base_key},{event_value})'
        component_fields = {
            'timestamp_kind': sql_literal('json_path'),
            'timestamp_raw_value': timestamp,
            'timestamp_raw_column': sql_literal(
                spec.get('timestamp', {}).get('column') or payload),
            'timestamp_json_path': sql_literal(spec.get('timestamp', {}).get('path')),
            'timestamp_day': 'NULL', 'timestamp_day_column': 'NULL',
            'timestamp_clock': 'NULL', 'timestamp_clock_column': 'NULL',
            'timestamp_clock_encoding': sql_literal(timestamp_spec.get('detected_format') or timestamp_spec.get('format')),
            'timestamp_timezone': _timestamp_timezone(timestamp, timestamp_spec)}
        components = ', '.join(f'{value} AS {name}' for name, value in component_fields.items())
        original_activity = f"json_object('type',typeof({raw_activity}),'value',{raw_activity})"
        object_ref = (
            "json_array(json_object(" + ','.join([
                sql_literal('object_type'), sql_literal(case.get('entity_type_name') or case.get('table')),
                sql_literal('entity_type_id'), sql_literal(case.get('entity_type_id')),
                sql_literal('table_key_id'), sql_literal(case.get('table_key_id')),
                sql_literal('object_id'), f'json({case_id})',
                sql_literal('table'), sql_literal(case.get('table')),
                sql_literal('role'), sql_literal('subject'),
                sql_literal('evidence_basis'), sql_literal('validated_json_case_attribution'),
            ]) + "))")
        select = (f'SELECT {case_id} AS case_id, {event_id} AS event_id, '
                  f'{activity} AS activity, {original_activity} AS activity_original, '
                  f'{source_binding} AS source_event_definition_id, '
                  f'{event_id} AS source_occurrence_id, {timestamp} AS timestamp, {components}, '
                  f'{sql_literal(source["table"])} AS source_table, '
                  f'{source_record} AS source_record_id, {object_ref} AS object_refs')
    return '\n'.join([select, *from_parts, 'WHERE ' + ' AND '.join(conditions)])


def compile_event_rule(source, rules, case, *, case_only=False):
    """PURPOSE: Compile one explicit v5 (Event Source, timestamp) rule group.
    INPUT: Event Source, one-or-more Activity Rules, canonical case and case-only flag.
    OUTPUT: Deterministic SQL branch; no signature-based source inference occurs.
    """
    case = source_case(source, case)
    if source.get('encoding') == 'json':
        return _compile_json_event_source(source, rules, case, case_only=case_only)
    return _compile_v4_event_rule(
        _compiler_rule(source, rules, case), case, case_only=case_only)


def _as_v5(es):
    """PURPOSE: Route v4 and v5 inputs through one native compiler representation.
    INPUT: Stored ES mapping.
    OUTPUT: Deep-copied v5 ES; unsupported versions and source conflicts raise.
    """
    normalized = upgrade_es_v4_to_v5(es) if es.get('es_version') == 4 else copy.deepcopy(es)
    return normalize_event_definition_references(normalized)


def validate_es(es):
    """PURPOSE: Check v5 source references and compiler invariants before SQL generation.
    INPUT: ES v5 or compatible v4 input upgraded in memory.
    OUTPUT: Passed flag and static issues; no DB reads or model calls.
    """
    issues = []
    try:
        normalized = _as_v5(es)
        if normalized.get('es_version') not in (5, 6):
            issues.append('ES version 5 or 6 required')
        issues.extend(validate_population(normalized)['issues'])
        if normalized.get('status') != 'accepted':
            issues.append('Only accepted ES can be compiled')
        selected_contract=selected_definition_contract(normalized)
        if not normalized.get('event_rules') and not (
                selected_contract and selected_contract['request_mode']=='implicit'
                and selected_contract['selected_event_definition_ids']==[]
                and normalized.get('case',{}).get('population',{}).get('status')=='valid'):
            issues.append('No event rules')
        sources = normalized.get('event_sources', {})
        rules = [*normalized.get('event_rules', []), *normalized.get('selection_rules', [])]
        references = [rule.get('source_id') for rule in rules]
        missing = sorted({source_id for source_id in references if source_id not in sources})
        orphan = sorted(set(sources) - set(references))
        if missing:
            issues.append('Missing Event Source references: ' + ', '.join(map(str, missing)))
        if orphan:
            issues.append('Unreferenced Event Sources: ' + ', '.join(orphan))
        for conflict in _source_conflicts(sources):
            issues.append('source_conflict: ' + json.dumps(conflict, sort_keys=True))
        for source_id, source in sources.items():
            issues.extend(source_id + ': ' + issue for issue in path_issues(
                source.get('case_attribution', {}).get('relationship_path', [])))
            physical_case = source_case(source, normalized['case'])
            path = source.get('case_attribution', {}).get('relationship_path', [])
            endpoint = path[-1].get('right_table') if path else source.get('table')
            if source.get('encoding') != 'json' and not physical_case.get('projection') and endpoint != physical_case.get('table'):
                issues.append('Attribution path does not reach physical case member: ' + source_id)
            from src.common.attribution_policy import role_scope_issues, role_scope_steps
            for scope in role_scope_steps(source.get('row_condition')):
                issues.extend(role_scope_issues(scope, path))
            if source_id != event_source_id(source):
                issues.append('Event Source ID does not match its content: ' + source_id)
            if source.get('encoding') not in ('row', 'column', 'json'):
                issues.append('Unsupported Event Source encoding: ' + source_id)
            if source.get('encoding') == 'row' and not source.get('activity_column'):
                issues.append('Row Event Source has no activity column: ' + source_id)
            if source.get('encoding') == 'json':
                spec = source.get('json_spec', {})
                required = {'payload_column', 'activity', 'timestamp', 'case', 'event_id'}
                if not required <= set(spec):
                    issues.append('JSON Event Source has incomplete json_spec: ' + source_id)
        for collection in ('event_rules', 'selection_rules'):
            seen = set()
            for rule in normalized.get(collection, []):
                contract = rule.get('eeg_candidate_validation')
                if contract is not None and (contract.get('extraction_status') != 'executable' or
                        not contract.get('extraction_checks') or
                        any(v != 'supported' for v in contract['extraction_checks'].values())):
                    issues.append('Unresolved EEG candidate cannot be compiled: ' + str(rule.get('id')))
                if rule.get('id') in seen:
                    issues.append('Duplicate rule ID')
                seen.add(rule.get('id'))
                if not rule.get('label'):
                    issues.append('Canonical activity label required')
                if rule.get('source_id') not in sources:
                    continue
                source = sources[rule['source_id']]
                if source['encoding'] in ('row', 'json') and not rule.get('raw_values'):
                    issues.append('Row Activity Rule has no raw values: ' + str(rule.get('id')))
                if source['encoding'] == 'column' and rule.get('raw_values'):
                    issues.append('Column Activity Rule cannot contain raw values: ' + str(rule.get('id')))
        sources_by_activity = {}
        for rule in normalized.get('event_rules', []):
            sources_by_activity.setdefault(rule.get('label'), set()).add(rule.get('source_id'))
        for label, source_ids in sources_by_activity.items():
            if (len(source_ids) > 1 and normalized.get('activity_source_policy') == 'single'
                    and not normalized.get('source_priority')):
                issues.append('Activity uses multiple sources without source_priority: ' + str(label))
            if len(source_ids) > 1 and normalized.get('activity_source_policy') == 'partitioned_attribution':
                activity_rules = [rule for rule in normalized.get('event_rules', [])
                                  if rule.get('label') == label]
                partition_ids = {
                    (rule.get('decision') or {}).get('partition_id')
                    for rule in activity_rules
                    if (rule.get('decision') or {}).get('partition_verified_complete')}
                member_ids = {rule.get('id') for rule in activity_rules}
                if (len(partition_ids) != 1 or any(
                        set((rule.get('decision') or {}).get(
                            'partition_member_candidate_ids', [])) != member_ids
                        for rule in activity_rules)):
                    issues.append('Activity has an invalid attribution partition: ' + str(label))
        for source_id, source, clock_rules in group_rules_by_source(normalized):
            if source.get('encoding') not in ('row', 'json'):
                continue
            mapping = {}
            for rule in clock_rules:
                for raw in rule.get('raw_values', []):
                    key = json.dumps(raw, sort_keys=True, ensure_ascii=False)
                    previous = mapping.setdefault(key, rule.get('label'))
                    if previous != rule.get('label'):
                        issues.append('Raw activity value maps to conflicting labels in ' + source_id)
        definitions = selected_definition_issues(normalized)
        targets = normalized.get('process_view', {}).get('target_activities', [])
        if definitions is not None:
            issues.extend('Selected Event definition absent: ' + item for item in definitions['missing'])
            issues.extend('Event definition outside PI selection: ' + item for item in definitions['extra'])
            issues.extend('Event rule lacks an Event definition ID: ' + item for item in definitions['unidentified_rules'])
            if definitions['selection_mismatch']:
                issues.append('Process View and ES contract select different Event definitions')
            if selected_contract.get('activity_label_policy') == 'eeg_canonical_only':
                labels = selected_contract.get('canonical_labels', {})
                if ('activity_mapping' in selected_contract
                        or 'activity_mapping' in normalized.get('process_view', {})
                        or set(labels) != set(selected_contract['selected_event_definition_ids'])
                        or any(rule['label'] != labels.get(rule.get('source_event_definition_id'))
                               for rule in normalized.get('event_rules', []))):
                    issues.append('Event rule label diverges from the canonical EEG Activity')
        elif targets:
            labels = [rule.get('label') for rule in normalized.get('event_rules', [])]
            for target in targets:
                count = labels.count(target)
                if count < 1:
                    issues.append(f'Target activity is absent: {target}')
            extra = sorted(set(labels) - set(targets))
            if extra:
                issues.append('Activities outside Process View: ' + ', '.join(extra))
        for collection in ('event_rules', 'selection_rules'):
            for source_id, source, grouped_rules in group_rules_by_source(normalized, collection):
                compile_event_rule(source, grouped_rules, normalized['case'],
                                   case_only=collection == 'selection_rules')
        selection = normalized.get('case_selection', {'kind': 'all_cases'})
        if selection['kind'] not in ('all_cases', 'exists_activity', 'reference_role'):
            issues.append('Unsupported case selection')
        if selection['kind'] == 'exists_activity' and not normalized.get('selection_rules'):
            issues.append('Missing selection rules')
    except (ESValidationError, KeyError, TypeError, ValueError) as exc:
        issues.append(str(exc))
    return {'passed': not issues, 'issues': issues}


def _base(es):
    """PURPOSE: Share v5 branch and case-selection construction across SQL packages.
    INPUT: v4/v5 ES with all_cases or exists_activity selection.
    OUTPUT: CTEs, source clause and normalized v5 ES; invalid ES raises.
    """
    normalized = _as_v5(es)
    check = validate_es(normalized)
    if not check['passed']:
        raise ESValidationError('; '.join(check['issues']))
    event_groups = group_rules_by_source(normalized, 'event_rules')
    branches = '\nUNION ALL\n'.join(
        compile_event_rule(source, rules, normalized['case'])
        for _, source, rules in event_groups)
    if not branches and selected_definition_contract(normalized):
        branches='SELECT '+','.join('NULL AS '+qi(column) for column in OUTPUT_COLUMNS)+' WHERE 0'
    priority = normalized.get('source_priority')
    if priority:
        rank = 'CASE source_table ' + ' '.join(
            f'WHEN {sql_literal(table)} THEN {index}'
            for index, table in enumerate(priority, 1)) + ' ELSE 999999 END'
        ctes = [f'unranked_event_rows AS (\n{branches}\n)',
                ('raw_event_rows AS (SELECT ' + ','.join(OUTPUT_COLUMNS) +
                 ' FROM (SELECT u.*,ROW_NUMBER() OVER(PARTITION BY event_id ORDER BY ' +
                 rank + ',source_record_id) AS source_rank FROM unranked_event_rows u) '
                 'WHERE source_rank=1)')]
    else:
        ctes = [f'raw_event_rows AS (\n{branches}\n)']
    population = population_cte(normalized['case'], normalized.get('case_selection'))
    if population:
        ctes.insert(0, population)
    source_clause = 'FROM raw_event_rows e'
    if population:
        source_clause += ' JOIN entity_cases ec USING (case_id)'
    if normalized.get('case_selection', {}).get('kind') == 'exists_activity':
        selection_groups = group_rules_by_source(normalized, 'selection_rules')
        selected = '\nUNION\n'.join(
            compile_event_rule(source, rules, normalized['case'], case_only=True)
            for _, source, rules in selection_groups)
        ctes.append(f'selected_cases AS (\n{selected}\n)')
        source_clause += ' JOIN selected_cases s USING (case_id)'
    return ctes, source_clause, normalized


def compile_es(es):
    """PURPOSE: Compile event-log SQL deterministically from v4/v5 ES.
    INPUT: Accepted ES; v4 is upgraded before compilation.
    OUTPUT: Deduplicated log SQL; conflict validation remains a separate package query.
    """
    ctes, source, normalized = _base(es)
    if selected_definition_contract(normalized):
        # Equivalent paths may differ only in provenance. Keep the richest projection.
        keys=','.join('e.'+column for column in OUTPUT_COLUMNS if column!='object_refs')
        ctes.append('projected_history AS (SELECT e.*,ROW_NUMBER() OVER(PARTITION BY '+keys+
                    ' ORDER BY LENGTH(e.object_refs) DESC,e.object_refs) AS projection_rank '+source+')')
        source='FROM projected_history e WHERE e.projection_rank=1'
    return ('WITH ' + ',\n'.join(ctes) + '\nSELECT DISTINCT ' +
            ','.join('e.' + column for column in OUTPUT_COLUMNS) + '\n' + source +
            '\nORDER BY case_id,timestamp,event_id;\n')


def compile_conflict_diagnostics(es):
    """PURPOSE: Detect conflicting labels/times for one physical event identity.
    INPUT: Accepted v4/v5 ES.
    OUTPUT: SQL returning conflict IDs in the same transaction as log extraction.
    """
    ctes, source, normalized = _base(es)
    ctes.append(f'variants AS (SELECT DISTINCT e.event_id,e.case_id,e.activity,e.timestamp {source})')
    enforce_single = any(
        item.get('case_attribution', {}).get('multiplicity_policy', {}).get('expected') == 'single'
        for item in normalized.get('event_sources', {}).values())
    case_clause = ' OR COUNT(DISTINCT case_id)>1' if enforce_single else ''
    return ('WITH ' + ',\n'.join(ctes) +
            '\nSELECT event_id,COUNT(*) AS variants,COUNT(DISTINCT case_id) AS case_count FROM variants '
            'GROUP BY event_id HAVING COUNT(*)>1 AND ' 
            '(COUNT(DISTINCT activity||char(31)||timestamp)>1' + case_clause + ');\n')


def compile_sql_package(es):
    """PURPOSE: Package v5 extraction/conflict SQL with a source-based plan.
    INPUT: Accepted v4/v5 ES.
    OUTPUT: SQL, precision, source/rule/branch counts and transaction instructions.
    """
    normalized = _as_v5(es)
    event_groups = group_rules_by_source(normalized, 'event_rules')
    selection_groups = group_rules_by_source(normalized, 'selection_rules')
    referenced_sources = {rule['source_id'] for rule in [
        *normalized.get('event_rules', []), *normalized.get('selection_rules', [])]}
    return {'package_version': 2, 'es_version': normalized['es_version'],
            'event_log_sql': compile_es(normalized),
            'conflict_sql': compile_conflict_diagnostics(normalized),
            'case_population_sql': ('WITH ' + population_cte(normalized['case'], normalized.get('case_selection')) +
                ' SELECT case_id FROM entity_cases ORDER BY case_id;' if normalized['case'].get('population') else None),
            'epoch_precision': 'source',
            'compilation_plan': {
                'event_sources': len(referenced_sources),
                'event_rules': len(normalized['event_rules']),
                'source_branches': len(event_groups),
                'event_source_branches': len(event_groups),
                'selection_rules': len(normalized.get('selection_rules', [])),
                'selection_source_branches': len(selection_groups)},
            'attribution_policy': POLICY,
            'contract': ['BEGIN on one read-only connection',
                         'Validate every attribution hop against declared FK and PK/UNIQUE schema',
                         'Execute conflict_sql; abort if any rows',
                         'Execute event_log_sql on the same connection', 'COMMIT']}


def extract_event_log(database, es):
    """PURPOSE: Validate conflicts and extract a v5 log on one read-only snapshot.
    INPUT: SQLite path and accepted v4/v5 ES.
    OUTPUT: (SQL, rows, diagnostics) with source-level dropped-key provenance.
    """
    normalized = _as_v5(es)
    package = compile_sql_package(normalized)
    with closing(connect_readonly(database)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute('BEGIN')
        attribution_issues = [source_id + ': ' + issue
            for source_id, source in normalized.get('event_sources', {}).items()
            for issue in database_path_issues(conn, source.get('case_attribution', {}).get('relationship_path', []))]
        from src.common.attribution_policy import role_scope_alternatives, role_scope_steps
        from src.common.occurrence_conditions import occurrence_condition_issues
        for source_id, source in normalized.get('event_sources', {}).items():
            attribution_issues.extend(occurrence_condition_issues(conn, source['table'], source.get('row_condition')))
            for scope in role_scope_steps(source.get('row_condition')):
                attribution_issues.extend(source_id + ': ' + issue
                                          for other in role_scope_alternatives(scope)
                                          for issue in database_path_issues(conn, [*scope['prefix'], other]))
        if (selection := normalized.get('case_selection', {})).get('kind') == 'reference_role':
            attribution_issues.extend(database_path_issues(conn, [selection['step']]))
        if attribution_issues:
            raise ESValidationError('; '.join(attribution_issues))
        conflicts = [dict(row) for row in conn.execute(package['conflict_sql'])]
        if conflicts:
            raise ESValidationError('Event identity conflicts: ' + json.dumps(conflicts[:10]))
        rows = [dict(row) for row in conn.execute(package['event_log_sql'])]
        rows.sort(key=lambda row: (row['case_id'], event_time_order(row), row['event_id']))
        case_population = ([dict(row) for row in conn.execute(package['case_population_sql'])]
                           if package.get('case_population_sql') else None)
        dropped = []
        grouped = {}
        for source_id, source, rules in group_rules_by_source(normalized, 'event_rules'):
            entry = grouped.setdefault(source_id, {'source': source, 'rules': [], 'conditions': []})
            entry['rules'].extend(rules)
            if source.get('encoding') == 'json':
                payload = source.get('json_spec', {}).get('payload_column')
                entry['conditions'].append(
                    f'json_valid(s0.{qi(payload)})' if payload else '0')
            else:
                branch = _compiler_rule(source, rules, normalized['case'])
                entry['conditions'].append(_condition(branch))
        for source_id, entry in grouped.items():
            source = entry['source']
            key_columns = source['event_identity']['key_columns']
            nulls = ' OR '.join(f's0.{qi(column)} IS NULL' for column in key_columns)
            condition = ' OR '.join('(' + value + ')' for value in entry['conditions'])
            count = conn.execute(
                f'SELECT COUNT(*) FROM {qi(source["table"])} s0 '
                f'WHERE ({condition}) AND ({nulls})').fetchone()[0]
            dropped.append({'source_id': source_id,
                            'rule_ids': sorted({rule['id'] for rule in entry['rules']}),
                            'null_key_source_rows': count})
        conn.commit()
    return package['event_log_sql'], rows, {
        'row_count': len(rows), 'identity_conflicts': 0,
        'case_population': case_population,
        'case_population_count': len(case_population) if case_population is not None else None,
        'empty_case_ids': ([r['case_id'] for r in case_population if r['case_id'] not in {e['case_id'] for e in rows}]
                           if case_population is not None else []),
        'conflict_sql': package['conflict_sql'], 'sql_package': package,
        'dropped_key_rows_by_source': dropped,
        'dropped_key_rows_by_rule': [
            {'rule_id': rule_id, 'source_id': item['source_id'],
             'null_key_source_rows': item['null_key_source_rows']}
            for item in dropped for rule_id in item['rule_ids']]}
