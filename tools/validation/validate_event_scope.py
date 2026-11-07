"""Audit authored extraction bindings against the restricted event-table contract.

This is a benchmark consistency check, not a learned carrier detector. Keep the
explicit author answers here, outside every model-input allowlist.
"""
import csv
import importlib.util
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# One activity-selecting column per carrier table. Other codes are attributes.
CARRIERS = {
    'warehouseflow': {'transaction_record': 'transaction_type', 'transaction_record_activity': 'activity'},
    'universityflow': {'assignment_grading': 'grading_kind'},
    'plateflow': {'material_operation_history': 'operation_code'},
    'hospitalflow': {'order_history': 'action', 'emar': 'event_txt'},
    'plateflow_new': {'furnace_operation_history': 'operation_code', 'rolling_operation_history': 'phase_code', 'finishing_operation_history': 'operation_code'},
    'warehouseflow_new': {'goods_movement': 'movement_code', 'request_action': 'action_code', 'warehouse_task_history': 'task_code', 'handling_history': 'handling_code'},
}
# Generic time names whose business meaning is supplied by their table.
TABLE_SEMANTICS = {
    ('hospitalflow', 'procedure_episode'),
    ('plateflow_new', 'rolling_instruction'), ('plateflow_new', 'dimension_inspection'), ('plateflow_new', 'plate_quality_review'),
    ('warehouseflow_new', 'goods_receipt'), ('warehouseflow_new', 'warehouse_audit'),
}

def lines(path):
    return [json.loads(s) for s in path.read_text().splitlines()]

