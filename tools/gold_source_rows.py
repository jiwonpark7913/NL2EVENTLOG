"""Replay authored Gold bindings to recover original SQLite rows for review."""
import html
import re
import sqlite3
from collections import defaultdict

from validate_event_scope import bindings


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def event_key(row):
    return row['event_id'], row['activity'], row['timestamp']


class SourceRows:
    def __init__(self, dataset):
        self.db = sqlite3.connect((dataset/'input/database.sqlite').resolve().as_uri()+'?mode=ro', uri=True)
        self.db.row_factory = sqlite3.Row
        self.events = defaultdict(list)
        for binding in bindings(dataset):
            table = binding['table']
            sql = binding['event_sql']
            # Authored bindings use a plain SELECT or a SELECT * wrapper.
            match = re.search(r'\bFROM\s+' + re.escape(table) + r'\b(?:\s+(?:AS\s+)?(\w+))?', sql, re.I)
            alias = match.group(1)
            if not alias or alias.upper() in {'WHERE','JOIN','LEFT','ORDER','GROUP','LIMIT','UNION'}:
                alias = table
            select = list(re.finditer(r'\bSELECT\s+', sql[:match.start()], re.I))[-1].end()
            instrumented = sql[:select] + quote(alias) + '.rowid AS __source_rowid, ' + sql[select:]
            for row in self.db.execute(instrumented):
                self.events[event_key(row)].append((table, row['__source_rowid'], binding['timestamp_column']))

    def inspect(self, gold_sql, rows):
        reads = defaultdict(set)
        def authorize(action, table, column, database, context):
            if action == sqlite3.SQLITE_READ and database == 'main':
                reads[table].add(column)
            return sqlite3.SQLITE_OK

        self.db.set_authorizer(authorize)
        try:
            self.db.execute('EXPLAIN QUERY PLAN ' + gold_sql).fetchall()
        finally:
            self.db.set_authorizer(None)

        matches = defaultdict(dict)
        missing = 0
        for event in rows:
            refs = [ref for ref in self.events[event_key(event)] if ref[0] in reads]
            if not refs:
                missing += 1
            for table, rowid, timestamp in refs:
                labels = matches[table].setdefault(rowid, set())
                labels.add((event['event_id'], event['activity'], timestamp, event['case_id']))

        tables = []
        for table, matched in sorted(matches.items()):
            columns = [row['name'] for row in self.db.execute('PRAGMA table_info('+quote(table)+')')]
            records = []
            for rowid, labels in matched.items():
                original = self.db.execute('SELECT * FROM '+quote(table)+' WHERE rowid=?', (rowid,)).fetchone()
                records.append(([original[column] for column in columns], sorted(labels)))
            tables.append((table, columns, records))
        related = self.related_rows(matches, reads)
        return tables, reads, missing, related

    def related_rows(self, matches, reads):
        """Show FK-linked examples from SQL-referenced tables as join context."""
        queue = [(table, rowid) for table, ids in matches.items() for rowid in ids]
        visited = set(queue)
        related = defaultdict(list)
        foreign_keys = {}
        for table, rowid in queue:
            if table not in foreign_keys:
                grouped = defaultdict(list)
                for fk in self.db.execute('PRAGMA foreign_key_list('+quote(table)+')'):
                    if fk['table'] in reads and fk['to']:
                        grouped[fk['id']].append(fk)
                foreign_keys[table] = list(grouped.values())
            source = self.db.execute('SELECT * FROM '+quote(table)+' WHERE rowid=?', (rowid,)).fetchone()
            for keys in foreign_keys[table]:
                parent = keys[0]['table']
                values = [source[fk['from']] for fk in keys]
                if any(value is None for value in values):
                    continue
                predicate = ' AND '.join(quote(fk['to'])+'=?' for fk in keys)
                for row in self.db.execute('SELECT rowid AS __source_rowid, * FROM '+quote(parent)+' WHERE '+predicate, values):
                    key = parent, row['__source_rowid']
                    if key in visited:
                        continue
                    visited.add(key)
                    queue.append(key)
                    if len(related[parent]) < 3:
                        related[parent].append(({k:row[k] for k in row.keys() if k!='__source_rowid'}, table, [fk['from']+' → '+fk['to'] for fk in keys]))
        return related


