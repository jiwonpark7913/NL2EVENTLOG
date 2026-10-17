"""Store one-time milestones on their existing business records without duplicating events."""
import json,sqlite3,csv,importlib.util
from pathlib import Path
MIGRATE={
 'warehouseflow':{'transaction_record':['Receiving Requested','Receiving Scheduled','Dispatch Requested','Dispatch Approved']},
 'universityflow':{'registration':['Registration Requested','Registration Approved','Course Started','Course Assessment Completed','Course Grade Finalized'],'degree_examination_result':['Examination Scheduled','Examination Checked In','Examination Score Published','Examination Result Reviewed'],'assignment':['Assignment Assigned','Assignment Submitted','Assignment Grade Finalized'],'thesis':['Thesis Draft Registered','Thesis Review Started','Thesis Accepted']}}
def readjl(p):return [json.loads(x) for x in p.read_text().splitlines()]
def writejl(p,rs):p.write_text(''.join(json.dumps(r)+'\n' for r in rs))
def builder(p):
 spec=importlib.util.spec_from_file_location(p.name+'_ts_builder',p/'build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);return b

def migrate(p):
 p=Path(p)
 if p.name not in MIGRATE:return
 con=sqlite3.connect(p/'input/database.sqlite');con.row_factory=sqlite3.Row;con.execute('PRAGMA foreign_keys=ON');d=json.loads((p/'input/data_dictionary.json').read_text());gs=readjl(p/'private/gold.jsonl');fid={'warehouseflow':'R05','universityflow':'U05'}[p.name];base=next(g['es'] for g in gs if g['question_id']==fid);native=[];removed=[];mapping=[]
 for obj,actions in MIGRATE[p.name].items():
  table=obj+'_activity';pk=[r['name'] for r in sorted(con.execute('PRAGMA table_info('+obj+')'),key=lambda r:r['pk']) if r['pk']];target=next(t for t in d['tables'] if t['table']==obj)
  for action in actions:
   column=action.lower().replace(' ','_')+'_at';con.execute('ALTER TABLE '+obj+' ADD COLUMN '+column+' TEXT');target['columns'].append(dict(name=column,type='TEXT',constraints='',source_origin='authored_milestone_column',event_activity=action,definition='Actual UTC time of '+action+'. NULL means no recorded occurrence. Authored single-occurrence milestone; not a source-provided field.'))
   rows=[dict(r) for r in con.execute('SELECT * FROM '+table+' WHERE activity=?',(action,))]
   assert len({tuple(r[k] for k in pk) for r in rows})==len(rows),'Repeated activities must stay row encoded'
   suffixes={r['event_id'].rsplit(':',1)[1] for r in rows};key=" || ':' || ".join(pk)
   if len(suffixes)==1:event_key="'LC:"+obj+":' || "+key+" || ':"+next(iter(suffixes))+"'"
   else:
    assert obj in ['assignment','thesis'];revision='Assignment Revision Requested' if obj=='assignment' else 'Thesis Revision Requested';yes='6' if obj=='assignment' else '5';condition="EXISTS (SELECT 1 FROM "+table+" rv WHERE "+' AND '.join('rv.'+k+'='+obj+'.'+k for k in pk)+" AND rv.activity='"+revision+"')"
    event_key="'LC:"+obj+":' || "+key+" || ':' || CASE WHEN "+condition+" THEN '"+yes+"' ELSE '3' END"

   for r in rows:con.execute('UPDATE '+obj+' SET '+column+'=? WHERE '+' AND '.join(k+'=?' for k in pk),(r['occurred_at'],*[r[k] for k in pk]))
   sql='SELECT '+event_key+" event_id, '"+action+"' activity, "+column+' timestamp FROM '+obj+' WHERE '+column+' IS NOT NULL'
   native.append(dict(activity=action,table=obj,object_table=obj,object_key=pk,encoding='column',timestamp_column=column,event_key=pk+[column],event_sql=sql))
   mapping.append(dict(table=obj,column=column,activity=action,old_table=table,preserved_event_ids=[r['event_id'] for r in rows]))
   con.execute('DELETE FROM '+table+' WHERE activity=?',(action,))
  if con.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0:con.execute('DROP TABLE '+table);removed.append(table)
 # Retained history sources capture only the remaining row-encoded activity labels.
 retained=[]
 for source in base['activity_sources']:
  if source['table'] in removed:continue
  source=dict(source);labels=[r[0] for r in con.execute('SELECT DISTINCT activity FROM '+source['table'])]
  source['event_sql']='SELECT event_id,activity,occurred_at timestamp FROM '+source['table'];source['encoding']='row';source['activities']=labels;retained.append(source)
 sources=retained+native;events=' UNION ALL '.join(s['event_sql'] for s in sources);old=base['original_event_specification'];b=builder(p);originalsql=b.compile_es(old).strip().rstrip(';').split(' ORDER BY case_id,timestamp,event_id')[0];case_table=base['case_table'];extra="SELECT e.event_id,l.case_id,e.activity,e.timestamp FROM ("+events+") e JOIN lifecycle_case_link l ON l.event_id=e.event_id WHERE l.case_table='"+case_table+"'";full='SELECT * FROM ('+originalsql+' UNION ALL '+extra+') ORDER BY case_id,timestamp,event_id;'
 hist=readjl(p/'private/canonical_history.jsonl');expected=sorted(hist,key=lambda e:(e['case_id'],e['timestamp'],e['event_id']))
 # University has course/module/task management events outside the student population.
 links=json.loads((p/'private/lifecycle_links.json').read_text());expected=sorted([e for e in hist if not e['event_id'].startswith('LC:')]+[dict(e,case_id=cid) for e in hist if e['event_id'].startswith('LC:') for cid in links.get(case_table,{}).get(e['event_id'],[])],key=lambda e:(e['case_id'],e['timestamp'],e['event_id']))
 assert [dict(r) for r in con.execute(full)]==expected
 pairs={'warehouseflow':['R05','R06'],'universityflow':['U05','U06']}[p.name]
 for g in gs:
  if g['question_id'] in pairs:g['es']=dict(version='mixed-milestone-es-1',original_event_specification=old,activity_sources=sources,case_population_query=base['case_population_query'],case_link_table='lifecycle_case_link',case_table=case_table,compiled_sql=full)
  if p.name=='universityflow' and g['question_id']=='U15':
   source=next(s for s in native if s['activity']=='Assignment Submitted');g['es'].update(activity_sources=[source],compiled_sql='SELECT e.event_id,a.student_id case_id,e.activity,e.timestamp FROM ('+source['event_sql']+") e JOIN assignment a ON e.event_id='LC:assignment:' || a.assignment_id || ':2' ORDER BY case_id,timestamp,event_id;")
  if g['question_id'] in pairs or g['question_id']=='U15' and p.name=='universityflow':(p/'private/gold_sql'/(g['question_id']+'.sql')).write_text(b.compile_es(g['es'])+'\n')
 writejl(p/'private/gold.jsonl',gs);d['tables']=[t for t in d['tables'] if t['table'] not in removed];d['business_rules']+=['One-time milestone events are stored in named timestamp columns on their business record. They have been removed from generic action rows to prevent duplicate extraction.','Repeated review/revision/grading/experiment actions remain row encoded; milestone timestamps preserve their original event IDs and actual times.'];(p/'input/data_dictionary.json').write_text(json.dumps(d,indent=2)+'\n');(p/'private/lifecycle_persistence_mapping.json').write_text(json.dumps(sources,indent=2)+'\n');(p/'design/timestamp_column_mapping.json').write_text(json.dumps(dict(migrated_columns=mapping,removed_empty_history_tables=removed),indent=2)+'\n')
 (p/'input/schema.sql').write_text('PRAGMA foreign_keys=ON;\n'+'\n'.join(r[0]+';' for r in con.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND type IN ('table','trigger') ORDER BY type,rowid"))+'\n');report=json.loads((p/'validation_report.json').read_text());report['table_rows']={t['table']:con.execute('SELECT COUNT(*) FROM '+t['table']).fetchone()[0] for t in d['tables']};report['timestamp_migration']=dict(added_columns=len(mapping),removed_empty_history_tables=removed,original_event_identity_and_time='preserved',duplicate_event_storage='none');(p/'validation_report.json').write_text(json.dumps(report,indent=2)+'\n')
 for fn in ['logical_schema.json','conceptual_model.json','adaptation_report.json']:
  path=p/'design'/fn
  if path.exists():data=json.loads(path.read_text());data.update(final_table_count=len(d['tables']),current_tables=d['tables'],timestamp_migration=mapping,removed_empty_history_tables=removed);path.write_text(json.dumps(data,indent=2)+'\n')
 plans=json.loads((p/'design/object_activity_design.json').read_text())
 for plan in plans:
  obj=plan['object_table'];moved=[x for x in mapping if x['table']==obj]
  if moved:
   plan['milestone_columns']=[dict(activity=x['activity'],column=x['column']) for x in moved];plan['row_activities']=[a for a in plan['activities'] if a not in {x['activity'] for x in moved}];plan['storage']='Actual milestone columns on '+obj+'; remaining repeatable actions stay in '+obj+'_activity' if plan['row_activities'] else 'Actual milestone columns on '+obj
   if obj+'_activity' in removed:plan.pop('activity_table',None)
 (p/'design/object_activity_design.json').write_text(json.dumps(plans,indent=2)+'\n');catalog=json.loads((p/'input/task_scope_catalog.json').read_text());catalog['object_activity_design']=plans;(p/'input/task_scope_catalog.json').write_text(json.dumps(catalog,indent=2)+'\n');d['object_activity_design']=plans;(p/'input/data_dictionary.json').write_text(json.dumps(d,indent=2)+'\n')
 doc='# Object activity storage\n\n- Actual one-time milestone columns and retained row histories are used together. Events are extracted once, not mirrored in two places.\n- Original event IDs and occurrence times are preserved. All added fields are authored synthetic extensions.\n\n| Object | Activities | Storage |\n|---|---|---|\n'+''.join('| '+x['object_table']+' | '+'; '.join(x['activities'])+' | '+x.get('storage',x.get('activity_table','Row history'))+' |\n' for x in plans)
 (p/'docs/object_activity_design.md').write_text(doc)
 assert not list(con.execute('PRAGMA foreign_key_check'));con.commit();con.close()

def add_queries(p):
 p=Path(p);configs={'warehouseflow':[('OW04',['Receiving Requested','Receiving Scheduled','Dispatch Requested','Dispatch Approved'])],'universityflow':[('OU01',['Examination Scheduled','Examination Checked In','Examination Score Published','Examination Result Reviewed']),('OU03',['Registration Requested','Registration Approved','Course Started','Course Assessment Completed','Course Grade Finalized']),('OU08',['Assignment Assigned','Assignment Submitted','Assignment Grade Finalized']),('OU06',['Thesis Draft Registered','Thesis Review Started','Thesis Accepted'])],'plateflow':[('OPV07',['Plate Quality Review Started','Plate Packing Started'])]};qs=readjl(p/'input/questions.jsonl');gs=readjl(p/'private/gold.jsonl');b=builder(p)
 for i,(anchor,acts) in enumerate(configs[p.name],1):
  import copy
  g=copy.deepcopy(next(g for g in gs if g['question_id']==anchor));qid='TS'+f'{i:02}';g.update(question_id=qid,category='explicit');g['process_view']['activities']=acts;g['process_view']['scope_rule']='Only the explicitly named actual milestone activities.';source=g['es'];sql='SELECT * FROM ('+b.compile_es(source).strip().rstrip(';')+') WHERE activity IN ('+','.join("'"+a+"'" for a in acts)+') ORDER BY case_id,timestamp,event_id;';g['es']=dict(version='timestamp-subset-es-1',case_population_query=source['case_population_query'],base_event_specification=source,selected_activities=acts,compiled_sql=sql);gs.append(g);qs.append(dict(question_id=qid,text='Extract '+', '.join(acts)+' events for each '+g['process_view']['case_concept'].lower()+'.',pair_of=None))
 writejl(p/'private/gold.jsonl',gs);writejl(p/'input/questions.jsonl',qs)
