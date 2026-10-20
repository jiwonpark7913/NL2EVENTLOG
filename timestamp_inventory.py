"""Count physical timestamp columns once per table.column; distinguish dates and non-event times."""
import json,sqlite3,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE={'warehouseflow':2,'universityflow':14,'plateflow':37,'hospitalflow':17}
NOTE='- Timestamp columns count physical table.column pairs storing date-and-time instants. Date-only birth/planning fields and recurring class schedules are excluded. Event timestamp columns are the subset actually selected as event times by the current ES; plans, technical times, snapshots, interval starts and copied key timestamps are listed separately.\n'
def inventory(p):
 con=sqlite3.connect(p/'input/database.sqlite');con.row_factory=sqlite3.Row;d=json.loads((p/'input/data_dictionary.json').read_text());rows=[];dates=[]
 for t in d['tables']:
  for c in t['columns']:
   n=t['table'];cn=c['name'];values=[r[0] for r in con.execute('SELECT '+cn+' FROM '+n+' WHERE '+cn+' IS NOT NULL LIMIT 3')]
   instant=any(isinstance(v,str) and re.match(r'^\d{4}-\d\d-\d\dT\d\d:\d\d',v) for v in values)
   if not instant:
    if values and all(isinstance(v,str) and re.fullmatch(r'\d{4}-\d\d-\d\d',v) for v in values):dates.append(n+'.'+cn)
    if values or not cn.endswith('_at'):continue
   role='actual event time';used=True
   if cn in ['created_at','updated_at']:role='technical record timestamp';used=False
   elif p.name=='hospitalflow' and cn=='storetime' and n in ['emar','procedureevents']:role='technical documentation time';used=False
   elif cn=='latest_operation_completed_at':role='latest-operation snapshot';used=False
   elif cn.startswith('planned_'):role='planned instant';used=False
   elif cn=='lot_charging_started_at':role='lot-level instant outside material-event scope';used=False
   elif cn=='started_at' and n=='material_operation_history':role='operation interval start, not a separately selected event';used=False
   elif n.endswith('_activity') and cn=='simulation_date':role='copied timestamp in parent identity';used=False
   count=con.execute('SELECT COUNT('+cn+') FROM '+n).fetchone()[0];rows.append(dict(table=n,column=cn,role=role,used_as_event_time=used,non_null_rows=count))
 out=dict(timestamp_columns=len(rows),event_timestamp_columns=sum(x['used_as_event_time'] for x in rows),other_timestamp_columns=sum(not x['used_as_event_time'] for x in rows),date_only_columns=dates,baseline_timestamp_columns=BASE[p.name],columns=rows);(p/'docs/timestamp_columns.json').write_text(json.dumps(out,indent=2)+'\n')
 doc='# Timestamp column inventory\n\n'+NOTE+'\n| Table | Column | Role | Used as event time | Non-null rows |\n|---|---|---|---|---:|\n'+''.join(f"| {x['table']} | {x['column']} | {x['role']} | {'Yes' if x['used_as_event_time'] else 'No'} | {x['non_null_rows']} |\n" for x in rows)+'\n- Date-only fields excluded: '+(', '.join(dates) or 'None')+'.\n- New timestamp questions TS01/TS02/... and their P counterparts explicitly test milestone-column extraction.\n';(p/'docs/timestamp_columns.md').write_text(doc)
 d['timestamp_summary']={k:v for k,v in out.items() if k!='columns'};(p/'input/data_dictionary.json').write_text(json.dumps(d,indent=2)+'\n');r=json.loads((p/'validation_report.json').read_text());r['timestamp_summary']=d['timestamp_summary'];(p/'validation_report.json').write_text(json.dumps(r,indent=2)+'\n');con.close();return out

def refresh():
 allrows=[]
 for name,title in [('warehouseflow','WarehouseFlow'),('universityflow','UniversityFlow'),('plateflow','PlateFlow'),('hospitalflow','HospitalFlow')]:
  p=ROOT/'datasets'/name;inv=inventory(p);r=json.loads((p/'validation_report.json').read_text());counts=[len(r['table_rows']),r.get('semantic_object_types',len(r['object_view_coverage'])),len(r['activity_counts']),inv['timestamp_columns'],inv['event_timestamp_columns'],r['events'],r['total_questions'],r['answerable_questions']];header='| Dataset | Tables | Object / case types | Activity types | Timestamp columns | Event timestamp columns | Distinct events | Questions | Gold CSVs |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|\n';row='| '+title+' | '+' | '.join(map(str,counts))+' |';readme=p/'README.md';s=readme.read_text();s=re.sub(r'\| Dataset \| Tables \|.*?(?=\n\n)',header+row,s,count=1,flags=re.S);s=re.sub(r'- \*\*Database:\*\*[^\n]*',f'- **Database:** {counts[0]} tables; {counts[1]} object / case types; {counts[2]} activity types; {counts[3]} timestamp columns ({counts[4]} event timestamp columns); {counts[5]} distinct events.',s);s=re.sub(r'\n## Timestamp columns\n.*?(?=\n## |\Z)','',s,flags=re.S);s+='\n## Timestamp columns\n\n'+NOTE+'- [Timestamp inventory and roles](docs/timestamp_columns.md)\n- [Milestone-column extraction questions and Gold activity counts](docs/questions.md)\n- Single-occurrence milestone times are stored on the existing business record. Repeated actions remain row encoded; the same event is not stored twice.\n';readme.write_text(s);allrows.append((title,counts,inv))
 p=ROOT/'README.md';s=p.read_text();table=header+''.join('| ['+title+'](datasets/'+title.lower()+'/README.md) | '+' | '.join(map(str,counts))+' |\n' for title,counts,_ in allrows);s=re.sub(r'\| Dataset \| Tables \|.*?(?=\n\n)',table.rstrip(),s,count=1,flags=re.S);s=re.sub(r'\n## Timestamp columns\n.*?(?=\n## |\Z)','',s,flags=re.S);s+='\n## Timestamp columns\n\n'+NOTE+'\n| Dataset | Baseline timestamp columns before milestone expansion | Current timestamp columns | Current event timestamp columns |\n|---|---:|---:|---:|\n'+''.join(f'| {title} | {i["baseline_timestamp_columns"]} | {i["timestamp_columns"]} | {i["event_timestamp_columns"]} |\n' for title,_,i in allrows);p.write_text(s)
 return allrows
if __name__=='__main__':
 for title,_,x in refresh():print(title,x['baseline_timestamp_columns'],'→',x['timestamp_columns'],'event timestamps:',x['event_timestamp_columns'])
