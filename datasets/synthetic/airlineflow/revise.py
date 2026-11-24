"""Revise the actual nested AirlineFlow SQLite fixtures; deterministic seed."""
import csv, hashlib, json, random, re, sqlite3
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
root=Path(__file__).resolve().parent
manifest_path=root/'evaluation/variant_manifest.json'
manifest=json.loads(manifest_path.read_text())
rng=random.Random(20261124)
def dt(x): return datetime.fromisoformat(x)
def ts(x): return x.strftime('%Y-%m-%d %H:%M:%S')
def add(x,n): return ts(dt(x)+timedelta(minutes=n))
def read(c,t): return list(c.execute('SELECT * FROM '+t))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def savecsv(p, rows):
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f); w.writerow(['case_id','activity','timestamp']); w.writerows(sorted(rows,key=lambda x:(x[0],x[2],x[1])))
# Read the checked-in original SQLite, not a projection of its Gold.
base=root/manifest[0]['database_path']
assert sha(base)==manifest[0]['database_sha256']
with sqlite3.connect(base) as c:
    flights=read(c,'flights'); turns=read(c,'turnarounds'); boards=read(c,'boarding_sessions'); jobs=read(c,'handling_jobs'); moves=read(c,'movement_reports')
assert len(turns)==48
def ids(prefix, values):
    numbers=rng.sample(range(100000,999999),len(values))
    return dict(zip(values,[prefix+str(n) for n in numbers]))
fm=ids('FL-', [x[0] for x in flights]); tm=ids('TU-', [x[0] for x in turns]); sm=ids('BS-', [x[0] for x in boards]); jm=ids('HJ-', [x[0] for x in jobs]); mm=ids('MR-', [x[0] for x in moves])
flight={x[0]:x for x in flights}; board={x[1]:x for x in boards}; byjob={(x[1],x[2]):x for x in jobs}; bymove={(x[1],x[2]):x for x in moves}
new={'flights':[(fm[x[0]],*x[1:]) for x in flights],'turnarounds':[],'boarding_sessions':[],'handling_jobs':[],'movement_reports':[]}
# Keep the original departure preparation milestones close to existing passenger/bag scans.
# Vary arrival/taxi/handling timing while preserving real operational precedence.
for i,(tid,inf,outf,h,ready) in enumerate(turns):
    land=bymove[inf,'LAND'][3]; block=bymove[inf,'IN'][3]; off=bymove[outf,'OUT'][3]
    block=add(block,rng.randint(-3,1))
    land=add(block,-rng.randint(6,17))
    handling=add(block,rng.randint(0,2))
    takeoff=add(off,rng.randint(8,24))
    new['turnarounds'].append((tm[tid],fm[inf],fm[outf],handling,ready))
    b=board[outf]
    new['boarding_sessions'].append((sm[b[0]],fm[outf],b[2],b[3]))
    # Include origin boarding of inbound legs too, with independent session identity.
    origin_off=add(flight[inf][2],rng.randint(-2,5))
    origin_air=add(origin_off,rng.randint(8,16))
    new['boarding_sessions'].append(('BS-I'+str(1000+i),fm[inf],add(origin_off,-rng.randint(35,48)),add(origin_off,-rng.randint(7,13))))
    # Destination arrival is part of the same operating leg, not the turnaround at the focal airport.
    dest_in=add(flight[outf][3],rng.randint(0,22))
    dest_land=add(dest_in,-rng.randint(6,15))
    for f,k,val in [(inf,'LAND',land),(inf,'IN',block),(outf,'OUT',off),(outf,'AIR',takeoff),
                    (inf,'OUT',origin_off),(inf,'AIR',origin_air),(outf,'LAND',dest_land),(outf,'IN',dest_in)]:
        old=bymove.get((f,k))
        mid=mm[old[0]] if old else 'MR-X'+str(i*8+len(new['movement_reports']))
        meta=old[5:] if old else ('AODB','AUTO_CHECKED','AIDX')
        new['movement_reports'].append((mid,fm[f],k,val,add(val,rng.randint(0,9)),*meta))
    est=bymove[outf,'EST']
    new['movement_reports'].append((mm[est[0]],fm[outf],'EST',add(off,rng.choice([-12,-7,3,8,14])),add(off,-rng.randint(18,35)),*est[5:]))
    # Overall handling starts before first job for selected cases. Preserve loading close
    # because later variants include individual bag scans tied to that milestone.
    for code in ['DP','UL','CL','FU','CA','BL']:
        j=byjob[tid,code]
        start=max(dt(j[3]),dt(handling)+timedelta(minutes=rng.randint(1,4)))
        finish=dt(j[4])
        if code in ['CL','FU','CA']:
            finish=min(dt(b[2])-timedelta(minutes=1),finish+timedelta(minutes=rng.randint(-5,4)))
        if finish<=start: start=finish-timedelta(minutes=1)
        assert start>=dt(handling),(tid,code)
        new['handling_jobs'].append((jm[j[0]],tm[tid],code,ts(start),ts(finish),add(ts(finish),rng.randint(1,18)),*j[6:]))
