"""Check dataset identity ground truth and persisted extraction artifacts, not a Step 2 implementation."""
from pathlib import Path
from collections import defaultdict,Counter
import json,sqlite3,csv
P=Path(__file__).resolve().parent
load=lambda n:json.loads((P/n).read_text())
lines=lambda n:[json.loads(x) for x in (P/n).read_text().splitlines()]
con=sqlite3.connect(P/'input/database.sqlite');con.row_factory=sqlite3.Row
assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert not list(con.execute('PRAGMA foreign_key_check'))
blank=sqlite3.connect(':memory:');blank.executescript((P/'input/schema.sql').read_text())
assert list(blank.execute('SELECT type,name,sql FROM sqlite_master ORDER BY type,name'))==[tuple(r) for r in con.execute('SELECT type,name,sql FROM sqlite_master ORDER BY type,name')]
tables={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")};assert not tables&{'object','object_type','clinical_order'};assert len(tables)==12
assert all('object_id' not in {r['name'] for r in con.execute('PRAGMA table_info('+t+')')} for t in tables)
identity=load('private/identity_gold.json');assert identity['physical_object_count']==12 and identity['expected_group_count']==10
pairs=identity['pairs'];assert len(pairs)==len({tuple(x['tables']) for x in pairs})==66;assert identity['expected_decision_counts']=={'MERGE':2,'SEPARATE':64,'UNRESOLVED':0}
positive={frozenset(x['tables']) for x in pairs if x['expected_decision']=='MERGE'};assert positive=={frozenset(['patients','patient_profile']),frozenset(['admissions','admission_detail'])}
for pair in pairs:
 a,b=pair['tables'];ka,kb=[p[0] for p in pair['primary_keys']];sa={r[0] for r in con.execute('SELECT '+ka+' FROM '+a)};sb={r[0] for r in con.execute('SELECT '+kb+' FROM '+b)};stats=pair['key_statistics'];assert stats['intersection_count']==len(sa&sb);assert stats['overlap_min']==len(sa&sb)/min(len(sa),len(sb))
 if pair['expected_decision']=='MERGE':assert sb<sa and stats['overlap_min']==1 and stats['coverage_A']<0.95
assert not list(con.execute('PRAGMA foreign_key_list(patient_profile)'))
assert con.execute('SELECT COUNT(*) FROM patient_profile p LEFT JOIN patients a USING(subject_id) WHERE a.subject_id IS NULL').fetchone()[0]==0
assert con.execute('SELECT COUNT(*) FROM lab_order l JOIN medication_order m USING(order_id) JOIN procedure_order p USING(order_id)').fetchone()[0]==3
catalog={v['case_concept']:v for v in load('private/case_population.json')};public=load('input/task_scope_catalog.json');assert all(not {'population','members','object_type','same_key_namespace'}&set(v) for v in public['views'])
questions=lines('input/questions.jsonl');gold=lines('private/gold.jsonl');qm={q['id']:q for q in questions};gm={g['id']:g for g in gold};history=lines('private/canonical_history.jsonl');hist={e['event_id']:e for e in history};assert len(hist)==len(history)==load('validation_report.json')['events']
links=defaultdict(set)
for r in load('private/object_event_links.json'):links[r['event_id']].add(r['object_id'])
results={}
for g in gold:
 q=qm[g['id']];pair=qm[q['pair_of']];assert pair['pair_of']==q['id'];assert {q['question_type'],pair['question_type']} in [{'Q1','Q2'},{'Q3','Q4'}];assert q['requested_activity_count']==pair['requested_activity_count'];assert g['es']==gm[pair['id']]['es']
 if not g['answerable']:assert g['es'] is None and not (P/'private/gold_logs'/str(g['id']+'.csv')).exists();continue
 es=g['es'];pop=set(catalog[q['case_concept']]['population']);assert set(es['case_population'])==pop
 actual=[dict(r) for r in con.execute((P/g['sql']).read_text())];expected=list(csv.DictReader((P/g['csv']).open()));assert actual==expected
 oracle=sorted([dict(event_id=e['event_id'],case_id=o,activity=e['activity'],timestamp=e['timestamp']) for e in history if e['activity'] in es['activities'] for o in links[e['event_id']]&pop],key=lambda r:(r['case_id'],r['timestamp'],r['event_id']))
 assert actual==oracle;assert len({(r['case_id'],r['event_id']) for r in actual})==len(actual);assert len({r['activity'] for r in actual})==q['extractable_activity_count'];results[g['id']]=actual
for q in questions:
 if q['answerable']:assert results[q['id']]==results[q['pair_of']]
assert Counter(q['question_type'] for q in questions)=={'Q1':12,'Q2':12,'Q3':10,'Q4':10}
# Combined same-identity sources: same patient/admission case, different preserved events.
assert len(results['H09'])==6;assert len(results['H10'])==5
for r in results['H11']:
 if r['event_id']=='PAT:10000001:profile':assert r['case_id']=='P:10000001'
assert {'PAT:10000001:profile','ADM:20000001:in'}<={r['event_id'] for r in results['HF01'] if r['case_id']=='P:10000001'}
assert {'ADM:20000001:in','ADM:20000001:summary'}<={r['event_id'] for r in results['HF02'] if r['case_id']=='A:20000001'}
assert len([r for r in results['HF01'] if r['case_id']=='P:10000001' and r['activity']=='Hospital Admitted'])==2
assert not any(r['case_id']=='P:10000012' for r in results['HF01']);assert 'P:10000012' in catalog['Patient']['population']
# Own occurrence cases are not replaced by FK-derived order or parent cases.
assert len(results['HF03'])==con.execute('SELECT COUNT(*) FROM order_history').fetchone()[0] and all(r['case_id']=='H:'+r['event_id'].split(':')[1] for r in results['HF03'])
assert len(results['HF07'])==2*con.execute('SELECT COUNT(*) FROM labevents').fetchone()[0]
assert len(results['HF08'])==con.execute('SELECT COUNT(*) FROM emar').fetchone()[0];assert len({r['case_id'] for r in results['HF09']})==con.execute('SELECT COUNT(*) FROM procedure_episode').fetchone()[0]
for r in con.execute('SELECT * FROM order_history'):
 eid='OH:'+str(r['history_id']);own='H:'+str(r['history_id']);cols=[(c,k) for c,k in [('lab_order_id','LAB'),('medication_order_id','MED'),('procedure_order_id','PROC')] if r[c] is not None];assert len(cols)==1
 c,kind=cols[0];order=kind+':'+str(r[c]);tbl={'LAB':'lab_order','MED':'medication_order','PROC':'procedure_order'}[kind]
 o=con.execute('SELECT * FROM '+tbl+' WHERE order_id=?',(r[c],)).fetchone()
 a=con.execute('SELECT * FROM admissions WHERE hadm_id=?',(o['hadm_id'],)).fetchone()
 subject=o['subject_id'] if kind=='LAB' else a['subject_id']
 expected={own,order,'P:'+str(subject)}|({'A:'+str(a['hadm_id'])} if a else set())
 assert links[eid]==expected
for row in con.execute('SELECT l.*,MAX(e.storetime) latest FROM lab_order l LEFT JOIN labevents e USING(order_id) GROUP BY l.order_id'):
 if row['results_verified_at']:assert row['specimen_received_at']<=row['latest']<=row['results_verified_at']
for row in con.execute('SELECT a.*,d.discharge_summary_signed_at FROM admissions a JOIN admission_detail d USING(hadm_id)'):assert row['admittime']<row['dischtime']<row['discharge_summary_signed_at']
sources=load('private/persistence_mapping.json');used={(s['table'],s['timestamp_column']) for s in sources};inv=load('docs/timestamp_columns.json');assert inv['timestamp_columns']==19 and inv['event_timestamp_columns']==17;assert used=={(r['table'],r['column']) for r in inv['columns'] if r['used_as_event_time']}
provenance=load('private/event_binding_provenance.json');assert len(provenance)==len(sources) and all(p['physical_object']['table'] in tables for p in provenance)
seeds=load('source/question_seeds.json');par=load('source/llm_paraphrases.json');assert set(par['outputs'])=={s['id'] for s in seeds}
for s in seeds:assert qm[s['id']]['question']==s['question'] and qm[s['id']+'P']['question']==par['outputs'][s['id']]
report=load('validation_report.json');report['persisted_artifact_validation']=dict(gold_csvs_verified=len(results),physical_objects=12,expected_identity_groups=10,expected_positive_pairs_verified=2,full_gold_pair_count=66,actual_identity_classifier_run=False,split_storage_events_preserve_sources_and_occurrences=True,own_and_fk_attribution_verified=True,physical_event_columns_covered=len(used),frozen_llm_pairs_verified=True,schema_round_trip=True);(P/'validation_report.json').write_text(json.dumps(report,indent=2)+'\n')
from realism_validation import validate_realism
validate_realism(P,con,results,history,links)
print('HospitalFlow:',len(results),'Gold logs; 12 Physical Objects → 10 expected groups; 2 positive identity pairs; split-source, own/FK and occurrence checks passed. No identity classifier executed.')

# Business metadata is checked independently of Gold extraction assertions.
import subprocess,sys
subprocess.run([sys.executable,str(P/"validate_dictionary.py")],check=True)

# Only record successful dictionary/ablation checks after the subprocess passes.
report=load('validation_report.json')
report['semantic_validation']={'laboratory_collection_receipt_result_verified_rows':con.execute('SELECT COUNT(*) FROM labevents').fetchone()[0], 'signed_summaries_after_discharge':con.execute('SELECT COUNT(*) FROM admission_detail').fetchone()[0], 'variable_count':sum(len(t['columns']) for t in load('input/data_dictionary.json')['tables']), 'nullable_time_interpretation':'timestamp not recorded; occurrence unknown', 'dictionary_conditions_prepared':['full_dictionary','concise_dictionary','no_dictionary'], 'actual_model_ablation_run':False, 'details':'docs/realism_validation.json'}
(P/'validation_report.json').write_text(json.dumps(report,indent=2)+'\n')
