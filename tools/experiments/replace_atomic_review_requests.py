"""Author-only request replacement; input databases are read-only and never altered."""
import json,csv,sqlite3,copy,sys,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
S=importlib.util.spec_from_file_location('lifecycle',ROOT/'tools/experiments/apply_lifecycle_contract_2026_11.py');L=importlib.util.module_from_spec(S);S.loader.exec_module(L)
def load(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
def save(p,rs):p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rs))
def identity(r):return r.get('question_id',r.get('id'))
CHANGES={
 'hospitalflow':{
 'HF03':('HF02','laboratory testing','Extract the full recorded laboratory-testing lifecycle for each hospital admission.','For every hospital stay, reconstruct the entire recorded history of its laboratory testing.'),
 'HF08':('HF01','medication treatment','Extract the full recorded medication-treatment lifecycle for each patient.','For every patient, reconstruct the complete recorded history of their medication treatment.')},
 'plateflow':{'N12':('N04',None,'For each mother material, extract Furnace Charged, Heating Completed and Furnace Discharged events.','For every mother material, show when furnace charging, heating and furnace discharge finished.')},
 'warehouseflow':{
 'W06':('WF04',None,'For each receiving request, extract Request Checked, Request Held and Request Released events.','For every receiving request, show when it was checked, put on hold and released from hold.'),
 'WF08':('WF02','inbound receiving','Extract the full recorded inbound-receiving lifecycle for each goods type.','For every goods type, reconstruct the complete recorded history of its inbound receiving process.'),
 'WF09':('WF03','outbound fulfillment work','Extract the full recorded outbound-fulfillment work lifecycle for each worker.','For every worker, reconstruct the complete recorded history of their work on outbound fulfillment.')},
 'universityflow':{'OU10':('OU09','assignment assessment','Extract the full recorded grading and regrading history for each instructor.','For every instructor, reconstruct the entire recorded history of their initial assignment assessments and reassessments.')}}
ACTS={
 'HF03':['Order Entered','Order Reviewed','Order Cancelled','Specimen Collected','Specimen Received','Lab Result Available','Lab Results Verified'],
 'HF08':['Order Entered','Order Reviewed','Order Cancelled','Medication Dispensed','Medication Administered','Medication Not Given','Medication Stopped'],
 'N12':['Furnace Charged','Heating Completed','Furnace Discharged'],
 'W06':['Request Checked','Request Held','Request Released'],
 'WF08':['Receiving Request Submitted','Request Checked','Request Held','Request Released','Unloading Started','Unloading Completed','Receipt Registered','Goods Received','Putaway Started','Putaway Completed'],
 'WF09':['Picking Started','Picking Completed','Packing Started','Packing Completed','Loading Started','Loading Completed'],
 'OU10':['Assignment Graded','Assignment Regraded']}
