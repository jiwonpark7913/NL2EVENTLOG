"""Deterministic MIMIC-inspired synthetic hospital benchmark; no patient records used."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
from collections import Counter,defaultdict
import json,sqlite3,csv,sys
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[1]/'tools'/'pipeline'))
sys.path.insert(0,str(P.parents[1]))
def js(n,v):
 f=P/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(json.dumps(v,indent=2)+'\n')
def jl(n,v): (P/n).write_text(''.join(json.dumps(x)+'\n' for x in v))
def md(n,s): (P/n).write_text(s)
def table(headers,rows):return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(str(v).replace('|','\\|') for v in r)+' |\n' for r in rows)
DDL='''PRAGMA foreign_keys=ON;
CREATE TABLE patients(subject_id INTEGER PRIMARY KEY NOT NULL, gender TEXT NOT NULL CHECK(gender IN ('F','M')));
CREATE TABLE patient_profile(subject_id INTEGER PRIMARY KEY NOT NULL, profile_verified_at TEXT NOT NULL, preferred_language TEXT NOT NULL);
CREATE TABLE admissions(hadm_id INTEGER PRIMARY KEY NOT NULL, subject_id INTEGER NOT NULL REFERENCES patients(subject_id), edregtime TEXT, admittime TEXT NOT NULL, discharge_authorized_at TEXT, dischtime TEXT, CHECK(edregtime IS NULL OR edregtime<=admittime), CHECK(dischtime IS NULL OR discharge_authorized_at<=dischtime));
CREATE TABLE admission_detail(hadm_id INTEGER PRIMARY KEY NOT NULL REFERENCES admissions(hadm_id), discharge_summary_signed_at TEXT NOT NULL);
CREATE TABLE lab_order(order_id INTEGER PRIMARY KEY NOT NULL, subject_id INTEGER NOT NULL REFERENCES patients(subject_id), hadm_id INTEGER REFERENCES admissions(hadm_id), specimen_received_at TEXT, results_verified_at TEXT);
CREATE TABLE medication_order(order_id INTEGER PRIMARY KEY NOT NULL, hadm_id INTEGER NOT NULL REFERENCES admissions(hadm_id), medication TEXT NOT NULL, stopped_at TEXT);
CREATE TABLE procedure_order(order_id INTEGER PRIMARY KEY NOT NULL, hadm_id INTEGER NOT NULL REFERENCES admissions(hadm_id), procedure_name TEXT NOT NULL, preparation_completed_at TEXT);
CREATE TABLE order_history(history_id INTEGER PRIMARY KEY NOT NULL, lab_order_id INTEGER REFERENCES lab_order(order_id), medication_order_id INTEGER REFERENCES medication_order(order_id), procedure_order_id INTEGER REFERENCES procedure_order(order_id), action TEXT NOT NULL CHECK(action IN ('ENTERED','REVIEWED','CANCELLED')), occurred_at TEXT NOT NULL, CHECK((lab_order_id IS NOT NULL)+(medication_order_id IS NOT NULL)+(procedure_order_id IS NOT NULL)=1));
CREATE TABLE labevents(labevent_id INTEGER PRIMARY KEY NOT NULL, order_id INTEGER NOT NULL REFERENCES lab_order(order_id), itemid INTEGER NOT NULL, charttime TEXT NOT NULL, storetime TEXT NOT NULL, valuenum REAL, valueuom TEXT, CHECK(charttime<=storetime));
CREATE TABLE pharmacy(pharmacy_id INTEGER PRIMARY KEY NOT NULL, order_id INTEGER NOT NULL REFERENCES medication_order(order_id), dispensed_at TEXT NOT NULL);
CREATE TABLE emar(emar_id INTEGER PRIMARY KEY NOT NULL, pharmacy_id INTEGER NOT NULL REFERENCES pharmacy(pharmacy_id), charttime TEXT NOT NULL, event_txt TEXT NOT NULL CHECK(event_txt IN ('Administered','Not Given')), storetime TEXT NOT NULL, CHECK(charttime<=storetime));
CREATE TABLE procedure_episode(procedureevent_id INTEGER PRIMARY KEY NOT NULL, order_id INTEGER NOT NULL REFERENCES procedure_order(order_id), starttime TEXT NOT NULL, endtime TEXT, storetime TEXT NOT NULL, CHECK(endtime IS NULL OR starttime<=endtime));
'''
ROLES={
'patients':'Patient identifiers and demographic categories.',
'admissions':'Distinct hospital stays per patient with actual admission/discharge milestones.',
'patient_profile':'Supplementary patient information keyed by patients.subject_id. Matching subject_id refers to the patient in patients; no SQL foreign key is declared.',
'admission_detail':'Signed discharge summaries keyed by admissions.hadm_id.',
'lab_order':'Laboratory request; multiple measurements can fulfill it. subject_id identifies the patient even when hadm_id is NULL for a request outside an admission.',
'medication_order':'One medication prescription, including its stop time. Dispensing is recorded separately in pharmacy.',
'procedure_order':'Distinct procedure order; repeated execution episodes belong to one order.',
'order_history':'Recorded actions on laboratory, medication or procedure requests, including repeated reviews.',
'labevents':'Laboratory measurement results with specimen collection and result-availability times. charttime denotes specimen collection, not measurement execution.',
'emar':'Medication administration or omission records associated with pharmacy dispensing records.',
'procedure_episode':'Hospital-level procedure execution episodes; the ICU stay_id hierarchy is excluded.',
'pharmacy':'One distinct dispensing record for a medication prescription; repeated dispensing records can fulfill the same prescription.'}
ENC={**{n:'No event encoding' for n in ['patients']},**{n:'Column encoding' for n in ['patient_profile','admissions','admission_detail','lab_order','medication_order','procedure_order','pharmacy']},**{n:'Row encoding' for n in ['order_history','emar']},**{n:'Column encoding' for n in ['labevents','procedure_episode']}}
DESCS={'subject_id':'Synthetic patient identity; can occur in multiple hospital admissions.','hadm_id':'Synthetic unique hospital admission identity.','gender':'Synthetic demographic category, F or M.','order_id':'Identity of a distinct order within its own business table. The three order tables use independent namespaces; equal integers do not mean the same request.','edregtime':'Emergency department registration time associated with this admission; NULL means the time is not recorded and registration occurrence is unknown.','admittime':'Actual hospital admission time.','discharge_authorized_at':'Recorded discharge authorization time; NULL means no time is recorded and authorization occurrence is unknown.','dischtime':'Actual hospital discharge time; NULL means the time is not recorded and discharge occurrence is unknown.','specimen_received_at':'Authored actual receipt of a specimen for this order.','results_verified_at':'Authored actual verification of results after all recorded measurements become available.','medication':'Generic medication name for synthetic records; not a treatment recommendation.','dispensed_at':'Time of this individual dispensing record, not the first dispensing time of its prescription.','stopped_at':'Recorded prescription stop time; NULL means no stop time is recorded and stop status is unknown.','procedure_name':'Fictional procedure label.','preparation_completed_at':'Authored actual completion of preparation for this procedure order.','history_id':'Unique occurrence identity for a repeated order action.','action':'ENTERED, REVIEWED or CANCELLED order action; repeated REVIEWED is permitted.','occurred_at':'Actual UTC time of the order action.','labevent_id':'Unique measurement occurrence identity; repeated item measurements remain distinct.','itemid':'Authored laboratory concept: 1001 Creatinine (mg/dL), 1002 Sodium (mmol/L), 1003 Hemoglobin (g/dL). Not original MIMIC codes.','charttime':'Specimen collection time in labevents; administration or omission time in emar.','storetime':'For labevents, time result becomes available; for emar/procedure_episode, system record time excluded as a separate business event.','valuenum':'Synthetic measurement numeric value.','valueuom':'Measurement unit; mg/dL for Creatinine, mmol/L for Sodium, g/dL for Hemoglobin.','emar_id':'Unique synthetic dose occurrence ID; simplified from the MIMIC identity structure.','event_txt':'Administered or Not Given; selects the activity of this dose occurrence.','procedureevent_id':'Authored unique procedure episode identity; not an original MIMIC column.','starttime':'Actual procedure episode start.','endtime':'Actual procedure episode completion; NULL means no completion time is recorded and completion status is unknown.'}
DESCS['pharmacy_id']='Identity of one dispensing record, distinct from its prescription and administration records.'
DESCS.update(profile_verified_at='Actual verification of supplementary patient information; one-time milestone for the same patient, not a separate profile object.',preferred_language='Synthetic preferred language.',discharge_summary_signed_at='Actual signing time of the summary for the same hospital admission; not a separate admission instance.',lab_order_id='FK to a distinct laboratory order; exactly one order FK is non-null per history row.',medication_order_id='FK to a distinct medication order; exactly one order FK is non-null per history row.',procedure_order_id='FK to a distinct procedure order; exactly one order FK is non-null per history row.')
def main():
 for n in ['input','private/gold_logs','private/gold_sql','docs','source','design']:(P/n).mkdir(parents=True,exist_ok=True)
 db=P/'input/database.sqlite';db.unlink(missing_ok=True)
 con=sqlite3.connect(db);con.row_factory=sqlite3.Row;con.executescript(DDL)
 (P/'input/schema.sql').write_text(DDL)
 def ins(t,**r):con.execute('INSERT INTO '+t+'('+','.join(r)+') VALUES ('+','.join('?' for _ in r)+')',list(r.values()))
 history=[];links=[];counts=Counter()
 def time(h):return (datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(minutes=round(h*60))).isoformat().replace('+00:00','Z')
 def event(eid,act,h,oids):
  history.append(dict(event_id=eid,activity=act,timestamp=time(h)))
  links.extend(dict(event_id=eid,object_id=o) for o in oids)
 def hist(oid,action,h,objs):
  counts['history']+=1;i=counts['history'];kind,local=oid.split(':');cols={'lab_order_id':None,'medication_order_id':None,'procedure_order_id':None};cols[{'LAB':'lab_order_id','MED':'medication_order_id','PROC':'procedure_order_id'}[kind]]=int(local);ins('order_history',history_id=i,**cols,action=action,occurred_at=time(h));event('OH:'+str(i),{'ENTERED':'Order Entered','REVIEWED':'Order Reviewed','CANCELLED':'Order Cancelled'}[action],h,objs)
 con.execute("PRAGMA defer_foreign_keys=ON")
 from simulation import populate
 populate(ins,event,hist,time,counts)
 for e in history:
  eid=e['event_id']
  own=(('H:'+eid.split(':')[1]) if eid.startswith('OH:') else ('LM:'+eid.split(':')[1]) if eid.startswith('LABEV:') else ('DOSE:'+eid.split(':')[1]) if eid.startswith('EMAR:') else ('EP:'+eid.split(':')[1]) if eid.startswith('PROCEV:') else None)
  if own:links.append(dict(event_id=eid,object_id=own))
 for row in con.execute('SELECT emar_id,pharmacy_id FROM emar'):
  links.append(dict(event_id='EMAR:'+str(row['emar_id']),object_id='PHARM:'+str(row['pharmacy_id'])))
 for row in con.execute('SELECT pharmacy_id FROM pharmacy'):
  links.append(dict(event_id='PHARM:'+str(row['pharmacy_id'])+':dispense',object_id='PHARM:'+str(row['pharmacy_id'])))
 con.commit()
 sources=[]
 def src(t,activity,ts,key,oid,where='1=1',encoding='Column encoding'):
  sql=f"SELECT {key} event_id,{oid} object_id,'{activity}' activity,{ts} timestamp FROM {t} WHERE {ts} IS NOT NULL AND ({where})"
  sources.append(dict(table=t.split()[0],activity=activity,timestamp_column=ts.split('.')[-1],encoding=encoding,event_sql=sql))
 for col,act,suffix in [('edregtime','Emergency Department Registered','ed'),('admittime','Hospital Admitted','in'),('discharge_authorized_at','Discharge Authorized','auth'),('dischtime','Hospital Discharged','out')]:src('admissions',act,col,"'ADM:'||hadm_id||':"+suffix+"'","'A:'||hadm_id")
 src('patient_profile','Patient Profile Verified','profile_verified_at',"'PAT:'||subject_id||':profile'","'P:'||subject_id")
 src('admission_detail','Discharge Summary Signed','discharge_summary_signed_at',"'ADM:'||hadm_id||':summary'","'A:'||hadm_id")
 for code,act in [('ENTERED','Order Entered'),('REVIEWED','Order Reviewed'),('CANCELLED','Order Cancelled')]:src('order_history',act,'occurred_at',"'OH:'||history_id","CASE WHEN lab_order_id IS NOT NULL THEN 'LAB:'||lab_order_id WHEN medication_order_id IS NOT NULL THEN 'MED:'||medication_order_id ELSE 'PROC:'||procedure_order_id END","action='"+code+"'",'Row encoding')
 for tbl,col,act,prefix,suffix in [('lab_order','specimen_received_at','Specimen Received','LAB','received'),('lab_order','results_verified_at','Lab Results Verified','LAB','verified'),('medication_order','stopped_at','Medication Stopped','MED','stop'),('procedure_order','preparation_completed_at','Procedure Preparation Completed','PROC','prep')]:src(tbl,act,col,"'"+prefix+":'||order_id||':"+suffix+"'","'"+prefix+":'||order_id")
 src('pharmacy','Medication Dispensed','dispensed_at',"'PHARM:'||pharmacy_id||':dispense'","'MED:'||order_id")
 for col,act,suffix in [('charttime','Specimen Collected','chart'),('storetime','Lab Result Available','result')]:src('labevents e JOIN lab_order o ON o.order_id=e.order_id',act,'e.'+col,"'LABEV:'||e.labevent_id||':"+suffix+"'","'LAB:'||o.order_id",encoding='Column encoding')
 for code,act in [('Administered','Medication Administered'),('Not Given','Medication Not Given')]:src('emar e JOIN pharmacy p ON p.pharmacy_id=e.pharmacy_id JOIN medication_order o ON o.order_id=p.order_id',act,'e.charttime',"'EMAR:'||e.emar_id","'MED:'||o.order_id","e.event_txt='"+code+"'",'Row encoding')
 for col,act,suffix in [('starttime','Procedure Started','start'),('endtime','Procedure Completed','end')]:src('procedure_episode e JOIN procedure_order o ON o.order_id=e.order_id',act,'e.'+col,"'PROCEV:'||e.procedureevent_id||':"+suffix+"'","'PROC:'||o.order_id",encoding='Column encoding')
 from timestamps import resolve_accidental_ties
 js('private/timestamp_collision_audit.json',resolve_accidental_ties(con,sources,history))
 base=' UNION ALL '.join(s['event_sql'] for s in sources)
 # Event IDs keep occurrence identity; physical keys determine own and FK paths.
 order_lookup="SELECT 'LAB:'||order_id order_key,hadm_id,subject_id FROM lab_order UNION ALL SELECT 'MED:'||o.order_id,o.hadm_id,a.subject_id FROM medication_order o JOIN admissions a USING(hadm_id) UNION ALL SELECT 'PROC:'||o.order_id,o.hadm_id,a.subject_id FROM procedure_order o JOIN admissions a USING(hadm_id)"
 attributed="SELECT e.*,CASE WHEN a.hadm_id IS NOT NULL THEN 'A:'||a.hadm_id END admission_object,'P:'||COALESCE(c.subject_id,a.subject_id) patient_object FROM events e LEFT JOIN orders c ON c.order_key=e.object_id LEFT JOIN admissions a ON e.object_id='A:'||a.hadm_id OR a.hadm_id=c.hadm_id WHERE c.order_key IS NOT NULL OR a.hadm_id IS NOT NULL UNION ALL SELECT e.*,NULL admission_object,e.object_id patient_object FROM events e WHERE e.object_id LIKE 'P:%'"
 physical={'patients':('Patient','P:','subject_id'),'patient_profile':('Patient','P:','subject_id'),'admissions':('Hospital Admission','A:','hadm_id'),'admission_detail':('Hospital Admission','A:','hadm_id'),'lab_order':('Laboratory Order','LAB:','order_id'),'medication_order':('Medication Order','MED:','order_id'),'procedure_order':('Procedure Order','PROC:','order_id'),'order_history':('Order History Record','H:','history_id'),'labevents':('Lab Measurement','LM:','labevent_id'),'emar':('Medication Administration','DOSE:','emar_id'),'procedure_episode':('Procedure Episode','EP:','procedureevent_id'),'pharmacy':('Pharmacy Dispensing','PHARM:','pharmacy_id')}
 objects=[]
 for tbl,(typ,prefix,key) in physical.items():
  for r in con.execute('SELECT '+key+' FROM '+tbl):
   obj=dict(object_id=prefix+str(r[key]),type_code=typ)
   if obj not in objects:objects.append(obj)
 viewdef={typ:None for typ,_,_ in physical.values()}
 linked=defaultdict(set)
 for r in links:linked[r['event_id']].add(r['object_id'])
 def population(view):return [o['object_id'] for o in objects if o['type_code']==view]
 def oracle(view,acts):
  pop=set(population(view));return sorted([dict(event_id=e['event_id'],case_id=o,activity=e['activity'],timestamp=e['timestamp']) for e in history if e['activity'] in acts for o in linked[e['event_id']]&pop],key=lambda r:(r['case_id'],r['timestamp'],r['event_id']))
 def compile_sql(view,acts):
  actlist=','.join("'"+a.replace("'","''")+"'" for a in acts)
  common='WITH events AS ('+base+'), orders AS ('+order_lookup+'), attributed AS ('+attributed+') '
  if view in ['Patient','Hospital Admission']:
   key='patient_object' if view=='Patient' else 'admission_object';body='SELECT event_id,'+key+' case_id,activity,timestamp FROM attributed WHERE '+key+' IS NOT NULL'
  elif view=='Pharmacy Dispensing':
   body="SELECT e.event_id,'PHARM:'||p.pharmacy_id case_id,e.activity,e.timestamp FROM events e JOIN pharmacy p ON e.event_id='PHARM:'||p.pharmacy_id||':dispense' UNION ALL SELECT e.event_id,'PHARM:'||m.pharmacy_id case_id,e.activity,e.timestamp FROM events e JOIN emar m ON e.event_id='EMAR:'||m.emar_id"
  elif view in ['Laboratory Order','Medication Order','Procedure Order']:
   prefix={'Laboratory Order':'LAB:','Medication Order':'MED:','Procedure Order':'PROC:'}[view];body="SELECT event_id,object_id case_id,activity,timestamp FROM events WHERE object_id LIKE '"+prefix+"%'"
  else:
   prefix,pattern,expr={'Order History Record':('H:','OH:%',"substr(event_id,4)"),'Lab Measurement':('LM:','LABEV:%',"substr(substr(event_id,7),1,instr(substr(event_id,7),':')-1)"),'Medication Administration':('DOSE:','EMAR:%',"substr(event_id,6)"),'Procedure Episode':('EP:','PROCEV:%',"substr(substr(event_id,8),1,instr(substr(event_id,8),':')-1)")}[view]
   body="SELECT event_id,'"+prefix+"'||"+expr+" case_id,activity,timestamp FROM events WHERE event_id LIKE '"+pattern+"'"
  return common+'SELECT * FROM ('+body+') WHERE activity IN ('+actlist+') ORDER BY case_id,timestamp,event_id;'
 coverage=[];catalog=[]
 for view in viewdef:
  pop=population(view);acts=sorted({e['activity'] for e in history if linked[e['event_id']]&set(pop)})
  catalog.append(dict(case_concept=view,object_type=view,population=pop,activities=acts,default_scope='All recorded events explicitly linked through business keys; no unrecorded care is inferred.'))
  coverage.append(dict(case_concept=view,object_type=view,case_count=len(pop),activity_count=len(acts),activities=acts,event_rows=len(oracle(view,acts)),cases_without_events=len(set(pop)-{r['case_id'] for r in oracle(view,acts)})))
 js('input/task_scope_catalog.json',dict(setting='Catalog-assisted scope only; no physical identity answers',views=[{k:v for k,v in row.items() if k not in ['population','object_type']} for row in catalog]))
 js('private/case_population.json',catalog)
 seeds=json.loads((P/'source/question_seeds.json').read_text());par=json.loads((P/'source/llm_paraphrases.json').read_text());questions=[];gold=[]
 for seed in seeds:
  view=seed['view'];full='activities' not in seed;acts=next(c['activities'] for c in catalog if c['case_concept']==view) if full else seed['activities'];answerable=seed.get('answerable',True);qid=seed['id'];pair=qid+'P'
  es=dict(version='hospital-es-1',case_concept=view,object_type=view,activities=acts,case_population=population(view),activity_sources=[s for s in sources if s['activity'] in acts],compiled_sql=compile_sql(view,acts)) if answerable else None
  for ident,text,typ,other in [(qid,seed['question'],'Q3' if full else 'Q1',pair),(pair,par['outputs'][qid],'Q4' if full else 'Q2',qid)]:
   q=dict(id=ident,question=text,question_type=typ,question_type_name={'Q1':'Explicit','Q2':'Paraphrased','Q3':'Full Lifecycle','Q4':'Full Lifecycle Paraphrased'}[typ],pair_of=other,pair_group_id=qid,case_concept=view,answerable=answerable,included_information='Case concept only' if full else 'Case concept and explicit activity scope',requested_activity_count=len(acts),extractable_activity_count=len(acts) if answerable else 0,activity_scope_explicit=not full)
   q['question_id']=ident;q['text']=text;q['answerability']='answerable' if answerable else 'non_answerable';questions.append(q);g=dict(id=ident,question_id=ident,question_type=typ,pair_of=other,answerability=q['answerability'],answerable=answerable,es=es,process_view=dict(case_concept=view,object_type=view,activities=acts),requested_activities=acts)
   if answerable:
    sql=es['compiled_sql'];actual=[dict(r) for r in con.execute(sql)];expected=oracle(view,acts);assert actual==expected,(ident,'SQL/oracle mismatch');assert len({(r['case_id'],r['event_id']) for r in actual})==len(actual)
    f='private/gold_logs/'+ident+'.csv'
    with (P/f).open('w',newline='') as stream:w=csv.DictWriter(stream,fieldnames=['event_id','case_id','activity','timestamp']);w.writeheader();w.writerows(expected)
    (P/'private/gold_sql'/str(ident+'.sql')).write_text(sql+'\n');g.update(csv=f,sql='private/gold_sql/'+ident+'.sql',event_count=len(expected),case_count=len({r['case_id'] for r in expected}))
   else:g['reason']='No claim or payment records/timestamps exist in this DB; no Gold CSV is emitted.'
   g.update({k:q[k] for k in ['question_type_name','pair_group_id','included_information','requested_activity_count','extractable_activity_count','activity_scope_explicit']});gold.append(g)
 jl('input/questions.jsonl',questions);jl('input/model_questions.jsonl',[dict(id=q['id'],question=q['question']) for q in questions]);jl('private/gold.jsonl',gold);jl('private/canonical_history.jsonl',history);js('private/object_event_links.json',links);js('private/persistence_mapping.json',sources)
 checks={}
 def rejected(name,sql):
  con.execute('SAVEPOINT probe')
  try:con.execute(sql)
  except sqlite3.IntegrityError:checks[name]=True
  else:raise AssertionError(name+' incorrectly accepted')
  finally:con.execute('ROLLBACK TO probe');con.execute('RELEASE probe')
 rejected('orphan_order',"INSERT INTO lab_order VALUES(999,999,999,NULL,NULL)")
 rejected('orphan_history',"INSERT INTO order_history VALUES(999,999,NULL,NULL,'ENTERED','2026-01-01T00:00:00Z')")
 rejected('ambiguous_history_order',"INSERT INTO order_history VALUES(999,1,1,NULL,'ENTERED','2026-01-01T00:00:00Z')")
 assert not list(con.execute('PRAGMA foreign_key_check'));assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 checks.update(gold_sql_matches_independent_generation_history=True,exact_question_pairs=True,independent_order_identities=True,patient_multiple_admissions=True,pending_cancelled_and_empty_cases=True)
 tables=[]
 for name in ROLES:
  cols=[]
  for r in con.execute('PRAGMA table_info('+name+')'):cols.append(dict(name=r['name'],type=r['type'],constraints='See executable table DDL',definition=DESCS[r['name']],source_origin='mimic_inspired_synthetic_benchmark'))
  fk=[dict(column=r['from'],parent_table=r['table'],parent_column=r['to']) for r in con.execute('PRAGMA foreign_key_list('+name+')')];pk=[r['name'] for r in con.execute('PRAGMA table_info('+name+')') if r['pk']]
  tables.append(dict(table=name,definition=ROLES[name],columns=cols,primary_key=pk,foreign_keys=fk))
 js('design/logical_schema.json',tables)
 timestamps=[]
 for t in tables:
  for c in t['columns']:
   n=c['name'];used=any(s['table']==t['table'] and s['timestamp_column']==n for s in sources)
   if n.endswith('_at') or n in ['edregtime','admittime','dischtime','occurred_at','charttime','storetime','starttime','endtime']:timestamps.append(dict(table=t['table'],column=n,used_as_event_time=used,role='Actual event time' if used else 'Technical documentation time'))
 summary=dict(timestamp_columns=len(timestamps),event_timestamp_columns=sum(r['used_as_event_time'] for r in timestamps));js('docs/timestamp_columns.json',dict(**summary,columns=timestamps))
 rows={n:con.execute('SELECT COUNT(*) FROM '+n).fetchone()[0] for n in ROLES};report=dict(table_rows=rows,semantic_object_types=len(viewdef),physical_objects=len(physical),identity_groups=len(viewdef),object_instances=len(objects),object_view_coverage=coverage,activity_counts=dict(Counter(e['activity'] for e in history)),events=len(history),total_questions=len(questions),answerable_questions=sum(q['answerable'] for q in questions),timestamp_summary=summary,checks=checks,validation_scope='Internal construction consistency, not model extraction accuracy or clinical realism evaluation.');js('validation_report.json',report)
 md('docs/timestamp_columns.md','# Timestamp columns\n\n'+table(['Table','Column','Event time?','Meaning'],[[r['table'],r['column'],r['used_as_event_time'],r['role']] for r in timestamps]))
 md('docs/object_activity_design.md','# Objects, types and activity scopes\n\n'+table(['Object Type','Instances','Activity types','Activity scope'],[[r['case_concept'],r['case_count'],r['activity_count'],', '.join(r['activities'])] for r in coverage])+'\n- Twelve Physical Objects map to ten expected identity-compatible Object Type groups. History/measurement/dose/episode records retain independent occurrence identities.\n- Individual instances may contain fewer activities due to cancellation, ongoing care or missing records.\n')
 js('design/object_activity_design.json',coverage)
 md('docs/object_event_logs.md','# Full lifecycle Gold logs\n\n'+table(['Object Type','Q3','Q4','Cases','Cases without events'],[[seed['view'],seed['id'],seed['id']+'P',len(population(seed['view'])),next(c['cases_without_events'] for c in coverage if c['case_concept']==seed['view'])] for seed in seeds if 'activities' not in seed])+'\n- Empty cases are retained in private Gold ES.case_population. These are case-based CSVs, not OCEL.\n')
 stats=[]
 for typ in ['Q1','Q2','Q3','Q4']:
  qs=[q for q in questions if q['question_type']==typ];stats.append([typ,len(qs),sum(q['answerable'] for q in qs),sum(not q['answerable'] for q in qs),f"{sum(q['requested_activity_count'] for q in qs)/len(qs):.2f}"])
 stattable=table(['Type','Questions','Answerable','Non-answerable','Avg. requested activity types'],stats)
 md('docs/questions.md','# HospitalFlow questions\n\n## Question types and pairs\n\n'+stattable+'\n- Average includes all requests in the type, including unsupported activity requests.\n- Process View includes the case concept and activity scope. Q3/Q4 leave the scope implicit via the catalog.\n- Each P question is an assistant-LLM paraphrase of the frozen seed; prompts and outputs are saved in source/llm_paraphrases.json.\n\n'+table(['ID','Type','Paired with','Answerability','Requested activities','Extractable activities','Question'],[[q['id'],q['question_type'],q['pair_of'],'Answerable' if q['answerable'] else 'Non-answerable',q['requested_activity_count'],q['extractable_activity_count'],q['question']] for q in questions]))
 from identity_benchmark import write_identity_gold,write_docs
 write_identity_gold(P,con,physical,sources)
 write_docs(P,report,coverage,ENC,stattable)
 from profile_update import update_profile
 update_profile(P,con,ROLES,DESCS)
 from hospital_dictionary import render as render_dictionary
 render_dictionary(P)
 con.close();print(json.dumps({k:report[k] for k in ['physical_objects','identity_groups','events','total_questions','answerable_questions','semantic_object_types','object_instances','timestamp_summary']},indent=2))
if __name__=='__main__':main()
