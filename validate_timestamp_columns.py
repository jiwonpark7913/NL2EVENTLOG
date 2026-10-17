"""Validate timestamp storage, generated questions and branch-aware time order."""
import json,csv,sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parent
for p in (ROOT/'datasets').iterdir():
 con=sqlite3.connect(p/'input/database.sqlite');con.row_factory=sqlite3.Row;inv=json.loads((p/'docs/timestamp_columns.json').read_text());assert inv['timestamp_columns']==len({(x['table'],x['column']) for x in inv['columns']})
 questions=[json.loads(l) for l in (p/'input/questions.jsonl').read_text().splitlines()];gs={g['question_id']:g for g in map(json.loads,(p/'private/gold.jsonl').read_text().splitlines())}
 for q in questions:
  if not q['question_id'].startswith('TS'):continue
  g=gs[q['question_id']];events=list(csv.DictReader((p/'private/gold_logs'/(q['question_id']+'.csv')).open()));assert {e['activity'] for e in events}==set(g['process_view']['activities'])
  history={e['event_id']:e for e in map(json.loads,(p/'private/canonical_history.jsonl').read_text().splitlines())};links=json.loads((p/'private/object_event_links.json').read_text())[g['process_view']['case_table']];expected=sorted([dict(e,case_id=cid) for eid,e in history.items() if e['activity'] in g['process_view']['activities'] for cid in links.get(eid,[])],key=lambda e:(e['case_id'],e['timestamp'],e['event_id']));assert events==expected

 if p.name in ['warehouseflow','universityflow']:
  mapping=json.loads((p/'design/timestamp_column_mapping.json').read_text())
  for m in mapping['migrated_columns']:
   assert con.execute('SELECT COUNT('+m['column']+') FROM '+m['table']).fetchone()[0]==len(m['preserved_event_ids'])
   if m['old_table'] not in mapping['removed_empty_history_tables']:assert con.execute('SELECT COUNT(*) FROM '+m['old_table']+' WHERE activity=?',(m['activity'],)).fetchone()[0]==0
 if p.name=='plateflow':
  for r in con.execute('SELECT * FROM plate_material'):
   if r['plate_quality_review_started_at']:assert r['plate_quality_review_started_at']<r['plate_quality_released_at']
   if r['plate_packing_started_at']:assert r['plate_quality_released_at']<r['plate_packing_started_at']<r['plate_packed_at']
 print(p.name,inv['timestamp_columns'],'timestamps;',inv['event_timestamp_columns'],'event sources; milestone questions and time order passed')
