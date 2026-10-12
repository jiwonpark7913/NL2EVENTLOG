"""Explicit event-storage semantics, separate from physical SQL row/column storage."""
import json
ROW={'warehouseflow':{'transaction_record':'transaction_type selects IN/OUT; one transaction occurrence per row.'},'universityflow':{'registration':'One successful registration occurrence per student-course row.','degree_examination_result':'One examination sitting per result row.','assignment_grading':'One grading occurrence per composite-key row.','student_simulation_experiment_result':'One completed simulation run per composite-key row.'},'plateflow':{'material_operation_history':'operation_code selects the action; one completed operation per history row. started_at is not currently extracted as a second event.'}}
COLUMN={'universityflow':{'thesis':('submission_date','One thesis object row stores its actual submission milestone.')},'plateflow':{'rolling_instruction':('released_at','Instruction object row stores its actual release milestone.'),'as_rolled_material':('furnace_charged_at, crop_shear_passed_at','One material object row contains two different extracted business milestones.'),'furnace_charge_tracking':('yard_instruction_received_at','Only yard instruction receipt is currently extracted; lot_charging_started_at is outside the declared material-event scope.'),'cutting_finishing_instruction':('released_at','Cutting instruction object row stores its actual release milestone.'),'plate_material':('dimension_inspected_at','One cut-piece object row stores its actual dimensional-inspection milestone.')}}
def encoding(name,table):
 if table.endswith('_activity'):return dict(event_encoding='Row encoding',encoding_detail='Each action is a separate row; activity selects its meaning and occurred_at is its actual time.')
 if table in ROW.get(name,{}):return dict(event_encoding='Row encoding',encoding_detail=ROW[name][table])
 if table in COLUMN.get(name,{}):cols,meaning=COLUMN[name][table];return dict(event_encoding='Column encoding',encoding_detail=meaning+' Extracted event columns: '+cols+'.')
 return dict(event_encoding='No event encoding',encoding_detail='Master, plan, reference or relationship/index data; this table does not directly produce an event in the current ES. Related objects can still have logs from other tables.')
def annotate(p):
 d=json.loads((p/'input/data_dictionary.json').read_text())
 for t in d['tables']:t.update(encoding(p.name,t['table']))
 (p/'input/data_dictionary.json').write_text(json.dumps(d,indent=2)+'\n');return d