# Fix legacy reference queries to select only departures at the focal airport, not inbound origin movements.
dpath=root/'private/D.sql'; tpath=root/'private/T.sql'
D="""SELECT * FROM (
SELECT b.flight_id AS case_id, 'Boarding started' AS activity,b.started_at AS timestamp FROM boarding_sessions b JOIN turnarounds t ON t.outbound_id=b.flight_id
UNION ALL SELECT b.flight_id,'Boarding closed',b.closed_at FROM boarding_sessions b JOIN turnarounds t ON t.outbound_id=b.flight_id
UNION ALL SELECT t.outbound_id,'Baggage loading closed',j.finished_at FROM handling_jobs j JOIN turnarounds t ON t.turn_id=j.turn_id WHERE j.job_code='BL'
UNION ALL SELECT outbound_id,'Aircraft ready',ready_at FROM turnarounds
UNION ALL SELECT m.flight_id,'Off-block',m.value_at FROM movement_reports m JOIN turnarounds t ON t.outbound_id=m.flight_id WHERE m.kind='OUT'
) ORDER BY case_id,timestamp,activity;"""
T="""SELECT * FROM (
SELECT t.turn_id AS case_id,CASE m.kind WHEN 'LAND' THEN 'Inbound landed' ELSE 'Inbound in-block' END AS activity,m.value_at AS timestamp FROM turnarounds t JOIN movement_reports m ON m.flight_id=t.inbound_id WHERE m.kind IN ('LAND','IN')
UNION ALL SELECT turn_id,'Ground handling started',handling_started_at FROM turnarounds
UNION ALL SELECT turn_id,CASE job_code WHEN 'DP' THEN 'Disembarkation completed' WHEN 'UL' THEN 'Baggage unloading completed' WHEN 'CL' THEN 'Cabin cleaning completed' WHEN 'FU' THEN 'Refuelling completed' WHEN 'CA' THEN 'Catering completed' WHEN 'BL' THEN 'Baggage loading closed' END,finished_at FROM handling_jobs WHERE job_code IN ('DP','UL','CL','FU','CA','BL')
UNION ALL SELECT t.turn_id,'Boarding started',b.started_at FROM turnarounds t JOIN boarding_sessions b ON b.flight_id=t.outbound_id
UNION ALL SELECT t.turn_id,'Boarding closed',b.closed_at FROM turnarounds t JOIN boarding_sessions b ON b.flight_id=t.outbound_id
UNION ALL SELECT turn_id,'Aircraft ready',ready_at FROM turnarounds
UNION ALL SELECT t.turn_id,CASE m.kind WHEN 'OUT' THEN 'Off-block' ELSE 'Outbound take-off' END,m.value_at FROM turnarounds t JOIN movement_reports m ON m.flight_id=t.outbound_id WHERE m.kind IN ('OUT','AIR')
) ORDER BY case_id,timestamp,activity;"""
dpath.write_text(D+'\n');tpath.write_text(T+'\n')
# Independent row-oriented references for D and T, not derived from SQL results.
dr=[];tr=[]
for t in new['turnarounds']:
    k,inf,outf,h,r=t
    bd=next(b for b in new['boarding_sessions'] if b[1]==outf)
    js={j[2]:j for j in new['handling_jobs'] if j[1]==k}
    ms={(m[1],m[2]):m[3] for m in new['movement_reports']}
    de=[('Boarding started',bd[2]),('Boarding closed',bd[3]),('Baggage loading closed',js['BL'][4]),('Aircraft ready',r),('Off-block',ms[outf,'OUT'])]
    dr.extend((outf,a,v) for a,v in de)
    te=[('Inbound landed',ms[inf,'LAND']),('Inbound in-block',ms[inf,'IN']),('Ground handling started',h),('Outbound take-off',ms[outf,'AIR'])]
    te+= [(a,js[c][4]) for c,a in [('DP','Disembarkation completed'),('UL','Baggage unloading completed'),('CL','Cabin cleaning completed'),('FU','Refuelling completed'),('CA','Catering completed')]]
    tr.extend((k,a,v) for a,v in te+de)
