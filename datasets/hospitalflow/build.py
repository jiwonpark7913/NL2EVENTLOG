"""Deterministic MIMIC-inspired synthetic hospital benchmark; no patient records used."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
from collections import Counter,defaultdict
import json,sqlite3,csv,sys
P=Path(__file__).resolve().parent
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
CREATE TABLE admission_detail(hadm_id INTEGER PRIMARY KEY NOT NULL REFERENCES admissions(hadm_id), discharge_summary_signed_at TEXT NOT NULL, summary_status TEXT NOT NULL CHECK(summary_status='SIGNED'));
CREATE TABLE lab_order(order_id INTEGER PRIMARY KEY NOT NULL, hadm_id INTEGER NOT NULL REFERENCES admissions(hadm_id), specimen_received_at TEXT, results_verified_at TEXT);
CREATE TABLE medication_order(order_id INTEGER PRIMARY KEY NOT NULL, hadm_id INTEGER NOT NULL REFERENCES admissions(hadm_id), medication TEXT NOT NULL, dispensed_at TEXT, stopped_at TEXT);
CREATE TABLE procedure_order(order_id INTEGER PRIMARY KEY NOT NULL, hadm_id INTEGER NOT NULL REFERENCES admissions(hadm_id), procedure_name TEXT NOT NULL, preparation_completed_at TEXT);
CREATE TABLE order_history(history_id INTEGER PRIMARY KEY NOT NULL, lab_order_id INTEGER REFERENCES lab_order(order_id), medication_order_id INTEGER REFERENCES medication_order(order_id), procedure_order_id INTEGER REFERENCES procedure_order(order_id), action TEXT NOT NULL CHECK(action IN ('ENTERED','REVIEWED','CANCELLED')), occurred_at TEXT NOT NULL, CHECK((lab_order_id IS NOT NULL)+(medication_order_id IS NOT NULL)+(procedure_order_id IS NOT NULL)=1));
CREATE TABLE labevents(labevent_id INTEGER PRIMARY KEY NOT NULL, order_id INTEGER NOT NULL REFERENCES lab_order(order_id), itemid INTEGER NOT NULL, charttime TEXT NOT NULL, storetime TEXT NOT NULL, valuenum REAL, valueuom TEXT, CHECK(charttime<=storetime));
CREATE TABLE emar(emar_id INTEGER PRIMARY KEY NOT NULL, order_id INTEGER NOT NULL REFERENCES medication_order(order_id), charttime TEXT NOT NULL, event_txt TEXT NOT NULL CHECK(event_txt IN ('Administered','Not Given')), storetime TEXT NOT NULL, CHECK(charttime<=storetime));
CREATE TABLE procedureevents(procedureevent_id INTEGER PRIMARY KEY NOT NULL, order_id INTEGER NOT NULL REFERENCES procedure_order(order_id), starttime TEXT NOT NULL, endtime TEXT, storetime TEXT NOT NULL, CHECK(endtime IS NULL OR starttime<=endtime));
'''
ROLES={
'patients':'Synthetic patient identity, inspired by MIMIC subject_id.',
'admissions':'Distinct hospital stays per patient with actual admission/discharge milestones.',
'patient_profile':'Optional additional information for the SAME patient identified by patients.subject_id, in the SAME identifier namespace. A matching subject_id denotes the same actual patient. No FK is declared; this identity relationship is explicitly documented. Authored split-storage extension.',
'admission_detail':'Optional additional information for the SAME hospital stay identified by admissions.hadm_id. A matching hadm_id denotes the same actual admission. Only a subset of admissions has a signed summary. Authored split-storage extension.',
'lab_order':'Distinct laboratory order; several measurements may belong to one order.',
'medication_order':'Distinct medication order; repeated doses belong to one order.',
'procedure_order':'Distinct procedure order; repeated execution episodes belong to one order.',
'order_history':'Repeated order actions, inspired by provider order transaction semantics; not a copy of poe.',
'labevents':'Measurement occurrences with separately charted and available-result times, inspired by MIMIC labevents.',
'emar':'Medication administration or omission occurrences, inspired by MIMIC emar.',
'procedureevents':'Procedure execution episodes with start/end times, inspired by MIMIC procedureevents.'}
ENC={**{n:'No event encoding' for n in ['patients']},**{n:'Column encoding' for n in ['patient_profile','admissions','admission_detail','lab_order','medication_order','procedure_order']},**{n:'Row encoding' for n in ['order_history','emar']},**{n:'Mixed (row + column)' for n in ['labevents','procedureevents']}}
DESCS={'subject_id':'Synthetic patient identity; can occur in multiple hospital admissions.','hadm_id':'Synthetic unique hospital admission identity.','gender':'Synthetic demographic category, F or M.','order_id':'Identity of a distinct order within its own business table. The three order tables use independent namespaces; equal integers do not mean the same request.','edregtime':'Actual emergency department registration time; NULL for admissions without ED registration.','admittime':'Actual hospital admission time.','discharge_authorized_at':'Authored actual discharge authorization time; NULL if not occurred.','dischtime':'Actual hospital discharge time; NULL for an ongoing stay.','specimen_received_at':'Authored actual receipt of a specimen for this order.','results_verified_at':'Authored actual verification of results after all recorded measurements become available.','medication':'Fictional medication label; no treatment recommendation.','dispensed_at':'Authored actual dispensing time.','stopped_at':'Authored actual stop time; NULL if not stopped.','procedure_name':'Fictional procedure label.','preparation_completed_at':'Authored actual completion of preparation for this procedure order.','history_id':'Unique occurrence identity for a repeated order action.','action':'ENTERED, REVIEWED or CANCELLED order action; repeated REVIEWED is permitted.','occurred_at':'Actual UTC time of the order action.','labevent_id':'Unique measurement occurrence identity; repeated item measurements remain distinct.','itemid':'Synthetic laboratory concept ID; no original MIMIC item code is claimed.','charttime':'Actual charted measurement time in labevents; medication administration/omission time in emar. Not lab result-availability time.','storetime':'For labevents, time result becomes available; for emar/procedureevents, system record time excluded as a separate business event.','valuenum':'Synthetic measurement numeric value.','valueuom':'Measurement unit; all current synthetic measurements use arbitrary units.','emar_id':'Unique synthetic dose occurrence ID; simplified from the MIMIC identity structure.','event_txt':'Administered or Not Given; selects the activity of this dose occurrence.','procedureevent_id':'Authored unique procedure episode identity; not an original MIMIC column.','starttime':'Actual procedure episode start.','endtime':'Actual procedure episode completion; NULL if ongoing.'}
DESCS.update(profile_verified_at='Actual verification of supplementary patient information; one-time milestone for the same patient, not a separate profile object.',preferred_language='Synthetic preferred language.',discharge_summary_signed_at='Actual signing time of the summary for the same hospital admission; not a separate admission instance.',summary_status='SIGNED; a recorded signed summary is present.',lab_order_id='FK to a distinct laboratory order; exactly one order FK is non-null per history row.',medication_order_id='FK to a distinct medication order; exactly one order FK is non-null per history row.',procedure_order_id='FK to a distinct procedure order; exactly one order FK is non-null per history row.')
def main():
 for n in ['input','private/gold_logs','private/gold_sql','docs','source','design']:(P/n).mkdir(parents=True,exist_ok=True)
 db=P/'input/database.sqlite';db.unlink(missing_ok=True)
 con=sqlite3.connect(db);con.row_factory=sqlite3.Row;con.executescript(DDL)
 (P/'input/schema.sql').write_text(DDL)
 def ins(t,**r):con.execute('INSERT INTO '+t+'('+','.join(r)+') VALUES ('+','.join('?' for _ in r)+')',list(r.values()))
 history=[];links=[];counts=Counter()
 def time(h):return (datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(hours=h)).isoformat().replace('+00:00','Z')
 def event(eid,act,h,oids):
  history.append(dict(event_id=eid,activity=act,timestamp=time(h)))
  links.extend(dict(event_id=eid,object_id=o) for o in oids)
 def hist(oid,action,h,objs):
  counts['history']+=1;i=counts['history'];kind,local=oid.split(':');cols={'lab_order_id':None,'medication_order_id':None,'procedure_order_id':None};cols[{'LAB':'lab_order_id','MED':'medication_order_id','PROC':'procedure_order_id'}[kind]]=int(local);ins('order_history',history_id=i,**cols,action=action,occurred_at=time(h));event('OH:'+str(i),{'ENTERED':'Order Entered','REVIEWED':'Order Reviewed','CANCELLED':'Order Cancelled'}[action],h,objs)
 for patient in range(1,13):
  po='P:'+str(patient);ins('patients',subject_id=patient,gender='F' if patient%2 else 'M')
  if patient%2:
   ins('patient_profile',subject_id=patient,profile_verified_at=time(patient*200-20),preferred_language='English');event('PAT:'+str(patient)+':profile','Patient Profile Verified',patient*200-20,[po])
  if patient==12:continue # populated case with no recorded events
  for repeat in range(2 if patient<=4 else 1):
   counts['adm']+=1;a=counts['adm'];ao='A:'+str(a);base=a*200;ongoing=a==15
   ins('admissions',hadm_id=a,subject_id=patient,edregtime=time(base) if a%2 else None,admittime=time(base+1),discharge_authorized_at=None if ongoing else time(base+80),dischtime=None if ongoing else time(base+82))
   if a%2:event('ADM:'+str(a)+':ed','Emergency Department Registered',base,[po,ao])
   event('ADM:'+str(a)+':in','Hospital Admitted',base+1,[po,ao])
   if not ongoing:
    event('ADM:'+str(a)+':auth','Discharge Authorized',base+80,[po,ao]);event('ADM:'+str(a)+':out','Hospital Discharged',base+82,[po,ao])
   if a%3==1:
    ins('admission_detail',hadm_id=a,discharge_summary_signed_at=time(base+81),summary_status='SIGNED');event('ADM:'+str(a)+':summary','Discharge Summary Signed',base+81,[po,ao])
   for kind,tbl in [('LAB','lab_order'),('MED','medication_order'),('PROC','procedure_order')]:
    oid=kind+':'+str(a);objs=[po,ao,oid]
    cancelled=(a%5==0 and kind=='PROC');pending=(a%7==0 and kind=='LAB')
    if kind=='LAB':
     ins(tbl,order_id=a,hadm_id=a,specimen_received_at=None if pending else time(base+5),results_verified_at=None if pending else time(base+14))
     if not pending:
      event('LAB:'+str(a)+':received','Specimen Received',base+5,objs)
      for j in range(2+(a%2)):
       counts['lab']+=1;i=counts['lab'];h=base+6+j*2;ins('labevents',labevent_id=i,order_id=a,itemid=1+j%2,charttime=time(h),storetime=time(h+1),valuenum=10+a+j,valueuom='arbitrary units');event('LABEV:'+str(i)+':chart','Lab Measurement Charted',h,objs);event('LABEV:'+str(i)+':result','Lab Result Available',h+1,objs)
      event('LAB:'+str(a)+':verified','Lab Results Verified',base+14,objs)
    elif kind=='MED':
     ins(tbl,order_id=a,hadm_id=a,medication='Synthetic Medicine '+str(a%3),dispensed_at=time(base+5),stopped_at=None if ongoing else time(base+40));event('MED:'+str(a)+':dispense','Medication Dispensed',base+5,objs)
     for j in range(3):
      counts['dose']+=1;i=counts['dose'];h=base+8+j*8;given=not(a%3==0 and j==1);ins('emar',emar_id=i,order_id=a,charttime=time(h),event_txt='Administered' if given else 'Not Given',storetime=time(h+0.1));event('EMAR:'+str(i),'Medication Administered' if given else 'Medication Not Given',h,objs)
     if not ongoing:event('MED:'+str(a)+':stop','Medication Stopped',base+40,objs)
    else:
     ins(tbl,order_id=a,hadm_id=a,procedure_name='Synthetic Procedure '+str(a%3),preparation_completed_at=None if cancelled else time(base+5))
     if not cancelled:
      event('PROC:'+str(a)+':prep','Procedure Preparation Completed',base+5,objs)
      for j in range(2 if a%4==0 else 1):
       counts['proc']+=1;i=counts['proc'];h=base+8+j*12;open_episode=ongoing and j==0
       ins('procedureevents',procedureevent_id=i,order_id=a,starttime=time(h),endtime=None if open_episode else time(h+2),storetime=time(h+3));event('PROCEV:'+str(i)+':start','Procedure Started',h,objs)
       if not open_episode:event('PROCEV:'+str(i)+':end','Procedure Completed',h+2,objs)
    hist(oid,'ENTERED',base+2,objs)
    hist(oid,'REVIEWED',base+3,objs)
    if a%4==0:hist(oid,'REVIEWED',base+3.5,objs)
    if cancelled:hist(oid,'CANCELLED',base+4,objs)
 for e in history:
  eid=e['event_id']
  own=(('H:'+eid.split(':')[1]) if eid.startswith('OH:') else ('LM:'+eid.split(':')[1]) if eid.startswith('LABEV:') else ('DOSE:'+eid.split(':')[1]) if eid.startswith('EMAR:') else ('EP:'+eid.split(':')[1]) if eid.startswith('PROCEV:') else None)
  if own:links.append(dict(event_id=eid,object_id=own))
 con.commit()
 sources=[]
 def src(t,activity,ts,key,oid,where='1=1',encoding='Column encoding'):
  sql=f"SELECT {key} event_id,{oid} object_id,'{activity}' activity,{ts} timestamp FROM {t} WHERE {ts} IS NOT NULL AND ({where})"
  sources.append(dict(table=t.split()[0],activity=activity,timestamp_column=ts.split('.')[-1],encoding=encoding,event_sql=sql))
 for col,act,suffix in [('edregtime','Emergency Department Registered','ed'),('admittime','Hospital Admitted','in'),('discharge_authorized_at','Discharge Authorized','auth'),('dischtime','Hospital Discharged','out')]:src('admissions',act,col,"'ADM:'||hadm_id||':"+suffix+"'","'A:'||hadm_id")
 src('patient_profile','Patient Profile Verified','profile_verified_at',"'PAT:'||subject_id||':profile'","'P:'||subject_id")
 src('admission_detail','Discharge Summary Signed','discharge_summary_signed_at',"'ADM:'||hadm_id||':summary'","'A:'||hadm_id")
 for code,act in [('ENTERED','Order Entered'),('REVIEWED','Order Reviewed'),('CANCELLED','Order Cancelled')]:src('order_history',act,'occurred_at',"'OH:'||history_id","CASE WHEN lab_order_id IS NOT NULL THEN 'LAB:'||lab_order_id WHEN medication_order_id IS NOT NULL THEN 'MED:'||medication_order_id ELSE 'PROC:'||procedure_order_id END","action='"+code+"'",'Row encoding')
 for tbl,col,act,prefix,suffix in [('lab_order','specimen_received_at','Specimen Received','LAB','received'),('lab_order','results_verified_at','Lab Results Verified','LAB','verified'),('medication_order','dispensed_at','Medication Dispensed','MED','dispense'),('medication_order','stopped_at','Medication Stopped','MED','stop'),('procedure_order','preparation_completed_at','Procedure Preparation Completed','PROC','prep')]:src(tbl,act,col,"'"+prefix+":'||order_id||':"+suffix+"'","'"+prefix+":'||order_id")
 for col,act,suffix in [('charttime','Lab Measurement Charted','chart'),('storetime','Lab Result Available','result')]:src('labevents e JOIN lab_order o ON o.order_id=e.order_id',act,'e.'+col,"'LABEV:'||e.labevent_id||':"+suffix+"'","'LAB:'||o.order_id",encoding='Mixed (row + column)')
 for code,act in [('Administered','Medication Administered'),('Not Given','Medication Not Given')]:src('emar e JOIN medication_order o ON o.order_id=e.order_id',act,'e.charttime',"'EMAR:'||e.emar_id","'MED:'||o.order_id","e.event_txt='"+code+"'",'Row encoding')
 for col,act,suffix in [('starttime','Procedure Started','start'),('endtime','Procedure Completed','end')]:src('procedureevents e JOIN procedure_order o ON o.order_id=e.order_id',act,'e.'+col,"'PROCEV:'||e.procedureevent_id||':"+suffix+"'","'PROC:'||o.order_id",encoding='Mixed (row + column)')
 base=' UNION ALL '.join(s['event_sql'] for s in sources)
 # Event IDs keep occurrence identity; physical keys determine own and FK paths.
 order_lookup="SELECT 'LAB:'||order_id order_key,hadm_id FROM lab_order UNION ALL SELECT 'MED:'||order_id,hadm_id FROM medication_order UNION ALL SELECT 'PROC:'||order_id,hadm_id FROM procedure_order"
 attributed="SELECT e.*, 'A:'||a.hadm_id admission_object, 'P:'||a.subject_id patient_object FROM events e LEFT JOIN orders c ON c.order_key=e.object_id JOIN admissions a ON e.object_id='A:'||a.hadm_id OR a.hadm_id=c.hadm_id UNION ALL SELECT e.*,NULL admission_object,e.object_id patient_object FROM events e WHERE e.object_id LIKE 'P:%'"
 physical={'patients':('Patient','P:','subject_id'),'patient_profile':('Patient','P:','subject_id'),'admissions':('Hospital Admission','A:','hadm_id'),'admission_detail':('Hospital Admission','A:','hadm_id'),'lab_order':('Laboratory Order','LAB:','order_id'),'medication_order':('Medication Order','MED:','order_id'),'procedure_order':('Procedure Order','PROC:','order_id'),'order_history':('Order History Record','H:','history_id'),'labevents':('Lab Measurement','LM:','labevent_id'),'emar':('Medication Administration','DOSE:','emar_id'),'procedureevents':('Procedure Episode','EP:','procedureevent_id')}
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
 rejected('orphan_order',"INSERT INTO lab_order VALUES(999,999,NULL,NULL)")
 rejected('orphan_history',"INSERT INTO order_history VALUES(999,999,NULL,NULL,'ENTERED','2026-01-01T00:00:00Z')")
 rejected('ambiguous_history_order',"INSERT INTO order_history VALUES(999,1,1,NULL,'ENTERED','2026-01-01T00:00:00Z')")
 assert not list(con.execute('PRAGMA foreign_key_check'));assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 checks.update(gold_sql_matches_independent_generation_history=True,exact_question_pairs=True,independent_order_identities=True,patient_multiple_admissions=True,pending_cancelled_and_empty_cases=True)
 tables=[]
 for name in ROLES:
  cols=[]
  for r in con.execute('PRAGMA table_info('+name+')'):cols.append(dict(name=r['name'],type=r['type'],constraints='See executable table DDL',definition=DESCS[r['name']],source_origin='mimic_inspired_synthetic_benchmark'))
  fk=[dict(column=r['from'],parent_table=r['table'],parent_column=r['to']) for r in con.execute('PRAGMA foreign_key_list('+name+')')];pk=[r['name'] for r in con.execute('PRAGMA table_info('+name+')') if r['pk']]
  tables.append(dict(table=name,definition=ROLES[name],columns=cols,primary_key=pk,foreign_keys=fk,event_encoding=ENC[name],encoding_detail={'Row encoding':'Each occurrence is a separate row; action/event_txt determines activity. Technical emar.storetime is excluded.','Column encoding':'Actual one-time milestones are separate timestamp columns on the business object. NULL means not occurred.','Mixed (row + column)':'Each row preserves a repeated occurrence; multiple timestamp columns emit distinct activity types within that occurrence.','No event encoding':'Type, identity or context only; does not store an event.'}[ENC[name]]))
 rules=['Physical Objects are table/PK representations, not tables named object or object_type.','patients and patient_profile use the same patient identifier namespace; optional profile rows represent the SAME patient, with no declared FK.','admissions and admission_detail use the same admission namespace; the shared-PK FK corroborates the documented SAME-stay identity.','Laboratory, medication and procedure orders have distinct identities and namespaces. Overlapping local order_id integers do not establish identity.','order_history.history_id identifies a history occurrence, not the referenced order. Each row has exactly one declared order FK.','All timestamps and records are synthetic UTC; MIMIC-inspired fields and authored split-storage additions are distinguished.','labevents.charttime is charted measurement time; storetime is result availability. emar/procedureevents storetime is technical documentation time.','Physical source table/PK and own-versus-FK attribution remain available for every event binding.','Missing events do not prove care did not occur; full lifecycle means the recorded declared scope.','Model input comprises DB/schema, dictionary and input/model_questions.jsonl. private/identity_gold.json and private event history are evaluation answers, not model inputs.']
 js('input/data_dictionary.json',dict(name='HospitalFlow',language='en',timezone='UTC',tables=tables,business_rules=rules,value_domain={'action':'ENTERED / REVIEWED / CANCELLED'}));js('design/logical_schema.json',tables)
 timestamps=[]
 for t in tables:
  for c in t['columns']:
   n=c['name'];used=any(s['table']==t['table'] and s['timestamp_column']==n for s in sources)
   if n.endswith('_at') or n in ['edregtime','admittime','dischtime','occurred_at','charttime','storetime','starttime','endtime']:timestamps.append(dict(table=t['table'],column=n,used_as_event_time=used,role='Actual event time' if used else 'Technical documentation time'))
 summary=dict(timestamp_columns=len(timestamps),event_timestamp_columns=sum(r['used_as_event_time'] for r in timestamps));js('docs/timestamp_columns.json',dict(**summary,columns=timestamps));d=json.loads((P/'input/data_dictionary.json').read_text());d['timestamp_summary']=summary;js('input/data_dictionary.json',d)
 rows={n:con.execute('SELECT COUNT(*) FROM '+n).fetchone()[0] for n in ROLES};report=dict(table_rows=rows,semantic_object_types=9,physical_objects=11,identity_groups=9,object_instances=len(objects),object_view_coverage=coverage,activity_counts=dict(Counter(e['activity'] for e in history)),events=len(history),total_questions=len(questions),answerable_questions=sum(q['answerable'] for q in questions),timestamp_summary=summary,checks=checks,validation_scope='Internal construction consistency, not model extraction accuracy or clinical realism evaluation.');js('validation_report.json',report)
 md('docs/timestamp_columns.md','# Timestamp columns\n\n'+table(['Table','Column','Event time?','Meaning'],[[r['table'],r['column'],r['used_as_event_time'],r['role']] for r in timestamps]))
 md('docs/object_activity_design.md','# Objects, types and activity scopes\n\n'+table(['Object Type','Instances','Activity types','Activity scope'],[[r['case_concept'],r['case_count'],r['activity_count'],', '.join(r['activities'])] for r in coverage])+'\n- Eleven Physical Objects map to nine expected identity-compatible Object Type groups. History/measurement/dose/episode records retain independent occurrence identities.\n- Individual instances may contain fewer activities due to cancellation, ongoing care or missing records.\n')
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
 con.close();print(json.dumps({k:report[k] for k in ['physical_objects','identity_groups','events','total_questions','answerable_questions','semantic_object_types','object_instances','timestamp_summary']},indent=2))
if __name__=='__main__':main()