def render_review_evidence(tables, missing, related, *, dataset_path, question_id):
    """Put original database values beside the corresponding Gold output."""
    def cell(value):
        return '<em>NULL</em>' if value is None else html.escape(str(value))

    def field_table(fields, rows):
        head = '<tr><th>Column</th>'+''.join(f'<th>Row {i}</th>' for i in range(1, len(rows)+1))+'</tr>'
        body = ''.join(
            '<tr><th>'+cell(field)+'</th>'+''.join('<td>'+cell(row[index])+'</td>' for row in rows)+'</tr>'
            for index, field in enumerate(fields)
        )
        return '<table>'+head+body+'</table>'

    out = [
        f'<p><a href="{dataset_path}/private/gold_sql/{question_id}.sql">Gold SQL</a> · '
        f'<a href="{dataset_path}/private/gold_logs/{question_id}.csv">Gold CSV</a> · '
        f'<a href="{dataset_path}/input/database.sqlite">Full source database (SQLite)</a></p>',
    ]
    if missing:
        out.append(f'<p><strong>{missing} Gold event rows could not be matched to an original row.</strong></p>')
    for table, columns, rows in tables:
        # Prefer different activities so rare branches are represented in the preview.
        selected = []
        seen = set()
        for idx, (_, labels) in enumerate(rows):
            activities = {label[1] for label in labels}
            if activities - seen:
                selected.append(idx)
                seen.update(activities)
                if len(selected) == 3:
                    break
        selected.extend(idx for idx in range(min(3, len(rows))) if idx not in selected)
        sample = [rows[idx] for idx in selected[:3]]
        out.append(f'<details><summary><code>{cell(table)}</code> · {len(rows)} matched source rows</summary>')
        out.append(field_table(columns, [values for values, _ in sample]))
        out.append('<p><strong>Gold output for the same source rows</strong></p><ul>')
        for idx, (_, events) in enumerate(sample, 1):
            for eid, activity, timestamp, case in events:
                out.append(f'<li>Row {idx} → {cell(activity)} · event {cell(eid)} · case {cell(case)} · time from <code>{cell(timestamp)}</code></li>')
        out.append('</ul></details>')
    if related:
        out.append('<details><summary>FK-linked case and join evidence</summary><ul>')
        for table, examples in sorted(related.items()):
            row, child, keys = examples[0]
            join_values = ', '.join(
                f'{key.split(" → ")[-1]} = {row[key.split(" → ")[-1]]}' for key in keys
            )
            out.append(f'<li><code>{cell(child)}</code> → <code>{cell(table)}</code> · {cell(", ".join(keys))} · {cell(join_values)}</li>')
        out.append('</ul></details>')
    return ''.join(out)


def render_source_panel(tables, missing, related):
    escape = html.escape
    def cell(value):
        return '<td><em>NULL</em></td>' if value is None else '<td>'+escape(str(value))+'</td>'

    def render_table(columns, rows):
        heads = ''.join('<th>'+escape(col)+'</th>' for col in columns)
        body = ''.join('<tr>'+''.join(cell(v) for v in row)+'</tr>' for row in rows)
        return '<div class="source-scroll"><table><thead><tr>'+heads+'</tr></thead><tbody>'+body+'</tbody></table></div>'

    out = ['<h4>Original tables</h4><p>First 3 matched rows per table, in Gold log order. Matching uses event ID, activity and timestamp.</p>']
    if missing:
        out.append(f'<p>{missing} Gold event rows have no matched source row.</p>')
    for table, columns, rows in tables:
        def table_html(records):
            return render_table([*columns, 'Gold event · timestamp column · case'], (
                [*values, ' | '.join(
                    f'{eid} · {activity} · {stamp_col} · {case}'
                    for eid, activity, stamp_col, case in events
                )]
                for values, events in records
            ))

        out.append(f'<p><strong><code>{escape(table)}</code></strong> · {len(rows)} source rows</p>')
        out.append(table_html(rows[:3]))
        if len(rows) > 3:
            out.append(f'<details><summary>Remaining {len(rows)-3} source rows</summary>'+table_html(rows[3:])+'</details>')
    if related:
        out.append('<details><summary>FK-linked row examples for case and join context</summary>')
        for table, examples in sorted(related.items()):
            out.append('<p><strong>'+escape(table)+'</strong></p>')
            columns = list(examples[0][0])
            out.append(render_table([*columns, 'Join from'], (
                [*(row[col] for col in columns), child+' ('+', '.join(keys)+')']
                for row, child, keys in examples
            )))
        out.append('</details>')
    return ''.join(out)
