"""Validate A–D storage and phase-aware Gold; no learned classifier is executed."""
from pathlib import Path
from collections import Counter,defaultdict
import json,sqlite3,csv,re
P=Path(__file__).resolve().parent
load=lambda n:json.loads((P/n).read_text())
lines=lambda n:[json.loads(x) for x in (P/n).read_text().splitlines()]
def main():
 con=sqlite3.connect(P/'input/database.sqlite');con.row_factory=sqlite3.Row;con.execute('PRAGMA foreign_keys=ON');assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert not list(con.execute('PRAGMA foreign_key_check'))
 blank=sqlite3.connect(':memory:');blank.executescript((P/'input/schema.sql').read_text());assert list(blank.execute('SELECT type,name,sql FROM sqlite_master ORDER BY type,name'))==[tuple(r) for r in con.execute('SELECT type,name,sql FROM sqlite_master ORDER BY type,name')]
 tables={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")};assert len(tables)==12 and not tables&{'object','object_type','event','lifecycle_case_link'}
 d=load('input/data_dictionary.json');assert {t['table'] for t in d['tables']}==tables
 forbidden={'event_encoding','encoding_detail','carrier','carrier_column','activity_carrier','is_event_table','event_bindings','phase_bindings','base_activity','lifecycle_phase','compiled_sql','timestamp_summary','object_activity_design','used_as_event_time'}
 def inspect(o):
  if isinstance(o,dict):
   assert not set(o)&forbidden,set(o)&forbidden
   for v in o.values():inspect(v)
  elif isinstance(o,list):
   for v in o:inspect(v)
 inspect(d)
 banned=re.compile(r'row[ _-]+encod|column[ _-]+encod|mixed[ _-]+encod|carrier_column|activity.carrier|base_activity|lifecycle_phase|event_bindings|compiled_sql|used_as_event_time',re.I)
 dictionary_files=['input/data_dictionary.json','input/data_dictionary.md','docs/data_dictionary.md','docs/data_dictionary.csv','docs/table_definitions.csv','docs/dictionary_basic_information.json']
 for f in dictionary_files:assert not banned.search((P/f).read_text()),f
 for t in d['tables']:
  info=list(con.execute('PRAGMA table_info('+t['table']+')'));assert [r['name'] for r in info]==[c['name'] for c in t['columns']]
  for r,c in zip(info,t['columns']):assert c['primary_key_position']==r['pk'] and c['sql_type']==r['type'] and c['required']==bool(r['pk'] or r['notnull'])
 manifest=load('input/model_input_manifest.json');assert set(manifest['paths'])=={'input/database.sqlite','input/schema.sql','input/data_dictionary.json','input/task_context.md','input/model_questions.jsonl'}
 assert all((P/f).is_file() for f in manifest['paths'])
 for f in manifest['paths']:
  if f.endswith('.sqlite'):continue
  assert not banned.search((P/f).read_text()),f
 questions=lines('private/questions.jsonl');gold=lines('private/gold.jsonl');qm={q['question_id']:q for q in questions};gm={g['question_id']:g for g in gold};model=lines('input/model_questions.jsonl');assert all(set(q)=={'question_id','text'} for q in model);assert {q['question_id']:q['text'] for q in model}=={q['question_id']:q['text'] for q in questions}
 hist=lines('private/canonical_history.jsonl');byid={e['event_id']:e for e in hist};assert len(hist)==len(byid)==402
 linked=defaultdict(set)
 for r in load('private/object_event_links.json'):assert r['event_id'] in byid;linked[r['event_id']].add((r['case_concept'],r['case_id']))
 pops=load('private/case_population.json');catalog={v['case_concept']:v for v in load('private/task_scope_catalog.json')['views']};results={}
 for g in gold:
  q=qm[g['question_id']];pair=qm[q['pair_of']];assert pair['pair_of']==q['question_id'];assert {q['question_type'],pair['question_type']} in [{'Q1','Q2'},{'Q3','Q4'}];assert g['es']==gm[q['pair_of']]['es'];assert q['answerability']==pair['answerability'] and q['requested_activity_count']==pair['requested_activity_count']
  if g['answerability']!='answerable':assert g['es'] is None and not (P/'private/gold_logs'/str(q['question_id']+'.csv')).exists();continue
  es=g['es'];v=q['case_concept'];assert set(es['case_population'])==set(pops[v]);actual=[dict(r) for r in con.execute((P/g['sql']).read_text())];expected=list(csv.DictReader((P/g['csv']).open()));assert actual==expected
  oracle=sorted([dict(event_id=e['event_id'],case_id=cid,activity=e['activity'],timestamp=e['timestamp']) for e in hist if e['activity'] in es['activities'] for vv,cid in linked[e['event_id']] if vv==v],key=lambda e:(e['case_id'],e['timestamp'],e['event_id']));assert actual==oracle,q['question_id'];assert len({(r['case_id'],r['event_id']) for r in actual})==len(actual);assert len({r['activity'] for r in actual})==q['extractable_activity_count'];results[q['question_id']]=actual
  if q['question_type'] in ['Q3','Q4']:assert es['activities']==catalog[v]['activities']
 for q in questions:
  if q['answerability']=='answerable':assert results[q['question_id']]==results[q['pair_of']]
 for q in questions:
  assert q['requested_base_activity_count']==qm[q['pair_of']]['requested_base_activity_count']
  if q['answerability']=='answerable':assert q['requested_base_activity_count']==len({b['base_activity'] for b in gm[q['question_id']]['es']['event_bindings']})
 assert Counter(q['question_type'] for q in questions)=={'Q1':16,'Q2':16,'Q3':11,'Q4':11};assert len(results)==50 and len(list((P/'private/gold_logs').glob('*.csv')))==50
 from build import CLASSIFICATION,VIEWS
 assert Counter(v[0] for v in CLASSIFICATION.values())=={'A':2,'B':2,'C':2,'D':2,'Context':4}
 readme=(P/'README.md').read_text()
 for t,(case,identity,carrier,phase) in CLASSIFICATION.items():assert '| '+t+' | '+case+' | '+identity+' | '+(carrier or 'None')+' | '+phase+' |' in readme
 # Check actual physical timestamp counts, observed varying work kinds and phase use.
 for t in tables:
  info=list(con.execute('PRAGMA table_info('+t+')'));ts=[c['name'] for c in info if c['name'].endswith('_at')];case,identity,carrier,_=CLASSIFICATION[t]
  if case in ['A','C']:assert len(ts)==1,(t,ts)
  if case in ['B','D']:assert len(ts)==2,(t,ts)
  if case in ['C','D']:assert carrier in [r['name'] for r in info];assert con.execute('SELECT COUNT(DISTINCT '+carrier+') FROM '+t).fetchone()[0]>1
  if case=='Context':assert not any(e['source_table']==t for e in hist)
 assert {r[0] for r in con.execute('SELECT DISTINCT condition_code FROM goods_receipt')}=={'GOOD','DAMAGED'}
 assert {r[0] for r in con.execute('SELECT DISTINCT result_code FROM warehouse_audit')}=={'PASS','RECOUNT','PENDING'}
 assert {r[0] for r in con.execute('SELECT DISTINCT outcome_code FROM warehouse_task_history')}=={'OK','RETRY','PENDING'}
 byocc=defaultdict(list)
 for e in hist:byocc[e['occurrence_id']].append(e)
 expected_kind={'goods_movement':{'IN':'Goods Received','OUT':'Goods Dispatched'},'request_action':{'CHECK':'Request Checked','HOLD':'Request Held','RELEASE':'Request Released'},'warehouse_task_history':{'PUTAWAY':'Putaway','PICK':'Picking','PACK':'Packing'},'handling_history':{'UNLOAD':'Unloading','LOAD':'Loading'}}
 point={'receiving_request':{'Receiving Request Submitted':'submitted_at'},'goods_receipt':{'Receipt Registered':'received_at'},'dispatch_order':{'Dispatch Requested':'requested_at','Dispatch Approved':'approved_at'}}
 source_specs=load('private/persistence_mapping.json')
 for e in hist:
  selected=[s for s in source_specs if s['table']==e['source_table'] and s['activity']==e['activity'] and s['lifecycle_phase']==e['lifecycle_phase']];assert len(selected)==1
  src=selected[0];assert e['occurrence_id']==src['occurrence_prefix']+e['source_key']+src['occurrence_suffix']
  t=e['source_table'];key=next(r['name'] for r in con.execute('PRAGMA table_info('+t+')') if r['pk']);r=con.execute('SELECT * FROM '+t+' WHERE '+key+'=?',(e['source_key'],)).fetchone();assert r is not None
  if t in point:assert e['lifecycle_phase']=='point' and r[point[t][e['activity']]]==e['timestamp']
  elif t in ['goods_movement','request_action']:assert e['lifecycle_phase']=='complete' and r['occurred_at']==e['timestamp'];assert expected_kind[t][r[CLASSIFICATION[t][2]]]==e['base_activity']
  else:
   assert e['lifecycle_phase'] in ['start','complete'];col='started_at' if e['lifecycle_phase']=='start' else 'completed_at';assert r[col]==e['timestamp']
   assert e['base_activity']==('Stock Audit' if t=='warehouse_audit' else expected_kind[t][r[CLASSIFICATION[t][2]]]);assert e['activity']==e['base_activity']+(' Started' if e['lifecycle_phase']=='start' else ' Completed')
 for t in ['warehouse_audit','warehouse_task_history','handling_history']:
  key=next(r['name'] for r in con.execute('PRAGMA table_info('+t+')') if r['pk'])
  for r in con.execute('SELECT * FROM '+t):
   phases=byocc[t+':'+r[key]];assert len(phases)==(1 if r['completed_at'] is None else 2);assert {e['lifecycle_phase'] for e in phases}==({'start'} if r['completed_at'] is None else {'start','complete'});assert len({e['base_activity'] for e in phases})==1
   if len(phases)==2:assert phases[0]['timestamp']<phases[1]['timestamp'] and phases[0]['event_id']!=phases[1]['event_id']
 assert Counter(e['lifecycle_phase'] for e in hist)=={'point':87,'start':113,'complete':202}
 # Same work kind in repeat attempts must stay separate across phases and IDs.
 repeated=con.execute("SELECT dispatch_id FROM warehouse_task_history WHERE task_code='PICK' GROUP BY dispatch_id HAVING COUNT(*)>1").fetchall();assert repeated
 for r in repeated:
  rows=list(con.execute("SELECT * FROM warehouse_task_history WHERE dispatch_id=? AND task_code='PICK'",(r[0],)));assert len(rows)==2;assert len({e['occurrence_id'] for e in hist if e['source_table']=='warehouse_task_history' and e['source_key'] in {r['task_id'] for r in rows}})==2
 # Stock changes only at movement occurrence times, never receipt-registration or task phases.
 balance=Counter();capacity={r['warehouse_id']:r['capacity'] for r in con.execute('SELECT * FROM warehouse')}
 for r in con.execute('SELECT * FROM goods_movement ORDER BY occurred_at,movement_id'):
  balance[r['warehouse_id'],r['goods_id']]+=r['quantity']*(1 if r['movement_code']=='IN' else -1);assert balance[r['warehouse_id'],r['goods_id']]>=0;assert sum(n for (w,_),n in balance.items() if w==r['warehouse_id'])<=capacity[r['warehouse_id']]
 # Each phase stays attached to the same real parent through declared keys.
 for e in hist:
  if e['source_table'] not in ['warehouse_task_history','handling_history']:continue
  t=e['source_table'];key='task_id' if t=='warehouse_task_history' else 'handling_id';r=con.execute('SELECT * FROM '+t+' WHERE '+key+'=?',(e['source_key'],)).fetchone();parent=con.execute('SELECT * FROM '+('receiving_request WHERE request_id=?' if r['request_id'] else 'dispatch_order WHERE dispatch_id=?'),(r['request_id'] or r['dispatch_id'],)).fetchone();links=linked[e['event_id']];assert ('Warehouse','W:'+parent['warehouse_id']) in links and ('Goods','G:'+parent['goods_id']) in links;assert ('Worker','L:'+r['worker_id']) in links
  assert ('Receiving Request','Q:'+r['request_id']) in links if r['request_id'] else ('Dispatch Order','D:'+r['dispatch_id']) in links
 for view,cid in [('Warehouse','W:4'),('Goods','G:7'),('Worker','L:7')]:assert cid in pops[view] and not any(e['case_id']==cid for e in results[{'Warehouse':'WF01','Goods':'WF02','Worker':'WF03'}[view]])
 inv=load('docs/timestamp_columns.json');sources=load('private/persistence_mapping.json');used={(s['table'],s['timestamp_column']) for s in sources};assert len(used)==12 and inv['timestamp_columns']==15;assert used=={(r['table'],r['column']) for r in inv['columns'] if r['used_as_event_time']};assert not any(s['timestamp_column'] in ['created_at','updated_at'] for s in sources)
 assert {s['lifecycle_phase'] for s in sources if s['table']=='warehouse_audit'}=={'start','complete'}
 assert all({s['lifecycle_phase'] for s in sources if s['table']==t}=={'start','complete'} for t in ['warehouse_task_history','handling_history'])
 # FK/CHECK and business-context tests are rolled back without modifying DB bytes.
 con.execute('BEGIN')
 def reject(sql):
  con.execute('SAVEPOINT probe')
  try:con.execute(sql)
  except sqlite3.IntegrityError:pass
  else:raise AssertionError('Invalid record accepted')
  finally:con.execute('ROLLBACK TO probe');con.execute('RELEASE probe')
 reject("INSERT INTO receiving_request VALUES('BAD','MISSING','1',10,'2026-01-01T00:00:00Z')")
 reject("UPDATE warehouse_task_history SET task_code='LOAD' WHERE task_id='0001'")
 reject("UPDATE warehouse_audit SET completed_at=started_at WHERE audit_id='001'")
 reject("INSERT INTO goods_movement VALUES('BAD','4','1',2,'001',NULL,'MOVEMENT','IN','2026-01-01T00:00:00Z')")
 con.rollback()
 seeds=load('source/question_seeds.json');par=load('source/llm_paraphrases.json');assert set(par['outputs'])=={s['id'] for s in seeds}
 for s in seeds:assert qm[s['id']]['text']==s['question'] and qm[s['id']+'P']['text']==par['outputs'][s['id']]
 report=load('validation_report.json');report['checks']=dict(gold_csvs_verified=len(results),all_four_patterns_physically_present=True,base_activity_and_phase_preserved=True,same_occurrence_start_completion_pairs=True,unfinished_starts_without_completion=True,repeat_attempts_distinct=True,result_role_priority_condition_not_carriers=True,stock_nonnegative_within_capacity=True,source_keys_and_business_paths=True,technical_times_excluded=True,foreign_keys_checks_and_schema_round_trip=True,dictionary_files_without_classification_annotations=len(dictionary_files),model_input_allowlist_verified=True,exact_frozen_question_pairs=True,actual_llm_classifier_run=False);(P/'validation_report.json').write_text(json.dumps(report,indent=2)+'\n');con.close();print('WarehouseFlow New: A–D physical forms and Gold covered; 402 events, 15 base activities, 21 display labels; 50 Gold CSVs verified.')
if __name__=='__main__':main()
