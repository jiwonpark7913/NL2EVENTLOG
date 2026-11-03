"""Reviewed clinical-time, NULL and record-grain business definitions."""

def revise(dictionary):
 dictionary['dictionary_basic_information']['version']='2026-11-03-semantics-revision'
 definitions={
  ('labevents','charttime'):('Specimen collection time','Time when the specimen used for this laboratory measurement was collected. This column does not store measurement execution time.'),
  ('lab_order','specimen_received_at'):('Specimen receipt time','Time when specimens associated with this laboratory request were received by the laboratory.'),
  ('pharmacy','dispensed_at'):('Dispensing record time','Time of the individual dispensing represented by this pharmacy record. This is not the first dispensing time for the prescription; each additional dispensing has its own pharmacy_id and row.'),
  ('admission_detail','discharge_summary_signed_at'):('Discharge summary signing time','Time when the discharge summary for this admission was signed; signing may occur after the patient has left the hospital.'),
 }
 nullable_times={
  ('admissions','edregtime'):'No emergency department registration time is recorded. Whether an ED registration occurred is unknown.',
  ('admissions','discharge_authorized_at'):'No discharge authorization time is recorded. Whether authorization occurred is unknown.',
  ('admissions','dischtime'):'No discharge time is recorded. Whether discharge occurred is unknown; an ongoing stay cannot be inferred from NULL alone.',
  ('lab_order','specimen_received_at'):'No specimen receipt time is recorded. Whether receipt occurred is unknown.',
  ('lab_order','results_verified_at'):'No results-verification time is recorded. Whether verification occurred is unknown.',
  ('medication_order','stopped_at'):'No prescription stop time is recorded. Whether stopping occurred is unknown.',
  ('procedure_order','preparation_completed_at'):'No preparation completion time is recorded. Whether completion occurred is unknown.',
  ('procedure_episode','endtime'):'No procedure completion time is recorded. Whether completion occurred is unknown; an ongoing procedure cannot be inferred from NULL alone.',
 }
 for t in dictionary['tables']:
  name=t['table']
  t['constraint_notes']=[]
  if name=='admissions':t['constraint_notes']=['CHECK(dischtime IS NULL OR discharge_authorized_at<=dischtime) rejects a known authorization time later than discharge. When discharge_authorized_at is NULL and dischtime is present, the expression evaluates to UNKNOWN and SQLite permits the row. Authorization is not mandatory for a recorded discharge.']
  if name=='admission_detail':t.update(definition='Recorded signed discharge summaries associated with hospital admissions.',row_grain='One recorded signed discharge summary per admission represented in this table. Draft documents are outside this table.')
  if name=='labevents':t['row_grain']='One laboratory measurement result associated with a collected specimen and a laboratory request; collection and result availability have separate timestamps.'
  for c in t['columns']:
   key=(name,c['name'])
   if key in definitions:c['readable_name'],c['definition']=definitions[key];c['description']=''
   if key in nullable_times:c['null_meaning']=nullable_times[key];c['null_interpretation']='Unknown occurrence; timestamp not recorded'
   elif not c['nullable']:c['null_interpretation']='Not allowed'
   elif name=='order_history':c['null_interpretation']='Not applicable to this order category'
   elif key==('lab_order','hadm_id'):c['null_interpretation']='No associated admission'
   else:c['null_interpretation']='Value not recorded'
   if c['name']=='order_id':c['description']=''
   if key==('labevents','charttime'):
    c['source_references']=['https://mimic.mit.edu/docs/iv/modules/hosp/labevents.html#charttime','HospitalFlow records specimen collection in charttime; measurement execution is not represented.']
   if name=='procedure_episode':c['source_references']=['Hospital-level adaptation of episode timing; the MIMIC ICU stay_id hierarchy is excluded. This is not the original procedureevents schema.']
   c['definition']=c['definition'].replace('synthetic laboratory measurement','laboratory measurement')
 dictionary['business_rules']=[
  'A patient can have multiple hospital admissions; hadm_id identifies an admission and subject_id identifies a patient.',
  'Supplementary profile rows use the patient identifier documented in patients; their logical relationship is not enforced by an SQL foreign key.',
  'A signed discharge summary uses the identifier of its hospital admission. Draft documents are not stored in admission_detail.',
  'Laboratory, medication and procedure requests use separate local identifier namespaces.',
  'An order-action history row has exactly one populated order-reference column; repeated reviews are separate records.',
  'A laboratory request can cover several specimens or measurements. For a recorded result the collection time precedes laboratory receipt, which precedes result availability; verification follows the available results.',
  'When a laboratory request has an associated admission, lab_order.subject_id must equal admissions.subject_id for that hadm_id. NULL hadm_id means no associated admission.',
  'A medication prescription can have multiple pharmacy dispensing records; each dispensing can have multiple administration or omission records.',
  'NULL is interpreted by the column-specific rule: an unrecorded clinical timestamp gives unknown occurrence status; a non-applicable order-reference column and an absent admission association have their separately defined structural meanings.',
  'Laboratory charttime represents specimen collection; storetime represents result availability. Medication and procedure storetime values represent system documentation times.',
  'Lab concept codes 1001, 1002 and 1003 mean Creatinine (mg/dL), Sodium (mmol/L) and Hemoglobin (g/dL), respectively.'
 ]
 return dictionary
