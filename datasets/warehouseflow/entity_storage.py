"""Reproducible optional worker attributes using a second, explicit identifier."""
from pathlib import Path
import json
import sqlite3

DDL = '''CREATE TABLE IF NOT EXISTS worker_contact(
    staff_no TEXT PRIMARY KEY NOT NULL REFERENCES worker(payroll_no),
    contact_channel TEXT NOT NULL
)'''

def apply(base):
    base = Path(base)
    con = sqlite3.connect(base / 'input/database.sqlite')
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    if 'payroll_no' not in {r['name'] for r in con.execute('PRAGMA table_info(worker)')}:
        con.execute('ALTER TABLE worker ADD COLUMN payroll_no TEXT')
    # The unique index is required for the alternate-key FK, including on a rebuilt DB.
    con.execute('CREATE UNIQUE INDEX IF NOT EXISTS ux_worker_payroll_no ON worker(payroll_no)')
    workers = [r[0] for r in con.execute('SELECT worker_id FROM worker ORDER BY worker_id')]
    for i, key in enumerate(workers, 1):
        con.execute('UPDATE worker SET payroll_no=? WHERE worker_id=? AND payroll_no IS NULL',
                    ('PAY-' + str(1000 + i), key))
    con.execute(DDL)
    for key in workers[::2][:3]:
        con.execute('INSERT OR IGNORE INTO worker_contact SELECT payroll_no, ? FROM worker WHERE worker_id=?',
                    ('internal messaging', key))
    assert not list(con.execute('PRAGMA foreign_key_check'))
    con.commit()

    path = base / 'input/data_dictionary.json'
    d = json.loads(path.read_text())
    d['name'] = 'WarehouseFlow'
    worker = next(t for t in d['tables'] if t['table'] == 'worker')
    if not any(c['name'] == 'payroll_no' for c in worker['columns']):
        worker['columns'].append(dict(name='payroll_no', sql_type='TEXT',
            definition='Unique payroll identifier for the same worker identified by worker_id in this row. Values differ from local worker IDs. NULL means no payroll identifier is recorded.',
            required=False, primary_key_position=0, default=None, foreign_keys=[], unit=None))
    worker['sql_definition'] = con.execute("SELECT sql FROM sqlite_master WHERE name='worker'").fetchone()[0]
    contact = dict(table='worker_contact',
        definition='Optional contact attributes of an existing worker, identified by the payroll number. A row describes that worker, not a separate contact entity. Absence of a row means no contact attributes are stored.',
        columns=[dict(name='staff_no', sql_type='TEXT',
            definition='Payroll identifier of the worker described here. References worker.payroll_no; resolve worker_id through that row rather than comparing staff_no with worker_id.',
            required=True, primary_key_position=1, default=None,
            foreign_keys=[dict(table='worker', column='payroll_no', constraint_id=0, position=0)], unit=None),
            dict(name='contact_channel', sql_type='TEXT', definition='Synthetic preferred communication channel; no separate entity identifier.',
            required=True, primary_key_position=0, default=None, foreign_keys=[], unit=None)],
        primary_key=['staff_no'], sql_definition=con.execute("SELECT sql FROM sqlite_master WHERE name='worker_contact'").fetchone()[0])
    d['tables'] = [t for t in d['tables'] if t['table'] != 'worker_contact'] + [contact]
    path.write_text(json.dumps(d, indent=2) + '\n')
    schema = '\n'.join(r[0] + ';' for r in con.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY CASE type WHEN 'table' THEN 0 WHEN 'index' THEN 1 ELSE 2 END,name")) + '\n'
    (base / 'evaluation/schema.sql').write_text('PRAGMA foreign_keys=ON;\n' + schema)
    if (base / 'input/schema.sql').exists():
        (base / 'input/schema.sql').write_text('PRAGMA foreign_keys=ON;\n' + schema)

    # Render ordinary metadata and all table/FK nodes from the actual updated database.
    import runpy
    shared = runpy.run_path(str(base.parent / 'plateflow/documentation.py'))
    input_md = base / 'input/data_dictionary.md'
    had_input_md = input_md.exists()
    shared['render_dictionary'](base, con, d)
    if not had_input_md:
        input_md.unlink()
    for csv_path in (base / 'docs').glob('*.csv'):
        if csv_path.name in {'data_dictionary.csv', 'table_definitions.csv'}:
            csv_path.write_text(csv_path.read_text())
    shared['diagram'](base, con, d, order=[['warehouse','goods','worker'],
        ['worker_contact','receiving_request','work_code'],
        ['dispatch_order','goods_receipt','request_action'],
        ['warehouse_audit','goods_movement','warehouse_task_history'],['handling_history']])
    report_path = base / 'validation_report.json'
    report = json.loads(report_path.read_text())
    report['table_rows']['worker_contact'] = con.execute('SELECT COUNT(*) FROM worker_contact').fetchone()[0]
    report['entity_storage_extension'] = dict(optional_worker_attributes=True, new_events=0,
        key_mapping='worker_contact.staff_no -> worker.payroll_no -> worker.worker_id',
        note='Same Worker type and instances; contact rows add attributes, not cases or events.')
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    con.close()

if __name__ == '__main__':
    apply(Path(__file__).resolve().parent)
