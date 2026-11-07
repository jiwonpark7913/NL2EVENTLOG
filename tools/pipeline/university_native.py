"""Consolidate university activity storage into the eleven source business-table roles."""
import json,sqlite3,csv,copy
from pathlib import Path
from timestamp_columns import builder,readjl,writejl
ACTIONS={'assignment':['Assignment Revision Requested','Assignment Resubmitted'],'thesis':['Thesis Revision Requested','Thesis Resubmitted'],'simulation_module':['Simulation Module Published','Simulation Module Validated','Simulation Module Released','Simulation Module Retired'],'student_simulation_experiment_result':['Simulation Run Scheduled','Simulation Run Started','Simulation Output Reviewed','Simulation Result Accepted'],'course':['Course Offering Proposed','Course Offering Approved','Course Offering Published','Course Offering Closed'],'task':['Design Task Created','Design Task Approved','Design Task Published','Design Task Closed']}
def convert(p):
 p=Path(p);c=sqlite3.connect(p/'input/database.sqlite');c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');d=json.loads((p/'input/data_dictionary.json').read_text());gs=readjl(p/'private/gold.jsonl');full=next(g['es'] for g in gs if g['question_id']=='U05');hist=readjl(p/'private/canonical_history.jsonl');links=json.loads((p/'private/lifecycle_links.json').read_text());sources=[];columns=[];removed=[];pkof=lambda t:[r['name'] for r in sorted(c.execute('PRAGMA table_info('+t+')'),key=lambda r:r['pk']) if r['pk']]
 # Explicit assessment kinds preserve original grading rows and distinguish the seven reassessments.
 c.execute("ALTER TABLE assignment_grading ADD COLUMN grading_kind TEXT NOT NULL DEFAULT 'ORIGINAL' CHECK(grading_kind IN ('ORIGINAL','REASSESSMENT'))")
 c.execute('ALTER TABLE assignment_grading ADD COLUMN reassessment_event_id TEXT');c.execute('CREATE UNIQUE INDEX ux_reassessment_event_id ON assignment_grading(reassessment_event_id)')
 grading=next(t for t in d['tables'] if t['table']=='assignment_grading');grading['columns'].append(dict(name='grading_kind',type='TEXT',constraints="NOT NULL DEFAULT 'ORIGINAL' CHECK(grading_kind IN ('ORIGINAL','REASSESSMENT'))",definition='ORIGINAL retains each existing Assignment Graded occurrence. REASSESSMENT denotes an authored Assignment Regraded occurrence.',source_origin='authored_assessment_classification'))
 grading['columns'].append(dict(name='reassessment_event_id',type='TEXT',constraints='UNIQUE through ux_reassessment_event_id; nullable for ORIGINAL rows',definition='Stable identity of an authored reassessment occurrence. The source composite PK remains unchanged; distinct reassessments have distinct occurrence IDs.',source_origin='authored_assessment_identifier'))
 for r in c.execute("SELECT * FROM assignment_activity WHERE activity='Assignment Regraded'").fetchall():
  prior=c.execute("SELECT * FROM assignment_grading WHERE assignment_id=? AND grading_kind='ORIGINAL' ORDER BY grading_time DESC LIMIT 1",(r['assignment_id'],)).fetchone();assert prior is not None
  c.execute('INSERT INTO assignment_grading VALUES (?,?,?,?,?,?,?)',(r['assignment_id'],prior['instructor_id'],r['occurred_at'],min(100,prior['score']+5),'Authored synthetic reassessment score and feedback','REASSESSMENT',r['event_id']));case=r['assignment_id']+':'+prior['instructor_id']+':'+r['occurred_at'];links.setdefault('assignment_grading',{})[r['event_id']]=[case]
 c.execute("DELETE FROM assignment_activity WHERE activity='Assignment Regraded'")
 reassessment=dict(activity='Assignment Regraded',table='assignment_grading',object_table='assignment_grading',object_key=pkof('assignment_grading'),encoding='row',timestamp_column='grading_time',event_sql="SELECT reassessment_event_id event_id,'Assignment Regraded' activity,grading_time timestamp FROM assignment_grading WHERE grading_kind='REASSESSMENT'")
 # Finish migrating each remaining one-time milestone. In this simulation each run/revision has its own source record.
 for obj,actions in ACTIONS.items():
  table=obj+'_activity';pk=pkof(obj);t=next(t for t in d['tables'] if t['table']==obj)
  for action in actions:
   rs=[dict(r) for r in c.execute('SELECT * FROM '+table+' WHERE activity=?',(action,))];assert len({tuple(r[k] for k in pk) for r in rs})==len(rs)
   suffix={r['event_id'].rsplit(':',1)[1] for r in rs};assert len(suffix)==1,(action,suffix)
   col=action.lower().replace(' ','_')+'_at';c.execute('ALTER TABLE '+obj+' ADD COLUMN '+col+' TEXT');t['columns'].append(dict(name=col,type='TEXT',constraints='',source_origin='authored_milestone_column',event_activity=action,definition='Actual UTC time of '+action+'. One occurrence per source business record in this simulation. NULL means no recorded occurrence.'))
   for r in rs:c.execute('UPDATE '+obj+' SET '+col+'=? WHERE '+' AND '.join(k+'=?' for k in pk),(r['occurred_at'],*[r[k] for k in pk]))
   key=" || ':' || ".join(pk);sql="SELECT 'LC:"+obj+":' || "+key+" || ':"+next(iter(suffix))+"' event_id,'"+action+"' activity,"+col+' timestamp FROM '+obj+' WHERE '+col+' IS NOT NULL';sources.append(dict(activity=action,table=obj,object_table=obj,object_key=pk,encoding='column',timestamp_column=col,event_sql=sql));columns.append(dict(table=obj,column=col,activity=action));c.execute('DELETE FROM '+table+' WHERE activity=?',(action,))
  assert c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0;c.execute('DROP TABLE '+table);removed.append(table)
 # Existing milestone IDs depended on whether the one revision branch occurred; preserve them using business milestones.
 for s in full['activity_sources']:
  if s['encoding']!='column':continue
  s=copy.deepcopy(s)
  if s['activity'] in ['Assignment Grade Finalized','Thesis Accepted']:
   obj=s['object_table'];kind='assignment' if obj=='assignment' else 'thesis';yes='6' if kind=='assignment' else '5';col=kind+'_revision_requested_at';key=" || ':' || ".join(s['object_key']);s['event_sql']="SELECT 'LC:"+obj+":' || "+key+" || ':' || CASE WHEN "+col+" IS NOT NULL THEN '"+yes+"' ELSE '3' END event_id,'"+s['activity']+"' activity,"+s['timestamp_column']+' timestamp FROM '+obj+' WHERE '+s['timestamp_column']+' IS NOT NULL'
  sources.append(s)
 sources.append(reassessment)
 # Every extra event exposes its typed business key; derive all case projections through existing PK/FK relationships.
 maps={};object_expr={}
 for s in sources:
  obj=s['object_table'];pk=s['object_key'];key=" || ':' || ".join(pk);needle=' timestamp FROM '+s['table'];assert needle in s['event_sql'];s['event_sql']=s['event_sql'].replace(needle,' timestamp,'+key+' object_key FROM '+s['table'],1);event='('+s['event_sql']+') e';join=' JOIN '+obj+' o ON '+" || ':' || ".join('o.'+k for k in pk)+'=e.object_key';targets={obj:(" || ':' || ".join('o.'+k for k in pk),'')}
  if obj in ['registration','degree_examination_result','thesis','student_simulation_experiment_result']:targets['student']=('o.student_id','')
  if obj=='registration':targets['course']=('o.course_id','')
  if obj=='student_simulation_experiment_result':targets['simulation_module']=('o.module_id','')
  if obj=='assignment':
   targets['student']=('o.student_id','');targets['instructor']=('g.instructor_id'," JOIN (SELECT DISTINCT assignment_id,instructor_id FROM assignment_grading WHERE grading_kind='ORIGINAL') g ON g.assignment_id=o.assignment_id")
  if obj=='assignment_grading':targets.update(assignment=('o.assignment_id',''),instructor=('o.instructor_id',''),student=('a.student_id',' JOIN assignment a ON a.assignment_id=o.assignment_id'))
  for target,(expr,extra) in targets.items():maps.setdefault(target,[]).append('SELECT e.event_id,'+expr+' case_id FROM '+event+join+extra)
 maps={t:' UNION ALL '.join(parts) for t,parts in maps.items()};c.execute('DROP TABLE lifecycle_case_link');d['tables']=[t for t in d['tables'] if t['table'] not in removed and t['table']!='lifecycle_case_link'];assert len(d['tables'])==11
 original=copy.deepcopy(full['original_event_specification'])
 for s in original['sources']:
  if s['activity']=='Assignment Graded':s['from_sql']+=" WHERE g.grading_kind='ORIGINAL'"
 b=builder(p);base=b.compile_es(original).strip().rstrip(';').split(' ORDER BY case_id,timestamp,event_id')[0];all_events=' UNION ALL '.join('SELECT event_id,activity,timestamp FROM ('+s['event_sql']+')' for s in sources);extra='SELECT e.event_id,l.case_id,e.activity,e.timestamp FROM ('+all_events+') e JOIN ('+maps['student']+') l ON l.event_id=e.event_id';sql='SELECT * FROM ('+base+' UNION ALL '+extra+') ORDER BY case_id,timestamp,event_id;';spec=dict(version='university-native-es-1',original_event_specification=original,activity_sources=sources,native_case_mapping_sql=maps,case_population_query=full['case_population_query'],compiled_sql=sql)
 for g in gs:
  if g['question_id'] in ['U05','U06']:g['es']=spec
  elif g.get('es') and 'sources' in g['es']:
   for s in g['es']['sources']:
    if s['activity']=='Assignment Graded':s['from_sql']+=" WHERE g.grading_kind='ORIGINAL'"
  elif g['question_id']=='U15':
   src=next(s for s in sources if s.get('activity')=='Assignment Submitted');g['es']=dict(version='university-native-subset-es-1',case_population_query='SELECT student_id FROM student',compiled_sql='SELECT e.event_id,a.student_id case_id,e.activity,e.timestamp FROM ('+src['event_sql']+') e JOIN assignment a ON a.assignment_id=e.object_key ORDER BY case_id,timestamp,event_id;',activity_sources=[src])
  if g['answerability']=='answerable':
   query=b.compile_es(g['es']);(p/'private/gold_sql'/(g['question_id']+'.sql')).write_text(query+'\n');actual=[dict(r) for r in c.execute(query)]
   with (p/'private/gold_logs'/(g['question_id']+'.csv')).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=['event_id','case_id','activity','timestamp']);w.writeheader();w.writerows(actual)
 expected=sorted([e for e in hist if not e['event_id'].startswith('LC:')]+[dict(e,case_id=cid) for e in hist if e['event_id'].startswith('LC:') for cid in links['student'].get(e['event_id'],[])],key=lambda e:(e['case_id'],e['timestamp'],e['event_id']));assert [dict(r) for r in c.execute(sql)]==expected
 writejl(p/'private/gold.jsonl',gs);(p/'private/lifecycle_links.json').write_text(json.dumps(links,indent=2)+'\n');(p/'private/lifecycle_persistence_mapping.json').write_text(json.dumps(sources,indent=2)+'\n');d['business_rules']+=["The eleven original university business-table roles are retained; generic activity and case-link tables are removed.","Single-occurrence stages use actual milestone columns; repeated grading and reassessment occurrences use assignment_grading rows.","grading_kind distinguishes preserved ORIGINAL grading rows from authored REASSESSMENT rows. Reassessment scores/feedback are synthetic additions.","Composite primary keys are a single key composed of multiple columns; each combination identifies one business record."]
 d['business_rules']=[r for r in d['business_rules'] if not any(x in r for x in ['Added typed activity histories','Only actual occurred_at','Repeated review/revision/grading/experiment actions remain row encoded'])]
 plans=json.loads((p/'design/object_activity_design.json').read_text())
 for plan in plans:
  plan.pop('activity_table',None);plan['milestone_columns']=[dict(activity=s['activity'],column=s['timestamp_column']) for s in sources if s['table']==plan['object_table'] and s['encoding']=='column'];plan['row_activities']=[];plan['storage']='Existing '+plan['object_table']+' milestone columns'+('; grading/regrading rows in assignment_grading' if plan['object_table']=='assignment' else '')
 d['object_activity_design']=plans;(p/'design/object_activity_design.json').write_text(json.dumps(plans,indent=2)+'\n');catalog=json.loads((p/'input/task_scope_catalog.json').read_text());catalog['object_activity_design']=plans;catalog['explicit_activity_scope_overrides']={'OU10':['Assignment Graded']};(p/'input/task_scope_catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
 (p/'input/data_dictionary.json').write_text(json.dumps(d,indent=2)+'\n');(p/'input/schema.sql').write_text('PRAGMA foreign_keys=ON;\n'+'\n'.join(r[0]+';' for r in c.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND type IN ('table','index','trigger') ORDER BY CASE type WHEN 'table' THEN 0 WHEN 'index' THEN 1 ELSE 2 END,rowid"))+'\n');mapping=dict(added_milestone_columns=columns,removed_tables=removed+['lifecycle_case_link'],assessment_storage='assignment_grading with grading_kind',case_mapping_sql=maps)
 (p/'design/native_storage_mapping.json').write_text(json.dumps(mapping,indent=2)+'\n');report=json.loads((p/'validation_report.json').read_text());report['table_rows']={t['table']:c.execute('SELECT COUNT(*) FROM '+t['table']).fetchone()[0] for t in d['tables']};report['native_consolidation']=dict(final_tables=11,removed_tables=mapping['removed_tables'],original_events='preserved',actual_source_pk_fk='retained');(p/'validation_report.json').write_text(json.dumps(report,indent=2)+'\n')
 for fn in ['logical_schema.json','conceptual_model.json','adaptation_report.json']:
  path=p/'design'/fn;model=json.loads(path.read_text());model.update(added_tables=[],authored_lifecycle_extensions=plans,final_table_count=11,current_tables=d['tables'],native_consolidation=mapping);path.write_text(json.dumps(model,indent=2)+'\n')
 assert not list(c.execute('PRAGMA foreign_key_check'));c.commit();c.close()
 doc='# UniversityFlow business-table storage\n\n- Eleven original source business-table roles remain. All six remaining generic activity tables and the case-link index are removed.\n- One-time stages are actual-time columns on registration, examination result, assignment, thesis, experiment result, module, course and task records. NULL means not recorded.\n- Repeat runs remain distinct experiment-result rows under the source composite key. Grading and reassessments remain separate assignment_grading rows.\n- The current simulation has at most one revision branch per assignment/thesis. Multiple revision rounds would require a dedicated submission/review history rather than overwriting these milestone columns.\n- Original source keys and business events remain. Added columns, grading_kind and reassessment scores are authored synthetic assumptions.\n- Event attribution uses declared keys and existing business JOINs; there is no persisted event-to-case index.\n\n| Business table | Added milestone activities |\n|---|---|\n'
 for t in d['tables']:
  acts=[s['activity'] for s in sources if s['table']==t['table']];doc+='| '+t['table']+' | '+'; '.join(acts)+' |\n'
 (p/'docs/object_activity_design.md').write_text(doc);(p/'design/requirements.md').write_text(doc)
