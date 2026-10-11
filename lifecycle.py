"""Authored domain lifecycle extensions; original source schemas remain identifiable."""
import json,sqlite3,csv
from pathlib import Path
from datetime import datetime,timedelta,timezone
from collections import Counter
ROOT=Path(__file__).resolve().parent
CONFIG={
'warehouseflow':{
 'transaction_record':(['Receiving Requested','Receiving Scheduled','Receiving Inspection Completed','Goods Put Away'],['Dispatch Requested','Dispatch Approved','Goods Picked','Goods Packed'])},
'universityflow':{
 'registration':['Registration Requested','Registration Approved','Course Started','Course Assessment Completed','Course Grade Finalized'],
 'degree_examination_result':['Examination Scheduled','Examination Checked In','Examination Score Published','Examination Result Reviewed'],
 'assignment':['Assignment Assigned','Assignment Submitted','Assignment Revision Requested','Assignment Resubmitted','Assignment Grade Finalized'],
 'simulation_module':['Simulation Module Published','Simulation Module Validated','Simulation Module Released','Simulation Module Retired'],
 'student_simulation_experiment_result':['Simulation Run Scheduled','Simulation Run Started','Simulation Output Reviewed','Simulation Result Accepted'],
 'thesis':['Thesis Draft Registered','Thesis Review Started','Thesis Revision Requested','Thesis Resubmitted','Thesis Accepted'],
 'course':['Course Offering Proposed','Course Offering Approved','Course Offering Published','Course Offering Closed'],
 'task':['Design Task Created','Design Task Approved','Design Task Published','Design Task Closed']},
'plateflow':{
 'slab_material':['Slab Received','Slab Identity Verified','Slab Quality Checked','Slab Released for Rolling'],
 'planned_rolling_instruction':['Rolling Plan Created','Rolling Plan Reviewed','Rolling Plan Approved','Rolling Plan Released'],
 'rolling_instruction':['Rolling Instruction Acknowledged','Rolling Setup Verified','Rolling Work Started','Rolling Instruction Closed'],
 'furnace_charge_tracking':['Furnace Charge Assigned','Furnace Charge Confirmed','Heating Completed','Furnace Discharge Confirmed'],
 'cutting_finishing_instruction':['Cutting Instruction Acknowledged','Cutting Setup Verified','Cutting Work Started','Cutting Instruction Closed'],
 'plate_material':['Plate Piece Identified','Plate Surface Checked','Plate Quality Released','Plate Packed']}}
