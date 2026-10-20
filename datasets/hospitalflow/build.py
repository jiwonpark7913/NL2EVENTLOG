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
CREATE TABLE object_type(type_code TEXT PRIMARY KEY NOT NULL, type_name TEXT NOT NULL UNIQUE, definition TEXT NOT NULL);
CREATE TABLE object(object_id TEXT PRIMARY KEY NOT NULL, type_code TEXT NOT NULL REFERENCES object_type(type_code), UNIQUE(object_id,type_code));
CREATE TABLE patients(subject_id INTEGER PRIMARY KEY NOT NULL, object_id TEXT NOT NULL UNIQUE REFERENCES object(object_id), gender TEXT NOT NULL CHECK(gender IN ('F','M')));
CREATE TABLE admissions(hadm_id INTEGER PRIMARY KEY NOT NULL, subject_id INTEGER NOT NULL REFERENCES patients(subject_id), object_id TEXT NOT NULL UNIQUE REFERENCES object(object_id), edregtime TEXT, admittime TEXT NOT NULL, discharge_authorized_at TEXT, dischtime TEXT, UNIQUE(hadm_id,subject_id), CHECK(edregtime IS NULL OR edregtime<=admittime), CHECK(dischtime IS NULL OR discharge_authorized_at<=dischtime));
CREATE TABLE clinical_order(object_id TEXT PRIMARY KEY NOT NULL REFERENCES object(object_id), subject_id INTEGER NOT NULL, hadm_id INTEGER NOT NULL, order_kind TEXT NOT NULL CHECK(order_kind IN ('LAB','MED','PROC')), UNIQUE(object_id,order_kind), FOREIGN KEY(hadm_id,subject_id) REFERENCES admissions(hadm_id,subject_id));
CREATE TABLE lab_order(order_id INTEGER PRIMARY KEY NOT NULL, object_id TEXT NOT NULL UNIQUE, order_kind TEXT NOT NULL DEFAULT 'LAB' CHECK(order_kind='LAB'), specimen_received_at TEXT, results_verified_at TEXT, FOREIGN KEY(object_id,order_kind) REFERENCES clinical_order(object_id,order_kind));
CREATE TABLE medication_order(order_id INTEGER PRIMARY KEY NOT NULL, object_id TEXT NOT NULL UNIQUE, order_kind TEXT NOT NULL DEFAULT 'MED' CHECK(order_kind='MED'), medication TEXT NOT NULL, dispensed_at TEXT, stopped_at TEXT, FOREIGN KEY(object_id,order_kind) REFERENCES clinical_order(object_id,order_kind));
CREATE TABLE procedure_order(order_id INTEGER PRIMARY KEY NOT NULL, object_id TEXT NOT NULL UNIQUE, order_kind TEXT NOT NULL DEFAULT 'PROC' CHECK(order_kind='PROC'), procedure_name TEXT NOT NULL, preparation_completed_at TEXT, FOREIGN KEY(object_id,order_kind) REFERENCES clinical_order(object_id,order_kind));
CREATE TABLE order_history(history_id INTEGER PRIMARY KEY NOT NULL, object_id TEXT NOT NULL REFERENCES clinical_order(object_id), action TEXT NOT NULL CHECK(action IN ('ENTERED','REVIEWED','CANCELLED')), occurred_at TEXT NOT NULL);
CREATE TABLE labevents(labevent_id INTEGER PRIMARY KEY NOT NULL, order_id INTEGER NOT NULL REFERENCES lab_order(order_id), itemid INTEGER NOT NULL, charttime TEXT NOT NULL, storetime TEXT NOT NULL, valuenum REAL, valueuom TEXT, CHECK(charttime<=storetime));
CREATE TABLE emar(emar_id INTEGER PRIMARY KEY NOT NULL, order_id INTEGER NOT NULL REFERENCES medication_order(order_id), charttime TEXT NOT NULL, event_txt TEXT NOT NULL CHECK(event_txt IN ('Administered','Not Given')), storetime TEXT NOT NULL, CHECK(charttime<=storetime));
CREATE TABLE procedureevents(procedureevent_id INTEGER PRIMARY KEY NOT NULL, order_id INTEGER NOT NULL REFERENCES procedure_order(order_id), starttime TEXT NOT NULL, endtime TEXT, storetime TEXT NOT NULL, CHECK(endtime IS NULL OR starttime<=endtime));
'''
# Registry type membership is enforced on inserts AND updates on either side.
for tbl,typ in [('patients','PATIENT'),('admissions','ADMISSION'),('clinical_order','CLINICAL_ORDER')]:
 for op in ['INSERT','UPDATE']:
  DDL+=f"CREATE TRIGGER {tbl}_type_{op.lower()} BEFORE {op} ON {tbl} WHEN NOT EXISTS(SELECT 1 FROM object WHERE object_id=NEW.object_id AND type_code='{typ}') BEGIN SELECT RAISE(ABORT,'Wrong object type'); END;\n"
 DDL+=f"CREATE TRIGGER object_{tbl}_type_update BEFORE UPDATE ON object WHEN EXISTS(SELECT 1 FROM {tbl} WHERE object_id=OLD.object_id) AND NEW.type_code<>'{typ}' BEGIN SELECT RAISE(ABORT,'Type conflicts with business record'); END;\n"
ROLES={
'object_type':'Semantic object types shared across business tables; not activities or case instances.',
'object':'Globally unique object identities and their semantic types; no events are stored here.',
'patients':'Synthetic patient identity, inspired by MIMIC subject_id.',
'admissions':'Distinct hospital stays per patient with actual admission/discharge milestones.',
'clinical_order':'Authored common parent for laboratory, medication and procedure orders; not a MIMIC table.',
'lab_order':'Authored laboratory-order subtype; several measurements may belong to one order.',
'medication_order':'Authored medication-order subtype; repeated doses belong to one order.',
'procedure_order':'Authored procedure-order subtype; repeated execution episodes belong to one order.',
'order_history':'Repeated order actions, inspired by provider order transaction semantics; not a copy of poe.',
'labevents':'Measurement occurrences with separately charted and available-result times, inspired by MIMIC labevents.',
'emar':'Medication administration or omission occurrences, inspired by MIMIC emar.',
'procedureevents':'Procedure execution episodes with start/end times, inspired by MIMIC procedureevents.'}
ENC={**{n:'No event encoding' for n in ['object_type','object','patients','clinical_order']},**{n:'Column encoding' for n in ['admissions','lab_order','medication_order','procedure_order']},**{n:'Row encoding' for n in ['order_history','emar']},**{n:'Mixed (row + column)' for n in ['labevents','procedureevents']}}
DESCS={'object_id':'Global object identity; distinct from local subtype order_id.','type_code':'Semantic type code, constrained by a foreign key or registry membership trigger.','type_name':'English name of the semantic object type.','definition':'Definition of the semantic object type.','subject_id':'Synthetic patient identity; can occur in multiple hospital admissions.','hadm_id':'Synthetic unique hospital admission identity.','gender':'Synthetic demographic category, F or M.','order_id':'Subtype-local order identity; deliberately overlaps across the three order tables.','order_kind':'LAB, MED or PROC; composite FK enforces membership in the matching common-parent subtype.','edregtime':'Actual emergency department registration time; NULL for admissions without ED registration.','admittime':'Actual hospital admission time.','discharge_authorized_at':'Authored actual discharge authorization time; NULL if not occurred.','dischtime':'Actual hospital discharge time; NULL for an ongoing stay.','specimen_received_at':'Authored actual receipt of a specimen for this order.','results_verified_at':'Authored actual verification of results after all recorded measurements become available.','medication':'Fictional medication label; no treatment recommendation.','dispensed_at':'Authored actual dispensing time.','stopped_at':'Authored actual stop time; NULL if not stopped.','procedure_name':'Fictional procedure label.','preparation_completed_at':'Authored actual completion of preparation for this procedure order.','history_id':'Unique occurrence identity for a repeated order action.','action':'ENTERED, REVIEWED or CANCELLED order action; repeated REVIEWED is permitted.','occurred_at':'Actual UTC time of the order action.','labevent_id':'Unique measurement occurrence identity; repeated item measurements remain distinct.','itemid':'Synthetic laboratory concept ID; no original MIMIC item code is claimed.','charttime':'Actual charted measurement time in labevents; medication administration/omission time in emar. Not lab result-availability time.','storetime':'For labevents, time result becomes available; for emar/procedureevents, system record time excluded as a separate business event.','valuenum':'Synthetic measurement numeric value.','valueuom':'Measurement unit; all current synthetic measurements use arbitrary units.','emar_id':'Unique synthetic dose occurrence ID; simplified from the MIMIC identity structure.','event_txt':'Administered or Not Given; selects the activity of this dose occurrence.','procedureevent_id':'Authored unique procedure episode identity; not an original MIMIC column.','starttime':'Actual procedure episode start.','endtime':'Actual procedure episode completion; NULL if ongoing.'}
def main():
 for n in ['input','private/gold_logs','private/gold_sql','docs','source','design']:(P/n).mkdir(parents=True,exist_ok=True)
 db=P/'input/database.sqlite';db.unlink(missing_ok=True)
 con=sqlite3.connect(db);con.row_factory=sqlite3.Row;con.executescript(DDL)
 (P/'input/schema.sql').write_text(DDL)
 def ins(t,**r):con.execute('INSERT INTO '+t+'('+','.join(r)+') VALUES ('+','.join('?' for _ in r)+')',list(r.values()))
 def reg(oid,typ):ins('object',object_id=oid,type_code=typ)
 for code,name in [('PATIENT','Patient'),('ADMISSION','Hospital Admission'),('CLINICAL_ORDER','Clinical Order')]:ins('object_type',type_code=code,type_name=name,definition='Individual '+name.lower()+' identity; subtype populations do not create new types.')
 history=[];links=[];counts=Counter();order_info={}
 def time(h):return (datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(hours=h)).isoformat().replace('+00:00','Z')
 def event(eid,act,h,oids):
  history.append(dict(event_id=eid,activity=act,timestamp=time(h)))
  links.extend(dict(event_id=eid,object_id=o) for o in oids)
 def hist(oid,action,h,objs):
  counts['history']+=1;i=counts['history'];ins('order_history',history_id=i,object_id=oid,action=action,occurred_at=time(h));event('OH:'+str(i),{'ENTERED':'Order Entered','REVIEWED':'Order Reviewed','CANCELLED':'Order Cancelled'}[action],h,objs)
 for patient in range(1,13):
  po='P:'+str(patient);reg(po,'PATIENT');ins('patients',subject_id=patient,object_id=po,gender='F' if patient%2 else 'M')
  if patient==12:continue # populated case with no recorded events
  for repeat in range(2 if patient<=4 else 1):
   counts['adm']+=1;a=counts['adm'];ao='A:'+str(a);reg(ao,'ADMISSION');base=a*200;ongoing=a==15
   ins('admissions',hadm_id=a,subject_id=patient,object_id=ao,edregtime=time(base) if a%2 else None,admittime=time(base+1),discharge_authorized_at=None if ongoing else time(base+80),dischtime=None if ongoing else time(base+82))
   if a%2:event('ADM:'+str(a)+':ed','Emergency Department Registered',base,[po,ao])
   event('ADM:'+str(a)+':in','Hospital Admitted',base+1,[po,ao])
   if not ongoing:
    event('ADM:'+str(a)+':auth','Discharge Authorized',base+80,[po,ao]);event('ADM:'+str(a)+':out','Hospital Discharged',base+82,[po,ao])
   for kind,tbl in [('LAB','lab_order'),('MED','medication_order'),('PROC','procedure_order')]:
    oid=kind+':'+str(a);reg(oid,'CLINICAL_ORDER');ins('clinical_order',object_id=oid,subject_id=patient,hadm_id=a,order_kind=kind);objs=[po,ao,oid];order_info[oid]=dict(subject_id=patient,hadm_id=a,order_kind=kind)
    cancelled=(a%5==0 and kind=='PROC');pending=(a%7==0 and kind=='LAB')
    hist(oid,'ENTERED',base+2,objs)
    hist(oid,'REVIEWED',base+3,objs)
    if a%4==0:hist(oid,'REVIEWED',base+3.5,objs)
    if cancelled:hist(oid,'CANCELLED',base+4,objs)
    if kind=='LAB':
     ins(tbl,order_id=a,object_id=oid,specimen_received_at=None if pending else time(base+5),results_verified_at=None if pending else time(base+14))
     if not pending:
      event('LAB:'+str(a)+':received','Specimen Received',base+5,objs)
      for j in range(2+(a%2)):
       counts['lab']+=1;i=counts['lab'];h=base+6+j*2;ins('labevents',labevent_id=i,order_id=a,itemid=1+j%2,charttime=time(h),storetime=time(h+1),valuenum=10+a+j,valueuom='arbitrary units');event('LABEV:'+str(i)+':chart','Lab Measurement Charted',h,objs);event('LABEV:'+str(i)+':result','Lab Result Available',h+1,objs)
      event('LAB:'+str(a)+':verified','Lab Results Verified',base+14,objs)
    elif kind=='MED':
     ins(tbl,order_id=a,object_id=oid,medication='Synthetic Medicine '+str(a%3),dispensed_at=time(base+5),stopped_at=None if ongoing else time(base+40));event('MED:'+str(a)+':dispense','Medication Dispensed',base+5,objs)
     for j in range(3):
      counts['dose']+=1;i=counts['dose'];h=base+8+j*8;given=not(a%3==0 and j==1);ins('emar',emar_id=i,order_id=a,charttime=time(h),event_txt='Administered' if given else 'Not Given',storetime=time(h+0.1));event('EMAR:'+str(i),'Medication Administered' if given else 'Medication Not Given',h,objs)
     if not ongoing:event('MED:'+str(a)+':stop','Medication Stopped',base+40,objs)
    else:
     ins(tbl,order_id=a,object_id=oid,procedure_name='Synthetic Procedure '+str(a%3),preparation_completed_at=None if cancelled else time(base+5))
     if not cancelled:
      event('PROC:'+str(a)+':prep','Procedure Preparation Completed',base+5,objs)
      for j in range(2 if a%4==0 else 1):
       counts['proc']+=1;i=counts['proc'];h=base+8+j*12;open_episode=ongoing and j==0
       ins('procedureevents',procedureevent_id=i,order_id=a,starttime=time(h),endtime=None if open_episode else time(h+2),storetime=time(h+3));event('PROCEV:'+str(i)+':start','Procedure Started',h,objs)
       if not open_episode:event('PROCEV:'+str(i)+':end','Procedure Completed',h+2,objs)
 con.commit()
 sources=[]
 def src(t,activity,ts,key,oid,where='1=1',encoding='Column encoding'):
  sql=f"SELECT {key} event_id,{oid} object_id,'{activity}' activity,{ts} timestamp FROM {t} WHERE {ts} IS NOT NULL AND ({where})"
  sources.append(dict(table=t.split()[0],activity=activity,timestamp_column=ts.split('.')[-1],encoding=encoding,event_sql=sql))
 for col,act,suffix in [('edregtime','Emergency Department Registered','ed'),('admittime','Hospital Admitted','in'),('discharge_authorized_at','Discharge Authorized','auth'),('dischtime','Hospital Discharged','out')]:src('admissions',act,col,"'ADM:'||hadm_id||':"+suffix+"'",'object_id')
 for code,act in [('ENTERED','Order Entered'),('REVIEWED','Order Reviewed'),('CANCELLED','Order Cancelled')]:src('order_history',act,'occurred_at',"'OH:'||history_id",'object_id',"action='"+code+"'",'Row encoding')
 for tbl,col,act,prefix,suffix in [('lab_order','specimen_received_at','Specimen Received','LAB','received'),('lab_order','results_verified_at','Lab Results Verified','LAB','verified'),('medication_order','dispensed_at','Medication Dispensed','MED','dispense'),('medication_order','stopped_at','Medication Stopped','MED','stop'),('procedure_order','preparation_completed_at','Procedure Preparation Completed','PROC','prep')]:src(tbl,act,col,"'"+prefix+":'||order_id||':"+suffix+"'",'object_id')
 for col,act,suffix in [('charttime','Lab Measurement Charted','chart'),('storetime','Lab Result Available','result')]:src('labevents e JOIN lab_order o ON o.order_id=e.order_id',act,'e.'+col,"'LABEV:'||e.labevent_id||':"+suffix+"'",'o.object_id',encoding='Mixed (row + column)')
 for code,act in [('Administered','Medication Administered'),('Not Given','Medication Not Given')]:src('emar e JOIN medication_order o ON o.order_id=e.order_id',act,'e.charttime',"'EMAR:'||e.emar_id",'o.object_id',"e.event_txt='"+code+"'",'Row encoding')
 for col,act,suffix in [('starttime','Procedure Started','start'),('endtime','Procedure Completed','end')]:src('procedureevents e JOIN procedure_order o ON o.order_id=e.order_id',act,'e.'+col,"'PROCEV:'||e.procedureevent_id||':"+suffix+"'",'o.object_id',encoding='Mixed (row + column)')
 base=' UNION ALL '.join(s['event_sql'] for s in sources)
 # Public SQL derives event/case relationships from actual business FK joins.
 attributed="SELECT e.*,a.object_id admission_object,p.object_id patient_object FROM events e LEFT JOIN clinical_order c ON c.object_id=e.object_id JOIN admissions a ON a.object_id=e.object_id OR a.hadm_id=c.hadm_id JOIN patients p ON p.subject_id=a.subject_id"
 viewdef={'Patient':('patient_object',None,'PATIENT'),'Hospital Admission':('admission_object',None,'ADMISSION'),'Clinical Order':('object_id',None,'CLINICAL_ORDER'),'Laboratory Order':('object_id','LAB','CLINICAL_ORDER'),'Medication Order':('object_id','MED','CLINICAL_ORDER'),'Procedure Order':('object_id','PROC','CLINICAL_ORDER')}
 objects=[dict(r) for r in con.execute('SELECT * FROM object')];byoid={r['object_id']:r for r in objects};linked=defaultdict(set)
 for r in links:linked[r['event_id']].add(r['object_id'])
 def population(view):
  _,kind,typ=viewdef[view];return [o['object_id'] for o in objects if o['type_code']==typ and (not kind or order_info[o['object_id']]['order_kind']==kind)]
 def oracle(view,acts):
  pop=set(population(view));return sorted([dict(event_id=e['event_id'],case_id=o,activity=e['activity'],timestamp=e['timestamp']) for e in history if e['activity'] in acts for o in linked[e['event_id']]&pop],key=lambda r:(r['case_id'],r['timestamp'],r['event_id']))
 def compile_sql(view,acts):
  key,kind,typ=viewdef[view];actlist=','.join("'"+a.replace("'","''")+"'" for a in acts);extra=" AND c.order_kind='"+kind+"'" if kind else ''
  return 'WITH events AS ('+base+'), attributed AS ('+attributed+") SELECT e.event_id,e."+key+" case_id,e.activity,e.timestamp FROM attributed e JOIN object o ON o.object_id=e."+key+" LEFT JOIN clinical_order c ON c.object_id=o.object_id WHERE o.type_code='"+typ+"'"+extra+' AND e.activity IN ('+actlist+') ORDER BY case_id,timestamp,event_id;'
 coverage=[];catalog=[]
 for view in viewdef:
  pop=population(view);acts=sorted({e['activity'] for e in history if linked[e['event_id']]&set(pop)})
  catalog.append(dict(case_concept=view,object_type=viewdef[view][2],population=pop,activities=acts,default_scope='All recorded events explicitly linked through business keys; no unrecorded care is inferred.'))
  coverage.append(dict(case_concept=view,object_type=viewdef[view][2],case_count=len(pop),activity_count=len(acts),activities=acts,event_rows=len(oracle(view,acts)),cases_without_events=len(set(pop)-{r['case_id'] for r in oracle(view,acts)})))
 js('input/task_scope_catalog.json',dict(setting='Catalog-assisted',views=catalog,semantic_object_types=3,case_population_scopes=6))
 seeds=json.loads((P/'source/question_seeds.json').read_text());par=json.loads((P/'source/llm_paraphrases.json').read_text());questions=[];gold=[]
 for seed in seeds:
  view=seed['view'];full='activities' not in seed;acts=next(c['activities'] for c in catalog if c['case_concept']==view) if full else seed['activities'];answerable=seed.get('answerable',True);qid=seed['id'];pair=qid+'P'
  es=dict(version='hospital-es-1',case_concept=view,object_type=viewdef[view][2],subtype_filter=viewdef[view][1],activities=acts,case_population=population(view),activity_sources=[s for s in sources if s['activity'] in acts],compiled_sql=compile_sql(view,acts)) if answerable else None
  for ident,text,typ,other in [(qid,seed['question'],'Q3' if full else 'Q1',pair),(pair,par['outputs'][qid],'Q4' if full else 'Q2',qid)]:
   q=dict(id=ident,question=text,question_type=typ,question_type_name={'Q1':'Explicit','Q2':'Paraphrased','Q3':'Full Lifecycle','Q4':'Full Lifecycle Paraphrased'}[typ],pair_of=other,pair_group_id=qid,case_concept=view,answerable=answerable,included_information='Case concept only' if full else 'Case concept and explicit activity scope',requested_activity_count=len(acts),extractable_activity_count=len(acts) if answerable else 0,activity_scope_explicit=not full)
   q['question_id']=ident;q['text']=text;q['answerability']='answerable' if answerable else 'non_answerable';questions.append(q);g=dict(id=ident,question_id=ident,question_type=typ,pair_of=other,answerability=q['answerability'],answerable=answerable,es=es,process_view=dict(case_concept=view,object_type=viewdef[view][2],activities=acts),requested_activities=acts)
   if answerable:
    sql=es['compiled_sql'];actual=[dict(r) for r in con.execute(sql)];expected=oracle(view,acts);assert actual==expected,(ident,'SQL/oracle mismatch');assert len({(r['case_id'],r['event_id']) for r in actual})==len(actual)
    f='private/gold_logs/'+ident+'.csv'
    with (P/f).open('w',newline='') as stream:w=csv.DictWriter(stream,fieldnames=['event_id','case_id','activity','timestamp']);w.writeheader();w.writerows(expected)
    (P/'private/gold_sql'/str(ident+'.sql')).write_text(sql+'\n');g.update(csv=f,sql='private/gold_sql/'+ident+'.sql',event_count=len(expected),case_count=len({r['case_id'] for r in expected}))
   else:g['reason']='No claim or payment records/timestamps exist in this DB; no Gold CSV is emitted.'
   g.update({k:q[k] for k in ['question_type_name','pair_group_id','included_information','requested_activity_count','extractable_activity_count','activity_scope_explicit']});gold.append(g)
 jl('input/questions.jsonl',questions);jl('input/model_questions.jsonl',[dict(id=q['id'],question=q['question']) for q in questions]);jl('private/gold.jsonl',gold);jl('private/canonical_history.jsonl',history);js('private/object_event_links.json',links);js('private/persistence_mapping.json',sources)
 # Adversarial membership tests run within savepoints; DB remains unchanged.
 checks={}
 def rejected(name,sql):
  con.execute('SAVEPOINT probe')
  try:con.execute(sql)
  except sqlite3.IntegrityError:checks[name]=True
  else:raise AssertionError(name+' incorrectly accepted')
  finally:con.execute('ROLLBACK TO probe');con.execute('RELEASE probe')
 rejected('wrong_registry_type',"INSERT INTO patients VALUES(999,'LAB:1','F')")
 rejected('wrong_subtype',"INSERT INTO lab_order VALUES(999,'MED:1','LAB',NULL,NULL)")
 reg('LAB:probe','CLINICAL_ORDER')
 rejected('cross_admission_patient',"INSERT INTO clinical_order VALUES('LAB:probe',2,1,'LAB')")
 con.execute("DELETE FROM object WHERE object_id='LAB:probe'")
 rejected('type_change_rejected',"UPDATE object SET type_code='PATIENT' WHERE object_id='LAB:1'")
 rejected('orphan_event',"INSERT INTO emar VALUES(999,999,'2026-01-01T00:00:00Z','Administered','2026-01-01T00:00:00Z')")
 assert not list(con.execute('PRAGMA foreign_key_check'));assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 assert len(population('Clinical Order'))==sum(len(population(v)) for v in ['Laboratory Order','Medication Order','Procedure Order'])
 assert len({o for v in ['Laboratory Order','Medication Order','Procedure Order'] for o in population(v)})==45
 for g in gold[::2]:
  gp=next(x for x in gold if x['id']==g['id']+'P');assert g['es']==gp['es'] and g['answerable']==gp['answerable']
  if g['answerable']:assert (P/g['csv']).read_bytes()==(P/gp['csv']).read_bytes()
 checks.update(gold_sql_matches_independent_generation_history=True,exact_question_pairs=True,subtypes_partition_common_type=True,local_ids_overlap_without_case_collision=True,patient_multiple_admissions=True,pending_cancelled_and_empty_cases=True)
 tables=[]
 for name in ROLES:
  cols=[]
  for r in con.execute('PRAGMA table_info('+name+')'):cols.append(dict(name=r['name'],type=r['type'],constraints='See executable table DDL',definition=DESCS[r['name']],source_origin='mimic_inspired_synthetic_benchmark'))
  fk=[dict(column=r['from'],parent_table=r['table'],parent_column=r['to']) for r in con.execute('PRAGMA foreign_key_list('+name+')')];pk=[r['name'] for r in con.execute('PRAGMA table_info('+name+')') if r['pk']]
  tables.append(dict(table=name,definition=ROLES[name],columns=cols,primary_key=pk,foreign_keys=fk,event_encoding=ENC[name],encoding_detail={'Row encoding':'Each occurrence is a separate row; action/event_txt determines activity. Technical emar.storetime is excluded.','Column encoding':'Actual one-time milestones are separate timestamp columns on the business object. NULL means not occurred.','Mixed (row + column)':'Each row preserves a repeated occurrence; multiple timestamp columns emit distinct activity types within that occurrence.','No event encoding':'Type, identity or context only; does not store an event.'}[ENC[name]]))
 rules=['Three order subtype tables share Clinical Order type; cases remain separate globally unique objects.','Object/type registry contains identity and classification, not precomputed event/case links.','All timestamps and all records are synthetic UTC; no MIMIC patient data is redistributed.','MIMIC-inspired relationships are adapted; lab/procedure order FKs and common object model are authored.','Patient identity never merges distinct admission cases. Composite admission/patient FK rejects cross-patient attribution.','labevents.charttime is a charted measurement time; storetime is result availability. They are distinct activities, not two names for one event.','emar.storetime and procedureevents.storetime are documentation times, excluded from business-event extraction.','Missing events do not prove care did not occur. Full lifecycle means all recorded events in the declared scope.','Repeated order reviews, doses, measurements and procedure episodes retain occurrence IDs.','Model input is input/model_questions.jsonl plus DB/schema and catalog; answerability, counts and private Gold are evaluation annotations.']
 js('input/data_dictionary.json',dict(name='HospitalFlow',language='en',timezone='UTC',tables=tables,business_rules=rules,value_domain={'order_kind':'LAB / MED / PROC','type_code':'PATIENT / ADMISSION / CLINICAL_ORDER'}));js('design/logical_schema.json',tables)
 timestamps=[]
 for t in tables:
  for c in t['columns']:
   n=c['name'];used=any(s['table']==t['table'] and s['timestamp_column']==n for s in sources)
   if n.endswith('_at') or n in ['edregtime','admittime','dischtime','occurred_at','charttime','storetime','starttime','endtime']:timestamps.append(dict(table=t['table'],column=n,used_as_event_time=used,role='Actual event time' if used else 'Technical documentation time'))
 summary=dict(timestamp_columns=len(timestamps),event_timestamp_columns=sum(r['used_as_event_time'] for r in timestamps));js('docs/timestamp_columns.json',dict(**summary,columns=timestamps));d=json.loads((P/'input/data_dictionary.json').read_text());d['timestamp_summary']=summary;js('input/data_dictionary.json',d)
 rows={n:con.execute('SELECT COUNT(*) FROM '+n).fetchone()[0] for n in ROLES};report=dict(table_rows=rows,semantic_object_types=3,object_instances=len(objects),object_view_coverage=coverage,activity_counts=dict(Counter(e['activity'] for e in history)),events=len(history),total_questions=len(questions),answerable_questions=sum(q['answerable'] for q in questions),timestamp_summary=summary,checks=checks,validation_scope='Internal construction consistency, not model extraction accuracy or clinical realism evaluation.');js('validation_report.json',report)
 md('docs/timestamp_columns.md','# Timestamp columns\n\n'+table(['Table','Column','Event time?','Meaning'],[[r['table'],r['column'],r['used_as_event_time'],r['role']] for r in timestamps]))
 md('docs/object_activity_design.md','# Objects, types and activity scopes\n\n'+table(['Case population','Semantic type','Objects','Activity types','Activity scope'],[[r['case_concept'],r['object_type'],r['case_count'],r['activity_count'],', '.join(r['activities'])] for r in coverage])+'\n- Six case population scopes use three semantic object types; subtype scopes are not additional semantic types.\n- Individual instances may have fewer activities due to cancellation, ongoing care or no records.\n')
 js('design/object_activity_design.json',coverage)
 md('docs/object_event_logs.md','# Full lifecycle Gold logs\n\n'+table(['Population','Q3','Q4','Objects','Cases without events'],[[v,'HF'+str(i).zfill(2),'HF'+str(i).zfill(2)+'P',len(population(v)),coverage[i-1]['cases_without_events']] for i,v in enumerate(viewdef,1)])+'\n- Gold CSVs contain events only. Empty cases remain in ES.case_population and the task scope catalog.\n- Query-specific CSVs are case-based logs, not OCEL. Shared events may occur under different cases in different process views.\n')
 stats=[]
 for typ in ['Q1','Q2','Q3','Q4']:
  qs=[q for q in questions if q['question_type']==typ];stats.append([typ,len(qs),sum(q['answerable'] for q in qs),sum(not q['answerable'] for q in qs),f"{sum(q['requested_activity_count'] for q in qs)/len(qs):.2f}"])
 stattable=table(['Type','Questions','Answerable','Non-answerable','Avg. requested activity types'],stats)
 md('docs/questions.md','# HospitalFlow questions\n\n## Question types and pairs\n\n'+stattable+'\n- Average includes all requests in the type, including unsupported activity requests.\n- Process View includes the case concept and activity scope. Q3/Q4 leave the scope implicit via the catalog.\n- Each P question is an assistant-LLM paraphrase of the frozen seed; prompts and outputs are saved in source/llm_paraphrases.json.\n\n'+table(['ID','Type','Paired with','Answerability','Requested activities','Extractable activities','Question'],[[q['id'],q['question_type'],q['pair_of'],'Answerable' if q['answerable'] else 'Non-answerable',q['requested_activity_count'],q['extractable_activity_count'],q['question']] for q in questions]))
 md('README.md','# HospitalFlow dataset\n\n- **Purpose:** validate one semantic object type spanning multiple business tables.\n- **Source:** public MIMIC-IV schema documentation with wholly synthetic records and authored extensions.\n\n'+table(['Dataset','Tables','Object types','Activity types','Timestamp columns','Event timestamp columns','Distinct events','Questions','Gold CSVs'],[['HospitalFlow',len(tables),3,len(report['activity_counts']),summary['timestamp_columns'],summary['event_timestamp_columns'],len(history),len(questions),report['answerable_questions']]])+'\n- **Objects:** '+str(len(objects))+' actual instances; six case population scopes over three semantic types.\n- Counts include identity/type infrastructure tables; these do not create business events.\n\n## Object and object type design\n\n- object_type defines Patient, Hospital Admission and Clinical Order.\n- object assigns every actual object a globally unique identity and exactly one type.\n- lab_order, medication_order and procedure_order all refer to clinical_order; all these objects share Clinical Order type.\n- LAB:1, MED:1 and PROC:1 deliberately share local order_id=1, while remaining three separate cases.\n- The common-type lifecycle must equal the union of the three subtype populations without ID collisions or duplicate case/event pairs.\n- This supertype/subtype design is authored for the benchmark, not supplied by MIMIC.\n- [Inspectable type membership and SQL examples](docs/object_type_verification.md)\n\n## Scenarios and activities\n\n'+(P/'docs/object_activity_design.md').read_text().split('\n\n',1)[1]+'\n## Event storage\n\n'+table(['Table','Encoding'],[[n,ENC[n]] for n in ROLES])+'\n- Column tables store one-time milestones; row tables preserve repeated actions.\n- Mixed tables preserve repeated occurrences and split their distinct milestones into activities.\n- [Timestamp meanings](docs/timestamp_columns.md)\n\n## Question types and pairs\n\n'+stattable+'\n- Q1/Q3 seeds are frozen before assistant-LLM paraphrasing into Q2/Q4; rebuilding reuses saved outputs. No external model call is claimed.\n- Each pair has identical ES and Gold; unsupported pairs have no CSV.\n- Avg. requested activity types includes unsupported requests.\n- [Questions and activity counts](docs/questions.md)\n- [LLM paraphrase prompts and outputs](source/llm_paraphrases.json)\n\n## Build and validation\n\n- Run `python datasets/hospitalflow/build.py`, `python make_docs.py`, then `python datasets/hospitalflow/validate.py` from the repository root.\n- Independent generation-time event/object history is compared with each SQL result and CSV.\n- Checks cover wrong types, wrong subtypes, cross-patient admissions, orphan events, local ID collisions, repetition, cancellation, ongoing care, empty cases and exact pairs.\n- Tests establish internal consistency, not clinical realism or model accuracy.\n- Model-facing questions are input/model_questions.jsonl; enriched questions.jsonl contains evaluation annotations.\n- [Source and adaptation mapping](design/source_mapping.json)\n- [Source references](source/references.md)\n- [Construction plan](design/plan.md)\n- [Object-specific Gold logs](docs/object_event_logs.md)\n')
 query="SELECT o.type_code,c.order_kind,o.object_id,l.order_id lab_local_id,m.order_id medication_local_id,p.order_id procedure_local_id FROM object o JOIN clinical_order c USING(object_id) LEFT JOIN lab_order l USING(object_id) LEFT JOIN medication_order m USING(object_id) LEFT JOIN procedure_order p USING(object_id) ORDER BY COALESCE(l.order_id,m.order_id,p.order_id),c.order_kind;"
 examples=[dict(r) for r in con.execute(query)];js('docs/object_type_membership.json',examples)
 md('docs/object_type_verification.md','# Inspecting object/type membership\n\n- This DB explicitly tests **different tables → one common semantic type**. Registry IDs do not contain precomputed event attribution.\n- All 45 order objects share CLINICAL_ORDER; the subtype is checked separately.\n- A common type selects the case population; it does not combine all orders into one case.\n\n```sql\n'+query+'\n```\n\n'+table(['Type','Subtype','Object','Local order ID'],[[r['type_code'],r['order_kind'],r['object_id'],r['lab_local_id'] or r['medication_local_id'] or r['procedure_local_id']] for r in examples[:12]])+'\n- [All memberships as JSON](object_type_membership.json)\n- Common-type full logs: HF03/HF03P. Subtype full logs: HF04–HF06 and their P pairs. H02/H02P explicitly request events across all three subtype tables.\n- Membership triggers and composite subtype FKs reject wrong classifications. Private history links are an independent oracle and are not consulted by extraction SQL.\n')
 con.close();print(json.dumps({k:report[k] for k in ['events','total_questions','answerable_questions','semantic_object_types','object_instances','timestamp_summary','checks']},indent=2))
if __name__=='__main__':main()
