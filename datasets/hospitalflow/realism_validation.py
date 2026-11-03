"""Evaluation-validity probes, not a claim of clinical distribution fidelity."""
import json,itertools
from collections import Counter
from datetime import datetime

def validate_realism(p,con,results,history,links):
 def scalar(sql):return con.execute(sql).fetchone()[0]
 def distribution(sql):return dict(sorted(Counter(r[0] for r in con.execute(sql)).items()))
 def mins(a,b):return round((datetime.fromisoformat(b.replace('Z','+00:00'))-datetime.fromisoformat(a.replace('Z','+00:00'))).total_seconds()/60,5)
 tests={};distributions={}
 assert scalar('SELECT COUNT(*) FROM admissions WHERE subject_id=hadm_id')==0
 for t in ['lab_order','medication_order','procedure_order']:
  assert scalar('SELECT COUNT(*) FROM '+t+' o JOIN admissions a ON o.order_id=a.hadm_id')==0
  correct=scalar('SELECT COUNT(*) FROM '+t+' o JOIN admissions a ON o.hadm_id=a.hadm_id')
  wrong=scalar('SELECT COUNT(*) FROM '+t+' o JOIN admissions a ON o.order_id=a.hadm_id')
  assert correct>wrong
  dist=distribution('SELECT COUNT(o.order_id) FROM admissions a LEFT JOIN '+t+' o USING(hadm_id) GROUP BY a.hadm_id')
  assert 0 in dist and max(dist)>=3 and len(dist)>=4
  distributions[t+'_per_admission']=dist
  tests['wrong_'+t+'_order_id_to_hadm_id']=dict(correct_rows=correct,wrong_rows=wrong,detected=True)
 for a,b in itertools.combinations(['lab_order','medication_order','procedure_order'],2):
  rows=list(con.execute('SELECT x.order_id,x.hadm_id,y.hadm_id FROM '+a+' x JOIN '+b+' y USING(order_id)'))
  assert rows and any(r[1]!=r[2] for r in rows)
 # Wrong fan-out multiplies the same dose once per lab order in an admission.
 correct=scalar('SELECT COUNT(*) FROM emar e JOIN pharmacy p USING(pharmacy_id) JOIN medication_order m ON m.order_id=p.order_id')
 wrong=scalar('SELECT COUNT(*) FROM emar e JOIN pharmacy p USING(pharmacy_id) JOIN medication_order m ON m.order_id=p.order_id JOIN lab_order l ON l.hadm_id=m.hadm_id')
 assert correct!=wrong;tests['unrelated_lab_fanout']=dict(correct_rows=correct,wrong_rows=wrong,detected=True)
 assert scalar('SELECT COUNT(*) FROM lab_order l JOIN admissions a USING(hadm_id) WHERE l.subject_id<>a.subject_id')==0
 outpatient={r[0] for r in con.execute('SELECT order_id FROM lab_order WHERE hadm_id IS NULL')};assert len(outpatient)==4
 outpatient_events={e for e,objects in links.items() if objects&{'LAB:'+str(x) for x in outpatient}}
 assert outpatient_events and outpatient_events<={r['event_id'] for r in results['HF01']}
 assert not outpatient_events&{r['event_id'] for r in results['HF02']}
 for t,sql in {'dispensings_per_prescription':'SELECT COUNT(p.pharmacy_id) FROM medication_order o LEFT JOIN pharmacy p USING(order_id) GROUP BY o.order_id','doses_per_dispensing':'SELECT COUNT(e.emar_id) FROM pharmacy p LEFT JOIN emar e USING(pharmacy_id) GROUP BY p.pharmacy_id','doses_per_prescription':'SELECT COUNT(e.emar_id) FROM medication_order o LEFT JOIN pharmacy p USING(order_id) LEFT JOIN emar e USING(pharmacy_id) GROUP BY o.order_id'}.items():
  dist=distribution(sql);assert len(dist)>=3 and 0 in dist;distributions[t]=dist
 assert scalar('SELECT COUNT(*) FROM emar e JOIN pharmacy p USING(pharmacy_id) WHERE e.charttime<p.dispensed_at')==0
 assert scalar('SELECT COUNT(*) FROM emar e JOIN pharmacy p USING(pharmacy_id) JOIN medication_order m ON m.order_id=p.order_id WHERE e.charttime>m.stopped_at')==0
 assert scalar('SELECT COUNT(*) FROM admissions WHERE dischtime IS NULL')>=2
 assert scalar('SELECT COUNT(*) FROM medication_order WHERE stopped_at IS NULL')>=2
 assert scalar('SELECT COUNT(*) FROM procedure_episode WHERE endtime IS NULL')>=1
 duration_queries={'stay_minutes':'SELECT admittime,dischtime FROM admissions WHERE dischtime IS NOT NULL','ed_to_admission_minutes':'SELECT edregtime,admittime FROM admissions WHERE edregtime IS NOT NULL','lab_turnaround_minutes':'SELECT charttime,storetime FROM labevents','authorization_to_discharge_minutes':'SELECT discharge_authorized_at,dischtime FROM admissions WHERE dischtime IS NOT NULL','readmission_gap_minutes':'SELECT a.dischtime,b.admittime FROM admissions a JOIN admissions b ON a.subject_id=b.subject_id AND a.admittime<b.admittime WHERE a.dischtime IS NOT NULL'}
 durations={}
 for k,sql in duration_queries.items():
  values=[mins(*r) for r in con.execute(sql)];assert min(values)>0 and len(set(values))>=4
  durations[k]=dict(n=len(values),distinct=len(set(values)),minimum=min(values),maximum=max(values),mean=round(sum(values)/len(values),2))
 assert len({e['timestamp'] for e in history})==len(history)
 assert sum(e['timestamp'][14:16]!='00' for e in history)>.9*len(history)
 tests.update(outpatient_patient_included_admission_excluded=True,variable_zero_to_many_cardinalities=True,minute_scale_nonconstant_time_intervals=True,no_unintended_event_ties=True,pharmacy_doses_follow_dispensing_and_precede_stop=True)
 report=dict(seed=20261103,simulation='Illustrative seeded skewed counts and lognormal stays; not fitted to MIMIC.',checks=tests,count_distributions=distributions,duration_summaries=durations,outpatient_orders=len(outpatient),outpatient_events=len(outpatient_events),actual_identity_classifier_run=False)
 (p/'docs/realism_validation.json').write_text(json.dumps(report,indent=2)+'\n')
 print('HospitalFlow realism probes: wrong joins and fan-out detected; outpatient scope, nonconstant cardinalities/time intervals, and dispensing chain verified.')
