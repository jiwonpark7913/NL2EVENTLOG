"""Render the authored event graph inventory for human review."""
import json
from collections import defaultdict

from gold_source_rows import quote


def render_event_graph(dataset, db, table_audit):
    report = json.loads((dataset/'validation_report.json').read_text())
    coverage = report['object_view_coverage']
    activities = {row['case_concept']: row['activities'] for row in coverage}
    members = defaultdict(list)
    split_activities = {}
    if dataset.name == 'hospitalflow':
        identity = json.loads((dataset/'private/identity_gold.json').read_text())
        event_labels = {}
        for line in (dataset/'private/canonical_history.jsonl').read_text().splitlines():
            event = json.loads(line)
            event_labels[event['event_id']] = event['activity']
        by_object = defaultdict(set)
        for link in json.loads((dataset/'private/object_event_links.json').read_text()):
            by_object[link['object_id']].add(event_labels[link['event_id']])
        for group in identity['groups']:
            physical_members = group['members']
            members[group['object_type']].extend(row['table'] for row in physical_members)
            if len(physical_members) > 1:
                for row in physical_members:
                    table = row['table']
                    pk, = row['primary_key']
                    ids = db.execute('SELECT '+quote(pk)+' FROM '+quote(table))
                    split_activities[table] = sorted({
                        activity for (key,) in ids
                        for activity in by_object[row['canonical_key_prefix']+str(key)]
                    })
        group_rule = 'OT groups use the authored identity annotations. For each split-table member, the object section projects canonical event links onto the keys present in that table.'
    else:
        for row in coverage:
            members[row['case_concept']].append(row['case_table'])
        group_rule = 'Documented object views supply the names of their singleton OTs.'
    table_types = {table: ot for ot, tables in members.items() for table in tables}
    keys = {}
    for row in table_audit:
        table = row['table']
        info = db.execute('PRAGMA table_info('+quote(table)+')').fetchall()
        keys[table] = [col['name'] for col in sorted(info, key=lambda col: col['pk']) if col['pk']]
        if keys[table] and table not in table_types:
            ot = f'`{table}` (singleton)'
            members[ot].append(table)
            table_types[table] = ot

    def linked_to_ot(ot):
        if ot not in activities:
            return 'No authored event-to-object links'
        return listing(activities[ot])

    def listing(values):
        return ', '.join(values) or '—'

    def code(values):
        return listing(f'`{value}`' for value in values)

    page = [
        f'# {dataset.name} · Event graph inventory',
        '',
        '**EVALUATION ONLY.** [Back to question and DFG review](README.md).',
        '',
        'This page shows the authored benchmark graph. Table bindings identify where events are recorded. '
        'Object links identify which activities are attributed to an object, including activities recorded in other tables.',
        '',
        group_rule,
        'Every physical object without an explicit group gets a singleton OT. Table-named singletons have no authored object-view attribution. See Events produced for their source activities.',
        '',
        '## Tables and event sources',
        '',
        '| Table | Event classification | Carrier column | Selected event timestamps | Physical object (table · PK) | OT group | Events produced |',
        '|---|---|---|---|---|---|---|',
    ]
    for row in table_audit:
        table = row['table']
        if row['carrier']:
            classification = 'Event · carrier'
        elif row['selected_timestamp_columns']:
            classification = 'Event · non-carrier'
        else:
            classification = 'Non-event'
        physical = f'`{table}` · {code(keys[table])}' if keys[table] else '—'
        page.append('| '+' | '.join([
            f'`{table}`', classification, code([row['carrier']] if row['carrier'] else []),
            code(row['selected_timestamp_columns']), physical, table_types.get(table, '—'),
            listing(row['activities']),
        ])+' |')

    page.extend([
        '',
        '## Object types and attributed activities',
        '',
        '| OT group | Member physical objects | Activities linked to OT |',
        '|---|---|---|',
    ])
    for ot, tables in members.items():
        page.append(f'| {ot} | {code(tables)} | {linked_to_ot(ot)} |')

    page.extend([
        '',
        '## Physical objects and attributed activities',
        '',
        '| Physical object | OT group | Activities linked to this object |',
        '|---|---|---|',
    ])
    for row in table_audit:
        table = row['table']
        if not keys[table]:
            continue
        ot = table_types[table]
        linked = listing(split_activities[table]) if table in split_activities else linked_to_ot(ot)
        page.append(f'| `{table}` | {ot} | {linked} |')
    return '\n'.join(page)+'\n'
