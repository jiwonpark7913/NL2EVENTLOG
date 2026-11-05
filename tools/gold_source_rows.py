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


def render_source_panel(tables, reads, missing, related, limit=None):
    escape = html.escape
    def cell(value):
        return '<td><em>NULL</em></td>' if value is None else '<td><code>'+escape(str(value))+'</code></td>'

    out = ['<h4>Original tables</h4><p>Rows matched by event ID, activity and timestamp using the authored source bindings.</p>']
    if missing:
        out.append(f'<p>{missing} Gold event rows have no matched source row.</p>')
    for table, columns, rows in tables:
        selected = []
        represented = set()
        for index, (_, labels) in enumerate(rows):
            activities = {label[1] for label in labels}
            if activities - represented:
                selected.append(index)
                represented.update(activities)
            if len(selected) == 3:
                break
        selected.extend(index for index in range(min(3,len(rows))) if index not in selected)
        selected = set(selected[:3])
        sample = [row for index,row in enumerate(rows) if index in selected]
        def table_html(records):
            heads = ''.join('<th>'+escape(col)+'</th>' for col in columns)
            body = ''.join('<tr>'+''.join(cell(v) for v in values)+cell(' | '.join(
                f'{eid} · {activity} · {stamp_col} · {case}' for eid, activity, stamp_col, case in events
            ))+'</tr>' for values, events in records)
            return '<div class="source-scroll"><table><thead><tr>'+heads+'<th>Gold event · timestamp column · case</th></tr></thead><tbody>'+body+'</tbody></table></div>'
        out.append(f'<p><strong><code>{escape(table)}</code></strong> · {len(rows)} source rows</p>')
        if limit is None:
            out.append(table_html(sample))
        else:
            for values, events in sample:
                out.append('<p>'+', '.join('<code>'+escape(c)+'</code> = '+escape(str(v) if v is not None else 'NULL') for c,v in zip(columns,values))+'<br>'+escape(' | '.join(f'{eid} · {activity} · {col} · {case}' for eid,activity,col,case in events))+'</p>')
        if len(rows) > 3 and limit is None:
            out.append(f'<details><summary>Remaining {len(rows)-3} source rows</summary>'+table_html([row for index,row in enumerate(rows) if index not in selected])+'</details>')
    if related:
        out.append('<details><summary>FK-linked row examples for case and join context</summary>')
        for table, examples in sorted(related.items()):
            out.append('<p><strong>'+escape(table)+'</strong></p>')
            for row, child, keys in examples:
                out.append('<p>'+escape(child+' ('+', '.join(keys)+')')+'<br>'+', '.join('<code>'+escape(k)+'</code> = '+escape(str(v) if v is not None else 'NULL') for k,v in row.items())+'</p>')
        out.append('</details>')
    others = {table: cols for table, cols in reads.items() if table not in {t[0] for t in tables}}
    if others:
        out.append('<details><summary>Other tables referenced by Gold SQL</summary><p>Includes case joins and branches of shared CTEs.</p><ul>')
        for table, cols in sorted(others.items()):
            out.append('<li><code>'+escape(table)+'</code> · '+escape(', '.join(sorted(c for c in cols if c)))+'</li>')
        out.append('</ul></details>')
    return ''.join(out)
