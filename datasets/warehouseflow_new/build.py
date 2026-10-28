"""Synthetic warehouse histories with independent activity identity and timestamp phase."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
from collections import Counter,defaultdict
import json,csv,sqlite3,sys
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
def write(n,s):
 f=P/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(s)
def js(n,x):write(n,json.dumps(x,indent=2)+'\n')
def jl(n,x):write(n,''.join(json.dumps(v)+'\n' for v in x))
def stamp(t):return (datetime(2026,2,1,tzinfo=timezone.utc)+timedelta(minutes=t)).isoformat().replace('+00:00','Z')
DDL='''PRAGMA foreign_keys=ON;
CREATE TABLE warehouse(warehouse_id TEXT PRIMARY KEY NOT NULL, warehouse_name TEXT NOT NULL, capacity INTEGER NOT NULL CHECK(capacity>0), created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE goods(goods_id TEXT PRIMARY KEY NOT NULL, goods_name TEXT NOT NULL, category_code TEXT NOT NULL CHECK(category_code IN ('NORMAL','FRAGILE')));
CREATE TABLE worker(worker_id TEXT PRIMARY KEY NOT NULL, worker_name TEXT NOT NULL, role_code TEXT NOT NULL CHECK(role_code IN ('HANDLER','SUPERVISOR')), updated_at TEXT NOT NULL);
CREATE TABLE work_code(code_family TEXT NOT NULL CHECK(code_family IN ('MOVEMENT','REQUEST','TASK','HANDLING')), code TEXT NOT NULL, meaning TEXT NOT NULL, PRIMARY KEY(code_family,code));
CREATE TABLE receiving_request(request_id TEXT PRIMARY KEY NOT NULL, warehouse_id TEXT NOT NULL REFERENCES warehouse(warehouse_id), goods_id TEXT NOT NULL REFERENCES goods(goods_id), quantity INTEGER NOT NULL CHECK(quantity>0), submitted_at TEXT NOT NULL);
CREATE TABLE goods_receipt(receipt_id TEXT PRIMARY KEY NOT NULL, request_id TEXT NOT NULL UNIQUE REFERENCES receiving_request(request_id), receiver_id TEXT NOT NULL REFERENCES worker(worker_id), received_at TEXT NOT NULL, condition_code TEXT NOT NULL CHECK(condition_code IN ('GOOD','DAMAGED')));
CREATE TABLE dispatch_order(dispatch_id TEXT PRIMARY KEY NOT NULL, warehouse_id TEXT NOT NULL REFERENCES warehouse(warehouse_id), goods_id TEXT NOT NULL REFERENCES goods(goods_id), quantity INTEGER NOT NULL CHECK(quantity>0), priority_code TEXT NOT NULL CHECK(priority_code IN ('NORMAL','URGENT')), requested_at TEXT NOT NULL, approved_at TEXT, CHECK(approved_at IS NULL OR requested_at<approved_at));
CREATE TABLE warehouse_audit(audit_id TEXT PRIMARY KEY NOT NULL, warehouse_id TEXT NOT NULL REFERENCES warehouse(warehouse_id), worker_id TEXT NOT NULL REFERENCES worker(worker_id), started_at TEXT NOT NULL, completed_at TEXT, result_code TEXT NOT NULL CHECK(result_code IN ('PASS','RECOUNT','PENDING')), CHECK((completed_at IS NULL AND result_code='PENDING') OR (completed_at IS NOT NULL AND started_at<completed_at AND result_code IN ('PASS','RECOUNT'))));
CREATE TABLE goods_movement(movement_id TEXT PRIMARY KEY NOT NULL, warehouse_id TEXT NOT NULL REFERENCES warehouse(warehouse_id), goods_id TEXT NOT NULL REFERENCES goods(goods_id), quantity INTEGER NOT NULL CHECK(quantity>0), receipt_id TEXT UNIQUE REFERENCES goods_receipt(receipt_id), dispatch_id TEXT UNIQUE REFERENCES dispatch_order(dispatch_id), code_family TEXT NOT NULL DEFAULT 'MOVEMENT' CHECK(code_family='MOVEMENT'), movement_code TEXT NOT NULL, occurred_at TEXT NOT NULL, FOREIGN KEY(code_family,movement_code) REFERENCES work_code(code_family,code), CHECK((movement_code='IN' AND receipt_id IS NOT NULL AND dispatch_id IS NULL) OR (movement_code='OUT' AND receipt_id IS NULL AND dispatch_id IS NOT NULL)));
CREATE TABLE request_action(action_id TEXT PRIMARY KEY NOT NULL, request_id TEXT NOT NULL REFERENCES receiving_request(request_id), worker_id TEXT NOT NULL REFERENCES worker(worker_id), code_family TEXT NOT NULL DEFAULT 'REQUEST' CHECK(code_family='REQUEST'), action_code TEXT NOT NULL, occurred_at TEXT NOT NULL, FOREIGN KEY(code_family,action_code) REFERENCES work_code(code_family,code));
CREATE TABLE warehouse_task_history(task_id TEXT PRIMARY KEY NOT NULL, request_id TEXT REFERENCES receiving_request(request_id), dispatch_id TEXT REFERENCES dispatch_order(dispatch_id), worker_id TEXT NOT NULL REFERENCES worker(worker_id), code_family TEXT NOT NULL DEFAULT 'TASK' CHECK(code_family='TASK'), task_code TEXT NOT NULL, started_at TEXT NOT NULL, completed_at TEXT, outcome_code TEXT NOT NULL CHECK(outcome_code IN ('OK','RETRY','PENDING')), FOREIGN KEY(code_family,task_code) REFERENCES work_code(code_family,code), CHECK((task_code='PUTAWAY' AND request_id IS NOT NULL AND dispatch_id IS NULL) OR (task_code IN ('PICK','PACK') AND dispatch_id IS NOT NULL AND request_id IS NULL)), CHECK((completed_at IS NULL AND outcome_code='PENDING') OR (completed_at IS NOT NULL AND started_at<completed_at AND outcome_code IN ('OK','RETRY'))));
CREATE TABLE handling_history(handling_id TEXT PRIMARY KEY NOT NULL, request_id TEXT REFERENCES receiving_request(request_id), dispatch_id TEXT REFERENCES dispatch_order(dispatch_id), worker_id TEXT NOT NULL REFERENCES worker(worker_id), code_family TEXT NOT NULL DEFAULT 'HANDLING' CHECK(code_family='HANDLING'), handling_code TEXT NOT NULL, started_at TEXT NOT NULL, completed_at TEXT, FOREIGN KEY(code_family,handling_code) REFERENCES work_code(code_family,code), CHECK((handling_code='UNLOAD' AND request_id IS NOT NULL AND dispatch_id IS NULL) OR (handling_code='LOAD' AND dispatch_id IS NOT NULL AND request_id IS NULL)), CHECK(completed_at IS NULL OR started_at<completed_at));
CREATE TRIGGER movement_context BEFORE INSERT ON goods_movement WHEN (NEW.receipt_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM goods_receipt r JOIN receiving_request q ON q.request_id=r.request_id WHERE r.receipt_id=NEW.receipt_id AND q.warehouse_id=NEW.warehouse_id AND q.goods_id=NEW.goods_id)) OR (NEW.dispatch_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM dispatch_order d WHERE d.dispatch_id=NEW.dispatch_id AND d.warehouse_id=NEW.warehouse_id AND d.goods_id=NEW.goods_id)) BEGIN SELECT RAISE(ABORT,'Movement context conflicts with its business reference'); END;
'''
TABLES={
 'warehouse':'Warehouse identity, capacity and database maintenance times. These maintenance times do not document warehouse work.',
 'goods':'Goods identity and product category; NORMAL/FRAGILE describe the goods.',
 'worker':'Worker identity and job role. role_code identifies a role, not an action performed.',
 'work_code':'Business meanings of codes within the specified code family.',
 'receiving_request':'One submitted request for receipt of one goods type into a warehouse.',
 'goods_receipt':'One actual receipt registration for a receiving request. condition_code describes goods condition, not the receipt action kind.',
 'dispatch_order':'One request to dispatch one goods type, with separate actual request and approval times. Priority describes urgency.',
 'warehouse_audit':'One stock-audit occurrence, its actual start and completion, and its outcome. PASS/RECOUNT describes the result of the same audit kind.',
 'goods_movement':'One completed inbound or outbound stock movement; each row records when the movement actually occurred.',
 'request_action':'One checking, holding or releasing action performed on a receiving request; repeated checking actions retain separate records.',
 'warehouse_task_history':'One putaway, picking or packing work occurrence, with actual start and optional completion. A repeated attempt has a new task_id.',
 'handling_history':'One unloading or loading occurrence, with actual start and optional completion. A repeated attempt has a new handling_id.'}
DEFS={
 'warehouse_id':'Unique warehouse identity; foreign references identify the warehouse concerned.', 'warehouse_name':'English warehouse name.', 'capacity':'Maximum stored stock units for the simulated warehouse.',
 'created_at':'UTC database record-creation time, not a warehouse business action.', 'updated_at':'UTC database maintenance time, not a warehouse business action.',
 'goods_id':'Unique goods identity; foreign references identify the goods concerned.', 'goods_name':'English goods name.', 'category_code':'NORMAL or FRAGILE product category, not an action.',
 'worker_id':'Unique worker identity; on a work or audit record, identifies the worker performing it.', 'worker_name':'English worker name.', 'role_code':'HANDLER or SUPERVISOR worker role, not the action performed.',
 'code_family':'Business context for the code. Each work table has one fixed family enforced by CHECK.', 'code':'Business code within the stated family.', 'meaning':'English business meaning of the code in its family.',
 'request_id':'Unique receiving-request identity; foreign references identify the same request.', 'quantity':'Positive number of goods units requested or moved.', 'submitted_at':'Actual UTC receiving-request submission time.',
 'receipt_id':'Unique receipt-registration identity; on a stock movement, references its receipt registration.', 'receiver_id':'Worker who registered the actual receipt.', 'received_at':'Actual UTC receipt-registration time.', 'condition_code':'GOOD or DAMAGED condition observed when goods were received. Either value denotes the same kind of receipt registration.',
 'dispatch_id':'Unique dispatch-order identity; foreign references identify the same dispatch request.', 'priority_code':'NORMAL or URGENT dispatch urgency; does not identify the action performed.', 'requested_at':'Actual UTC dispatch-request submission time.', 'approved_at':'Actual UTC dispatch-approval time; NULL if not yet approved.',
 'audit_id':'Unique stock-audit occurrence identifier.', 'started_at':'Actual UTC start time of this audit or work occurrence.', 'completed_at':'Actual UTC completion time of this audit or work occurrence; NULL if unfinished.', 'result_code':'PASS or RECOUNT outcome of a completed stock audit, or PENDING for an unfinished audit.',
 'movement_id':'Unique stock-movement occurrence identifier.', 'movement_code':'IN means actual receipt into warehouse stock; OUT means actual dispatch from warehouse stock.', 'occurred_at':'Actual UTC time of this completed stock movement or request action.',
 'action_id':'Unique receiving-request action occurrence identifier.', 'action_code':'CHECK, HOLD or RELEASE action actually performed on the referenced request, as defined in work_code.',
 'task_id':'Unique task-attempt identifier; repeat work has a new identifier.', 'task_code':'PUTAWAY, PICK or PACK work actually performed, as defined in work_code.', 'outcome_code':'OK or RETRY result of a completed task attempt, or PENDING while unfinished; the outcome does not change the kind of work.',
 'handling_id':'Unique handling-attempt identifier.', 'handling_code':'UNLOAD or LOAD work actually performed, as defined in work_code.'}
CODES=[('MOVEMENT','IN','Receipt into warehouse stock','Goods Received'),('MOVEMENT','OUT','Dispatch from warehouse stock','Goods Dispatched'),('REQUEST','CHECK','Check receiving request','Request Checked'),('REQUEST','HOLD','Hold receiving request','Request Held'),('REQUEST','RELEASE','Release receiving request','Request Released'),('TASK','PUTAWAY','Putaway work','Putaway'),('TASK','PICK','Picking work','Picking'),('TASK','PACK','Packing work','Packing'),('HANDLING','UNLOAD','Unloading work','Unloading'),('HANDLING','LOAD','Loading work','Loading')]
# Author reference answers only; never exported into the business dictionary.
CLASSIFICATION={**{t:('A','Column',None,'one point') for t in ['receiving_request','goods_receipt']},**{t:('B','Column',None,'separate milestones' if t=='dispatch_order' else 'start + complete') for t in ['dispatch_order','warehouse_audit']},'goods_movement':('C','Row','movement_code','one completion'),'request_action':('C','Row','action_code','one completion'),'warehouse_task_history':('D','Row','task_code','start + complete'),'handling_history':('D','Row','handling_code','start + complete'),**{t:('Context','No direct business events',None,'technical or absent') for t in ['warehouse','goods','worker','work_code']}}
VIEWS={'Warehouse':('warehouse','warehouse_id','W:'),'Goods':('goods','goods_id','G:'),'Worker':('worker','worker_id','L:'),'Receiving Request':('receiving_request','request_id','Q:'),'Receipt':('goods_receipt','receipt_id','R:'),'Dispatch Order':('dispatch_order','dispatch_id','D:'),'Stock Audit':('warehouse_audit','audit_id','A:'),'Stock Movement':('goods_movement','movement_id','M:'),'Request Action':('request_action','action_id','C:'),'Warehouse Task':('warehouse_task_history','task_id','T:'),'Handling Record':('handling_history','handling_id','H:')}

def main():
 for n in ['input','private/gold_logs','private/gold_sql','docs','design','source']:(P/n).mkdir(parents=True,exist_ok=True)
 db=P/'input/database.sqlite';db.unlink(missing_ok=True);con=sqlite3.connect(db);con.row_factory=sqlite3.Row;con.executescript(DDL);write('input/schema.sql',DDL)
 def ins(t,**r):con.execute('INSERT INTO '+t+'('+','.join(r)+') VALUES ('+','.join('?' for _ in r)+')',list(r.values()))
 for i in range(1,5):ins('warehouse',warehouse_id=str(i),warehouse_name='Warehouse '+str(i),capacity=1000,created_at=stamp(-1000),updated_at=stamp(200000))
 for i in range(1,8):ins('goods',goods_id=str(i),goods_name='Goods '+str(i),category_code='NORMAL' if i%2 else 'FRAGILE');ins('worker',worker_id=str(i),worker_name='Worker '+str(i),role_code='SUPERVISOR' if i%3==0 else 'HANDLER',updated_at=stamp(200000+i))
 for fam,code,meaning,_ in CODES:ins('work_code',code_family=fam,code=code,meaning=meaning)
 hist=[];links=[];counter=Counter();req={};dispatch={};stock=Counter()
 def emit(eid,base,phase,t,table,key,own,related,occurrence=None,label=None):
  hist.append(dict(event_id=eid,activity=label or base,base_activity=base,lifecycle_phase=phase,occurrence_id=occurrence or table+':'+key,timestamp=stamp(t),source_table=table,source_key=key))
  for v,cid in sorted(set(related+[own])):links.append(dict(event_id=eid,case_concept=v,case_id=cid,attribution='own' if (v,cid)==own else 'business-key path'))
 def context(qid=None,did=None):
  data=req[qid] if qid else dispatch[did];v='Receiving Request' if qid else 'Dispatch Order';return [('Warehouse','W:'+data['warehouse_id']),('Goods','G:'+data['goods_id']),(v,('Q:' if qid else 'D:')+(qid or did))]
 def phased(table,keyname,view,prefix,codefield,code,base,t0,t1,worker,qid=None,did=None,outcome='OK'):
  counter[table]+=1;key=str(counter[table]).zfill(4);row={keyname:key,'request_id':qid,'dispatch_id':did,'worker_id':worker,'code_family':'TASK' if table=='warehouse_task_history' else 'HANDLING',codefield:code,'started_at':stamp(t0),'completed_at':None if t1 is None else stamp(t1)}
  if table=='warehouse_task_history':row['outcome_code']='PENDING' if t1 is None else outcome
  ins(table,**row);own=(view,prefix+key);related=context(qid,did)+[('Worker','L:'+worker)];occ=table+':'+key
  emit(prefix+key+':start',base,'start',t0,table,key,own,related,occ,base+' Started')
  if t1 is not None:emit(prefix+key+':complete',base,'complete',t1,table,key,own,related,occ,base+' Completed')
 for i in range(1,27):
  q=str(i).zfill(3);w=str(1+(i-1)%3);g=str(1+(i-1)%6);worker=str(1+(i-1)%6);b=i*300;req[q]=dict(warehouse_id=w,goods_id=g,quantity=10)
  ins('receiving_request',request_id=q,warehouse_id=w,goods_id=g,quantity=10,submitted_at=stamp(b));related=[('Warehouse','W:'+w),('Goods','G:'+g)];emit('Q:'+q,'Receiving Request Submitted','point',b,'receiving_request',q,('Receiving Request','Q:'+q),related)
  if i>=25:continue
  actions=[('CHECK',b+5)]+([('HOLD',b+8),('CHECK',b+10)] if i%5==0 else [])+[('RELEASE',b+12)]
  for code,t in actions:
   counter['action']+=1;a=str(counter['action']).zfill(4);ins('request_action',action_id=a,request_id=q,worker_id=worker,code_family='REQUEST',action_code=code,occurred_at=stamp(t));base=next(a for f,c,_,a in CODES if f=='REQUEST' and c==code);emit('C:'+a,base,'complete',t,'request_action',a,('Request Action','C:'+a),context(qid=q)+[('Worker','L:'+worker)])
  phased('handling_history','handling_id','Handling Record','H:','handling_code','UNLOAD','Unloading',b+20,None if i==24 else b+30,worker,qid=q)
  if i==24:continue
  r=q;ins('goods_receipt',receipt_id=r,request_id=q,receiver_id=worker,received_at=stamp(b+32),condition_code='DAMAGED' if i%7==0 else 'GOOD');emit('R:'+r,'Receipt Registered','point',b+32,'goods_receipt',r,('Receipt','R:'+r),context(qid=q)+[('Worker','L:'+worker)])
  counter['movement']+=1;m=str(counter['movement']).zfill(4);ins('goods_movement',movement_id=m,warehouse_id=w,goods_id=g,quantity=10,receipt_id=r,dispatch_id=None,code_family='MOVEMENT',movement_code='IN',occurred_at=stamp(b+35));emit('M:'+m,'Goods Received','complete',b+35,'goods_movement',m,('Stock Movement','M:'+m),context(qid=q)+[('Receipt','R:'+r)]);stock[w,g]+=10
  phased('warehouse_task_history','task_id','Warehouse Task','T:','task_code','PUTAWAY','Putaway',b+40,None if i in [21,23] else b+50,worker,qid=q)
 for i in range(1,21):
  did=str(i).zfill(3);w=str(1+(i-1)%3);g=str(1+(i-1)%6);worker=str(1+i%6);b=100000+i*300;dispatch[did]=dict(warehouse_id=w,goods_id=g,quantity=4);approved=None if i>=19 else b+10
  ins('dispatch_order',dispatch_id=did,warehouse_id=w,goods_id=g,quantity=4,priority_code='URGENT' if i%3==0 else 'NORMAL',requested_at=stamp(b),approved_at=None if approved is None else stamp(approved));related=[('Warehouse','W:'+w),('Goods','G:'+g)];own=('Dispatch Order','D:'+did)
  emit('D:'+did+':requested','Dispatch Requested','point',b,'dispatch_order',did,own,related,occurrence='dispatch_order:'+did+':requested')
  if approved is None:continue
  emit('D:'+did+':approved','Dispatch Approved','point',approved,'dispatch_order',did,own,related,occurrence='dispatch_order:'+did+':approved')
  phased('warehouse_task_history','task_id','Warehouse Task','T:','task_code','PICK','Picking',b+20,b+30,worker,did=did,outcome='RETRY' if i%4==0 else 'OK')
  if i%4==0:phased('warehouse_task_history','task_id','Warehouse Task','T:','task_code','PICK','Picking',b+31,b+33,worker,did=did)
  phased('warehouse_task_history','task_id','Warehouse Task','T:','task_code','PACK','Packing',b+35,None if i==18 else b+45,worker,did=did)
  if i==18:continue
  phased('handling_history','handling_id','Handling Record','H:','handling_code','LOAD','Loading',b+50,None if i==17 else b+60,worker,did=did)
  if i==17:continue
  counter['movement']+=1;m=str(counter['movement']).zfill(4);ins('goods_movement',movement_id=m,warehouse_id=w,goods_id=g,quantity=4,receipt_id=None,dispatch_id=did,code_family='MOVEMENT',movement_code='OUT',occurred_at=stamp(b+65));emit('M:'+m,'Goods Dispatched','complete',b+65,'goods_movement',m,('Stock Movement','M:'+m),context(did=did));stock[w,g]-=4;assert stock[w,g]>=0
 for i in range(1,10):
  a=str(i).zfill(3);w=str(1+(i-1)%3);worker=str(1+(i-1)%6);b=150000+i*100;end=None if i==9 else b+40
  ins('warehouse_audit',audit_id=a,warehouse_id=w,worker_id=worker,started_at=stamp(b),completed_at=None if end is None else stamp(end),result_code='PENDING' if end is None else 'RECOUNT' if i%3==0 else 'PASS');related=[('Warehouse','W:'+w),('Worker','L:'+worker)];own=('Stock Audit','A:'+a)
  emit('A:'+a+':start','Stock Audit','start',b,'warehouse_audit',a,own,related,label='Stock Audit Started')
  if end is not None:emit('A:'+a+':complete','Stock Audit','complete',end,'warehouse_audit',a,own,related,label='Stock Audit Completed')
 con.commit();assert not list(con.execute('PRAGMA foreign_key_check'));assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 jl('private/canonical_history.jsonl',hist);js('private/object_event_links.json',links)
 sources=[]
 def source(t,base,phase,col,prefix,pk,where='1=1',filtercol=None,filtervalue=None,label=None,suffix='',occ_suffix=''):
  eid="'"+prefix+"'||"+pk+("||'"+suffix+"'" if suffix else '');activity=label or base
  sql=f"SELECT {eid} event_id,'{activity}' activity,{col} timestamp,{pk} source_key FROM {t} WHERE {col} IS NOT NULL AND ({where})"
  sources.append(dict(table=t,primary_key=pk,base_activity=base,lifecycle_phase=phase,timestamp_column=col,activity=activity,occurrence_prefix=t+':',occurrence_suffix=occ_suffix,row_filter=None if filtercol is None else dict(column=filtercol,value=filtervalue),event_sql=sql))
 source('receiving_request','Receiving Request Submitted','point','submitted_at','Q:','request_id')
 source('goods_receipt','Receipt Registered','point','received_at','R:','receipt_id')
 for col,label,suffix in [('requested_at','Dispatch Requested',':requested'),('approved_at','Dispatch Approved',':approved')]:source('dispatch_order',label,'point',col,'D:','dispatch_id',suffix=suffix,occ_suffix=suffix)
 for phase,col,label,suffix in [('start','started_at','Stock Audit Started',':start'),('complete','completed_at','Stock Audit Completed',':complete')]:source('warehouse_audit','Stock Audit',phase,col,'A:','audit_id',label=label,suffix=suffix)
 for fam,code,_,base in CODES:
  if fam in ['MOVEMENT','REQUEST']:
   t,key,c,prefix=('goods_movement','movement_id','movement_code','M:') if fam=='MOVEMENT' else ('request_action','action_id','action_code','C:');source(t,base,'complete','occurred_at',prefix,key,c+"='"+code+"'",c,code)
  else:
   t,key,c,prefix=('warehouse_task_history','task_id','task_code','T:') if fam=='TASK' else ('handling_history','handling_id','handling_code','H:')
   for phase,col,suffix in [('start','started_at',':start'),('complete','completed_at',':complete')]:source(t,base,phase,col,prefix,key,c+"='"+code+"'",c,code,label=base+(' Started' if phase=='start' else ' Completed'),suffix=suffix)
 js('private/persistence_mapping.json',sources)
 # Key-based case routes keep phase occurrence IDs; no precomputed event/case table enters the DB.
 paths={v:{} for v in VIEWS}
 def path(v,t,key,joins=''):paths[v][t]=dict(case_key=key,joins=joins)
 for v,(t,key,_) in VIEWS.items():path(v,t,'s.'+key)
 for t in ['receiving_request','dispatch_order','goods_movement']:
  path('Warehouse',t,'s.warehouse_id');path('Goods',t,'s.goods_id')
 path('Receiving Request','goods_receipt','s.request_id');path('Worker','goods_receipt','s.receiver_id')
 for v,key in [('Warehouse','q.warehouse_id'),('Goods','q.goods_id')]:path(v,'goods_receipt',key,' JOIN receiving_request q ON q.request_id=s.request_id')
 for v,key in [('Warehouse','s.warehouse_id'),('Worker','s.worker_id')]:path(v,'warehouse_audit',key)
 for v,key in [('Warehouse','q.warehouse_id'),('Goods','q.goods_id')]:path(v,'request_action',key,' JOIN receiving_request q ON q.request_id=s.request_id')
 path('Receiving Request','request_action','s.request_id');path('Worker','request_action','s.worker_id')
 # An order/request branch is selected from declared FK columns; the parent types are distinct.
 optional=' LEFT JOIN receiving_request q ON q.request_id=s.request_id LEFT JOIN dispatch_order d ON d.dispatch_id=s.dispatch_id'
 for t in ['warehouse_task_history','handling_history']:
  path('Warehouse',t,'COALESCE(q.warehouse_id,d.warehouse_id)',optional);path('Goods',t,'COALESCE(q.goods_id,d.goods_id)',optional);path('Receiving Request',t,'s.request_id');path('Dispatch Order',t,'s.dispatch_id');path('Worker',t,'s.worker_id')
 path('Receipt','goods_movement','s.receipt_id');path('Dispatch Order','goods_movement','s.dispatch_id');path('Receiving Request','goods_movement','r.request_id',' JOIN goods_receipt r ON r.receipt_id=s.receipt_id')
 js('private/case_paths.json',paths);linked=defaultdict(set)
 for r in links:linked[r['event_id']].add((r['case_concept'],r['case_id']))
 populations={};coverage=[]
 for v,(t,key,prefix) in VIEWS.items():
  pops=[prefix+r[0] for r in con.execute('SELECT '+key+' FROM '+t+' ORDER BY '+key)];populations[v]=pops;counts=Counter(cid for e in hist for vv,cid in linked[e['event_id']] if vv==v);acts=sorted({e['activity'] for e in hist if any(vv==v for vv,_ in linked[e['event_id']])});coverage.append(dict(case_concept=v,case_table=t,case_count=len(pops),activity_count=len(acts),base_activity_count=len({e['base_activity'] for e in hist if any(vv==v for vv,_ in linked[e['event_id']])}),activities=acts,event_rows=sum(counts.values()),cases_without_events=len(set(pops)-set(counts))))
 js('private/case_population.json',populations);js('private/task_scope_catalog.json',dict(views=coverage))
 def compile_es(v,acts):
  pieces=[];bindings=[];prefix=VIEWS[v][2]
  for src in sources:
   t=src['table'];route=paths[v].get(t)
   if not route or src['activity'] not in acts:continue
   pieces.append("SELECT e.event_id,'"+prefix+"'||"+route['case_key']+" case_id,e.activity,e.timestamp FROM ("+src['event_sql']+") e JOIN "+t+' s ON s.'+src['primary_key']+'=e.source_key'+route['joins']+' WHERE '+route['case_key']+' IS NOT NULL');bindings.append(dict(source_table=t,primary_key=src['primary_key'],base_activity=src['base_activity'],lifecycle_phase=src['lifecycle_phase'],occurrence_identity=dict(source_table=t,key_columns=[src['primary_key']],discriminator=src['occurrence_suffix']),timestamp_column=src['timestamp_column'],row_filter=src['row_filter'],case_path=route))
  assert pieces,v
  return 'SELECT * FROM ('+' UNION ALL '.join(pieces)+') ORDER BY case_id,timestamp,event_id;',bindings
 seeds=json.loads((P/'source/question_seeds.json').read_text());par=json.loads((P/'source/llm_paraphrases.json').read_text());questions=[];gold=[]
 for seed in seeds:
  v=seed['view'];qid=seed['id'];full='activities' not in seed;acts=next(c['activities'] for c in coverage if c['case_concept']==v) if full else seed['activities'];answerable=seed.get('answerable',True)
  if answerable:
   sql,bindings=compile_es(v,acts);es=dict(version='warehouse-new-es-1',case_concept=v,activities=acts,case_population=populations[v],event_bindings=bindings,compiled_sql=sql)
   expected=sorted([dict(event_id=e['event_id'],case_id=cid,activity=e['activity'],timestamp=e['timestamp']) for e in hist if e['activity'] in acts for vv,cid in linked[e['event_id']] if vv==v],key=lambda e:(e['case_id'],e['timestamp'],e['event_id']));actual=[dict(r) for r in con.execute(sql)];assert actual==expected,qid;assert len({(r['case_id'],r['event_id']) for r in actual})==len(actual)
  else:es=None
  for ident,text,typ,pair in [(qid,seed['question'],'Q3' if full else 'Q1',qid+'P'),(qid+'P',par['outputs'][qid],'Q4' if full else 'Q2',qid)]:
   base_types={s['base_activity'] for s in sources if s['activity'] in acts} if answerable else set(acts)
   q=dict(question_id=ident,text=text,question_type=typ,question_type_name={'Q1':'Explicit','Q2':'Paraphrased','Q3':'Full Lifecycle','Q4':'Full Lifecycle Paraphrased'}[typ],pair_of=pair,pair_group_id=qid,answerability='answerable' if answerable else 'non_answerable',case_concept=v,included_information='Process View: case concept only' if full else 'Process View: case concept and explicit activity scope',requested_activity_count=len(acts),extractable_activity_count=len(acts) if answerable else 0,activity_scope_explicit=not full,requested_base_activity_count=len(base_types),extractable_base_activity_count=len(base_types) if answerable else 0);questions.append(q);g=dict(**q,process_view=dict(case_concept=v,case_table=VIEWS[v][0],activities=acts),es=es)
   if answerable:
    csvpath='private/gold_logs/'+ident+'.csv';sqlpath='private/gold_sql/'+ident+'.sql'
    with (P/csvpath).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=['event_id','case_id','activity','timestamp']);w.writeheader();w.writerows(expected)
    write(sqlpath,sql+'\n');g.update(csv=csvpath,sql=sqlpath,event_count=len(expected))
   else:g['reason']='No corresponding invoicing or carrier delivery records exist in this DB.'
   gold.append(g)
 jl('input/model_questions.jsonl',[dict(question_id=q['question_id'],text=q['text']) for q in questions]);jl('private/questions.jsonl',questions);jl('private/gold.jsonl',gold)
 metadata=[]
 for t in TABLES:
  info=list(con.execute('PRAGMA table_info('+t+')'));fks=list(con.execute('PRAGMA foreign_key_list('+t+')'));cols=[]
  for r in info:cols.append(dict(name=r['name'],sql_type=r['type'],definition=DEFS[r['name']],required=bool(r['notnull'] or r['pk']),primary_key_position=r['pk'],default=r['dflt_value'],foreign_keys=[dict(table=f['table'],column=f['to'],constraint_id=f['id'],position=f['seq']) for f in fks if f['from']==r['name']],unit='UTC' if r['name'].endswith('_at') else 'stock units' if r['name'] in ['quantity','capacity'] else None))
  metadata.append(dict(table=t,definition=TABLES[t],columns=cols,primary_key=[r['name'] for r in sorted(info,key=lambda r:r['pk']) if r['pk']],sql_definition=con.execute('SELECT sql FROM sqlite_master WHERE name=?',(t,)).fetchone()[0]))
 d=dict(name='WarehouseFlow New',language='en',timezone='UTC',dbms='SQLite',description='Synthetic warehouse receiving, dispatch, stock-audit and handling records.',tables=metadata,code_values=[dict(code_family=f,code=c,meaning=m) for f,c,m,_ in CODES],business_rules=['Each receiving request and dispatch order concerns one goods type in one warehouse; quantities are positive. This sample does not model multi-line orders.','One actual receipt registration can exist for each receiving request. Actual stock posting is recorded separately.','Each movement refers either to an inbound receipt or an outbound dispatch, with the same warehouse and goods context.','Every work attempt and audit retains its own start and optional completion times. Unfinished work has no completion time.','Repeated task attempts and request checks retain separate occurrence identifiers.','Goods category, dispatch urgency, goods condition, worker role, audit result and task outcome describe their respective business contexts rather than different kinds of action.','A handling/task occurrence refers either to a receiving request or to a dispatch order as constrained by its work kind.','All rows, code conventions, times and quantities are synthetic.'])
 js('input/data_dictionary.json',d)
 used={(s['table'],s['timestamp_column']) for s in sources};timestamps=[]
 for t in metadata:
  for c in t['columns']:
   if c['name'].endswith('_at'):timestamps.append(dict(table=t['table'],column=c['name'],role='Selected actual business instant' if (t['table'],c['name']) in used else 'Technical maintenance instant',used_as_event_time=(t['table'],c['name']) in used,non_null_rows=con.execute('SELECT COUNT('+c['name']+') FROM '+t['table']).fetchone()[0]))
 inv=dict(timestamp_columns=len(timestamps),event_timestamp_columns=len(used),other_timestamp_columns=len(timestamps)-len(used),baseline_timestamp_columns=len(timestamps),date_only_columns=[],columns=timestamps);js('docs/timestamp_columns.json',inv)
 report=dict(table_rows={t:con.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in TABLES},semantic_object_types=len(VIEWS),object_view_coverage=coverage,activity_counts=dict(Counter(e['activity'] for e in hist)),base_activity_counts=dict(Counter(e['base_activity'] for e in hist)),activity_type_count=len({e['base_activity'] for e in hist}),activity_display_label_count=len({e['activity'] for e in hist}),phase_counts=dict(Counter(e['lifecycle_phase'] for e in hist)),events=len(hist),total_questions=len(questions),answerable_questions=sum(q['answerability']=='answerable' for q in questions),timestamp_summary={k:v for k,v in inv.items() if k!='columns'},validation_scope='Dataset construction and Gold consistency, not a measured classifier result.');js('validation_report.json',report)
 from documentation import render
 render(P,con,d,report,questions,coverage,CLASSIFICATION)
 con.close();print(json.dumps({k:report[k] for k in ['events','phase_counts','total_questions','answerable_questions','semantic_object_types','timestamp_summary']},indent=2))
if __name__=='__main__':main()