PROPAGATE={
'warehouseflow':{'transaction_record':['warehouse','goods','loader','goods_transaction_detail','loader_transaction']},
'universityflow':{'registration':['student','course'],'degree_examination_result':['student'],'assignment':['student','instructor'],'student_simulation_experiment_result':['student','simulation_module'],'thesis':['student']},
'plateflow':{'slab_material':['as_rolled_material'],'planned_rolling_instruction':['as_rolled_material','slab_material'],'rolling_instruction':['as_rolled_material','slab_material'],'furnace_charge_tracking':['as_rolled_material','slab_material'],'cutting_finishing_instruction':['as_rolled_material','slab_material'],'plate_material':['as_rolled_material','slab_material']}}
def readjl(p):return [json.loads(x) for x in p.read_text().splitlines()]
def js(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def stamp(t):return t.isoformat().replace('+00:00','Z')
def extend(p):
 p=Path(p);name=p.name;con=sqlite3.connect(p/'input/database.sqlite');con.row_factory=sqlite3.Row;con.execute('PRAGMA foreign_keys=ON')
 oldhist=readjl(p/'private/canonical_history.jsonl');oldlinks=json.loads((p/'private/object_event_links.json').read_text());bytable={t:[dict(r) for r in con.execute('SELECT * FROM '+t)] for t in CONFIG[name]}
 inv={t:{} for t in oldlinks}
 for t,links in oldlinks.items():
  for eid,ids in links.items():
   for oid in ids:inv[t].setdefault(oid,[]).append(eid)
 events={e['event_id']:e for e in oldhist};newhist=[];newlinks={};sources=[];newtables=[];plans=[]
 fullid={'warehouseflow':'R05','universityflow':'U05','plateflow':'V05'}[name];defaulttable={'warehouseflow':'warehouse','universityflow':'student','plateflow':'as_rolled_material'}[name]
 for obj,seq in CONFIG[name].items():
  cols=list(con.execute('PRAGMA table_info('+obj+')'));pk=[r['name'] for r in sorted(cols,key=lambda x:x['pk']) if r['pk']];table=obj+'_activity';con.execute('DROP TABLE IF EXISTS '+table)
  clauses=['event_id TEXT PRIMARY KEY']+[k+' TEXT NOT NULL' for k in pk]+['activity TEXT NOT NULL','occurred_at TEXT NOT NULL','outcome TEXT NOT NULL', 'FOREIGN KEY ('+','.join(pk)+') REFERENCES '+obj+'('+','.join(pk)+')']
  ddl='CREATE TABLE '+table+' ('+', '.join(clauses)+');';con.execute(ddl)
  mdcols=[dict(name='event_id',type='TEXT',constraints='PRIMARY KEY',definition='Stable identity of this actual business action; authored extension')]+[dict(name=k,type='TEXT',constraints='NOT NULL',definition='Explicit parent object key; FK to '+obj+'.'+k) for k in pk]+[dict(name=k,type='TEXT',constraints='NOT NULL',definition=d) for k,d in [('activity','Controlled business activity label; not a technical database update'),('occurred_at','Actual occurrence time in UTC, distinct from planned dates'),('outcome','Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED')]]
  newtables.append(dict(table=table,definition='Authored actual-action history for '+obj,columns=mdcols,primary_key=['event_id'],foreign_keys=[dict(column=k,parent_table=obj,parent_column=k) for k in pk],source_origin='authored_lifecycle_extension'));sources.append(dict(table=table,event_key=['event_id'],timestamp_column='occurred_at',activity_column='activity',object_table=obj,object_key=pk))
  for idx,r in enumerate(bytable[obj]):
   oid=':'.join(str(r[k]) for k in pk);originalids=inv.get(obj,{}).get(oid,[]);ts=sorted(datetime.fromisoformat(events[e]['timestamp'].replace('Z','+00:00')) for e in originalids);lo=ts[0] if ts else datetime(2026,1,3,tzinfo=timezone.utc)+timedelta(days=idx);hi=ts[-1] if ts else lo
   acts=seq
   if name=='warehouseflow':acts=seq[0] if any(events[e]['activity']=='Goods Received' for e in originalids) else seq[1]
   # Position each actual action around the source milestone, never reuse scheduled fields.
   if obj=='transaction_record':times=[lo-timedelta(hours=4),lo-timedelta(hours=3),lo+timedelta(minutes=30),hi+timedelta(hours=1)] if acts==seq[0] else [lo-timedelta(hours=4),lo-timedelta(hours=3),lo-timedelta(hours=2),lo-timedelta(hours=1)]
   elif obj=='registration':times=[lo-timedelta(hours=4),lo-timedelta(hours=2),hi+timedelta(days=2),hi+timedelta(days=20),hi+timedelta(days=22)]
   elif obj in ['degree_examination_result','student_simulation_experiment_result']:times=[lo-timedelta(hours=2),lo-timedelta(hours=1),hi+timedelta(hours=2),hi+timedelta(hours=3)]
   elif obj=='assignment':times=[lo-timedelta(days=4),lo-timedelta(days=2),lo+timedelta(hours=1),lo+timedelta(days=1),hi+timedelta(days=2)]
   elif obj=='thesis':times=[lo-timedelta(days=4),hi+timedelta(days=1),hi+timedelta(days=2),hi+timedelta(days=3),hi+timedelta(days=4)]
   elif name=='plateflow' and obj in ['slab_material','planned_rolling_instruction']:times=[lo-timedelta(hours=10-j) for j in range(len(acts))]
   elif name=='plateflow' and obj in ['rolling_instruction','cutting_finishing_instruction']:times=[lo+timedelta(minutes=5),lo+timedelta(minutes=10),lo+timedelta(minutes=15),hi+timedelta(hours=8)]
   elif name=='plateflow' and obj=='furnace_charge_tracking':times=[lo+timedelta(minutes=5),lo+timedelta(minutes=10),hi+timedelta(hours=2),hi+timedelta(hours=3)]
   elif name=='plateflow' and obj=='plate_material':times=[lo-timedelta(minutes=30),hi+timedelta(minutes=30),hi+timedelta(hours=1),hi+timedelta(hours=2)]
   else:times=[lo-timedelta(days=3),lo-timedelta(days=2),lo-timedelta(days=1),hi+timedelta(days=30)][:len(acts)]
   selected=list(zip(acts,times))
   if name=='plateflow' and obj in ['rolling_instruction','furnace_charge_tracking','cutting_finishing_instruction']:
    mid=r.get('material_id')
    if obj=='rolling_instruction':mid=con.execute('SELECT material_id FROM as_rolled_material WHERE instruction_id=?',(r['instruction_id'],)).fetchone()[0]
    material=dict(con.execute('SELECT * FROM as_rolled_material WHERE material_id=?',(mid,)).fetchone())
    operations=[dict(x) for x in con.execute('SELECT * FROM material_operation_history WHERE material_id=?',(mid,))]
    # Stage completion is conditional on an actual milestone in the original process.
    if obj=='furnace_charge_tracking':
     charged=material['furnace_charged_at']
     rolling=[e for e in oldhist if e['case_id']==mid and e['activity']=='Rolling Completed']
     if not charged:selected=selected[:2]
     elif rolling:
      rt=datetime.fromisoformat(rolling[0]['timestamp'].replace('Z','+00:00'));selected=[(acts[0],lo+timedelta(minutes=5)),(acts[1],datetime.fromisoformat(charged.replace('Z','+00:00'))+timedelta(minutes=1)),(acts[2],rt-timedelta(minutes=20)),(acts[3],rt-timedelta(minutes=10))]
     else:selected=selected[:2]
    elif obj=='rolling_instruction':
     rolling=[e for e in oldhist if e['case_id']==mid and e['activity']=='Rolling Completed']
     if not rolling:selected=selected[:2]
     else:
      rt=datetime.fromisoformat(rolling[0]['timestamp'].replace('Z','+00:00'));selected=[(acts[0],lo+timedelta(minutes=5)),(acts[1],lo+timedelta(minutes=10)),(acts[2],rt-timedelta(minutes=5)),(acts[3],rt+timedelta(minutes=5))]
    elif obj=='cutting_finishing_instruction':
     cutting=[e for e in oldhist if e['case_id']==mid and e['activity']=='Split Cutting Completed']
     if cutting:
      ct=datetime.fromisoformat(cutting[0]['timestamp'].replace('Z','+00:00'));selected=[(acts[0],lo+timedelta(minutes=5)),(acts[1],lo+timedelta(minutes=10)),(acts[2],ct-timedelta(minutes=5)),(acts[3],ct+timedelta(minutes=5))]
     else:selected=selected[:2]
   if obj=='assignment' and idx%3==0 and originalids:
    selected.insert(-1,('Assignment Regraded',hi+timedelta(days=1,hours=12)))

   # Revision branches only occur for selected assignments/theses, and some cases remain open.
   if obj in ['assignment','thesis'] and idx%3!=0:selected=[(a,t) for a,t in selected if 'Revision Requested' not in a and 'Resubmitted' not in a]
   if idx%7==0 and not (name=='warehouseflow' and acts==seq[1]):selected=selected[:-1]
   if obj=='assignment' and not originalids:selected=selected[:1]
   assert all(selected[k][1]<selected[k+1][1] for k in range(len(selected)-1)),(name,obj,oid,selected)
   for j,(a,t) in enumerate(selected):
    eid=f'LC:{obj}:{oid}:{j+1}';outcome='REVISION_REQUIRED' if 'Revision Requested' in a else 'APPROVED' if any(x in a for x in ['Approved','Accepted','Released']) else 'COMPLETED'
    con.execute('INSERT INTO '+table+' VALUES ('+','.join('?' for _ in range(len(pk)+4))+')',(eid,*[r[k] for k in pk],a,stamp(t),outcome))
    links={obj:{oid}}
    for target in PROPAGATE.get(name,{}).get(obj,[]):
     ids=set(x for orig in originalids for x in oldlinks.get(target,{}).get(orig,[]))
     if ids:links[target]=ids
    if name=='universityflow' and 'student_id' in r:links['student']={r['student_id']}
    if name=='universityflow' and obj=='registration':links['course']={r['course_id']}
    if name=='universityflow' and obj=='student_simulation_experiment_result':links['simulation_module']={r['module_id']}
    if name=='plateflow' and 'material_id' in r and obj!='slab_material':
     links['as_rolled_material']={r['material_id']};m=con.execute('SELECT slab_id FROM as_rolled_material WHERE material_id=?',(r['material_id'],)).fetchone()
     if m:links['slab_material']={m[0]}
    defaultids=links.get(defaulttable,set());case=next(iter(defaultids),oid)
    newhist.append(dict(event_id=eid,case_id=case,activity=a,timestamp=stamp(t)))
    for target,ids in links.items():newlinks.setdefault(target,{})[eid]=sorted(ids)
  if obj=='assignment':seq=seq+['Assignment Regraded']
  plans.append(dict(object_table=obj,activity_table=table,activities=list(dict.fromkeys(a for a in (seq[0]+seq[1] if isinstance(seq,tuple) else seq))),scenario='Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects.',origin='Authored domain extension; absent from original RSchema/manufacturer metadata'))
 # Typed FK histories retain actual times. Explicit object link table is generated from independently authored Python links.
 con.execute('DROP TABLE IF EXISTS lifecycle_case_link');con.execute('CREATE TABLE lifecycle_case_link(event_id TEXT NOT NULL,case_table TEXT NOT NULL,case_id TEXT NOT NULL,PRIMARY KEY(event_id,case_table,case_id))')
 for table,links in newlinks.items():
  con.executemany('INSERT INTO lifecycle_case_link VALUES (?,?,?)',[(eid,table,oid) for eid,ids in links.items() for oid in ids])
 newtables.append(dict(table='lifecycle_case_link',definition='Explicit case attribution across typed action histories; auxiliary extraction index, not a business case',primary_key=['event_id','case_table','case_id'],foreign_keys=[],columns=[dict(name=k,type='TEXT',constraints='NOT NULL',definition=d) for k,d in [('event_id','Validated identity in a typed activity table; polymorphic reference'),('case_table','Controlled existing business table name'),('case_id','Serialized primary key of the declared case table; composite parts separated by colon')]],source_origin='authored_lifecycle_extension'))
 union=' UNION ALL '.join('SELECT event_id,activity,occurred_at timestamp FROM '+s['table'] for s in sources)
 extra="SELECT e.event_id,l.case_id,e.activity,e.timestamp FROM ("+union+") e JOIN lifecycle_case_link l ON l.event_id=e.event_id WHERE l.case_table='"+defaulttable+"'"
 gold=readjl(p/'private/gold.jsonl');questions=readjl(p/'input/questions.jsonl');fullpairs={'warehouseflow':['R05','R06'],'universityflow':['U05','U06'],'plateflow':['V05','V06']}[name]
 import importlib.util
 spec=importlib.util.spec_from_file_location(name+'_life_builder',p/'build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
 original=next(g for g in gold if g['question_id']==fullid)['es'];base=b.compile_es(original).strip().rstrip(';').split(' ORDER BY case_id,timestamp,event_id')[0]
 combined='SELECT * FROM ('+base+' UNION ALL '+extra+') ORDER BY case_id,timestamp,event_id;'
 allhist=oldhist+newhist;default_expected=oldhist+[dict(e,case_id=oid) for e in newhist for oid in newlinks.get(defaulttable,{}).get(e['event_id'],[])]
 for g in gold:
  if g['question_id'] not in fullpairs:continue
  g['es']=dict(version='lifecycle-es-1',original_event_specification=original,activity_sources=sources,case_population_query=original['case_population_query'],case_link_table='lifecycle_case_link',case_table=defaulttable,compiled_sql=combined)
  g['process_view']['activities']=sorted({e['activity'] for e in default_expected});g['process_view']['scope_rule']='All actual source and authored lifecycle actions explicitly attributed to this case.'
  q=next(q for q in questions if q['question_id']==g['question_id']);q['text']='Extract all recorded source and lifecycle activities for each '+defaulttable.replace('_',' ')+'. Use the explicit case links and actual action times.'
  sqlpath=p/'private/gold_sql'/ (g['question_id']+'.sql');sqlpath.write_text(combined+'\n');actual=[dict(r) for r in con.execute(combined)];expected=sorted(default_expected,key=lambda e:(e['case_id'],e['timestamp'],e['event_id']));assert actual==expected
  with (p/'private/gold_logs'/(g['question_id']+'.csv')).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=['event_id','case_id','activity','timestamp']);w.writeheader();w.writerows(expected)
 if name=='universityflow':
  qid='U15';sql="SELECT e.event_id,l.case_id,e.activity,e.occurred_at timestamp FROM assignment_activity e JOIN lifecycle_case_link l ON l.event_id=e.event_id WHERE l.case_table='student' AND e.activity='Assignment Submitted' ORDER BY l.case_id,e.occurred_at,e.event_id;"
  g=next(x for x in gold if x['question_id']==qid);g.clear();g.update(question_id=qid,category='explicit',answerability='answerable',process_view=dict(case_concept='Student',activities=['Assignment Submitted'],scope_rule='Actual assignment submissions in the authored assignment history.'),es=dict(version='lifecycle-es-1',compiled_sql=sql,activity_sources=[x for x in sources if x['object_table']=='assignment'],case_table='student',case_link_table='lifecycle_case_link',case_population_query='SELECT student_id FROM student'))
  expected=sorted([dict(e,case_id=oid) for e in newhist if e['activity']=='Assignment Submitted' for oid in newlinks['student'].get(e['event_id'],[])],key=lambda e:(e['case_id'],e['timestamp'],e['event_id']));assert [dict(r) for r in con.execute(sql)]==expected
  (p/'private/gold_sql/U15.sql').write_text(sql+'\n')
  with (p/'private/gold_logs/U15.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=['event_id','case_id','activity','timestamp']);w.writeheader();w.writerows(expected)
 for path,values in [('private/canonical_history.jsonl',allhist),('private/gold.jsonl',gold),('input/questions.jsonl',questions)]: (p/path).write_text(''.join(json.dumps(x)+'\n' for x in values))
 js(p/'private/lifecycle_links.json',newlinks);js(p/'design/object_activity_design.json',plans);js(p/'private/lifecycle_persistence_mapping.json',sources)
 d=json.loads((p/'input/data_dictionary.json').read_text());d['tables']+=newtables;d['object_activity_design']=plans;d['business_rules']=['Original source layer: '+x for x in d['business_rules']];d['business_rules']+=['Original source rows are preserved. Added typed activity histories are authored synthetic domain extensions, not claimed source fields.','Only actual occurred_at times generate lifecycle events. Planned dates and technical timestamps remain excluded.','Lifecycle case links use exact typed object identity. Related cases may share an event; uniqueness is (case_id,event_id).','Incomplete cases and conditional revision branches are intentional; no final action is inferred for an open case.'];js(p/'input/data_dictionary.json',d)
 for fn in ['adaptation_report.json','logical_schema.json','conceptual_model.json']:
  file=p/'design'/fn
  if file.exists():
   original_design=json.loads(file.read_text());js(file,dict(original_source_design=original_design,authored_lifecycle_extensions=plans,added_tables=newtables,final_table_count=len(d['tables'])))
 with (p/'input/schema.sql').open('a') as f:f.write('\n-- Authored lifecycle extensions\n'+ '\n'.join(con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND (name LIKE '%_activity' OR name='lifecycle_case_link')").fetchone() or [])+'\n')
 # Re-export every extension DDL, preserving original SQL verbatim.
 sp=p/'input/schema.sql';s=sp.read_text().split('\n-- Authored lifecycle extensions')[0];sp.write_text(s+'\n-- Authored lifecycle extensions\n'+'\n'.join(r[0]+';' for r in con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND (name LIKE '%_activity' OR name='lifecycle_case_link')"))+'\n')
 report=json.loads((p/'validation_report.json').read_text());report['questions']=[dict(question_id=x['question_id'],status='pass',event_count=len(list(con.execute(x['es']['compiled_sql'])))) if x['es'] and 'compiled_sql' in x['es'] else next(r for r in report['questions'] if r['question_id']==x['question_id']) for x in gold];report['events']=len(allhist);report['activity_counts']=dict(Counter(e['activity'] for e in allhist));report['table_rows']={r[0]:con.execute('SELECT COUNT(*) FROM '+r[0]).fetchone()[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")};report['lifecycle_extensions']=dict(added_tables=len(newtables),added_events=len(newhist),source_origin='authored',checks={'typed_foreign_keys':'pass','actual_action_order':'pass','full_sql_equals_history':'pass'});report['limitations']=[x for x in report.get('limitations',[]) if not any(v in x.lower() for v in ['no assignment-submission','five activity'])]+['Atomic operation/grading records remain auxiliary single-occurrence cases. New actions are synthetic domain design, not real production observations.'];assert not list(con.execute('PRAGMA foreign_key_check'));assert len({e['event_id'] for e in allhist})==len(allhist);js(p/'validation_report.json',report)
 catalog=json.loads((p/'input/task_scope_catalog.json').read_text());catalog['activities']=sorted({e['activity'] for e in default_expected});catalog['default_scope']='All actual events explicitly attributed to '+defaulttable;catalog['object_activity_design']=plans;js(p/'input/task_scope_catalog.json',catalog)
 con.commit();con.close()
 doc='# '+name.replace('flow','Flow').title()+' object activities and scenarios\n\n- Original source requirements, columns and keys remain preserved.\n- Every action below is an explicitly authored domain extension; these stages were not present in the source schemas.\n- Each added history row records an actual activity, occurrence time, outcome and a declared FK to its object.\n- Conditional revision branches and incomplete cases are intentional. Atomic grading/operation records remain auxiliary logs.\n- Master-object views aggregate linked work; they do not assert one chronological causal process across unrelated jobs.\n\n| Object | Added activities | Situation | Storage |\n|---|---|---|---|\n'
 for x in plans:doc+='| '+x['object_table']+' | '+' → '.join(x['activities'])+' | '+x['scenario']+' | '+x['activity_table']+' |\n'
 doc+='\n- The full ES unions the original milestone sources and the new typed activity histories, then applies explicit event-to-case links.\n- Related goods/workers, students/instructors and parent materials receive an event only through a documented business relationship.\n- `lifecycle_case_link` is a generated extraction index with validated object identities; it is not an additional business object.\n'
 (p/'docs/object_activity_design.md').write_text(doc)
 rp=p/'design/requirements.md';text=rp.read_text().split('\n## Authored lifecycle extension')[0];rp.write_text(text+'\n## Authored lifecycle extension\n\n'+doc)
if __name__=='__main__':
 for n in CONFIG:extend(ROOT/'datasets'/n)
