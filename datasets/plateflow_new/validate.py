"""Validate persisted dataset and input boundary; no trained detector is executed."""
from pathlib import Path
from collections import Counter,defaultdict
import csv,json,sqlite3,re,hashlib,sys
P=Path(__file__).resolve().parent
load=lambda n:json.loads((P/n).read_text())
lines=lambda n:[json.loads(x) for x in (P/n).read_text().splitlines()]

def main():
 con=sqlite3.connect(P/'input/database.sqlite');con.row_factory=sqlite3.Row;con.execute('PRAGMA foreign_keys=ON')
 assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert not list(con.execute('PRAGMA foreign_key_check'))
 blank=sqlite3.connect(':memory:');blank.executescript((P/'input/schema.sql').read_text());assert list(blank.execute('SELECT type,name,sql FROM sqlite_master ORDER BY type,name'))==[tuple(r) for r in con.execute('SELECT type,name,sql FROM sqlite_master ORDER BY type,name')]
 tables={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")};assert len(tables)==12;assert not tables&{'event','object','object_type','case_event','lifecycle_case_link'}
 dictionary=load('input/data_dictionary.json');assert {t['table'] for t in dictionary['tables']}==tables
 forbidden_keys={'event_encoding','encoding_detail','carrier','carrier_column','activity_carrier','is_event_table','event_table','used_as_event_time','event_timestamp_columns','activity_sources','event_bindings','compiled_sql','row_filter','object_activity_design','timestamp_summary'}
 def inspect(value):
  if isinstance(value,dict):
   assert not forbidden_keys&set(value),forbidden_keys&set(value)
   for v in value.values():inspect(v)
  elif isinstance(value,list):
   for v in value:inspect(v)
 inspect(dictionary)
 banned=re.compile(r'row[ _-]+encod|column[ _-]+encod|mixed[ _-]+encod|carrier|is_event_table|used_as_event_time|event_timestamp_columns|event_bindings|compiled_sql',re.I)
 dictionary_files=['input/data_dictionary.json','input/data_dictionary.md','docs/data_dictionary.md','docs/data_dictionary.csv','docs/table_definitions.csv','docs/dictionary_basic_information.json']
 for path in dictionary_files:assert not banned.search((P/path).read_text()),path
 for t in dictionary['tables']:
  info=list(con.execute('PRAGMA table_info('+t['table']+')'));assert [r['name'] for r in info]==[c['name'] for c in t['columns']]
  for c,r in zip(t['columns'],info):assert c['sql_type']==r['type'] and c['primary_key_position']==r['pk'] and c['required']==bool(r['notnull'] or r['pk'])
 assert (P/'input/data_dictionary.md').read_bytes()==(P/'docs/data_dictionary.md').read_bytes()
 manifest=load('input/model_input_manifest.json');assert set(manifest['paths'])=={'input/database.sqlite','input/schema.sql','input/data_dictionary.json','input/task_context.md','input/model_questions.jsonl'}
 assert all((P/f).is_file() and not f.startswith(('private/','docs/','source/','design/')) for f in manifest['paths'])
 for path in manifest['paths']:
  if path.endswith('.sqlite'):continue
  assert not banned.search((P/path).read_text()),path
 questions=lines('private/questions.jsonl');gold=lines('private/gold.jsonl');qm={q['question_id']:q for q in questions};gm={g['question_id']:g for g in gold};model=lines('input/model_questions.jsonl');assert all(set(q)=={'question_id','text'} for q in model);assert {q['question_id']:q['text'] for q in model}=={q['question_id']:q['text'] for q in questions}
 history=lines('private/canonical_history.jsonl');hist={e['event_id']:e for e in history};assert len(history)==len(hist)==620
 links=defaultdict(set)
 for r in load('private/object_event_links.json'):assert r['event_id'] in hist;links[r['event_id']].add((r['case_concept'],r['case_id']))
 pops=load('private/case_population.json');catalog={c['case_concept']:c for c in load('private/task_scope_catalog.json')['views']};results={}
 for g in gold:
  q=qm[g['question_id']];pair=qm[q['pair_of']];assert pair['pair_of']==q['question_id'];assert {q['question_type'],pair['question_type']} in [{'Q1','Q2'},{'Q3','Q4'}];assert g['es']==gm[q['pair_of']]['es'];assert q['answerability']==pair['answerability'];assert q['requested_activity_count']==pair['requested_activity_count']
  if g['answerability']!='answerable':assert g['es'] is None and not (P/'private/gold_logs'/str(q['question_id']+'.csv')).exists();continue
  view=q['case_concept'];es=g['es'];assert set(es['case_population'])==set(pops[view]);actual=[dict(r) for r in con.execute((P/g['sql']).read_text())];expected=list(csv.DictReader((P/g['csv']).open()));assert actual==expected
  oracle=sorted([dict(event_id=e['event_id'],case_id=cid,activity=e['activity'],timestamp=e['timestamp']) for e in history if e['activity'] in es['activities'] for v,cid in links[e['event_id']] if v==view],key=lambda e:(e['case_id'],e['timestamp'],e['event_id']))
  assert actual==oracle,q['question_id'];assert len({(e['case_id'],e['event_id']) for e in actual})==len(actual);assert len({e['activity'] for e in actual})==q['extractable_activity_count'];results[q['question_id']]=actual
  if q['question_type'] in ['Q3','Q4']:assert es['activities']==catalog[view]['activities']
 for q in questions:
  if q['answerability']=='answerable':assert results[q['question_id']]==results[q['pair_of']]
 assert Counter(q['question_type'] for q in questions)=={'Q1':16,'Q2':16,'Q3':11,'Q4':11};assert len(results)==50
 assert len(list((P/'private/gold_logs').glob('*.csv')))==len(results)
 # Every event refers to a real complete physical source row, with the exact chosen completion/milestone time.
 from build import ENCODING,VIEWS
 expected_selection={('slab_material','Slab Received'):'received_at',('slab_material','Slab Verified'):'verified_at',('slab_material','Slab Released'):'released_at',('planned_rolling_instruction','Rolling Plan Submitted'):'submitted_at',('planned_rolling_instruction','Rolling Plan Approved'):'approved_at',('planned_rolling_instruction','Rolling Plan Released'):'released_at',('rolling_instruction','Rolling Instruction Issued'):'issued_at',('plate_material','Plate Identified'):'identified_at',('plate_material','Plate Released'):'released_at',('plate_material','Plate Packed'):'packed_at',('dimension_inspection','Dimensional Inspection Completed'):'inspected_at',('plate_quality_review','Plate Quality Review Completed'):'finished_at'}
 expected_codes={'furnace_operation_history':{'CH':'Furnace Charged','HT':'Heating Completed','DS':'Furnace Discharged'},'rolling_operation_history':{'RR':'Rough Rolling Completed','FR':'Finish Rolling Completed'},'finishing_operation_history':{'LEV':'Leveling Completed','HT':'Heat Treatment Completed','SF':'Surface Finishing Completed'}}
 for e in history:
  t=e['source_table'];pk=next(r['name'] for r in con.execute('PRAGMA table_info('+t+')') if r['pk']);row=con.execute('SELECT * FROM '+t+' WHERE '+pk+'=?',(e['source_key'],)).fetchone();assert row is not None
  if t in expected_codes:
   c='phase_code' if t=='rolling_operation_history' else 'operation_code';assert e['activity']==expected_codes[t][row[c]];assert row['finished_at']==e['timestamp'];assert row['started_at']<row['finished_at']
  else:assert row[expected_selection[(t,e['activity'])]]==e['timestamp']
 # Verify author table answers and edge cases, not predictions of the separate model.
 assert Counter(v[0] for v in ENCODING.values())=={'Row':3,'Column':6,'No business events':3}
 readme=(P/'README.md').read_text();answer_rows=[line for line in readme.splitlines() if line.startswith('| ') and any(line.startswith('| '+t+' |') for t in tables)];assert len(answer_rows)==12
 for t,(kind,col) in ENCODING.items():assert any(line.startswith('| '+t+' | '+kind+' | '+(col or '—')+' |') for line in answer_rows)
 assert len(list(con.execute('PRAGMA table_info(rolling_instruction)')))==3
 assert ENCODING['rolling_instruction']==('Column',None);assert ENCODING['dimension_inspection']==('Column',None);assert ENCODING['plate_quality_review']==('Column',None)
 assert {r[0] for r in con.execute('SELECT DISTINCT result_code FROM dimension_inspection')}=={'PASS','FAIL'}
 assert {e['activity'] for e in history if e['source_table']=='dimension_inspection'}=={'Dimensional Inspection Completed'}
 assert {r[0] for r in con.execute('SELECT DISTINCT review_status FROM plate_quality_review')}=={'APPROVED','REWORK','PENDING'}
 assert {e['activity'] for e in history if e['source_table']=='plate_quality_review'}=={'Plate Quality Review Completed'}
 assert {e['activity'] for e in results['N11']}=={'Heating Completed','Heat Treatment Completed'}
 assert all(e['source_table'] not in ['as_rolled_material','process_code','equipment'] for e in history)
 assert not any(e['activity'].endswith('Started') for e in history)
 for t in expected_codes:
  rows=list(con.execute('SELECT * FROM '+t));actual={e['source_key'] for e in history if e['source_table']==t};assert actual=={r['operation_id'] for r in rows if r['finished_at'] is not None}
  for r in rows:
   if r['finished_at'] is not None:assert r['started_at']<r['finished_at']
 # Repeat work and multiple records must survive; result/status values must not split activity kinds.
 assert con.execute("SELECT COUNT(*) FROM (SELECT plate_id FROM finishing_operation_history WHERE operation_code='HT' GROUP BY plate_id HAVING COUNT(*)>1)").fetchone()[0]>0
 assert con.execute('SELECT COUNT(*) FROM (SELECT plate_id FROM dimension_inspection GROUP BY plate_id HAVING COUNT(*)>1)').fetchone()[0]>0
 assert any(sum(r['activity']=='Heat Treatment Completed' for r in results['N06'] if r['case_id']==cid)>1 for cid in {r['case_id'] for r in results['N06']})
 for view in ['Furnace Operation Record','Rolling Operation Record','Finishing Operation Record']:
  t,key,prefix=VIEWS[view];eids={cid for eid in links for v,cid in links[eid] if v==view};assert eids=={prefix+r[0] for r in con.execute('SELECT '+key+' FROM '+t+' WHERE finished_at IS NOT NULL')}
 assert 'E:IDLE' in pops['Equipment'] and not any(e['case_id']=='E:IDLE' for e in results['NF08'])
 assert catalog['Mother Material']['cases_without_events']>0 and catalog['Quality Review']['cases_without_events']>0
 # Check geneaology independently of compiler routes.
 for e in history:
  associated=links[e['event_id']];pieces=[cid[2:] for v,cid in associated if v=='Plate Piece']
  for plate in pieces:
   r=con.execute('SELECT p.mother_material_id,m.slab_id,m.instruction_id FROM plate_material p JOIN as_rolled_material m ON m.material_id=p.mother_material_id WHERE p.plate_id=?',(plate,)).fetchone();assert ('Mother Material','M:'+r['mother_material_id']) in associated;assert ('Slab','S:'+r['slab_id']) in associated;assert ('Rolling Instruction','INST:'+r['instruction_id']) in associated
 for p in con.execute('SELECT * FROM plate_material'):
  if p['released_at'] is not None:
   approved=con.execute("SELECT MAX(finished_at) FROM plate_quality_review WHERE plate_id=? AND review_status='APPROVED'",(p['plate_id'],)).fetchone()[0];assert approved and approved<p['released_at'];assert not p['packed_at'] or p['released_at']<p['packed_at']
 inv=load('docs/timestamp_columns.json');sources=load('private/persistence_mapping.json');used={(s['table'],s['timestamp_column']) for s in sources};assert len(used)==15;assert inv['timestamp_columns']==24 and inv['event_timestamp_columns']==15;assert {(r['table'],r['column']) for r in inv['columns'] if r['used_as_event_time']}==used
 assert not any(s['timestamp_column'] in ['started_at','created_at','updated_at','planned_reheat_at'] for s in sources)
 # Keep every destructive probe inside one rolled-back outer transaction.
 con.execute('BEGIN')
 def reject(sql):
  con.execute('SAVEPOINT probe')
  try:con.execute(sql)
  except sqlite3.IntegrityError:pass
  else:raise AssertionError('Invalid row accepted')
  finally:con.execute('ROLLBACK TO probe');con.execute('RELEASE probe')
 reject("INSERT INTO rolling_instruction VALUES('BAD','MISSING','2026-01-01T00:00:00Z')")
 reject("UPDATE furnace_operation_history SET operation_code='FR' WHERE operation_id='0001'")
 reject("UPDATE plate_quality_review SET review_status='APPROVED',finished_at=NULL WHERE review_status='PENDING'")
 reject("UPDATE rolling_operation_history SET finished_at=started_at WHERE operation_id='0001'")
 con.rollback()
 seeds=load('source/question_seeds.json');par=load('source/llm_paraphrases.json');assert set(par['outputs'])=={s['id'] for s in seeds}
 for s in seeds:assert qm[s['id']]['text']==s['question'] and qm[s['id']+'P']['text']==par['outputs'][s['id']]
 for f in [P/'docs/questions.md']:
  rows=[r for r in f.read_text().splitlines() if r.startswith('|')];assert all(r.count('|')==rows[0].count('|') for r in rows[:5])
 report=load('validation_report.json');report['checks']=dict(gold_sql_csv_oracle_match=True,gold_csvs_verified=len(results),schema_round_trip=True,foreign_keys_and_checks=True,completion_only=True,group_qualified_codes=True,repeat_work_retained=True,outcomes_and_machine_codes_not_activities=True,source_keys_and_genealogy=True,empty_cases_retained=True,exact_frozen_question_pairs=True,dictionary_files_without_encoding_or_carrier_labels=len(dictionary_files),model_input_allowlist_checked=True,actual_llm_discovery_or_classification_run=False)
 (P/'validation_report.json').write_text(json.dumps(report,indent=2)+'\n');con.close();print('PlateFlow New: 12 tables; 620 events; 50 Gold logs; input-boundary, completion-only, codes, repeat work, genealogy and pair checks passed.')
if __name__=='__main__':main()
