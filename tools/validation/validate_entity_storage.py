"""Check live entity-storage examples and all stored Gold; no semantic judge."""
from pathlib import Path
import csv
import importlib.util
import json
import sqlite3
import tempfile
import shutil

ROOT=Path(__file__).resolve().parents[2]
def connect(base):
    con=sqlite3.connect('file:'+str(base/'input/database.sqlite')+'?mode=ro',uri=True)
    assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert not list(con.execute('PRAGMA foreign_key_check'))
    return con

def main():
    counts={}
    for name in ('universityflow','hospitalflow','warehouseflow','plateflow'):
        base=ROOT/'datasets'/name
        con=connect(base)
        d=json.loads((base/'input/data_dictionary.json').read_text())
        actual_tables={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        assert {t['table'] for t in d['tables']}==actual_tables
        for t in d['tables']:
            assert {c['name'] for c in t['columns']}=={r[1] for r in con.execute('PRAGMA table_info('+t['table']+')')}
        pairs=0
        for sql in sorted((base/'private/gold_sql').glob('*.sql')):
            path=base/'private/gold_logs'/(sql.stem+'.csv')
            with path.open(newline='') as f:
                reader=csv.reader(f); header=next(reader); expected=list(reader)
            cur=con.execute(sql.read_text())
            assert [x[0] for x in cur.description]==header
            actual=[['' if v is None else str(v) for v in r] for r in cur]
            assert actual==expected,(name,sql.stem)
            pairs+=1
        assert pairs>0
        counts[name]=dict(tables=len(actual_tables),gold_pairs=pairs)
        con.close()

    base=ROOT/'datasets/warehouseflow'; con=connect(base)
    assert con.execute('SELECT COUNT(*) FROM worker').fetchone()[0]==7
    assert con.execute('SELECT COUNT(*) FROM worker_contact').fetchone()[0]==3
    assert con.execute('SELECT COUNT(*) FROM worker_contact c JOIN worker w ON c.staff_no=w.payroll_no').fetchone()[0]==3
    assert con.execute('SELECT COUNT(*) FROM worker_contact c JOIN worker w ON c.staff_no=w.worker_id').fetchone()[0]==0
    assert con.execute('SELECT COUNT(*) FROM worker w LEFT JOIN worker_contact c ON c.staff_no=w.payroll_no WHERE c.staff_no IS NULL').fetchone()[0]==4
    assert con.execute('SELECT COUNT(*) FROM goods_receipt r JOIN worker w ON r.receiver_id=w.worker_id').fetchone()[0]==con.execute('SELECT COUNT(*) FROM goods_receipt').fetchone()[0]
    # These numerically equal keys identify related but distinct Request and Receipt entities.
    assert con.execute('SELECT COUNT(*) FROM goods_receipt WHERE receipt_id=request_id').fetchone()[0]>0
    blank=sqlite3.connect(':memory:'); blank.executescript((base/'evaluation/schema.sql').read_text())
    query="SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
    assert list(blank.execute(query))==list(con.execute(query))
    blank.close();con.close()
    u=connect(ROOT/'datasets/universityflow')
    assert u.execute('SELECT COUNT(*) FROM (SELECT student_id FROM registration GROUP BY student_id HAVING COUNT(*)>1)').fetchone()[0]>0
    assert u.execute('SELECT COUNT(*) FROM (SELECT assignment_id FROM assignment_grading GROUP BY assignment_id HAVING COUNT(*)>1)').fetchone()[0]>0
    u.close()
    h=connect(ROOT/'datasets/hospitalflow')
    assert h.execute('SELECT COUNT(*) FROM admission_detail d JOIN admissions a ON a.hadm_id=d.hadm_id').fetchone()[0]==h.execute('SELECT COUNT(*) FROM admission_detail').fetchone()[0]>0
    assert h.execute('SELECT COUNT(*) FROM lab_order l JOIN medication_order m ON l.order_id=m.order_id').fetchone()[0]>0
    h.close()
    # FK/uniqueness negative probes in memory, no modification of the live DB.
    live=connect(base); mem=sqlite3.connect(':memory:');live.backup(mem);live.close()
    mem.execute('PRAGMA foreign_keys=ON')
    for sql in ["INSERT INTO worker_contact VALUES('MISSING','x')", "UPDATE worker SET payroll_no='PAY-1001' WHERE worker_id='2'", "INSERT INTO worker_contact VALUES('PAY-1001','duplicate')"]:
        try:mem.execute(sql)
        except sqlite3.IntegrityError:pass
        else:raise AssertionError('Invalid identity accepted: '+sql)
        mem.rollback()
    mem.close()
    # Running the extension twice preserves every row and schema; operate on a temporary copy.
    spec=importlib.util.spec_from_file_location('entity_storage',base/'entity_storage.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as temp:
        parent=Path(temp); target=parent/'warehouseflow';shutil.copytree(base,target)
        (parent/'plateflow').mkdir();shutil.copy(ROOT/'datasets/plateflow/documentation.py',parent/'plateflow/documentation.py')
        def dump():
            c=sqlite3.connect(target/'input/database.sqlite');text='\n'.join(c.iterdump());c.close();return text
        before=dump(); module.apply(target); assert dump()==before
        module.apply(target); assert dump()==before
    print(json.dumps(dict(datasets=counts,storage_examples='passed',constraint_negatives='passed',extension_idempotence='passed'),indent=2))
if __name__=='__main__':main()
