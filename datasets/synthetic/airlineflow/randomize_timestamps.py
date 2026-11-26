"""Deterministically revise the timestamp fixture, keeping IDs/schema/schedules unchanged.
Input: directory with variants/l05...l20/input/database.sqlite (original snapshot).
Output: copied variants with changed clocks and canonical L20 records. No Gold used.
"""
import sqlite3,random,hashlib,json,shutil,sys
from datetime import datetime,timedelta
from pathlib import Path
from collections import defaultdict,Counter
SEED=20261126

def fmt(x):return datetime.fromtimestamp(x, __import__('datetime').timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
def sec(x):return int(datetime.fromisoformat(x).replace(tzinfo=__import__('datetime').timezone.utc).timestamp())
def revise(src,dst):
 rng=random.Random(SEED);dst.mkdir(parents=True,exist_ok=True)
 shutil.copytree(src/'variants',dst/'variants',dirs_exist_ok=True)
 c=sqlite3.connect(src/'variants/l20/input/database.sqlite');c.row_factory=sqlite3.Row
 names=[r[0] for r in c.execute("select name from sqlite_master where type='table' order by rowid")]
 cols={t:[r[1] for r in c.execute(f'pragma table_info({t})')] for t in names};pk={t:next(r[1] for r in c.execute(f'pragma table_info({t})') if r[5]==1) for t in names};T={t:{r[pk[t]]:dict(r) for r in c.execute(f'select * from {t} order by {pk[t]}')} for t in names};c.close()
 old=json.loads(json.dumps(T));
 def at(r,k):return sec(r[k])
 def set_(r,k,v):r[k]=fmt(v)
 def ran(a,b):return rng.randint(int(a),int(b))
 def near(v,a,b,j=180):
  a,b=int(a),int(b);assert a<=b,(v,a,b)
  l,h=max(a,v-j),min(b,v+j)
  return ran(l,h) if l<=h else ran(a,b)
 def ix(t,k):
  d=defaultdict(list)
  for r in T[t].values():d[r[k]].append(r)
  return d
 moves={f:{r['kind']:r for r in rs} for f,rs in ix('movement_reports','flight_id').items()};bs={r['flight_id']:r for r in T['boarding_sessions'].values()};jobs={u:{r['job_code']:r for r in rs} for u,rs in ix('handling_jobs','turn_id').items()}
 for u in T['turnarounds'].values():
  i,o=u['inbound_id'],u['outbound_id'];im,om=moves[i],moves[o];ib=at(im['IN'],'value_at')+ran(-110,110);ob=at(om['OUT'],'value_at')+ran(-150,150)
  # Anchor the operational day and preserve scheduled flights and broad delay patterns.
  for m,anchor,is_in in [(im,ib,True),(om,ob,False)]:
   if is_in:
    end=anchor;land=end-ran(360,1020);air=near(at(m['AIR'],'value_at'),land-7200,land-2100,180);off=air-ran(420,1380)
   else:
    off=anchor;air=off+ran(540,1440);land=near(at(m['LAND'],'value_at'),air+2100,air+9000,240);end=land+ran(360,1020)
   for k,v in [('OUT',off),('AIR',air),('LAND',land),('IN',end)]:
    set_(m[k],'value_at',v);set_(m[k],'received_at',v+ran(12,540))
   if 'EST' in m:
    e=m['EST'];v=near(at(e,'value_at'),off-1500,off+1500,240);receipt=min(v-30,off-30,near(at(e,'received_at'),off-3600,off-60,180));set_(e,'value_at',v);set_(e,'received_at',receipt)
  # Incoming leg origin boarding has its own independent time window.
  bb=bs[i];off=at(im['OUT'],'value_at');close=near(at(bb,'closed_at'),off-1500,off-150,180);start=near(at(bb,'started_at'),close-2700,close-900,180);set_(bb,'started_at',start);set_(bb,'closed_at',close)
  # Ground operations: coordination, disembark/unload, overlapping services, boarding, loading, ready.
  h=ib+ran(20,230);readygap=at(om['OUT'],'value_at')-at(u,'ready_at');oldgap=at(old['movement_reports'][om['OUT']['report_id']],'value_at')-at(u,'ready_at');ready=ob-max(150,oldgap+ran(-160,160));close=near(at(bs[o],'closed_at'),max(h+1800,ready-900),ready-45,180)
  bstart=near(at(bs[o],'started_at'),h+1200,close-900,210)
  set_(u,'handling_started_at',h);set_(u,'ready_at',ready);set_(bs[o],'started_at',bstart);set_(bs[o],'closed_at',close)
  j=jobs[u['turn_id']]
  def job(k,lo,hi,min_d,max_d):
   r=j[k];s=near(at(r,'started_at'),lo,hi-min_d,160);e=near(at(r,'finished_at'),s+min_d,min(s+max_d,hi),220);set_(r,'started_at',s);set_(r,'finished_at',e);set_(r,'posted_at',e+ran(20,1080));return s,e
  dp=job('DP',h+20,bstart-600,180,1050)
  ul=job('UL',h+20,bstart-300,180,1200)
  # Cabin access after passengers disembark, complete before gate session begins.
  cl=job('CL',dp[1]+10,bstart-10,240,2700)
  ca=job('CA',dp[1]+10,bstart-10,240,2700)
  fu=job('FU',h+30,ready-45,300,3000)
  bl=job('BL',max(h+30,ul[1]+10),ready-30,420,3600)
 # Passenger journey and security, with per-passenger nonconstant time windows.
 legs=T['passenger_legs']; tickets=T['tickets'];acts={k:{r['action_code']:r for r in v} for k,v in ix('passenger_actions','leg_id').items()};vis={r['leg_id']:r for r in T['security_visits'].values()};se={k:{r['point']:r for r in v} for k,v in ix('security_events','visit_id').items()};bag=ix('bag_legs','leg_id');sc={k:{r['scan_code']:r for r in v} for k,v in ix('bag_scans','bag_leg_id').items()};turnby={u['outbound_id']:u for u in T['turnarounds'].values()}
 for r in T['bookings'].values():set_(r,'booked_at',at(r,'booked_at')+ran(-2700,2700))
 for lid,l in legs.items():
  a=acts[lid];bb=bs[l['flight_id']];b0,b1=at(bb,'started_at'),at(bb,'closed_at');bd=near(at(a['BD'],'action_at'),b0+ran(25,85),b1-30,390);set_(a['BD'],'action_at',bd)
  if 'RJ' in a:
   # Ensure rejected scan during gate session, before later success; nonconstant delay.
   if bd-b0<45:bd=b0+90;set_(a['BD'],'action_at',bd)
   set_(a['RJ'],'action_at',bd-ran(15,min(240,bd-b0-1)))
  latest=min(bd,at(a['RJ'],'action_at') if 'RJ' in a else bd)
  k=se[vis[lid]['visit_id']];ck=near(at(a['CK'],'action_at'),b0-7200,b0-2100,480);set_(a['CK'],'action_at',ck)
  q=near(at(k['Q'],'observed_at'),ck+300,latest-420,420);s=q+ran(120,min(840,latest-q-150));end=s+ran(55,min(300,latest-s-20));
  for code,v in [('Q',q),('S',s),('C',end)]:set_(k[code],'observed_at',v);set_(k[code],'received_at',v+ran(10,250))
  for b in bag[lid]:
   z=sc[b['bag_leg_id']];bl=jobs[turnby[l['flight_id']]['turn_id']]['BL'];start,finish=at(bl,'started_at'),at(bl,'finished_at');acc=near(at(z['ACC'],'scanned_at'),ck+15,min(q-10,start-40),360);ld=near(at(z['LD'],'scanned_at'),max(acc+60,start+10),finish-30,360);set_(z['ACC'],'scanned_at',acc);set_(z['LD'],'scanned_at',ld)
 # Strong invariants; do not force uniqueness of genuinely simultaneous timestamps.
 for u in T['turnarounds'].values():
  i,o=u['inbound_id'],u['outbound_id'];h,ready=at(u,'handling_started_at'),at(u,'ready_at');assert at(moves[i]['IN'],'value_at')<h<ready<at(moves[o]['OUT'],'value_at');b=bs[o];assert h<at(b,'started_at')<at(b,'closed_at')<ready
  for j in jobs[u['turn_id']].values():assert h<at(j,'started_at')<at(j,'finished_at')<ready and at(j,'finished_at')<at(j,'posted_at')
  assert h<min(at(j,'started_at') for j in jobs[u['turn_id']].values())
 for f,m in moves.items():
  assert at(m['OUT'],'value_at')<at(m['AIR'],'value_at')<at(m['LAND'],'value_at')<at(m['IN'],'value_at');b=bs[f];assert at(b,'started_at')<at(b,'closed_at')<at(m['OUT'],'value_at')
  for k in ['OUT','AIR','LAND','IN']:assert at(m[k],'value_at')<at(m[k],'received_at')
 for lid,l in legs.items():
  a=acts[lid];b=bs[l['flight_id']];k=se[vis[lid]['visit_id']];assert at(T['bookings'][tickets[l['ticket_id']]['booking_id']],'booked_at')<at(a['CK'],'action_at')<at(k['Q'],'observed_at')<at(k['S'],'observed_at')<at(k['C'],'observed_at')<at(a['BD'],'action_at');assert at(b,'started_at')<at(a['BD'],'action_at')<at(b,'closed_at')
  if 'RJ' in a:assert at(b,'started_at')<at(a['RJ'],'action_at')<at(a['BD'],'action_at') and at(k['C'],'observed_at')<at(a['RJ'],'action_at')
  for z in k.values():assert at(z,'observed_at')<at(z,'received_at')
  for x in bag[lid]:
   z=sc[x['bag_leg_id']];j=jobs[turnby[l['flight_id']]['turn_id']]['BL'];assert at(a['CK'],'action_at')<at(z['ACC'],'scanned_at')<at(z['LD'],'scanned_at');assert at(j,'started_at')<at(z['LD'],'scanned_at')<at(j,'finished_at')
 # Compare only timestamp columns changed; same row order, schema, IDs, counts, DD.
 report={};prev={}
 for p in sorted((dst/'variants').glob('l*/input/database.sqlite')):
  db=sqlite3.connect(p);db.execute('pragma foreign_keys=ON');ns=[r[0] for r in db.execute("select name from sqlite_master where type='table'")];changes={}
  for t in ns:
   n=0
   for k,r in T[t].items():
    diff={a:v for a,v in r.items() if old[t][k][a]!=v};assert all(a.endswith('_at') for a in diff)
    if diff:db.execute(f'update {t} set '+','.join(f'{a}=?' for a in diff)+f' where {pk[t]}=?',(*diff.values(),k));n+=len(diff)
   changes[t]=n
  db.commit();assert db.execute('pragma integrity_check').fetchone()[0]=='ok' and not db.execute('pragma foreign_key_check').fetchall();curr={t:db.execute(f'select * from {t} order by {pk[t]}').fetchall() for t in ns};assert all(curr[t]==v for t,v in prev.items());prev=curr;db.close();report[p.parent.parent.name]={'timestamp_cells_changed':sum(changes.values()),'by_table':changes,'db_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'rows':sum(map(len,curr.values()))}
 (dst/'source').mkdir(exist_ok=True);(dst/'source/records.json').write_text(json.dumps({t:{'columns':cols[t],'rows':[[r[k] for k in cols[t]] for r in T[t].values()]} for t in names},ensure_ascii=False,indent=2)+'\n');(dst/'timestamp_audit.json').write_text(json.dumps({'seed':SEED,'variants':report,'constraints':'PASS; nested rows equal; scheduled clocks and all non-timestamp attributes unchanged'},indent=2)+'\n');return report
if __name__=='__main__':print(json.dumps(revise(Path(sys.argv[1]),Path(sys.argv[2])),indent=2))