savecsv(root/'private/D_events.csv',dr);savecsv(root/'private/T_events.csv',tr)
raw={}
for v in manifest:
    p=root/v['database_path']; dp=root/v['dictionary_path']
    assert sha(p)==v['database_sha256'],p
    with sqlite3.connect(p) as c:
        c.execute('PRAGMA foreign_keys=OFF')
        names=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        for table in new:
            c.execute('DELETE FROM '+table)
            c.executemany('INSERT INTO '+table+' VALUES ('+','.join('?' for _ in new[table][0])+')',new[table])
        for table in ['passenger_legs','flight_dispatch']:
            if table in names:
                c.executemany('UPDATE '+table+' SET flight_id=? WHERE flight_id=?',[(b,a) for a,b in fm.items()])
        assert not c.execute('PRAGMA foreign_key_check').fetchall()
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert Counter(c.execute(D))==Counter(dr)
        assert Counter(c.execute(T))==Counter(tr)
        v['table_rows']={t:c.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in names}
        v['row_count']=sum(v['table_rows'].values())
        raw[v['table_count']]={t:{'columns':[x[1] for x in c.execute('PRAGMA table_info('+t+')')],'rows':read(c,t)} for t in names}
        # Ensure flight-level preparation and movement events still have valid temporal ordering.
        for t,inf,outf,h,r in new['turnarounds']:
            assert ms.get((inf,'LAND')) is not None
            assert ms[inf,'LAND']<ms[inf,'IN']<=h<r<=ms[outf,'OUT']<ms[outf,'AIR']
        c.commit()
    dd=json.loads(dp.read_text())
    dd['boarding_sessions']['description']='Flight-level boarding sessions at the origin of every dated operating leg. One session per flight in this example; inbound legs also have origin boarding records.'
    dd['movement_reports']['description']='Estimated and actual movement messages for operating legs. Actual OUT and AIR refer to the origin; LAND and IN refer to the destination. Both inbound and outbound legs have all four actual movements; EST estimates origin off-block.'
    dd['turnarounds']['description']='Ground stay at the focal airport linking an arriving operating leg to the next departing operating leg of the same aircraft. The overall handling start is the start of coordination, which can precede individual jobs.'
    dp.write_text(json.dumps(dd,indent=2,ensure_ascii=False)+'\n')
    v['database_sha256']=sha(p);v['dictionary_sha256']=sha(dp)
manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
# Regenerate the embedded raw tables without retaining stale example times/IDs.
htmlpath=root/'docs/scenario.html'; html=htmlpath.read_text()
for n,data in raw.items():
    pattern=r'(<script type="application/json" id="raw-data-'+str(n)+r'">)[\s\S]*?(</script>)'
    html,nsub=re.subn(pattern,lambda m:m[1]+json.dumps(data,ensure_ascii=False,separators=(',',':'))+m[2],html)
    assert nsub==1
# Keep the existing ERD and dictionary dialogs; replace the outdated example section.
start=html.index('<h1>'); end=html.index('</section>',start)+len('</section>')
import html as esc
def table(rows,headers):
    return '<table><tr>'+''.join('<th>'+esc.escape(x)+'</th>' for x in headers)+'</tr>'+''.join('<tr>'+''.join('<td>'+esc.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</table>'
example=sorted(tr,key=lambda x:(x[0],x[2],x[1])); first=example[0][0]
html=html[:start]+'<h1>AirlineFlow: revised operating-leg and turnaround data</h1><p>All four nested variants share the same revised five core tables. Origin and destination movements are present for each operating leg. Boarding sessions exist at the origin of both inbound and outbound flights; turnaround membership identifies the focal-airport departure. IDs are independent. Actual and receipt times differ.</p><h2>Example turnaround</h2>'+table([r for r in example if r[0]==first],['Case','Activity','Actual event time'])+html[end:]
# Update embedded dictionary prose (existing diagram schema remains valid).
html=html.replace('Flight-level boarding sessions. This example does not model diversions or reopened boarding.','Flight-level boarding sessions at the origin of every dated operating leg, including inbound legs.')
html=html.replace('Estimated and actual movement messages for inbound and outbound operating legs.','Estimated and actual movement messages; OUT/AIR at origin, LAND/IN at destination for both inbound and outbound legs.')
htmlpath.write_text(html)
# Retain flight schedule as a separate evaluator artifact, with consistent IDs.
sched=root/'private/flight_schedule.csv'
with sched.open(encoding='utf-8-sig',newline='') as f: sr=list(csv.reader(f))
with sched.open('w',encoding='utf-8-sig',newline='') as f:
    csv.writer(f).writerows([[fm.get(x,x) for x in r] for r in sr])
readme=root/'README.md'; s=readme.read_text()
s=s.replace('Flight-level operational completion is recorded separately from individual scans.','Flight-level operational completion is recorded separately from individual scans. Each of the 96 legs has an origin boarding session and origin/departure and destination/arrival actual movement messages.')
s=s.replace('## Representation choices','## Dataset revision (2026-11-24)\n\nThe original databases were migrated in place across all nested sizes with deterministic seed 20261124. Core tables remain unchanged in schema. Independent surrogate identifiers replace aligned flight, turnaround, boarding, job and movement IDs. Both arrival and departure legs now carry all four actual movements; receipt delays, taxi durations and handling timing vary. The additional boarding sessions represent inbound flights boarding at their origin, not reopened boarding. Outbound flight and turnaround remain one-to-one within the focal-airport scope; strict original case-ID comparison is required. D and T references use the turnaround role to exclude movements at the other airport.\n\n## Representation choices')
readme.write_text(s)
print('PASS: revised',[(v['variant_id'],v['row_count']) for v in manifest])
print('D/T independent reference counts',len(dr),len(tr))
