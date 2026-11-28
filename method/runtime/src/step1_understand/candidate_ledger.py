"""Record structural discovery, admission, and runtime projection independently."""

from collections import Counter

from src.common.graph_identifiers import content_hash, event_definition_id


def candidate_key(kind, source):
    """PURPOSE: Identify a physical candidate independently of language or display labels.
    INPUT: Candidate kind and source fields, including an optional typed SQLite scalar.
    OUTPUT: Stable candidate ID.
    """
    fields = dict(source)
    if 'value' in fields:
        value = fields['value']
        fields['value'] = [type(value).__name__, value.hex() if isinstance(value, bytes) else value]
    return 'candidate:' + content_hash([kind, fields])


def build_ledger(activity_traces, timestamp_traces, bindings, units, scan_limit, *, native=None, reviews=()):
    """PURPOSE: Preserve the choices that lead from profiled sources to native Event Definitions.
    INPUT: Timestamp and carrier traces, finalized native definitions, accepted clocks and scan bound.
    OUTPUT: Candidate entries and discovery limits, before runtime family projection.
    """
    rows, limits = {}, []

    def record(kind, source, decision, reason, **facts):
        """PURPOSE: Record a candidate under its physical identity.
        INPUT: Kind, source, terminal decision, reason and optional evidence facts.
        OUTPUT: None. Updates the in-progress ledger.
        """
        candidate = candidate_key(kind, source)
        rows[candidate] = dict(id=candidate, kind=kind, source=source, decision=decision, reason=reason, **facts)

    for table, trace in sorted(timestamp_traces.items()):
        for column, result in sorted(trace['columns'].items()):
            if result.get('sample_count', 0) >= scan_limit:
                limits.append(dict(table=table, column=column, reason='timestamp_scan_limit_reached'))
            if not result.get('accepted_by'):
                record('timestamp_source', dict(table=table, column=column), 'unresolved',
                       result.get('rejection_reason') or 'timestamp_signals_insufficient')
    for unit in units:
        source = dict(table=unit['table'], timestamp_unit_id=unit['ts_id'])
        record('timestamp', source, 'supported_source', 'recognized_timestamp_representation',
               evidence_ids=[unit['dd_definition_id']] if unit.get('dd_definition_id') else [])
        record('column_event', source, 'unresolved', 'column_event_not_admitted',
               definition_id=event_definition_id(unit['table'], {'kind': 'column'}, unit['ts_id']))
    timed_tables = {unit['table'] for unit in units}
    for table, trace in sorted(activity_traces.items()):
        if table not in timed_tables:
            limits.append(dict(table=table, reason='carrier_discovery_blocked_by_timestamp_detection'))
        for item in trace.get('activity_evaluations', []):
            status = 'supported_source' if item.get('accepted') else item['evidence_status']
            if status == 'supported':
                status = 'unresolved'
            record('carrier', dict(table=table, column=item['column']), status,
                   item.get('admission') or ','.join(item['rejection_reasons']) or 'profiled_carrier',
                   evidence_ids=[item['column_id']], distinct_count=item['distinct_count'])
        for row in trace.get('carrier_timestamp_matrix', []):
            source = dict(table=table, column=row['carrier'], value=row['value'], timestamp_unit_id=row['ts_id'])
            state = 'unresolved' if row['status'] in {'supported', 'unresolved', 'no_timed_rows'} else 'rejected'
            refs = {citation['evidence_id'] for citation in row.get('value_citations', []) + row.get('citations', [])}
            if row.get('clock_evidence_id'):
                refs.add(row['clock_evidence_id'])
            record('carrier_event', source, state, row['reason'], definition_id=row['candidate_id'],
                   timed_rows=row['timed_rows'], population=row['population'], evidence_ids=sorted(refs),
                   semantic_status=row['status'])
    for binding in bindings:
        alpha = binding['alpha']
        source = dict(table=binding['table'], timestamp_unit_id=binding['ts_id'])
        if alpha['kind'] == 'value':
            source.update(column=alpha['column'], value=alpha['value'])
        if conditions := binding.get('documented_source_conditions'):
            source['occurrence_conditions_id'] = content_hash(conditions)
        kind = {'value': 'carrier_event', 'column': 'column_event'}.get(alpha['kind'], 'table_event')
        previous = rows.get(candidate_key(kind, source), {})
        status = binding.get('extraction_status')
        decision = 'approved' if status == 'executable' else 'unresolved'
        refs = set(previous.get('evidence_ids', [])) | {e['ref'] for e in binding.get('evidence', []) if e.get('ref')}
        reason = previous.get('reason') if previous.get('decision') == decision else None
        record(kind, source, decision, reason or 'definition_' + (status or 'unresolved'),
               definition_id=binding['id'], evidence_ids=sorted(refs), validation_status=status,
               **{k: previous[k] for k in ('timed_rows', 'population', 'semantic_status') if k in previous})
    native = native or {}
    identification = {}
    for rule in native.get('identification_rules', []):
        if rule.get('status') == 'supported':
            identification.setdefault(rule['target_id'], []).append(rule['id'])
    for target in native.get('identification_targets', []):
        projections = identification.get(target['id'], [])
        record('entity_identification', target['source'], 'approved' if projections else 'unresolved',
               'verified_identification_rule' if projections else 'identification_rule_unresolved',
               projected_rule_ids=sorted(projections), evidence_ids=sorted(
                   {ev['id'] for ev in target.get('evidence', []) if ev.get('id')}))
    for path in native.get('attribution_paths', []):
        source = dict(table=path['from_table'], event_definition_id=path['event_definition_id'],
                      case_id=path['to'], rule_id=path['id'])
        outcome = path['validation_status']
        accepted = outcome in {'valid', 'rule_confirmed_no_occurrences'}
        record('attribution', source, 'approved' if accepted else 'unresolved',
               path.get('reason_code') or outcome, projected_rule_ids=[path['id']] if accepted else [],
               scope_proof=path.get('case_map', {}).get('validation', {}))
    missing_reviews = [{'stage': review['kind'], 'table': review['table'],
                        'carrier_column': review.get('carrier_column'), 'candidate_id': identifier}
                       for review in reviews for identifier in review.get('missing_candidate_ids', [])]
    return {'version': 'candidate-ledger-v2', 'candidates': list(rows.values()),
            'discovery_limits': limits, 'missing_reviews': missing_reviews}


