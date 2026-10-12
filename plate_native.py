"""Persist PlateFlow lifecycle simulation in existing business tables, not generic activity tables."""
import json,sqlite3,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ROW_ACTIONS={'Heating Completed':'HF','Plate Surface Checked':'SF'}
def convert(p):
 p=Path(p);con=sqlite3.connect(p/'input/database.sqlite');con.row_factory=sqlite3.Row;con.execute('PRAGMA foreign_keys=ON');d=json.loads((p/'input/data_dictionary.json').read_text());hist=[json.loads(x) for x in (p/'private/canonical_history.jsonl').read_text().splitlines()];links=json.loads((p/'private/lifecycle_links.json').read_text());plans=json.loads((p/'design/object_activity_design.json').read_text());sources=[];union=[];mapping_by_object={};newcolumns=[]
 for action,code in ROW_ACTIONS.items():con.execute('INSERT INTO operation_code VALUES (?,?)',(code,action))
 for plan in plans:
  obj=plan['object_table'];old=plan['activity_table'];pk=con.execute('PRAGMA table_info('+obj+')').fetchone()['name'];rows=[dict(x) for x in con.execute('SELECT * FROM '+old)];target=next(t for t in d['tables'] if t['table']==obj);columns=[]
  for action in plan['activities']:
   selected=[r for r in rows if r['activity']==action]
   if action in ROW_ACTIONS:
    code=ROW_ACTIONS[action]
    for r in selected:
     oid=r[pk]
     if obj=='furnace_charge_tracking':material=con.execute('SELECT material_id FROM furnace_charge_tracking WHERE tracking_id=?',(oid,)).fetchone()[0]
     else:material=oid
     # Existing history has strict start-before-completion; synthetic one-minute duration is authored.
     from datetime import datetime,timedelta
     end=r['occurred_at'];start=(datetime.fromisoformat(end.replace('Z','+00:00'))-timedelta(minutes=1)).isoformat().replace('+00:00','Z')
     con.execute('INSERT INTO material_operation_history VALUES (?,?,?,?,?,?)',(r['event_id'],material,code,start,end,start))
    sql="SELECT transaction_id event_id, '"+action+"' activity, completed_at timestamp FROM material_operation_history WHERE operation_code='"+code+"'"
    sources.append(dict(activity=action,table='material_operation_history',encoding='row',timestamp_column='completed_at',code=code,event_id_column='transaction_id',event_sql=sql))
   else:
    column=action.lower().replace(' ','_')+'_at';con.execute('ALTER TABLE '+obj+' ADD COLUMN '+column+' TEXT');target['columns'].append(dict(name=column,type='TEXT',constraints='',definition='Actual UTC time of '+action+'. NULL means this step has not occurred. Authored lifecycle addition; not an original manufacturer field.',source_origin='authored_lifecycle_extension'));columns.append(column);newcolumns.append(dict(table=obj,column=column,activity=action))
    for r in selected:con.execute('UPDATE '+obj+' SET '+column+'=? WHERE '+pk+'=?',(r['occurred_at'],r[pk]))
    j=next((int(r['event_id'].rsplit(':',1)[1]) for r in selected),plan['activities'].index(action)+1)
    sql="SELECT 'LC:"+obj+":' || "+pk+" || ':"+str(j)+"' event_id, '"+action+"' activity, "+column+' timestamp FROM '+obj+' WHERE '+column+' IS NOT NULL'
    sources.append(dict(activity=action,table=obj,encoding='column',timestamp_column=column,event_key=[pk,column],event_sql=sql))
   union.append(sql)
  plan['storage']='Existing '+obj+' milestone columns; repeatable checks/heating use material_operation_history where applicable';plan.pop('activity_table',None)
  con.execute('DROP TABLE '+old)
 con.execute('DROP TABLE lifecycle_case_link')
 con.execute("UPDATE plate_material SET latest_operation_completed_at=MAX(COALESCE(latest_operation_completed_at,''),COALESCE((SELECT MAX(completed_at) FROM material_operation_history h WHERE h.material_id=plate_material.plate_material_id),''))")
 d['code_domain'].update({code:action for action,code in ROW_ACTIONS.items()}) if 'code_domain' in d else None
 d['tables']=[t for t in d['tables'] if not t['table'].endswith('_activity') and t['table']!='lifecycle_case_link'];assert len(d['tables'])==9
 allsql=' UNION ALL '.join(union)
 # Derive every additional event-to-case link through existing business keys. No event/case index is stored in the DB.
 for case_table in links:
  parts=[]
  for source in sources:
   action=source['activity'];obj=next(e['event_id'].split(':')[1] for e in hist if e['event_id'].startswith('LC:') and e['activity']==action);pk=con.execute('PRAGMA table_info('+obj+')').fetchone()['name'];s=source['event_sql']
   if source['encoding']=='column':join=" JOIN "+obj+" o ON e.event_id='LC:"+obj+":' || o."+pk+" || ':"+str(next(int(e['event_id'].rsplit(':',1)[1]) for e in hist if e['event_id'].startswith('LC:') and e['activity']==action))+"'"
   else:
    join=' JOIN material_operation_history h ON h.transaction_id=e.event_id'
    join+= ' JOIN furnace_charge_tracking o ON o.material_id=h.material_id' if obj=='furnace_charge_tracking' else ' JOIN plate_material o ON o.plate_material_id=h.material_id'
   # All instruction/slab work rolls up to its mother and source slab; pieces roll up through genealogy.
   if obj=='slab_material':mother=' JOIN as_rolled_material m ON m.slab_id=o.slab_id'
   elif obj=='planned_rolling_instruction':mother=' JOIN as_rolled_material m ON m.slab_id=o.slab_id'
   elif obj=='rolling_instruction':mother=' JOIN as_rolled_material m ON m.instruction_id=o.instruction_id'
   elif obj=='plate_material':mother=' JOIN as_rolled_material m ON m.as_rolled_plate_no=o.parent_as_rolled_plate_no'
   else:mother=' JOIN as_rolled_material m ON m.material_id=o.material_id'
   if case_table==obj:expr='o.'+pk;extra=''
   elif case_table=='as_rolled_material':expr='m.material_id';extra=mother
   elif case_table=='slab_material':expr='m.slab_id';extra=mother
   else:continue
   parts.append('SELECT e.event_id,'+expr+' case_id FROM ('+s+') e'+join+extra)
  if case_table=='material_operation_history':parts.append("SELECT transaction_id event_id, transaction_id case_id FROM material_operation_history WHERE operation_code IN ('HF','SF')")
  if parts:mapping_by_object[case_table]=' UNION ALL '.join(parts)
 mapping_by_object['material_operation_history']="SELECT transaction_id event_id, transaction_id case_id FROM material_operation_history WHERE operation_code IN ('HF','SF')"
 extra='SELECT e.event_id,l.case_id,e.activity,e.timestamp FROM ('+allsql+') e JOIN ('+mapping_by_object['as_rolled_material']+') l ON l.event_id=e.event_id'
 gs=[json.loads(x) for x in (p/'private/gold.jsonl').read_text().splitlines()];old=next(g for g in gs if g['question_id']=='V05')['es'];original=old['original_event_specification']
 import importlib.util
 spec=importlib.util.spec_from_file_location('plate_builder',p/'build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);base=b.compile_es(original).strip().rstrip(';').split(' ORDER BY case_id,timestamp,event_id')[0];full='SELECT * FROM ('+base+' UNION ALL '+extra+') ORDER BY case_id,timestamp,event_id;'
 for g in gs:
  if g['question_id'] in ['V05','V06']:
   g['es']=dict(version='plateflow-native-es-1',original_event_specification=original,activity_sources=sources,native_case_mapping_sql=mapping_by_object,case_population_query=original['case_population_query'],compiled_sql=full)
   (p/'private/gold_sql'/(g['question_id']+'.sql')).write_text(full+'\n')
   expected=sorted(hist,key=lambda e:(e['case_id'],e['timestamp'],e['event_id']));assert [dict(r) for r in con.execute(full)]==expected
 (p/'private/gold.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in gs));d['object_activity_design']=plans;d['business_rules']=[r for r in d['business_rules'] if 'typed activity' not in r and 'Lifecycle case links' not in r];d['business_rules']+=['Single-occurrence milestones use actual time columns on the existing business object. NULL means the milestone did not occur.','Repeatable heating completions and surface checks use HF/SF codes in existing material_operation_history; activity meanings are in operation_code.','Added milestone columns and HF/SF codes are authored synthetic extensions, not original manufacturer metadata.','Event-to-case attribution uses existing FK/genealogy joins; there is no persisted lifecycle_case_link table.'];(p/'input/data_dictionary.json').write_text(json.dumps(d,indent=2)+'\n')
 (p/'private/lifecycle_persistence_mapping.json').write_text(json.dumps(sources,indent=2)+'\n');(p/'design/object_activity_design.json').write_text(json.dumps(plans,indent=2)+'\n')
 (p/'input/schema.sql').write_text('PRAGMA foreign_keys=ON;\n'+'\n'.join(r[0]+';' for r in con.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND type IN ('table','trigger') ORDER BY type,rowid"))+'\n')
 for fn in ['logical_schema.json','conceptual_model.json']:
  path=p/'design'/fn;design=json.loads(path.read_text());design.update(authored_lifecycle_extensions=plans,final_table_count=9,added_tables=[],authored_milestone_columns=newcolumns,storage_policy='Existing nine business tables, column milestones and operation-history rows');path.write_text(json.dumps(design,indent=2)+'\n')
 report=json.loads((p/'validation_report.json').read_text());report['table_rows']={t['table']:con.execute('SELECT COUNT(*) FROM '+t['table']).fetchone()[0] for t in d['tables']};report['lifecycle_extensions'].update(added_tables=0,added_columns=len(newcolumns),storage_policy='native business columns plus existing operation history');assert not list(con.execute('PRAGMA foreign_key_check'));assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok';(p/'validation_report.json').write_text(json.dumps(report,indent=2)+'\n');con.commit();con.close()
 doc='# PlateFlow activity storage in existing business tables\n\n- Nine original table roles are retained. Generic activity tables and the persisted case-link index are removed.\n- Actual one-time milestones use nullable timestamp columns on their existing business objects.\n- Repeatable heating completions and surface checks use HF/SF rows in material_operation_history, with meanings in operation_code.\n- Technical timestamps, planned times and latest-operation snapshots remain excluded as separate events.\n- Milestone additions and code meanings are authored assumptions, not claimed original source fields.\n- Existing FK and material-genealogy paths derive event-to-case links directly in SQL.\n\n| Object | Activities | Storage |\n|---|---|---|\n'+''.join('| '+x['object_table']+' | '+'; '.join(x['activities'])+' | '+x['storage']+' |\n' for x in plans)
 (p/'design/native_storage_mapping.json').write_text(json.dumps(dict(milestone_columns=newcolumns,operation_codes={v:k for k,v in ROW_ACTIONS.items()},sources=sources,case_mapping_sql=mapping_by_object),indent=2)+'\n');(p/'docs/object_activity_design.md').write_text(doc);(p/'design/requirements.md').write_text(doc)
