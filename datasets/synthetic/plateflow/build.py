"""Deterministic English manufacturing simulation. Author answers never enter the dictionary."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
from collections import Counter,defaultdict
import json,csv,sqlite3,sys
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))

def write(n,s):
 f=P/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(s,encoding='utf-8')
def js(n,v):write(n,json.dumps(v,indent=2)+'\n')
def jl(n,v):write(n,''.join(json.dumps(x)+'\n' for x in v))
def stamp(minute):return (datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(minutes=minute)).isoformat().replace('+00:00','Z')

DDL='''PRAGMA foreign_keys=ON;
CREATE TABLE slab_material(slab_id TEXT PRIMARY KEY NOT NULL, charge_id TEXT NOT NULL, steel_grade TEXT NOT NULL CHECK(steel_grade IN ('G1','G2')), received_at TEXT NOT NULL, verified_at TEXT, released_at TEXT, CHECK(verified_at IS NULL OR received_at<=verified_at), CHECK(released_at IS NULL OR (verified_at IS NOT NULL AND verified_at<=released_at)));
CREATE TABLE planned_rolling_instruction(plan_id TEXT PRIMARY KEY NOT NULL, slab_id TEXT NOT NULL UNIQUE REFERENCES slab_material(slab_id), planned_reheat_at TEXT NOT NULL, submitted_at TEXT NOT NULL, approved_at TEXT, released_at TEXT, CHECK(approved_at IS NULL OR submitted_at<=approved_at), CHECK(released_at IS NULL OR (approved_at IS NOT NULL AND approved_at<=released_at)));
CREATE TABLE rolling_instruction(instruction_id TEXT PRIMARY KEY NOT NULL, plan_id TEXT NOT NULL UNIQUE REFERENCES planned_rolling_instruction(plan_id), issued_at TEXT NOT NULL);
CREATE TABLE as_rolled_material(material_id TEXT PRIMARY KEY NOT NULL, plate_no TEXT NOT NULL UNIQUE, slab_id TEXT NOT NULL UNIQUE REFERENCES slab_material(slab_id), instruction_id TEXT NOT NULL UNIQUE REFERENCES rolling_instruction(instruction_id), created_at TEXT NOT NULL, updated_at TEXT NOT NULL, CHECK(created_at<=updated_at));
CREATE TABLE process_code(process_group TEXT NOT NULL CHECK(process_group IN ('FURNACE','ROLLING','FINISHING')), code TEXT NOT NULL, meaning TEXT NOT NULL, PRIMARY KEY(process_group,code));
CREATE TABLE equipment(equipment_id TEXT PRIMARY KEY NOT NULL, equipment_code TEXT NOT NULL UNIQUE, equipment_name TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, CHECK(created_at<=updated_at));
CREATE TABLE furnace_operation_history(operation_id TEXT PRIMARY KEY NOT NULL, material_id TEXT NOT NULL REFERENCES as_rolled_material(material_id), process_group TEXT NOT NULL DEFAULT 'FURNACE' CHECK(process_group='FURNACE'), operation_code TEXT NOT NULL, equipment_id TEXT NOT NULL REFERENCES equipment(equipment_id), started_at TEXT NOT NULL, finished_at TEXT, FOREIGN KEY(process_group,operation_code) REFERENCES process_code(process_group,code), CHECK(finished_at IS NULL OR started_at<finished_at));
CREATE TABLE rolling_operation_history(operation_id TEXT PRIMARY KEY NOT NULL, material_id TEXT NOT NULL REFERENCES as_rolled_material(material_id), process_group TEXT NOT NULL DEFAULT 'ROLLING' CHECK(process_group='ROLLING'), phase_code TEXT NOT NULL, equipment_id TEXT NOT NULL REFERENCES equipment(equipment_id), started_at TEXT NOT NULL, finished_at TEXT, FOREIGN KEY(process_group,phase_code) REFERENCES process_code(process_group,code), CHECK(finished_at IS NULL OR started_at<finished_at));
CREATE TABLE plate_material(plate_id TEXT PRIMARY KEY NOT NULL, plate_no TEXT NOT NULL UNIQUE, mother_material_id TEXT NOT NULL REFERENCES as_rolled_material(material_id), identified_at TEXT NOT NULL, released_at TEXT, packed_at TEXT, CHECK(released_at IS NULL OR identified_at<=released_at), CHECK(packed_at IS NULL OR (released_at IS NOT NULL AND released_at<=packed_at)));
CREATE TABLE finishing_operation_history(operation_id TEXT PRIMARY KEY NOT NULL, plate_id TEXT NOT NULL REFERENCES plate_material(plate_id), process_group TEXT NOT NULL DEFAULT 'FINISHING' CHECK(process_group='FINISHING'), operation_code TEXT NOT NULL, equipment_id TEXT NOT NULL REFERENCES equipment(equipment_id), started_at TEXT NOT NULL, finished_at TEXT, FOREIGN KEY(process_group,operation_code) REFERENCES process_code(process_group,code), CHECK(finished_at IS NULL OR started_at<finished_at));
CREATE TABLE dimension_inspection(inspection_id TEXT PRIMARY KEY NOT NULL, plate_id TEXT NOT NULL REFERENCES plate_material(plate_id), inspected_at TEXT NOT NULL, result_code TEXT NOT NULL CHECK(result_code IN ('PASS','FAIL')), thickness_mm REAL NOT NULL CHECK(thickness_mm>0));
CREATE TABLE plate_quality_review(review_id TEXT PRIMARY KEY NOT NULL, plate_id TEXT NOT NULL REFERENCES plate_material(plate_id), started_at TEXT NOT NULL, finished_at TEXT, review_status TEXT NOT NULL CHECK(review_status IN ('APPROVED','REWORK','PENDING')), CHECK((review_status='PENDING' AND finished_at IS NULL) OR (review_status IN ('APPROVED','REWORK') AND finished_at IS NOT NULL AND started_at<finished_at)));
'''
TABLES={
 'slab_material':'Slab identity, steel grade and actual receipt, verification and release times.',
 'planned_rolling_instruction':'One rolling plan per slab, its scheduled reheating time and actual submission, approval and release times.',
 'rolling_instruction':'An issued rolling instruction for an approved plan.',
 'as_rolled_material':'Allocated mother-material identity and genealogy for a rolling instruction; created_at and updated_at describe database maintenance, not production completion.',
 'process_code':'Business code meanings within each manufacturing process group. The same code text can have a different meaning in another group.',
 'equipment':'Equipment identifiers, names and system-maintenance times. Each equipment_code identifies a machine, not a manufacturing step.',
 'furnace_operation_history':'Actual furnace work occurrences for mother materials, retaining repeat work and unfinished intervals.',
 'rolling_operation_history':'Actual rolling phase occurrences for mother materials, retaining repeat work and unfinished intervals.',
 'plate_material':'Individual plate-piece identity and mother-material genealogy, with actual identification, release and packing times.',
 'finishing_operation_history':'Actual finishing work occurrences for individual plate pieces, including repeated heat treatment after rework.',
 'dimension_inspection':'One dimensional inspection record per inspection occurrence. Reinspection has a new inspection_id; PASS/FAIL describes its result.',
 'plate_quality_review':'One quality review record per review round. APPROVED/REWORK describes its outcome; PENDING means the review has not finished.'}
DEFS={
 'slab_id':'Unique slab identifier; on a plan or mother record, identifies its source slab.',
 'charge_id':'Steelmaking charge identifier recorded for material genealogy; no casting time is recorded here.',
 'steel_grade':'Synthetic steel-grade category G1 or G2.',
 'received_at':'Actual UTC time at which the slab was received.',
 'verified_at':'Actual UTC time at which the slab identity was verified; NULL if not yet verified.',
 'released_at':'Actual UTC release time for the slab, rolling plan or plate piece described by this table; NULL if not yet released.',
 'plan_id':'Unique rolling-plan identifier; on an instruction, references its plan.',
 'planned_reheat_at':'Scheduled UTC reheating time; a schedule does not establish that reheating occurred.',
 'submitted_at':'Actual UTC rolling-plan submission time.',
 'approved_at':'Actual UTC rolling-plan approval time; NULL if not yet approved.',
 'instruction_id':'Unique rolling-instruction identifier; on a mother record, references the instruction allocating it.',
 'issued_at':'Actual UTC rolling-instruction issue time.',
 'material_id':'Unique mother-material identifier; on a work record, references the mother material processed.',
 'plate_no':'Unique business plate number within this table; mother and piece numbers have separate ranges.',
 'mother_material_id':'Mother material from which the individual plate piece was derived.',
 'created_at':'UTC database record-creation time; this field does not document a production action.',
 'updated_at':'UTC database maintenance time; this field does not document a production action.',
 'process_group':'Business context FURNACE, ROLLING or FINISHING; each work-history table has one fixed group enforced by CHECK.',
 'code':'Business code within a process group; the pair (process_group,code) uniquely identifies its meaning.',
 'meaning':'English business meaning of the code in the specified process group.',
 'equipment_id':'Unique equipment-unit identifier; on a work record, references the unit that performed the work.',
 'equipment_code':'Human-readable machine code; identifies the machine, not the work performed.',
 'equipment_name':'English equipment-unit name.',
 'operation_id':'Unique work-occurrence identifier within this table; repeat work receives a new identifier.',
 'operation_code':'Kind of manufacturing work performed, as defined by the matching process_group/code entry.',
 'phase_code':'Rolling phase performed, as defined by the matching process_group/code entry.',
 'started_at':'Actual UTC start of this manufacturing work occurrence or quality-review round.',
 'finished_at':'Actual UTC finish of this manufacturing work occurrence or quality-review round; NULL if unfinished.',
 'plate_id':'Unique individual plate-piece identifier; on work, inspection or review records, references the piece concerned.',
 'identified_at':'Actual UTC time at which the plate piece was identified after rolling.',
 'packed_at':'Actual UTC packing-completion time; NULL if not yet packed.',
 'inspection_id':'Unique dimensional-inspection occurrence identifier; distinct for each reinspection.',
 'inspected_at':'Actual UTC dimensional-inspection completion time.',
 'result_code':'Inspection outcome PASS or FAIL; either value represents a completed dimensional inspection.',
 'thickness_mm':'Synthetic measured thickness in millimetres.',
 'review_id':'Unique quality-review round identifier; distinct for each subsequent review.',
 'review_status':'APPROVED or REWORK for a finished quality review, PENDING for an unfinished review.'}
CODES=[('FURNACE','CH','Furnace charging','Furnace Charged'),('FURNACE','HT','Furnace heating','Heating Completed'),('FURNACE','DS','Furnace discharge','Furnace Discharged'),('ROLLING','RR','Rough rolling','Rough Rolling Completed'),('ROLLING','FR','Finish rolling','Finish Rolling Completed'),('FINISHING','LEV','Leveling','Leveling Completed'),('FINISHING','HT','Heat treatment','Heat Treatment Completed'),('FINISHING','SF','Surface finishing','Surface Finishing Completed')]
# Author-only metadata used for README generation and validation; never exported to input dictionaries.
ENCODING={n:('Row',c) for n,c in [('furnace_operation_history','operation_code'),('rolling_operation_history','phase_code'),('finishing_operation_history','operation_code')]}
ENCODING.update({n:('Column',None) for n in ['slab_material','planned_rolling_instruction','rolling_instruction','plate_material','dimension_inspection','plate_quality_review']})
ENCODING.update({n:('No business events',None) for n in ['as_rolled_material','process_code','equipment']})
VIEWS={
 'Slab':('slab_material','slab_id','S:'),
 'Rolling Plan':('planned_rolling_instruction','plan_id','PLAN:'),
 'Rolling Instruction':('rolling_instruction','instruction_id','INST:'),
 'Mother Material':('as_rolled_material','material_id','M:'),
 'Plate Piece':('plate_material','plate_id','P:'),
 'Dimension Inspection':('dimension_inspection','inspection_id','DIM:'),
 'Quality Review':('plate_quality_review','review_id','REV:'),
 'Equipment':('equipment','equipment_id','E:'),
 'Furnace Operation Record':('furnace_operation_history','operation_id','FOP:'),
 'Rolling Operation Record':('rolling_operation_history','operation_id','ROP:'),
 'Finishing Operation Record':('finishing_operation_history','operation_id','TOP:')}

def main():
 for n in ['input','private/gold_logs','private/gold_sql','docs','design','source']:(P/n).mkdir(parents=True,exist_ok=True)
 db=P/'input/database.sqlite';db.unlink(missing_ok=True)
 con=sqlite3.connect(db);con.row_factory=sqlite3.Row;con.executescript(DDL);write('input/schema.sql',DDL)
 def ins(t,**row):con.execute('INSERT INTO '+t+'('+','.join(row)+') VALUES ('+','.join('?' for _ in row)+')',list(row.values()))
 for group,code,meaning,_ in CODES:ins('process_code',process_group=group,code=code,meaning=meaning)
 equipment={}
 for group in ['FURNACE','ROLLING','FINISHING']:
  equipment[group]=[]
  for j in range(2):
   eid=group[:2]+str(j+1);equipment[group].append(eid);ins('equipment',equipment_id=eid,equipment_code=group+'-UNIT-'+str(j+1),equipment_name=group.title()+' unit '+str(j+1),created_at=stamp(-1000),updated_at=stamp(500000))
 # An idle machine has technical times but no completed business work.
 ins('equipment',equipment_id='IDLE',equipment_code='SPARE-UNIT',equipment_name='Idle spare unit',created_at=stamp(-900),updated_at=stamp(500100))
 history=[];links=[];counter=Counter();lookup={}
 def event(eid,activity,t,table,pk,oids):
  history.append(dict(event_id=eid,activity=activity,timestamp=stamp(t),source_table=table,source_key=pk))
  links.extend(dict(event_id=eid,case_concept=v,case_id=k,attribution='own' if table==VIEWS[v][0] else 'business-key path') for v,k in sorted(set(oids)))
 def op(group,parent,code,start,end,oidlinks,sequence):
  table={'FURNACE':'furnace_operation_history','ROLLING':'rolling_operation_history','FINISHING':'finishing_operation_history'}[group];counter[table]+=1;opid=str(counter[table]).zfill(4)
  eq=equipment[group][sequence%2];key='phase_code' if group=='ROLLING' else 'operation_code';parentcol='plate_id' if group=='FINISHING' else 'material_id'
  ins(table,operation_id=opid,**{parentcol:parent,'process_group':group,key:code,'equipment_id':eq,'started_at':stamp(start),'finished_at':None if end is None else stamp(end)})
  if end is not None:
   activity=next(a for g,c,_,a in CODES if g==group and c==code);view={'FURNACE':'Furnace Operation Record','ROLLING':'Rolling Operation Record','FINISHING':'Finishing Operation Record'}[group];prefix=VIEWS[view][2]
   event(prefix+opid,activity,end,table,opid,oidlinks+[(view,prefix+opid),('Equipment','E:'+eq)])
  return opid
 for i in range(1,31):
  slab='S'+str(i).zfill(3);plan='L'+str(i).zfill(3);instruction='I'+str(i).zfill(3);material='M'+str(i).zfill(3);base=i*5000
  sv=('Slab','S:'+slab);pv=('Rolling Plan','PLAN:'+plan);iv=('Rolling Instruction','INST:'+instruction);mv=('Mother Material','M:'+material)
  verified=None if i<=2 else base+10;released=None if i<=2 else base+20
  ins('slab_material',slab_id=slab,charge_id='C'+str((i-1)//3+1).zfill(3),steel_grade='G1' if i%2 else 'G2',received_at=stamp(base),verified_at=None if verified is None else stamp(verified),released_at=None if released is None else stamp(released))
  for col,act,t in [('received_at','Slab Received',base),('verified_at','Slab Verified',verified),('released_at','Slab Released',released)]:
   if t is not None:event('SLAB:'+slab+':'+col,act,t,'slab_material',slab,[sv])
  if i<=2:continue
  approved=None if i<=4 else base+40;planrelease=None if approved is None else base+50
  ins('planned_rolling_instruction',plan_id=plan,slab_id=slab,planned_reheat_at=stamp(base+500),submitted_at=stamp(base+30),approved_at=None if approved is None else stamp(approved),released_at=None if planrelease is None else stamp(planrelease))
  for col,act,t in [('submitted_at','Rolling Plan Submitted',base+30),('approved_at','Rolling Plan Approved',approved),('released_at','Rolling Plan Released',planrelease)]:
   if t is not None:event('PLAN:'+plan+':'+col,act,t,'planned_rolling_instruction',plan,[sv,pv])
  if approved is None:continue
  ins('rolling_instruction',instruction_id=instruction,plan_id=plan,issued_at=stamp(base+60));event('INST:'+instruction,'Rolling Instruction Issued',base+60,'rolling_instruction',instruction,[sv,pv,iv])
  ins('as_rolled_material',material_id=material,plate_no='MOTHER-'+str(i),slab_id=slab,instruction_id=instruction,created_at=stamp(base+61),updated_at=stamp(base+4000));work=[sv,iv,mv]
  if i<=6:continue
  op('FURNACE',material,'CH',base+70,base+80,work,i)
  if i%11==0:op('FURNACE',material,'HT',base+85,None,work,i);continue
  op('FURNACE',material,'HT',base+85,base+120,work,i);op('FURNACE',material,'DS',base+125,base+130,work,i)
  op('ROLLING',material,'RR',base+140,base+160,work,i)
  if i%13==0:op('ROLLING',material,'FR',base+170,None,work,i);continue
  op('ROLLING',material,'FR',base+170,base+195,work,i)
  for j in range(1,2+i%3):
   plate='P'+str(i).zfill(3)+'-'+str(j);platev=('Plate Piece','P:'+plate);start=base+230+j*500;rework=(i+j)%4==0;pending=(i+j)%7==0;pack=(i+j)%5!=0
   identified=start;release=None if pending else start+(180 if rework else 100);packed=None if release is None or not pack else release+20
   ins('plate_material',plate_id=plate,plate_no='PIECE-'+str(i)+'-'+str(j),mother_material_id=material,identified_at=stamp(identified),released_at=None if release is None else stamp(release),packed_at=None if packed is None else stamp(packed))
   pw=work+[platev];event('PLATE:'+plate+':identified','Plate Identified',identified,'plate_material',plate,pw)
   op('FINISHING',plate,'LEV',start+5,start+15,pw,i+j);op('FINISHING',plate,'HT',start+20,start+40,pw,i+j);op('FINISHING',plate,'SF',start+45,start+55,pw,i+j)
   def inspection(roundno,t,result):
    did=plate+'-'+str(roundno);ins('dimension_inspection',inspection_id=did,plate_id=plate,inspected_at=stamp(t),result_code=result,thickness_mm=20.1 if result=='PASS' else 22.5);event('DIM:'+did,'Dimensional Inspection Completed',t,'dimension_inspection',did,pw+[('Dimension Inspection','DIM:'+did)])
   def review(roundno,t,end,status):
    rid=plate+'-'+str(roundno);ins('plate_quality_review',review_id=rid,plate_id=plate,started_at=stamp(t),finished_at=None if end is None else stamp(end),review_status=status)
    if end is not None:event('REV:'+rid,'Plate Quality Review Completed',end,'plate_quality_review',rid,pw+[('Quality Review','REV:'+rid)])
   inspection(1,start+65,'FAIL' if rework else 'PASS')
   review(1,start+70,None if pending else start+80,'PENDING' if pending else 'REWORK' if rework else 'APPROVED')
   if rework and not pending:
    op('FINISHING',plate,'HT',start+90,start+120,pw,i+j);op('FINISHING',plate,'SF',start+125,start+135,pw,i+j);inspection(2,start+145,'PASS');review(2,start+150,start+165,'APPROVED')
   if release is not None:event('PLATE:'+plate+':released','Plate Released',release,'plate_material',plate,pw)
   if packed is not None:event('PLATE:'+plate+':packed','Plate Packed',packed,'plate_material',plate,pw)
 con.commit()
 assert not list(con.execute('PRAGMA foreign_key_check'));assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 jl('private/canonical_history.jsonl',history);js('private/object_event_links.json',links)
 sources=[]
 def source(table,activity,col,idexpr,key,where='1=1',**selector):
  sql=f"SELECT {idexpr} event_id,'{activity}' activity,{col} timestamp,{key} source_key FROM {table} WHERE {col} IS NOT NULL AND ({where})"
  sources.append(dict(table=table,activity=activity,timestamp_column=col,event_sql=sql,**selector))
 for col,act in [('received_at','Slab Received'),('verified_at','Slab Verified'),('released_at','Slab Released')]:source('slab_material',act,col,"'SLAB:'||slab_id||':"+col+"'",'slab_id')
 for col,act in [('submitted_at','Rolling Plan Submitted'),('approved_at','Rolling Plan Approved'),('released_at','Rolling Plan Released')]:source('planned_rolling_instruction',act,col,"'PLAN:'||plan_id||':"+col+"'",'plan_id')
 source('rolling_instruction','Rolling Instruction Issued','issued_at',"'INST:'||instruction_id",'instruction_id')
 for group,code,_,act in CODES:
  table={'FURNACE':'furnace_operation_history','ROLLING':'rolling_operation_history','FINISHING':'finishing_operation_history'}[group];field='phase_code' if group=='ROLLING' else 'operation_code';prefix={'FURNACE':'FOP:','ROLLING':'ROP:','FINISHING':'TOP:'}[group]
  source(table,act,'finished_at',"'"+prefix+"'||operation_id",'operation_id',field+"='"+code+"'",row_filter=dict(column=field,value=code,process_group=group))
 for col,act,suffix in [('identified_at','Plate Identified','identified'),('released_at','Plate Released','released'),('packed_at','Plate Packed','packed')]:source('plate_material',act,col,"'PLATE:'||plate_id||':"+suffix+"'",'plate_id')
 source('dimension_inspection','Dimensional Inspection Completed','inspected_at',"'DIM:'||inspection_id",'inspection_id')
 source('plate_quality_review','Plate Quality Review Completed','finished_at',"'REV:'||review_id",'review_id')
 js('private/persistence_mapping.json',sources)
 # Direct key-based SQL paths; no persisted event-to-case index is present in the DB.
 case_paths={v:{} for v in VIEWS}
 def path(v,t,key,joins='',distinct=False):case_paths[v][t]=dict(case_key=key,joins=joins,distinct=distinct)
 path('Slab','slab_material','s.slab_id')
 path('Slab','planned_rolling_instruction','s.slab_id');path('Rolling Plan','planned_rolling_instruction','s.plan_id')
 path('Slab','rolling_instruction','p.slab_id',' JOIN planned_rolling_instruction p ON p.plan_id=s.plan_id');path('Rolling Plan','rolling_instruction','s.plan_id');path('Rolling Instruction','rolling_instruction','s.instruction_id')
 for t in ['furnace_operation_history','rolling_operation_history']:
  join=' JOIN as_rolled_material m ON m.material_id=s.material_id'
  for v,key in [('Slab','m.slab_id'),('Rolling Instruction','m.instruction_id'),('Mother Material','s.material_id')]:path(v,t,key,join)
  path('Equipment',t,'s.equipment_id');path('Furnace Operation Record' if t.startswith('furnace') else 'Rolling Operation Record',t,'s.operation_id')
 for t in ['plate_material','finishing_operation_history','dimension_inspection','plate_quality_review']:
  join='' if t=='plate_material' else ' JOIN plate_material piece ON piece.plate_id=s.plate_id';mothercol='s.mother_material_id' if t=='plate_material' else 'piece.mother_material_id';join+=' JOIN as_rolled_material m ON m.material_id='+mothercol
  for v,key in [('Slab','m.slab_id'),('Rolling Instruction','m.instruction_id'),('Mother Material','m.material_id'),('Plate Piece','s.plate_id')]:path(v,t,key,join)
 path('Equipment','finishing_operation_history','s.equipment_id');path('Finishing Operation Record','finishing_operation_history','s.operation_id');path('Dimension Inspection','dimension_inspection','s.inspection_id');path('Quality Review','plate_quality_review','s.review_id')
 js('private/case_paths.json',case_paths)
 def compile_es(view,activities):
  parts=[];bindings=[];prefix=VIEWS[view][2]
  for source in sources:
   t=source['table'];route=case_paths[view].get(t)
   if source['activity'] not in activities or route is None:continue
   # Source filtering occurs before joins; per-source key is still tied to its physical row.
   key=VIEWS.get(view,(None,None,None))[1];pk=con.execute('PRAGMA table_info('+t+')').fetchall();source_pk=next(c['name'] for c in pk if c['pk'])
   parts.append("SELECT e.event_id,'"+prefix+"'||"+route['case_key']+" case_id,e.activity,e.timestamp FROM ("+source['event_sql']+") e JOIN "+t+" s ON s."+source_pk+"=e.source_key"+route['joins'])
   bindings.append(dict(source_table=t,source_pk=source_pk,activity=source['activity'],timestamp_column=source['timestamp_column'],row_filter=source.get('row_filter'),case_path=route))
  assert parts,view
  return 'SELECT * FROM ('+' UNION ALL '.join(parts)+') ORDER BY case_id,timestamp,event_id;',bindings
 linked=defaultdict(set)
 for r in links:linked[r['event_id']].add((r['case_concept'],r['case_id']))
 coverage=[];populations={}
 for view,(table,key,prefix) in VIEWS.items():
  pop=[prefix+r[0] for r in con.execute('SELECT '+key+' FROM '+table+' ORDER BY '+key)];populations[view]=pop
  acts=sorted({e['activity'] for e in history if any(v==view for v,_ in linked[e['event_id']])});casecount=Counter(cid for e in history for v,cid in linked[e['event_id']] if v==view)
  coverage.append(dict(case_concept=view,case_table=table,case_count=len(pop),activity_count=len(acts),activities=acts,event_rows=sum(casecount.values()),cases_without_events=len(set(pop)-set(casecount))))
 js('private/case_population.json',populations);js('private/task_scope_catalog.json',dict(views=coverage,completion_policy='Use completed occurrences and actual point milestones only; start times do not create extra labels.'))
 seeds=json.loads((P/'source/question_seeds.json').read_text());paraphrases=json.loads((P/'source/llm_paraphrases.json').read_text());questions=[];gold=[]
 for seed in seeds:
  qid=seed['id'];view=seed['view'];full='activities' not in seed;activities=next(r['activities'] for r in coverage if r['case_concept']==view) if full else seed['activities'];answerable=seed.get('answerable',True)
  if answerable:
   sql,bindings=compile_es(view,activities);es=dict(version='plateflow-new-es-1',case_concept=view,activities=activities,case_population=populations[view],event_bindings=bindings,compiled_sql=sql)
   expected=sorted([dict(event_id=e['event_id'],case_id=cid,activity=e['activity'],timestamp=e['timestamp']) for e in history if e['activity'] in activities for v,cid in linked[e['event_id']] if v==view],key=lambda e:(e['case_id'],e['timestamp'],e['event_id']))
   actual=[dict(r) for r in con.execute(sql)];assert actual==expected,qid
   assert len({(r['case_id'],r['event_id']) for r in actual})==len(actual)
  else:es=None
  for ident,text,typ,pair in [(qid,seed['question'],'Q3' if full else 'Q1',qid+'P'),(qid+'P',paraphrases['outputs'][qid],'Q4' if full else 'Q2',qid)]:
   q=dict(question_id=ident,text=text,question_type=typ,question_type_name={'Q1':'Explicit','Q2':'Paraphrased','Q3':'Full Lifecycle','Q4':'Full Lifecycle Paraphrased'}[typ],pair_of=pair,pair_group_id=qid,answerability='answerable' if answerable else 'non_answerable',included_information='Process View: case concept only' if full else 'Process View: case concept and explicit activity scope',requested_activity_count=len(activities),extractable_activity_count=len(activities) if answerable else 0,activity_scope_explicit=not full,case_concept=view)
   questions.append(q);g=dict(**q,process_view=dict(case_concept=view,case_table=VIEWS[view][0],activities=activities),es=es)
   if answerable:
    csvpath='private/gold_logs/'+ident+'.csv';sqlpath='private/gold_sql/'+ident+'.sql'
    with (P/csvpath).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=['event_id','case_id','activity','timestamp']);w.writeheader();w.writerows(expected)
    write(sqlpath,sql+'\n');g.update(csv=csvpath,sql=sqlpath,event_count=len(expected))
   else:g['reason']='No corresponding casting or dispatch records or actual times are stored.'
   gold.append(g)
 jl('input/model_questions.jsonl',[dict(question_id=q['question_id'],text=q['text']) for q in questions]);jl('private/questions.jsonl',questions);jl('private/gold.jsonl',gold)
 # Dictionary has only schema/business semantics. No benchmark event-selection answers are exported.
 metadata=[]
 for table in TABLES:
  info=list(con.execute('PRAGMA table_info('+table+')'));cols=[];fks=[dict(r) for r in con.execute('PRAGMA foreign_key_list('+table+')')]
  for r in info:
   definition=DEFS[r['name']]
   cols.append(dict(name=r['name'],sql_type=r['type'],definition=definition,required=bool(r['notnull'] or r['pk']),primary_key_position=r['pk'],default=r['dflt_value'],foreign_keys=[dict(table=f['table'],column=f['to'],constraint_id=f['id'],position=f['seq']) for f in fks if f['from']==r['name']],unit='mm' if r['name']=='thickness_mm' else 'UTC' if r['name'].endswith('_at') else None))
  metadata.append(dict(table=table,definition=TABLES[table],columns=cols,primary_key=[r['name'] for r in sorted(info,key=lambda r:r['pk']) if r['pk']],sql_definition=con.execute('SELECT sql FROM sqlite_master WHERE name=?',(table,)).fetchone()[0]))
 dictionary=dict(name='PlateFlow New',language='en',timezone='UTC',dbms='SQLite',description='Synthetic plate-manufacturing business records with explicitly declared identifiers and relationships.',tables=metadata,code_values=[dict(process_group=g,code=c,meaning=m) for g,c,m,_ in CODES],business_rules=['Each plan concerns one slab. Each issued instruction refers to one plan. Mother and plate-piece identifiers refer to distinct physical materials.','A mother-material identity can be allocated before work finishes. Database creation and maintenance times are not evidence of production completion.','Every work occurrence retains its own identifier. Repeat work, reinspection and later review rounds retain separate records.','Each work-history table is restricted to its declared process group. Code meanings are resolved within that group.','Review outcome and inspection result describe the result of the same kind of business record; they do not change its business purpose.','Actual start times may exist without finish times. NULL finish means unfinished work; NULL release/packing means not yet released/packed.','Scheduled reheating time is a plan and may differ from actual heating time.','An approved quality review is required before piece release; packing follows release.','All business records, identifiers, times and measurements are synthetic.'])
 js('input/data_dictionary.json',dictionary)
 timestamps=[];used={(s['table'],s['timestamp_column']) for s in sources}
 for t in metadata:
  for c in t['columns']:
   if not c['name'].endswith('_at'):continue
   name=c['name'];role='Completed work or actual milestone' if (t['table'],name) in used else 'Actual interval start; not separately emitted' if name=='started_at' else 'Scheduled instant' if name.startswith('planned_') else 'Technical maintenance instant'
   timestamps.append(dict(table=t['table'],column=name,role=role,used_as_event_time=(t['table'],name) in used,non_null_rows=con.execute('SELECT COUNT('+name+') FROM '+t['table']).fetchone()[0]))
 inv=dict(timestamp_columns=len(timestamps),event_timestamp_columns=len(used),other_timestamp_columns=len(timestamps)-len(used),baseline_timestamp_columns=len(timestamps),columns=timestamps,date_only_columns=[]);js('docs/timestamp_columns.json',inv)
 report=dict(table_rows={t:con.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in TABLES},semantic_object_types=len(VIEWS),object_view_coverage=coverage,activity_counts=dict(Counter(e['activity'] for e in history)),events=len(history),total_questions=len(questions),answerable_questions=sum(q['answerability']=='answerable' for q in questions),timestamp_summary={k:v for k,v in inv.items() if k!='columns'},validation_scope='Construction consistency and Gold extraction; no model classification/extraction accuracy is claimed.');js('validation_report.json',report)
 from documentation import render
 render(P,con,dictionary,report,questions,coverage,ENCODING)
 con.close();print(json.dumps({k:report[k] for k in ['events','total_questions','answerable_questions','semantic_object_types','timestamp_summary']},indent=2))
if __name__=='__main__':main()
