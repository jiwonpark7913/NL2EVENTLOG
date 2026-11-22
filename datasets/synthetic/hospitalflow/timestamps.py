"""Explicit simulation-only collision handling, before Gold generation.

Minute-scale samples can accidentally collide. Assign distinct seconds only to
those collisions, update physical timestamps and the independent history, and
retain an audit. This is not a log-sort or extraction rule.
"""
from collections import defaultdict
from datetime import datetime,timedelta

def resolve_accidental_ties(con,sources,history):
 grouped=defaultdict(list)
 for e in history:grouped[e['timestamp']].append(e)
 changes={};audit=[]
 for timestamp,events in grouped.items():
  if len(events)<2:continue
  assert len(events)<=60
  for seconds,e in enumerate(sorted(events,key=lambda e:e['event_id'])):
   new=(datetime.fromisoformat(timestamp.replace('Z','+00:00'))+timedelta(seconds=seconds)).isoformat().replace('+00:00','Z')
   changes[e['event_id']]=new;audit.append(dict(event_id=e['event_id'],sampled_timestamp=timestamp,stored_timestamp=new,reason='Avoid incidental simulation collision; no simultaneous clinical occurrence intended.'));e['timestamp']=new
 for source in sources:
  sql=source['event_sql'];alias='e.rowid' if (' FROM '+source['table']+' e ') in sql else 'rowid'
  rows=list(con.execute('SELECT '+alias+' physical_rowid,'+sql[len('SELECT '):]))
  for row in rows:
   if row['event_id'] in changes:
    con.execute('UPDATE '+source['table']+' SET '+source['timestamp_column']+'=? WHERE rowid=?',(changes[row['event_id']],row['physical_rowid']))
 con.commit()
 return audit
