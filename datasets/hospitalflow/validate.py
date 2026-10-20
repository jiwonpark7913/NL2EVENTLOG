"""Validate persisted HospitalFlow artifacts independently of the builder's SQL compiler."""
import json,csv,sqlite3,hashlib
from pathlib import Path
from collections import Counter,defaultdict
P=Path(__file__).resolve().parent
load=lambda n:json.loads((P/n).read_text())
lines=lambda n:[json.loads(x) for x in (P/n).read_text().splitlines()]
con=sqlite3.connect(P/'input/database.sqlite');con.row_factory=sqlite3.Row
assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
assert not list(con.execute('PRAGMA foreign_key_check'))
blank=sqlite3.connect(':memory:');blank.executescript((P/'input/schema.sql').read_text())
assert list(blank.execute("SELECT type,name,sql FROM sqlite_master ORDER BY type,name"))==[tuple(r) for r in con.execute("SELECT type,name,sql FROM sqlite_master ORDER BY type,name")]
questions=lines('input/questions.jsonl');gold=lines('private/gold.jsonl');qm={q['id']:q for q in questions};gm={g['id']:g for g in gold};events=lines('private/canonical_history.jsonl');hist={e['event_id']:e for e in events};assert len(hist)==len(events)
links=defaultdict(set)
for r in load('private/object_event_links.json'):links[r['event_id']].add(r['object_id'])
objects={r['object_id']:r['type_code'] for r in con.execute('SELECT * FROM object')};catalog={v['case_concept']:v for v in load('input/task_scope_catalog.json')['views']}
assert set(objects)==set.union(*(set(v['population']) for v in catalog.values()))
for typ,tbl in [('PATIENT','patients'),('ADMISSION','admissions'),('CLINICAL_ORDER','clinical_order')]:assert {o for o,t in objects.items() if t==typ}=={r['object_id'] for r in con.execute('SELECT object_id FROM '+tbl)}
subsets=[]
for kind,tbl in [('LAB','lab_order'),('MED','medication_order'),('PROC','procedure_order')]:
 subset={r['object_id'] for r in con.execute('SELECT object_id FROM '+tbl)};subsets.append(subset)
 assert subset=={r['object_id'] for r in con.execute('SELECT object_id FROM clinical_order WHERE order_kind=?',(kind,))}
assert len(set.union(*subsets))==sum(map(len,subsets))==45
assert con.execute('SELECT COUNT(*) FROM lab_order l JOIN medication_order m USING(order_id) JOIN procedure_order p USING(order_id)').fetchone()[0]==15
results={}
for g in gold:
 q=qm[g['id']];pair=qm[q['pair_of']];assert pair['pair_of']==q['id'];assert {q['question_type'],pair['question_type']} in [{'Q1','Q2'},{'Q3','Q4'}]
 assert q['requested_activity_count']==pair['requested_activity_count'];assert g['es']==gm[pair['id']]['es']
 if not g['answerable']:
  assert g['es'] is None and not (P/'private/gold_logs'/str(g['id']+'.csv')).exists();continue
 es=g['es'];assert set(es['case_population'])==set(catalog[q['case_concept']]['population'])
 actual=[dict(r) for r in con.execute((P/g['sql']).read_text())];expected=list(csv.DictReader((P/g['csv']).open()));assert actual==expected
 pop=set(es['case_population']);oracle=sorted([dict(event_id=e['event_id'],case_id=o,activity=e['activity'],timestamp=e['timestamp']) for e in events if e['activity'] in es['activities'] for o in links[e['event_id']]&pop],key=lambda r:(r['case_id'],r['timestamp'],r['event_id']))
 assert actual==oracle;assert len({(r['case_id'],r['event_id']) for r in actual})==len(actual)
 assert len({r['activity'] for r in actual})==q['extractable_activity_count'];results[g['id']]=actual
for q in questions:
 if q['answerable']:assert results[q['id']]==results[q['pair_of']]
assert sorted(results['HF03'],key=str)==sorted(results['HF04']+results['HF05']+results['HF06'],key=str)
assert {'LAB:1','MED:1','PROC:1'}<={r['case_id'] for r in results['HF03']}
# Every event linked to an order must be assigned to precisely that order's own admission/patient.
for r in con.execute('SELECT c.object_id,a.object_id ao,p.object_id po FROM clinical_order c JOIN admissions a ON a.hadm_id=c.hadm_id JOIN patients p ON p.subject_id=c.subject_id'):
 for eid,oids in links.items():
  if r['object_id'] in oids:assert oids=={r['object_id'],r['ao'],r['po']}
assert not any(r['case_id']=='P:12' for r in results['HF01']);assert 'P:12' in catalog['Patient']['population']
assert con.execute('SELECT COUNT(*) FROM (SELECT object_id FROM order_history WHERE action="REVIEWED" GROUP BY object_id HAVING COUNT(*)>1)').fetchone()[0]>0
assert con.execute('SELECT COUNT(*) FROM (SELECT order_id FROM procedureevents GROUP BY order_id HAVING COUNT(*)>1)').fetchone()[0]>0
# Business time order and no post-discharge execution for this controlled simulation.
for row in con.execute('SELECT * FROM admissions'):
 times=[hist[eid]['timestamp'] for eid,oids in links.items() if row['object_id'] in oids]
 assert not row['dischtime'] or max(times)<=row['dischtime']
for row in con.execute('SELECT l.*,MAX(e.storetime) latest FROM lab_order l LEFT JOIN labevents e USING(order_id) GROUP BY l.order_id'):
 if row['results_verified_at']:assert row['specimen_received_at']<=row['latest']<=row['results_verified_at']
for row in con.execute('SELECT o.object_id FROM clinical_order o JOIN order_history h USING(object_id) WHERE action="CANCELLED"'):
 assert {hist[e]['activity'] for e,oids in links.items() if row['object_id'] in oids}<={'Order Entered','Order Reviewed','Order Cancelled'}
# Every physical event timestamp is used by a full-lifecycle ES, and technical store times are excluded.
sources=load('private/persistence_mapping.json');used={(s['table'],s['timestamp_column']) for s in sources};inv=load('docs/timestamp_columns.json');assert {(r['table'],r['column']) for r in inv['columns'] if r['used_as_event_time']}==used
assert not any('emar'==s['table'] and 'storetime'==s['timestamp_column'] for s in sources)
assert set(Counter(q['question_type'] for q in questions).values())=={6,8}
seeds=load('source/question_seeds.json');par=load('source/llm_paraphrases.json');assert set(par['outputs'])=={s['id'] for s in seeds}
for s in seeds:assert qm[s['id']]['question']==s['question'] and qm[s['id']+'P']['question']==par['outputs'][s['id']]
report=load('validation_report.json');report['persisted_artifact_validation']={'gold_csvs_verified':len(results),'common_type_equals_disjoint_subtype_union':True,'physical_event_columns_covered':len(used),'cross_admission_leakage':False,'repeated_occurrences_preserved':True,'frozen_llm_pairs_verified':True,'schema_round_trip':True};(P/'validation_report.json').write_text(json.dumps(report,indent=2)+'\n')
print('HospitalFlow:',len(results),'Gold logs verified;',len(events),'events; common-type union, type/subtype membership, business joins, repeated occurrences, empty cases, time order and frozen paraphrase pairs passed.')