def audit_ledger(ledger, graph):
    """PURPOSE: Check accounting and approved-to-executable mapping after runtime projection.
    INPUT: Discovery ledger and final runtime EEG.
    OUTPUT: Ledger with projection IDs and separate discovery, decision and projection counters.
    """
    executable = {d['id']: d for d in graph.get('event_definitions', []) if d.get('extraction_status') == 'executable'}
    rules = {r['id'] for r in graph.get('identification_rules', []) if r.get('status') == 'supported'}
    paths = {p['id']: p for p in graph.get('attribution_paths', [])
             if p.get('validation_status') in {'valid', 'rule_confirmed_no_occurrences'}}
    retired = {path['id']: path for path in (graph.get('dbu_rewrite') or {}).get('attribution_paths', [])}
    migrations = graph.get('event_definition_migration', {})
    rows, missing, unaccounted = [], [], []
    for raw in ledger['candidates']:
        row = dict(raw)
        if not row.get('decision') or not row.get('reason'):
            unaccounted.append(row['id'])
        if row.get('decision') == 'approved':
            definition = row.get('definition_id')
            migration = migrations.get(definition, {})
            replacements = migration.get('replacement_ids', []) if migration.get('status') == 'replaced_by_family' else []
            if row.get('kind') == 'entity_identification':
                required = row['projected_rule_ids']
                row['projected_ids'] = required if set(required) <= rules else []
            elif row.get('kind') == 'attribution':
                rule_id = row['source']['rule_id']
                original = retired.get(rule_id)
                orig_ed = row['source']['event_definition_id']
                family = migrations.get(orig_ed, {})
                members = family.get('replacement_ids', []) if family.get('status') == 'replaced_by_family' else []
                if rule_id in paths:
                    row['projected_ids'] = [rule_id]
                else:
                    equivalent = {p['event_definition_id']: p['id'] for p in paths.values() if members and original and
                        p['event_definition_id'] in members and
                        all(p.get(k) == original.get(k) for k in ('to', 'target_table_key_id', 'joins', 'role_scope'))}
                    row['projected_ids'] = [equivalent[i] for i in members] if set(members) <= equivalent.keys() else []
            else:
                source = row.get('source', {})
                direct = executable.get(definition)
                same_value = ('value' not in source or direct and any(
                    type(value) is type(source['value']) and value == source['value'] for value in direct.get('raw_values', [])))
                scope_id = source.get('occurrence_conditions_id')
                same_scope = (scope_id is None or direct and
                              content_hash(direct.get('documented_source_conditions', [])) == scope_id)
                row['projected_ids'] = ([definition] if direct and same_value and same_scope else
                                        replacements if set(replacements) <= executable.keys() else [])
            if not row['projected_ids']:
                missing.append(row['id'])
        rows.append(row)
    counts = Counter(r.get('decision') for r in rows)
    return dict(ledger, candidates=rows, audit={
        'enumerated': len(rows), 'decided': len(rows) - len(unaccounted),
        'approved': counts['approved'], 'represented': counts['approved'] - len(missing),
        'unresolved': counts['unresolved'], 'missing_decisions': unaccounted + ledger.get('missing_reviews', []),
        'missing_projections': missing, 'discovery_limited': bool(ledger['discovery_limits']),
    })