def bindings(p):
    if p.name not in {'warehouseflow', 'universityflow', 'plateflow'}:
        return json.loads((p/'private/persistence_mapping.json').read_text())
    qid = {'warehouseflow': 'R05', 'universityflow': 'U05', 'plateflow': 'V05'}[p.name]
    es = next(g['es'] for g in lines(p/'private/gold.jsonl') if g['question_id'] == qid)
    spec = importlib.util.spec_from_file_location(p.name+'_scope_builder', p/'build.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    out = []
    for s in es['original_event_specification']['sources']:
        table = s.get('table', s.get('from_expression', '').split()[0] if s.get('from_expression') else None)
        timestamp = s.get('timestamp_column', s.get('timestamp_expression')).split('.')[-1]
        out.append(dict(table=table, timestamp_column=timestamp, event_sql=module.compile_es({'sources': [s]})))
    out.extend(es['activity_sources'])
    return out

def audit(p):
    con = sqlite3.connect(p/'input/database.sqlite')
    con.row_factory = sqlite3.Row
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert set(CARRIERS[p.name]) <= tables
    inventory = json.loads((p/'docs/timestamp_columns.json').read_text())
    physical_times = defaultdict(list)
    for column in inventory['columns']:
        physical_times[column['table']].append(column['column'])
    by_table = defaultdict(list)
    actual = {}
    for s in bindings(p):
        table, timestamp = s['table'], s['timestamp_column'].split('.')[-1]
        columns = {r['name'] for r in con.execute('PRAGMA table_info('+table+')')}
        assert timestamp in columns, ('cross-table timestamp', p.name, table, timestamp)
        sql = s['event_sql']
        carrier = CARRIERS[p.name].get(table)
        if carrier:
            assert carrier in columns
            # Every binding in a carrier table must use that carrier, including
            # constant-label CASE/WHERE branches. Independent milestones fail.
            assert re.search(r'\b'+carrier+r'\b', sql, re.I), ('mixed encoding', p.name, table, timestamp)
        rows = [dict(r) for r in con.execute(sql)]
        assert rows, ('empty authored binding needs manual review', p.name, table)
        by_table[table].append(dict(timestamp=timestamp, activities=sorted({r['activity'] for r in rows})))
        for r in rows:
            value = {k:r[k] for k in ('event_id','activity','timestamp')}
            assert r['event_id'] not in actual or actual[r['event_id']] == value
            actual[r['event_id']] = value
    history = {r['event_id']:{k:r[k] for k in ('event_id','activity','timestamp')} for r in lines(p/'private/canonical_history.jsonl')}
    assert actual == history, (p.name, 'source bindings differ from canonical history')
    result = []
    for table in sorted(tables):
        sources = by_table[table]
        times = sorted({s['timestamp'] for s in sources})
        carrier = CARRIERS[p.name].get(table)
        patterns = ['a' if len(physical_times[table])==1 else 'b'] if carrier else (['d'] if (p.name,table) in TABLE_SEMANTICS else ['c']) if sources else []
        # Constant code namespaces are context, not a second varying carrier.
        namespaces = {}
        for col in ('process_group','code_family'):
            if sources and col in {r['name'] for r in con.execute('PRAGMA table_info('+table+')')}:
                values = [r[0] for r in con.execute('SELECT DISTINCT '+col+' FROM '+table)]
                assert len(values)==1, ('composite namespace requires review',p.name,table)
                namespaces[col] = values[0]
        result.append(dict(table=table, pattern=patterns, carrier=carrier, selected_timestamp_columns=times, physical_timestamp_columns=sorted(physical_times[table]),
                           activities=sorted({a for s in sources for a in s['activities']}), constant_namespaces=namespaces))
    checked = 0
    for g in lines(p/'private/gold.jsonl'):
        if not g.get('answerable', g.get('answerability')=='answerable'):
            continue
        qid = g.get('question_id',g.get('id'))
        rows = [dict(r) for r in con.execute((p/'private/gold_sql'/f'{qid}.sql').read_text())]
        with (p/'private/gold_logs'/f'{qid}.csv').open() as f:
            assert rows == list(csv.DictReader(f)), (p.name,qid)
        assert len({(r['case_id'],r['event_id']) for r in rows}) == len(rows)
        for r in rows:
            assert {k:r[k] for k in ('event_id','activity','timestamp')} == history[r['event_id']]
        checked += 1
    con.close()
    return dict(dataset=p.name, tables=result, event_tables=sum(bool(v) for v in by_table.values()), events=len(actual), gold_logs_verified=checked)

def main():
    reports = [audit(ROOT/'datasets'/name) for name in CARRIERS]
    report = dict(scope='One local carrier column, or table/time-column semantics; no composite/multiple carriers, mixed encoding or split activity/time storage.',
                  method='Manual carrier contracts plus executable source-binding, canonical-history and Gold SQL/CSV checks. Not a general SQL semantic proof or model evaluation.',
                  table_count=sum(len(r['tables']) for r in reports), event_table_count=sum(r['event_tables'] for r in reports),
                  gold_logs_verified=sum(r['gold_logs_verified'] for r in reports), violations=[], datasets=reports)
    (ROOT/'docs/system/event_scope_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    doc = '# Event-table scope audit\n\n'
    doc += 'All six datasets are audited. (a) one physical timestamp column with one carrier; (b) multiple physical timestamp columns with one carrier; (c) activity from time-column meaning; (d) activity from table meaning. These are representative, non-exclusive patterns. The (a)/(b) distinction uses the physical timestamp inventory. Only selected business-event times produce events; plans, technical timestamps and snapshots may coexist without becoming activities. The selected-time column is listed separately below.\n\n'
    doc += '## Findings and repair\n\n'
    doc += '- **Structural violation:** WarehouseFlow.transaction_record combined transaction_type/occurred_at with four independently named lifecycle milestones (mixed encoding). The four authored milestone columns were removed; their 160 occurrences now remain in transaction_record_activity with activity/occurred_at. Both tables are now (a). The builder enforces this storage choice.\n'
    doc += '- **Annotation correction:** UniversityFlow.registration, degree_examination_result and student_simulation_experiment_result are non-carrier (c), although previous documentation called them mixed/row encoded. status, examination_name and result data do not select their activity labels. assignment_grading uses grading_kind and is (a). No UniversityFlow records or Gold events change.\n'
    doc += '- No additional composite-carrier, multiple-carrier or split activity/time violation was found in the authored extraction bindings. A composite PK is an occurrence identifier, not a composite activity carrier. process_group/code_family are fixed per history table, so one varying code determines the activity. Code-reference dictionaries decode codes; case-attribution JOINs do not split activity and time across event records. Descriptive procedure, medication, item, result and outcome fields are not carriers under the current activity definitions.\n'
    doc += '- Carrier interval start/completion phases remain allowed under (b). Non-carrier procedure episodes and audits use table meaning plus temporal phase under (d); they may also be described by (c). No extra independent carrier column is introduced.\n'
    doc += '- Gold ES/SQL were regenerated for the changed storage. Every pre-existing Gold CSV, question, canonical event and case membership was preserved. WarehouseFlow timestamp-column count falls from 6 to 2; event count remains 394 and activity count remains 10.\n\n'
    doc += '## Verification\n\n'+f'{report["table_count"]} physical tables; {report["event_table_count"]} event-source tables; {report["gold_logs_verified"]} Gold logs verified. Run `python validate_event_scope.py`. The explicit contracts are author annotations outside model-input manifests. This checks this benchmark and its current authored bindings; it is not a general detector or independent validation of business assumptions.\n\n'
    for r in reports:
        doc += '## '+r['dataset']+'\n\n| Table | Pattern | Carrier | Selected event times |\n|---|---|---|---|\n'
        for t in r['tables']:
            doc += '| '+t['table']+' | '+(', '.join(t['pattern']) or 'No selected events')+' | '+(t['carrier'] or '—')+' | '+(', '.join(t['selected_timestamp_columns']) or '—')+' |\n'
        doc += '\n'
    (ROOT/'docs/system/EVENT_TABLE_SCOPE.md').write_text(doc.rstrip()+'\n')
    print(json.dumps({k:report[k] for k in ('table_count','event_table_count','gold_logs_verified','violations')}))

if __name__=='__main__':
    main()
