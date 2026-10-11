"""Add an explicitly scoped event log for every usable keyed table in each dataset."""
import json,csv,sqlite3
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parent
FIELDS=['event_id','case_id','activity','timestamp']
def readjl(p):return [json.loads(l) for l in p.read_text().splitlines()]
def writejson(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def writejl(p,rows):p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
def extend_dataset(p):
 p=Path(p);name=p.name;con=sqlite3.connect(p/'input/database.sqlite');con.row_factory=sqlite3.Row
 rows={r[0]:[dict(x) for x in con.execute('SELECT * FROM '+r[0])] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
 hist=readjl(p/'private/canonical_history.jsonl');by_id={e['event_id']:e for e in hist};questions=readjl(p/'input/questions.jsonl');gold=readjl(p/'private/gold.jsonl')
 prefix={'warehouseflow':'OW','universityflow':'OU','plateflow':'OPV'}[name]
 questions=[q for q in questions if not q['question_id'].startswith(prefix)];gold=[g for g in gold if not g['question_id'].startswith(prefix)]
 fullid={'warehouseflow':'R05','universityflow':'U05','plateflow':'V05'}[name];base=next(g['es'] for g in gold if g['question_id']==fullid)
 # Reuse each dataset's SQL compiler without running its generation entry point.
 import importlib.util
 spec=importlib.util.spec_from_file_location(name+'_builder',p/'build.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
 base_sql=(base['compiled_sql'] if 'compiled_sql' in base else builder.compile_es(base)).strip().rstrip(';').split(' ORDER BY case_id,timestamp,event_id')[0]
 original_hist=[e for e in hist if not e['event_id'].startswith('LC:')]
 if 'original_event_specification' in base:base_sql=builder.compile_es(base['original_event_specification']).strip().rstrip(';').split(' ORDER BY case_id,timestamp,event_id')[0]
 views=[]
 def add(table,concept,scope,mapping_sql,links,kind='business_object'):
  mapping=defaultdict(set)
  for eid,oid in links:
   if eid in by_id:mapping[eid].add(str(oid))
  pk=[r[1] for r in sorted(con.execute('PRAGMA table_info('+table+')'),key=lambda r:r[5]) if r[5]]
  case_ids=[':'.join(str(r[k]) for k in pk) for r in rows[table]]
  views.append(dict(table=table,case_concept=concept,scope_rule=scope,kind=kind,mapping_sql=mapping_sql,mapping=mapping,case_ids=case_ids,key_columns=pk))
 if name=='warehouseflow':
  transactions=rows['transaction_record'];eid=lambda r:'TX:'+r['transaction_id']
  add('warehouse','Warehouse','All receiving and dispatching tasks recorded for this warehouse.',"SELECT 'TX:' || transaction_id event_id, warehouse_number case_id FROM transaction_record",[(eid(r),r['warehouse_number']) for r in transactions])
  add('goods','Goods','Receiving and dispatching tasks that contain this goods type; one event per goods type and transaction.',"SELECT 'TX:' || transaction_id event_id, goods_id case_id FROM goods_transaction_detail",[('TX:'+r['transaction_id'],r['goods_id']) for r in rows['goods_transaction_detail']])
  add('loader','Worker','Receiving and dispatching tasks assigned to this worker; one event per worker and transaction.',"SELECT 'TX:' || transaction_id event_id, loader_id case_id FROM loader_transaction",[('TX:'+r['transaction_id'],r['loader_id']) for r in rows['loader_transaction']])
  add('transaction_record','Warehouse transaction','The single receiving or dispatching event represented by this transaction.',"SELECT 'TX:' || transaction_id event_id, transaction_id case_id FROM transaction_record",[(eid(r),r['transaction_id']) for r in transactions],'event_record')
  add('goods_transaction_detail','Goods transaction line','The transaction event linked to this composite-key goods line.',"SELECT 'TX:' || transaction_id event_id, goods_id || ':' || transaction_id case_id FROM goods_transaction_detail",[('TX:'+r['transaction_id'],r['goods_id']+':'+r['transaction_id']) for r in rows['goods_transaction_detail']],'association_record')
  add('loader_transaction','Worker transaction assignment','The transaction event linked to this composite-key worker assignment.',"SELECT 'TX:' || transaction_id event_id, loader_id || ':' || transaction_id case_id FROM loader_transaction",[('TX:'+r['transaction_id'],r['loader_id']+':'+r['transaction_id']) for r in rows['loader_transaction']],'association_record')
 elif name=='universityflow':
  add('student','Student','All five recorded academic activity types linked to this student.',"SELECT event_id, case_id FROM ("+base_sql+")",[(e['event_id'],e['case_id']) for e in original_hist])
  regs=rows['registration'];exams=rows['degree_examination_result'];grades=rows['assignment_grading'];sims=rows['student_simulation_experiment_result'];theses=rows['thesis']
  regid=lambda r:'REG:'+r['student_id']+':'+r['course_id'];gradeid=lambda r:'GRADE:'+r['assignment_id']+':'+r['instructor_id']+':'+r['grading_time'];simid=lambda r:'SIM:'+r['student_id']+':'+r['module_id']+':'+r['simulation_date']
  add('course','Course','Successful registrations for this course offering. Course schedules and text-only instructor labels do not add events.',"SELECT 'REG:' || student_id || ':' || course_id event_id, course_id case_id FROM registration",[(regid(r),r['course_id']) for r in regs])
  add('registration','Student-course registration','The successful registration event represented by this student-course pair.',"SELECT 'REG:' || student_id || ':' || course_id event_id, student_id || ':' || course_id case_id FROM registration",[(regid(r),r['student_id']+':'+r['course_id']) for r in regs],'association_record')
  add('degree_examination_result','Examination result record','The examination occurrence represented by this result ID; score publication is not timestamped.',"SELECT 'EX:' || result_id event_id, result_id case_id FROM degree_examination_result",[('EX:'+r['result_id'],r['result_id']) for r in exams],'event_record')
  add('simulation_module','Simulation module','Every recorded student experiment completion using this module, including repeat runs.',"SELECT 'SIM:' || student_id || ':' || module_id || ':' || simulation_date event_id, module_id case_id FROM student_simulation_experiment_result",[(simid(r),r['module_id']) for r in sims])
  add('thesis','Thesis','The actual submission event for this thesis; no review events are recorded.',"SELECT 'THESIS:' || thesis_id event_id, thesis_id case_id FROM thesis",[('THESIS:'+r['thesis_id'],r['thesis_id']) for r in theses])
  add('student_simulation_experiment_result','Simulation experiment result record','The experiment-completion occurrence identified by student, module and simulation time.',"SELECT 'SIM:' || student_id || ':' || module_id || ':' || simulation_date event_id, student_id || ':' || module_id || ':' || simulation_date case_id FROM student_simulation_experiment_result",[(simid(r),r['student_id']+':'+r['module_id']+':'+r['simulation_date']) for r in sims],'event_record')
  add('assignment','Assignment','All recorded grading and regrading actions for this assignment; no submission timestamp is inferred.',"SELECT 'GRADE:' || assignment_id || ':' || instructor_id || ':' || grading_time event_id, assignment_id case_id FROM assignment_grading",[(gradeid(r),r['assignment_id']) for r in grades])
  add('instructor','Instructor','Grading and regrading actions performed by this instructor, without inferring links from course-name strings.',"SELECT 'GRADE:' || assignment_id || ':' || instructor_id || ':' || grading_time event_id, instructor_id case_id FROM assignment_grading",[(gradeid(r),r['instructor_id']) for r in grades])
  add('assignment_grading','Assignment grading record','The single grading action represented by the assignment-instructor-time key.',"SELECT 'GRADE:' || assignment_id || ':' || instructor_id || ':' || grading_time event_id, assignment_id || ':' || instructor_id || ':' || grading_time case_id FROM assignment_grading",[(gradeid(r),r['assignment_id']+':'+r['instructor_id']+':'+r['grading_time']) for r in grades],'event_record')
 elif name=='plateflow':
  materials=rows['as_rolled_material'];plans={r['plan_id']:r for r in rows['planned_rolling_instruction']};instructions={r['instruction_id']:r for r in rows['rolling_instruction']}
  by_m={r['material_id']:r for r in materials}
  add('slab_material','Slab','All recorded manufacturing events of the mother material and cut pieces derived from this slab; no upstream casting events are inferred.',"SELECT e.event_id, m.slab_id case_id FROM ("+base_sql+") e JOIN as_rolled_material m ON m.material_id=e.case_id",[(e['event_id'],by_m[e['case_id']]['slab_id']) for e in original_hist])
  add('planned_rolling_instruction','Rolling plan','The actual release of the rolling instruction linked to this plan; planned reheating times are not execution events.',"SELECT 'RI:' || instruction_id event_id, plan_id case_id FROM rolling_instruction",[('RI:'+r['instruction_id'],r['plan_id']) for r in instructions.values()])
  add('rolling_instruction','Rolling instruction','The actual release event for this rolling instruction.',"SELECT 'RI:' || instruction_id event_id, instruction_id case_id FROM rolling_instruction",[('RI:'+r['instruction_id'],r['instruction_id']) for r in instructions.values()])
  add('as_rolled_material','Mother material','All recorded mother-material events and its descendant-piece events, each occurrence once.',"SELECT event_id, case_id FROM ("+base_sql+")",[(e['event_id'],e['case_id']) for e in original_hist])
  add('furnace_charge_tracking','Furnace tracking record','The recorded yard-instruction receipt for this tracking record; lot-level charging events remain outside the material-event set.',"SELECT 'YD:' || tracking_id event_id, tracking_id case_id FROM furnace_charge_tracking",[('YD:'+r['tracking_id'],r['tracking_id']) for r in rows['furnace_charge_tracking']],'tracking_record')
  add('cutting_finishing_instruction','Cutting instruction','The actual release event for this cutting/finishing instruction.',"SELECT 'CI:' || instruction_id event_id, instruction_id case_id FROM cutting_finishing_instruction",[('CI:'+r['instruction_id'],r['instruction_id']) for r in rows['cutting_finishing_instruction']])
  pieces={r['plate_material_id']:r for r in rows['plate_material']};ops=rows['material_operation_history']
  piece_sql="SELECT 'OP:' || h.transaction_id event_id, p.plate_material_id case_id FROM material_operation_history h JOIN plate_material p ON p.plate_material_id=h.material_id UNION ALL SELECT 'DIM:' || plate_material_id event_id, plate_material_id case_id FROM plate_material WHERE dimension_inspected_at IS NOT NULL"
  links=[('OP:'+r['transaction_id'],r['material_id']) for r in ops if r['material_id'] in pieces]+[('DIM:'+r['plate_material_id'],r['plate_material_id']) for r in pieces.values() if r['dimension_inspected_at']]
  add('plate_material','Cut plate piece','Only operations recorded on this piece and its dimensional inspection. Upstream mother events are not copied to each piece.',piece_sql,links)
  add('material_operation_history','Material operation record','The operation-completion event represented by this transaction ID, preserving its process-code meaning.',"SELECT 'OP:' || transaction_id event_id, transaction_id case_id FROM material_operation_history",[('OP:'+r['transaction_id'],r['transaction_id']) for r in ops],'event_record')
 if (p/'private/lifecycle_links.json').exists():
  original=base['original_event_specification'];base_sql=builder.compile_es(original).strip().rstrip(';').split(' ORDER BY case_id,timestamp,event_id')[0]
  extra=' UNION ALL '.join('SELECT event_id, NULL case_id, activity, occurred_at timestamp FROM '+x['table'] for x in base['activity_sources'])
  base_sql += ' UNION ALL '+extra
 if (p/'private/lifecycle_links.json').exists():
  added=json.loads((p/'private/lifecycle_links.json').read_text())
  for v in views:
   links=added.get(v['table'],{})
   for eid,ids in links.items():v['mapping'][eid].update(ids)
   if links:
    v['mapping_sql'] += " UNION ALL SELECT event_id,case_id FROM lifecycle_case_link WHERE case_table='"+v['table']+"'"
    v['scope_rule']='Original recorded actions and authored lifecycle actions explicitly linked to this '+v['case_concept'].lower()+'.'
  if name=='universityflow':
   add('task','Course-design task','Actual creation, publication and closure of this design task; these are authored task-management actions, not inferred student executions.',"SELECT event_id,case_id FROM lifecycle_case_link WHERE case_table='task'",[(eid,oid) for eid,ids in added.get('task',{}).items() for oid in ids])
 catalog=json.loads((p/'input/task_scope_catalog.json').read_text());report=json.loads((p/'validation_report.json').read_text());report['questions']=[q for q in report['questions'] if not q['question_id'].startswith(prefix)];results=[];coverage=[]
 for k,v in enumerate(views,1):
  qid=prefix+f'{k:02}';sql='SELECT e.event_id, m.case_id, e.activity, e.timestamp FROM ('+base_sql+') e JOIN ('+v['mapping_sql']+') m ON m.event_id=e.event_id ORDER BY m.case_id,e.timestamp,e.event_id;'
  expected=sorted([dict(e,case_id=cid) for e in hist for cid in v['mapping'].get(e['event_id'],[])],key=lambda e:(e['case_id'],e['timestamp'],e['event_id']))
  actual=[dict(r) for r in con.execute(sql)];assert actual==expected,(name,qid);assert len({(e['case_id'],e['event_id']) for e in expected})==len(expected)
  assert {e['case_id'] for e in expected}<=set(v['case_ids'])
  acts=sorted({e['activity'] for e in expected});population="SELECT "+" || ':' || ".join(v['key_columns'])+" case_id FROM "+v['table']
  question='Extract an event log for each '+v['case_concept'].lower()+'. Include '+v['scope_rule'][0].lower()+v['scope_rule'][1:]
  questions.append(dict(question_id=qid,text=question,pair_of=None));gold.append(dict(question_id=qid,category='object_view',answerability='answerable',process_view=dict(case_concept=v['case_concept'],case_table=v['table'],activities=acts,scope_rule=v['scope_rule']),es=dict(version='object-view-es-1',base_event_specification=base,case_population_query=population,event_to_case_mapping_sql=v['mapping_sql'],compiled_sql=sql)))
  (p/'private/gold_sql'/f'{qid}.sql').write_text(sql+'\n')
  with (p/'private/gold_logs'/f'{qid}.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(expected)
  active={e['case_id'] for e in expected};entry=dict(question_id=qid,case_table=v['table'],case_concept=v['case_concept'],kind=v['kind'],status='answerable',scope_rule=v['scope_rule'],case_count=len(v['case_ids']),cases_with_events=len(active),cases_without_events=len(set(v['case_ids'])-active),event_rows=len(expected),activities=acts,log_path=f'private/gold_logs/{qid}.csv')
  coverage.append(entry);results.append(dict(question_id=qid,status='pass',event_count=len(expected)));report['questions'].append(results[-1])
 unavailable=[]
 if name=='universityflow' and not (p/'private/lifecycle_links.json').exists():
  qid='OU11';reason='Task dates are scheduled periods, not actual student actions. No declared task-to-student, task-to-experiment or timestamped task-assignment relationship exists.'
  questions.append(dict(question_id=qid,text='Extract actual task-execution events for each course-design task.',pair_of=None));gold.append(dict(question_id=qid,category='object_view',answerability='unsupported',reason=reason,process_view=dict(case_concept='Course-design task',case_table='task'),es=None));report['questions'].append(dict(question_id=qid,status='unsupported_by_design'));unavailable.append(dict(case_table='task',case_concept='Course-design task',status='unsupported',reason=reason,question_id=qid))
 if name=='plateflow':unavailable.append(dict(case_table='operation_code',status='reference_table',reason='Operation codes define activity meanings. They are not business-object instances or cases.'))
 for table in rows:
  if table.endswith('_activity') or table=='lifecycle_case_link':unavailable.append(dict(case_table=table,status='supporting_history',reason='Activity storage/index for its parent-object log; not an independent business case.'))
 catalog['object_views']=[{k:v for k,v in c.items() if k not in ['event_rows','log_path','cases_with_events','cases_without_events']} for c in coverage];catalog['unavailable_object_views']=unavailable
 report['object_view_checks']=dict(sql_equals_canonical_events='pass',unique_event_per_case='pass',case_population_coverage='pass');report['object_view_coverage']=coverage;report['unavailable_object_views']=unavailable;report['total_questions']=len(questions);report['answerable_questions']=sum(g['answerability']=='answerable' for g in gold)
 writejl(p/'input/questions.jsonl',questions);writejl(p/'private/gold.jsonl',gold);writejson(p/'input/task_scope_catalog.json',catalog);writejson(p/'validation_report.json',report);writejson(p/'private/object_event_links.json',{v['table']:{eid:sorted(ids) for eid,ids in v['mapping'].items()} for v in views})
 doc='# Object-based event logs\n\n- Each answerable row below has its own English question, Gold specification, SQL and CSV event log.\n- Business objects, event records and association records are labelled separately; a row-level case is useful for coverage but is not necessarily a rich business lifecycle.\n- Case population includes records with no selected events; their event CSV has no row.\n- One event may belong to several different cases, such as multiple goods types or workers. These are valid event-to-case links; the same event is not repeated within one case.\n- Every view uses the exact scope stated below. Related upstream or downstream events are not automatically included through every reachable join.\n- Existing explicit/paraphrase questions are retained. Paired questions may have identical Gold logs.\n- Logs are case-based CSVs, not OCEL files.\n\n| Case table | Case concept | Kind | Question | Cases | Event rows | Gold CSV |\n|---|---|---|---|---:|---:|---|\n'
 for c in coverage:doc+=f"| {c['case_table']} | {c['case_concept']} | {c['kind'].replace('_',' ')} | {c['question_id']} | {c['case_count']} | {c['event_rows']} | [CSV](../{c['log_path']}) |\n"
 doc+='\n## Scope of each view\n\n'+''.join('- **'+c['question_id']+' — '+c['case_concept']+':** '+c['scope_rule']+'\n' for c in coverage)+'\n## Tables without an actual event-log view\n\n'
 doc+=''.join('- **'+x['case_table']+':** '+x['reason']+'\n' for x in unavailable) if unavailable else '- Every keyed table in this database has an actual recorded-event view.\n'
 (p/'docs/object_event_logs.md').write_text(doc);con.close();return dict(dataset=name,added_logs=len(coverage),total_questions=len(questions),answerable_questions=report['answerable_questions'],unavailable=unavailable)
if __name__=='__main__':
 for n in ['warehouseflow','universityflow','plateflow']:print(json.dumps(extend_dataset(ROOT/'datasets'/n)))
