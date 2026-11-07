"""Prepare controlled dictionary-input conditions; never call or score a model."""
from pathlib import Path
import hashlib,json

COMMON=['input/database.sqlite','input/schema.sql','input/model_questions.jsonl']

def concise_dictionary(dictionary):
 out={k:dictionary[k] for k in ['name','language','timezone']};out['tables']=[]
 neutral={
  'patients':('Patients','One patient record.'),
  'patient_profile':('Supplementary patient information','One supplementary patient information record.'),
  'admissions':('Hospital admissions','One hospital stay.'),
  'admission_detail':('Signed discharge summaries','One recorded signed discharge summary per admission; draft documents are excluded.'),
  'lab_order':('Laboratory requests','One laboratory request for a patient, optionally associated with a hospital admission.'),
  'medication_order':('Medication prescriptions','One medication prescription.'),
  'procedure_order':('Procedure requests','One procedure request.'),
  'order_history':('Order actions','One recorded action referring to exactly one order category.'),
  'labevents':('Laboratory results','One laboratory measurement result, with specimen collection and result-availability times.'),
  'pharmacy':('Pharmacy dispensing records','One individual dispensing record fulfilling a medication prescription.'),
  'emar':('Medication administration records','One administration or omission associated with a dispensing record.'),
  'procedure_episode':('Hospital procedure episodes','One hospital-level execution episode; ICU stay hierarchy is excluded.'),
 }
 keys=['name','type','definition','nullable','null_meaning','null_interpretation','unit','format','timezone','allowed_values','allowed_codes','code_meanings']
 for table in dictionary['tables']:
  name=table['table'];label,grain=neutral[name]
  t=dict(table=name,definition=label,row_grain=grain,primary_key=table['primary_key'],foreign_keys=table['foreign_keys'],columns=[])
  for c in table['columns']:
   col={k:c[k] for k in keys}
   if c['name']=='subject_id':col['definition']='Patient identifier.'
   if c['name']=='hadm_id':col['definition']='Hospital admission identifier; optional where the column is nullable.'
   if c['name']=='order_id':col['definition']='Local request or prescription identifier, according to the table.'
   t['columns'].append(col)
  out['tables'].append(t)
 return out

def render(p,dictionary):
 p=Path(p);target=p/'input/ablation';target.mkdir(exist_ok=True)
 concise=concise_dictionary(dictionary)
 (target/'data_dictionary.concise.json').write_text(json.dumps(concise,indent=2)+'\n')
 conditions=[dict(id='full_dictionary',paths=COMMON+['input/data_dictionary.json']),dict(id='concise_dictionary',paths=COMMON+['input/ablation/data_dictionary.concise.json']),dict(id='no_dictionary',paths=COMMON)]
 (target/'conditions.json').write_text(json.dumps(dict(conditions=conditions),indent=2)+'\n')
 # Byte/character counts are explicit; no tokenizer or token count is claimed.
 sizes={name:dict(bytes=len((p/path).read_bytes()),characters=len((p/path).read_text())) for name,path in [('full_dictionary','input/data_dictionary.json'),('concise_dictionary','input/ablation/data_dictionary.concise.json')]}
 sizes['no_dictionary']=dict(bytes=0,characters=0)
 report=dict(status='Input conditions prepared and structurally validated; no model run or performance result.',common_inputs={path:hashlib.sha256((p/path).read_bytes()).hexdigest() for path in COMMON},dictionary_sizes=sizes,gold_sha256=hashlib.sha256((p/'private/gold.jsonl').read_bytes()).hexdigest())
 (p/'docs/dictionary_ablation_inputs.json').write_text(json.dumps(report,indent=2)+'\n')
 return conditions

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('dataset',type=Path);parser.add_argument('--condition',choices=['full_dictionary','concise_dictionary','no_dictionary'],required=True);args=parser.parse_args()
 conditions=json.loads((args.dataset/'input/ablation/conditions.json').read_text())['conditions'];condition=next(c for c in conditions if c['id']==args.condition)
 # Output only the selected paths. Loading a containing directory would leak the
 # other condition or author answers and is intentionally unsupported.
 print(json.dumps(dict(condition=condition['id'],paths=[str((args.dataset/path).resolve()) for path in condition['paths']]),indent=2))