def run():
 for ds,changes in CHANGES.items():
  b=ROOT/'datasets'/ds;gold=load(b/'private/gold.jsonl');by={identity(g):g for g in gold};db=sqlite3.connect(f'file:{b}/input/database.sqlite?mode=ro',uri=True);db.row_factory=sqlite3.Row;fix={};oldtext={}
  for target,(parent,focus,text,para) in changes.items():
   t=copy.deepcopy(by[parent]);acts=ACTS[target]
   if ds=='hospitalflow':
    pref='LAB:' if target=='HF03' else 'MED:';bs=[]
    for x in json.loads((b/'private/persistence_mapping.json').read_text()):
     if x['activity'] in acts:
      x=copy.deepcopy(x);x['event_sql']=f"SELECT * FROM ({x['event_sql']}) WHERE object_id LIKE '{pref}%'";bs.append(x)
    if target=='HF03':orders="SELECT 'LAB:'||order_id object_id,hadm_id,subject_id FROM lab_order";case="'A:'||o.hadm_id";guard='o.hadm_id IS NOT NULL'
    else:orders="SELECT 'MED:'||m.order_id object_id,m.hadm_id,a.subject_id FROM medication_order m JOIN admissions a USING(hadm_id)";case="'P:'||o.subject_id";guard='o.subject_id IS NOT NULL'
    sql='WITH events AS ('+' UNION ALL '.join(x['event_sql'] for x in bs)+'), orders AS ('+orders+') SELECT e.event_id,'+case+' case_id,e.activity,e.timestamp FROM events e JOIN orders o ON o.object_id=e.object_id WHERE '+guard+' ORDER BY case_id,timestamp,event_id;';t['es']['activity_sources']=bs
   elif ds in ('warehouseflow','plateflow'):
    d=L.Dataset(ds);sql=d.build(t,acts);bs=[]
    for a in acts:
     x=d.binding(a);m=[y for y in t['es']['event_bindings'] if y['source_table']==x['table'] and y['timestamp_column']==x['timestamp_column'] and y.get('row_filter')==x.get('row_filter')];assert len(m)==1;bs+=m
    t['es']['event_bindings']=bs;d.con.close()
   else:
    sql="SELECT CASE WHEN grading_kind='R' THEN reassessment_event_id ELSE 'GRADE:'||assignment_id||':'||instructor_id||':'||grading_time END event_id,instructor_id case_id,CASE WHEN grading_kind='R' THEN 'Assignment Regraded' ELSE 'Assignment Graded' END activity,grading_time timestamp FROM assignment_grading WHERE grading_time IS NOT NULL AND grading_kind IN ('A','R') ORDER BY case_id,timestamp,event_id;"
    t['es']={'version':'focused-grading-history-1','case_population_query':'SELECT instructor_id case_id FROM instructor','source_table':'assignment_grading','case_column':'instructor_id','timestamp_column':'grading_time','row_filter':{'grading_kind':['A','R']}}
   rows=[dict(r) for r in db.execute(sql)];concept=t['process_view']['case_concept']
   for id,txt in [(target,text),(target+'P',para)]:
    g=by[id];oldtext[id]=g.get('text',g.get('question'));fix[id]=txt
    g['es']=copy.deepcopy(t['es']);g['es'].update(compiled_sql=sql,case_concept=concept,activities=sorted(acts))
    g['process_view']=copy.deepcopy(t['process_view']);g['process_view']['activities']=sorted(acts)
    if focus:g['process_view'].update(process_focus=focus,scope_rule='All recorded occurrences within the named process focus attributable to the selected case; retain repeats and incomplete cases.')
    for key in ['text','question']:
     if key in g:g[key]=txt
    g.update(case_concept=concept,event_count=len(rows),requested_activity_count=len(acts),extractable_activity_count=len(acts))
    if 'case_count' in g:g['case_count']=len({r['case_id'] for r in rows})
    if 'requested_activities' in g:g['requested_activities']=acts if g['question_type'] in ['Q1','Q2'] else []
    for k in ['requested_base_activity_count','extractable_base_activity_count']:
     if k in g:g[k]=len({x.get('base_activity',x.get('activity')) for x in g['es'].get('event_bindings',[])})
    g['csv']=f'private/gold_logs/{id}.csv';g['sql']=f'private/gold_sql/{id}.sql';g['author_revision']={'date':'2026-11-20','reason':'Replace atomic-record case with business case; focus stated explicitly.'}
    (b/f'private/gold_sql/{id}.sql').write_text(sql+'\n')
    with (b/f'private/gold_logs/{id}.csv').open('w',newline='') as f:
     w=csv.DictWriter(f,fieldnames=['event_id','case_id','activity','timestamp']);w.writeheader();w.writerows(rows)
   print(ds,target,len(rows),'events',len({r['case_id'] for r in rows}),'cases',flush=True)
  save(b/'private/gold.jsonl',gold)
  for rel in ['private/questions.jsonl','evaluation/questions.jsonl','evaluation/model_questions.jsonl']:
   p=b/rel
   if not p.exists():continue
   rs=load(p)
   for r in rs:
    id=identity(r)
    if id not in fix:continue
    for key in ['text','question']:
     if key in r:r[key]=fix[id]
    if not rel.endswith('model_questions.jsonl'):
     for key in ['case_concept','requested_activity_count','extractable_activity_count','requested_base_activity_count','extractable_base_activity_count']:
      if key in r or key=='case_concept':r[key]=by[id][key]
   save(p,rs)
  p=b/'source/question_seeds.json'
  if p.exists():
   rs=json.loads(p.read_text())
   for r in rs:
    id=identity(r)
    if id in fix:r.update(question=fix[id],case_concept=by[id]['case_concept'],activities=by[id]['process_view']['activities'],post_generation_edit='Author revised following 2026-11-20 audit.')
   p.write_text(json.dumps(rs,indent=2)+'\n')
  p=b/'source/llm_paraphrases.json'
  if p.exists():
   o=json.loads(p.read_text())
   for id in changes:
    if id in o.get('outputs',{}):o['outputs'][id]=fix[id+'P']
   o['post_generation_edit']='Affected paraphrases author-revised 2026-11-20; not a new original-LLM run.';p.write_text(json.dumps(o,indent=2)+'\n')
  for p in b.glob('**/*.md'):
   s=p.read_text();new=s
   for id,old in oldtext.items():
    if old:new=new.replace(old,fix[id])
   if s!=new:p.write_text(new)
  db.close()
if __name__=='__main__':run()
