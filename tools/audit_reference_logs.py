"""Author-only verification from event definitions/paths, independent of stored Gold SQL."""
import csv,json,sqlite3,sys,re,subprocess
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/validation')]
from build_gold_review_pages import bindings
from gold_source_rows import SourceRows
S=__import__('importlib.util',fromlist=['spec_from_file_location']);sp=S.spec_from_file_location('replacement',ROOT/'tools/experiments/replace_atomic_review_requests.py');M=S.module_from_spec(sp);sp.loader.exec_module(M)
FOCUS={'laboratory testing':set(M.ACTS['HF03']),'medication treatment':set(M.ACTS['HF08']),'inbound receiving':set(M.ACTS['WF08']),'outbound fulfillment work':set(M.ACTS['WF09'])}
def key(rows):return Counter(tuple(r[k] for k in ['event_id','case_id','activity','timestamp']) for r in rows)
def read(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
def hospital(db,pm,concept,focus):
 tables={t:{str(r[k]):dict(r) for r in db.execute('SELECT * FROM '+t)} for t,k in [('lab_order','order_id'),('medication_order','order_id'),('procedure_order','order_id'),('admissions','hadm_id'),('emar','emar_id')]};out=[]
 for b in pm:
  for e in db.execute(b['event_sql']):
   e=dict(e);kind,id=e['object_id'].split(':',1);eid=e['event_id'];adm=None;patient=None;case=None
   if kind in ['LAB','MED','PROC']:
    order=tables[{'LAB':'lab_order','MED':'medication_order','PROC':'procedure_order'}[kind]][id];adm=order.get('hadm_id');patient=order.get('subject_id')
   elif kind=='A':adm=id
   if adm is not None:adm=str(adm);patient=tables['admissions'][adm]['subject_id']
   if concept=='Patient' and patient is not None:case='P:'+str(patient)
   elif concept=='Hospital Admission' and adm is not None:case='A:'+adm
   elif concept in ['Laboratory Order','Medication Order','Procedure Order'] and kind=={'Laboratory Order':'LAB','Medication Order':'MED','Procedure Order':'PROC'}[concept]:case=kind+':'+id
   elif concept=='Lab Measurement' and eid.startswith('LABEV:'):case='LM:'+eid.split(':')[1]
   elif concept=='Procedure Episode' and eid.startswith('PROCEV:'):case='EP:'+eid.split(':')[1]
   elif concept=='Pharmacy Dispensing':
    if eid.startswith('PHARM:'):case='PHARM:'+eid.split(':')[1]
    elif eid.startswith('EMAR:'):case='PHARM:'+str(tables['emar'][eid.split(':')[1]]['pharmacy_id'])
   if focus=='laboratory testing' and kind!='LAB':continue
   if focus=='medication treatment' and kind!='MED':continue
   if case is not None:out.append(dict(e,case_id=case))
 return out
def audit(name):
 base=ROOT/'datasets'/name;db=sqlite3.connect(f'file:{base}/input/database.sqlite?mode=ro',uri=True);db.row_factory=sqlite3.Row
 assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert not db.execute('PRAGMA foreign_key_check').fetchall()
 gold=read(base/'private/gold.jsonl');qp=base/('evaluation/questions.jsonl' if name=='hospitalflow' else 'private/questions.jsonl');qs={M.identity(r):r for r in read(qp)};models={M.identity(r):r for r in read(base/'evaluation/model_questions.jsonl')}
 pm=bindings(base);source=SourceRows(base);paths=json.loads((base/'private/case_paths.json').read_text()) if name!='hospitalflow' else None;cache={};records=[]
 for g in gold:
  id=g['question_id'];q=qs[id];pv=g['process_view'];concept=g['es']['case_concept'];focus=pv.get('process_focus');sql=(base/f'private/gold_sql/{id}.sql').read_text();actual=list(csv.DictReader((base/f'private/gold_logs/{id}.csv').open()))
  assert key(actual)==key(db.execute(sql)),(id,'SQL/CSV');assert g['es']['compiled_sql'].strip().rstrip(';')==sql.strip().rstrip(';'),(id,'ES/SQL')
  assert q.get('text',q.get('question'))==models[id].get('text',models[id].get('question')),(id,'question text')
  if g['question_type'] in ['Q1','Q2']:
   seed=q if g['question_type']=='Q1' else qs[g['pair_of']];text=seed.get('text',seed.get('question'));acts={b['activity'] for b in pm if b['activity'] in text};assert acts==set(pv['activities']),(id,'request scope')
  else:acts=FOCUS.get(focus)
  if name=='hospitalflow':expected=hospital(db,pm,concept,focus)
  else:
   if concept not in cache:
    cache[concept]=[];prefix=re.search(r"SELECT e\.event_id,'([^']+)'\|\|",sql).group(1)
    for b in pm:
     path=paths[concept].get(b['table'])
     if path is None:continue
     pk=[r['name'] for r in db.execute('PRAGMA table_info('+b['table']+')') if r['pk']];assert len(pk)==1
     branch=f"SELECT e.event_id,'{prefix}'||{path['case_key']} case_id,e.activity,e.timestamp FROM ({b['event_sql']}) e JOIN {b['table']} s ON s.{pk[0]}=e.source_key{path['joins']} WHERE {path['case_key']} IS NOT NULL"
     cache[concept].extend(dict(r) for r in db.execute(branch))
   expected=cache[concept]
  if acts is not None:expected=[r for r in expected if r['activity'] in acts]
  missing=key(expected)-key(actual);extra=key(actual)-key(expected);assert not missing and not extra,(name,id,'source replay',sum(missing.values()),sum(extra.values()))
  assert len({(r['event_id'],r['case_id']) for r in actual})==len(actual),(id,'duplicate')
  assert all(all(r[k] for k in ['event_id','case_id','activity','timestamp']) for r in actual)
  _,_,unmatched,_=source.inspect(sql,actual);assert unmatched==0,(id,'provenance')
  population=g['es']['case_population'];cases=Counter(r['case_id'] for r in actual);assert not set(cases)-set(population),(id,'population')
  pair=g.get('pair_of')
  if pair:assert key(actual)==key(csv.DictReader((base/f'private/gold_logs/{pair}.csv').open())),(id,'pair')
  single=sum(n==1 for n in cases.values());assert not(g['question_type'] in ['Q3','Q4'] and cases and single==len(cases)),(id,'all singleton lifecycle')
  records.append(dict(id=id,type=g['question_type'],case=concept,focus=focus,events=len(actual),cases_with_events=len(cases),case_population=len(population),empty_cases=len(population)-len(cases),singleton_cases=single,activities=len({r['activity'] for r in actual}),supported_but_unobserved=sorted(set(pv['activities'])-{r['activity'] for r in actual}),missing=0,extra=0,unmatched=0))
 assert len(records)==40;assert Counter(r['type'] for r in records)==Counter(Q1=10,Q2=10,Q3=10,Q4=10)
 source.db.close();db.close();return dict(dataset=name,questions=records)
if __name__=='__main__':
 results=[audit(n) for n in ['hospitalflow','plateflow','warehouseflow']]
 (ROOT/'docs/reference_gold_audit_2026-11-20.json').write_text(json.dumps(results,indent=2)+'\n')
 for r in results:print(r['dataset'],len(r['questions']),'passed; missing=0 extra=0 unmatched=0')
