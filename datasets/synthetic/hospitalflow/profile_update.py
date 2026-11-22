"""Migrate reviewed business metadata alongside the authored schema (not event answers)."""
import json,copy,re

def update_profile(p,con,roles,descs):
 d=json.loads((p/'source/dictionary_profile.json').read_text())
 old={t['table']:t for t in d['tables']}
 old.setdefault('procedure_episode',copy.deepcopy(old.get('procedureevents',{})))
 templates={c['name']:c for t in d['tables'] for c in t['columns']}
 def split_fields(ddl):
  body=ddl[ddl.index('(')+1:ddl.rindex(')')];depth=0;quoted=False;parts=[];start=0
  for i,ch in enumerate(body):
   if ch=="'":quoted=not quoted
   if not quoted:
    if ch=='(':depth+=1
    elif ch==')':depth-=1
    elif ch==',' and depth==0:parts.append(body[start:i].strip());start=i+1
  return parts+[body[start:].strip()]
 tables=[]
 for name,role in roles.items():
  t=copy.deepcopy(old.get(name,old['medication_order']))
  t.update(table=name,metadata_id='hospitalflow.'+name,readable_name=name.replace('_',' ').capitalize(),definition=role)
  t['row_grain']={'pharmacy':'One dispensing record for one medication prescription; a prescription may have zero or multiple dispensing records.', 'emar':'One administration or omission record referring to one pharmacy dispensing record.', 'lab_order':'One authored laboratory request for one patient, optionally associated with an admission.', 'medication_order':'One medication prescription; dispensing records and dose records have their own identities.', 'procedure_episode':'One hospital-level procedure execution episode, not an ICU stay.'}.get(name,t['row_grain'])
  if name=='pharmacy':t['logical_relationships']=[]
  ddl=con.execute("SELECT sql FROM sqlite_master WHERE name=?",(name,)).fetchone()[0]
  parts=split_fields(ddl);definitions={x.split()[0]:x for x in parts if not x.startswith('CHECK')}
  t['sql_definition']=ddl;t['table_checks']=[x for x in parts if x.startswith('CHECK')]
  info=list(con.execute('PRAGMA table_info('+name+')'));fks=list(con.execute('PRAGMA foreign_key_list('+name+')'))
  t['primary_key']=[r['name'] for r in info if r['pk']]
  t['foreign_keys']=[dict(column=r['from'],parent_table=r['table'],parent_column=r['to']) for r in fks]
  prev={c['name']:c for c in t['columns']};cols=[]
  for r in info:
   n=r['name'];c=copy.deepcopy(prev.get(n,templates.get(n,templates['order_id'])))
   c.update(metadata_id='hospitalflow.'+name+'.'+n,name=n,type=r['type'],nullable=not bool(r['notnull']),required=bool(r['notnull']),primary_key_position=r['pk'],unique=bool(r['pk']),default_value=r['dflt_value'],foreign_keys=[dict(table=f['table'],column=f['to']) for f in fks if f['from']==n],constraints=definitions[n].split(r['type'],1)[1].strip() or 'No additional column constraint')
   if n=='pharmacy_id':c.update(readable_name='Pharmacy dispensing ID',definition='Identifier of a single pharmacy dispensing record, distinct from prescription and administration identifiers.',description='',allowed_values='Integer dispensing identifier; emar references an existing pharmacy record.',allowed_codes=[],code_meanings={})
   if name in ('pharmacy','emar') and n in ('order_id','pharmacy_id'):
    c['description']='';c['definition']=('Medication prescription fulfilled by this dispensing record.' if n=='order_id' else 'Dispensing record associated with this administration or omission.') if not r['pk'] else c['definition']
   if name=='lab_order' and n=='subject_id':c['definition']='Patient for this laboratory request, including requests not associated with a hospital admission.'
   if name=='lab_order' and n=='hadm_id':c.update(definition='Optional hospital admission associated with this laboratory request.',null_meaning='No hospital admission is associated with this request, as in outpatient testing.')
   if not c['nullable']:c['null_meaning']='NULL is not allowed by the declared schema.'
   if name=='pharmacy' and n=='dispensed_at':c.update(null_meaning='NULL is not allowed by the declared schema.',description='Authored dispensing milestone; not an original MIMIC pharmacy column.')
   if n=='itemid':c.update(definition=descs[n],allowed_values='1001 = Creatinine; 1002 = Sodium; 1003 = Hemoglobin. Authored concept codes.',description='Authored concept dictionary; no original MIMIC item IDs are claimed.')
   if n=='valuenum':c.update(unit='As specified by valueuom for the corresponding test.',description='Synthetic illustrative values; not fitted to clinical distributions.')
   if n=='valueuom':c.update(definition=descs[n],allowed_values='mg/dL, mmol/L or g/dL, as specified by itemid.',description='1001 uses mg/dL; 1002 uses mmol/L; 1003 uses g/dL.')
   if n=='medication':c.update(definition=descs[n],description='Illustrative generic drug labels; these records do not represent treatment recommendations.')
   if name=='procedure_episode':c['source_references']=['HospitalFlow authored hospital-level procedure schema; unlike MIMIC ICU procedureevents']
   cols.append(c)
  t['columns']=cols;tables.append(t)
 d['tables']=tables;d['dictionary_basic_information']['version']='2026-11-03-realism-revision'
 d['business_rules']=[r for r in d['business_rules'] if 'procedureevents' not in r and 'laboratory request' not in r.lower()]
 rules=['Laboratory, medication and procedure requests retain separate identifier namespaces; equal local values identify different requests.', 'lab_order.subject_id identifies its patient even when hadm_id is NULL. When hadm_id is present its patient must agree with admissions.subject_id; this is a documented cross-table rule checked by the construction validator.', 'medication_order represents a prescription; pharmacy represents a dispensing record; emar represents an administration or omission associated with one dispensing record.', 'Lab concept codes 1001, 1002 and 1003 mean Creatinine (mg/dL), Sodium (mmol/L) and Hemoglobin (g/dL), respectively.', 'Hospital-level procedure_episode is authored and does not reproduce the ICU procedureevents table.', 'The three order tables are an intentional alternative to MIMIC poe; laboratory-request and dispensing-milestone structures are authored simplifications.']
 for rule in rules:
  if rule not in d['business_rules']:d['business_rules'].append(rule)
 from semantic_metadata import revise
 d=revise(d)
 (p/'source/dictionary_profile.json').write_text(json.dumps(d,indent=2)+'\n')
