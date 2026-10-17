"""Verify regenerated schemas, every Gold SQL/CSV, case identities and lifecycle order."""
import csv,json,sqlite3,hashlib,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
for name in ['warehouseflow','universityflow','plateflow']:
 p=ROOT/'datasets'/name;con=sqlite3.connect(p/'input/database.sqlite');con.row_factory=sqlite3.Row
 assert not list(con.execute('PRAGMA foreign_key_check'))
 assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 blank=sqlite3.connect(':memory:');blank.executescript((p/'input/schema.sql').read_text())
 assert {r[0] for r in blank.execute("SELECT name FROM sqlite_master WHERE type='table'")}=={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
 hist={x['event_id']:x for x in map(json.loads,(p/'private/canonical_history.jsonl').read_text().splitlines())};gold=list(map(json.loads,(p/'private/gold.jsonl').read_text().splitlines()));count=0
 for g in gold:
  if g['answerability']!='answerable':continue
  q=g['question_id'];sql=(p/'private/gold_sql'/f'{q}.sql').read_text();actual=[dict(r) for r in con.execute(sql)];expected=list(csv.DictReader((p/'private/gold_logs'/f'{q}.csv').open()))
  assert actual==expected,(name,q);assert len({(e['case_id'],e['event_id']) for e in actual})==len(actual)
  assert all(all(e[k]==hist[e['event_id']][k] for k in ['activity','timestamp']) for e in actual);count+=1
 for table in ({r['case_table'] for r in con.execute('SELECT DISTINCT case_table FROM lifecycle_case_link')} if name!='plateflow' else set()):
  pk=[r['name'] for r in sorted(con.execute('PRAGMA table_info('+table+')'),key=lambda r:r['pk']) if r['pk']];keys={':'.join(str(r[k]) for k in pk) for r in con.execute('SELECT * FROM '+table)}
  assert {r[0] for r in con.execute('SELECT case_id FROM lifecycle_case_link WHERE case_table=?',(table,))}<=keys
 if name!='plateflow':assert {r[0] for r in con.execute('SELECT event_id FROM lifecycle_case_link')}<=hist.keys()
 for table in [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_activity'")]:
  parent=table[:-9];pk=[r['name'] for r in sorted(con.execute('PRAGMA table_info('+parent+')'),key=lambda r:r['pk']) if r['pk']];groups={}
  for row in con.execute('SELECT * FROM '+table):groups.setdefault(tuple(row[k] for k in pk),[]).append(row)
  for rows in groups.values():assert len({r['occurred_at'] for r in rows})==len(rows)
 if name=='warehouseflow':
  for r in con.execute('SELECT * FROM transaction_record'):
   acts={x['activity']:x['occurred_at'] for x in con.execute('SELECT * FROM transaction_record_activity WHERE transaction_id=?',(r['transaction_id'],))};original=hist['TX:'+r['transaction_id']]
   if original['activity']=='Goods Received':assert r['receiving_scheduled_at']<original['timestamp']<acts['Receiving Inspection Completed']
   else:assert r['dispatch_approved_at']<acts['Goods Picked']<acts['Goods Packed']<original['timestamp']
 if name=='plateflow':
  for r in con.execute('SELECT * FROM furnace_charge_tracking'):
   acts={k:v for k,v in [('Furnace Discharge Confirmed',r['furnace_discharge_confirmed_at']),('Heating Completed',con.execute("SELECT completed_at FROM material_operation_history WHERE material_id=? AND operation_code='HF'",(r['material_id'],)).fetchone())] if v};acts['Heating Completed']=acts['Heating Completed'][0] if 'Heating Completed' in acts else None
   if 'Furnace Discharge Confirmed' in acts:
    times=[e['timestamp'] for e in hist.values() if e['case_id']==r['material_id'] and e['activity']=='Rolling Completed'];assert times and acts['Heating Completed']<acts['Furnace Discharge Confirmed']<times[0]
 print(name,':',count,'Gold logs verified; schemas, typed FKs, case links and stage ordering passed')
