"""One-time migration of the checked-in AirlineFlow baggage fixtures (seed 20261125).
Keep the 5 core tables and all schema constraints unchanged.
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
import csv, hashlib, html, json, random, re, sqlite3

root = Path(__file__).resolve().parent
mp = root / 'evaluation/variant_manifest.json'
manifest = json.loads(mp.read_text())
rng = random.Random(20261125)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dt(s): return datetime.fromisoformat(s)
def ts(d): return d.strftime('%Y-%m-%d %H:%M:%S')
def rows(c,t): return c.execute('SELECT * FROM "'+t+'" ORDER BY 1').fetchall()
def tables(c): return [x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
def records(c): return {t:rows(c,t) for t in tables(c)}
def loadcsv(p):
    with p.open(encoding='utf-8-sig',newline='') as f:
        return Counter((r['case_id'],r['activity'],r['timestamp']) for r in csv.DictReader(f))
def savecsv(p,rr):
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['case_id','activity','timestamp'])
        w.writerows(sorted(rr,key=lambda r:(r[0],r[2],r[1])))

for v in manifest:
    assert sha(root/v['database_path'])==v['database_sha256']
    assert sha(root/v['dictionary_path'])==v['dictionary_sha256']

# One shared update map, applied identically to L15 and L20.
join = """SELECT s.scan_id,s.bag_leg_id,s.scanned_at,pl.flight_id,j.started_at,j.finished_at,a.scanned_at
FROM bag_scans s JOIN bag_legs b USING(bag_leg_id)
JOIN passenger_legs pl USING(leg_id)
JOIN turnarounds t ON t.outbound_id=pl.flight_id
JOIN handling_jobs j ON j.turn_id=t.turn_id AND j.job_code='BL'
JOIN bag_scans a ON a.bag_leg_id=s.bag_leg_id AND a.scan_code='ACC'
WHERE s.scan_code='LD' ORDER BY pl.flight_id,s.scanned_at,s.scan_id"""
source=next(v for v in manifest if v['variant_id']=='l15')
with sqlite3.connect(root/source['database_path']) as c:
    old=c.execute(join).fetchall()
groups=defaultdict(list)
for r in old: groups[r[3]].append(r)
assert len(groups)==48 and len(old)==144
updates={}; old_gaps=[]; new_gaps=[]
for flight,group in sorted(groups.items()):
    close=dt(group[0][5]); latest=max(dt(r[2]) for r in group)
    gap=int((close-latest).total_seconds()/60)
    old_gaps.append(gap)
    assert gap==3
    # Shift individual LD observations within the actual loading interval;
    # keep all acceptance timestamps unchanged. Positive gaps, varied 1–9 min.
    lower=max(max(dt(r[4]),dt(r[6])) for r in group)
    feasible=[g for g in range(1,10) if all(dt(r[2])+timedelta(minutes=gap-g)>=max(dt(r[4]),dt(r[6])) for r in group)]
    assert feasible
    target=rng.choice(feasible)
    new_gaps.append(target)
    for scan,bag,when,f,start,finish,accepted in group:
        val=dt(when)+timedelta(minutes=gap-target)
        assert dt(accepted)<=val and dt(start)<=val<dt(finish)
        updates[scan]=ts(val)
assert len(set(new_gaps))>=5 and min(new_gaps)>0
assert len(updates)==144
# Natural operational dictionary definitions, not extraction instructions.
patch={
 'handling_jobs':{
  '__table__':'Ground handling work orders associated with aircraft turnarounds.',
  'turn_id':'Aircraft turnaround associated with the job.',
  'job_code':'Type of ground handling operation. BL = Baggage loading; CL = Cabin cleaning; DP = Passenger disembarkation; UL = Baggage unloading; FU = Refuelling; CA = Catering loading.',
  'started_at':'Actual start time of the assigned job.',
  'finished_at':'Time at which completion of the assigned operation was confirmed.',
  'posted_at':'Time at which the job record was posted to the system.'},
 'bag_legs':{
  '__table__':'Transport records for a sample of checked bags associated with passenger flight legs.',
  'bag_leg_id':'Baggage transport record identifier.',
  'leg_id':'Passenger flight leg associated with the checked bag.',
  'bag_tag':'Baggage tag identifier.'},
 'bag_scans':{
  '__table__':'Individual baggage tracking records for the checked bags represented in the dataset.',
  'scan_id':'Baggage scan record identifier.',
  'bag_leg_id':'Baggage transport record associated with the scan.',
  'scan_code':'Baggage tracking event code. ACC = Bag accepted; LD = Bag loaded into the aircraft hold.',
  'scanned_at':'Date and time of the baggage scan.'}
}
bpath=root/'private/B_events.csv'
old_b=loadcsv(bpath)
b_reference=None; raw={}; dictionaries={}; audit={}
dsql=(root/'private/D.sql').read_text()
tsql=(root/'private/T.sql').read_text()
bsql=(root/'private/B.sql').read_text()
dref=loadcsv(root/'private/D_events.csv'); tref=loadcsv(root/'private/T_events.csv')
for v in manifest:
    level=v['variant_id']; p=root/v['database_path']; ddp=root/v['dictionary_path']
    old_hash=sha(p); old_dd_hash=sha(ddp)
    with sqlite3.connect(p) as c:
        before=records(c)
        schema=c.execute("SELECT type,name,sql FROM sqlite_master ORDER BY type,name").fetchall()
        if 'bag_scans' in before:
            assert c.execute(join).fetchall()==old
            c.executemany("UPDATE bag_scans SET scanned_at=? WHERE scan_id=? AND scan_code='LD'",[(val,key) for key,val in updates.items()])
            c.commit()
        after=records(c)
        assert schema==c.execute("SELECT type,name,sql FROM sqlite_master ORDER BY type,name").fetchall()
        for name in before:
            if name!='bag_scans': assert before[name]==after[name],(level,name)
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not c.execute('PRAGMA foreign_key_check').fetchall()
        assert Counter(c.execute(dsql))==dref
        assert Counter(c.execute(tsql))==tref
        info={'database_before':old_hash,'changed_ld_rows':0}
        if 'bag_scans' in before:
            original={r[0]:r for r in before['bag_scans']}
            changed=[r for r in after['bag_scans'] if r!=original[r[0]]]
            assert all(r[2]=='LD' and r[:3]==original[r[0]][:3] for r in changed)
            info['changed_ld_rows']=len(changed)
            gaprows=c.execute(join).fetchall()
            latest_by_f={}
            for scan,bag,when,f,start,finish,accepted in gaprows:
                assert dt(accepted)<=dt(when) and dt(start)<=dt(when)<dt(finish)
                latest_by_f[f]=max(latest_by_f.get(f,when),when)
            gaps={f:int((dt(groups[f][0][5])-dt(val)).total_seconds()/60) for f,val in latest_by_f.items()}
            assert len(gaps)==48 and min(gaps.values())>0
            info['gap_minutes_distribution']=dict(sorted(Counter(gaps.values()).items()))
            # Independent row-based legacy B reference (not produced from B.sql).
            bl={r[0]:r[1] for r in after['bag_legs']}
            independent=[(r[1],{'CK':'Check-in completed','BD':'Boarding confirmed'}[r[2]],r[3]) for r in after['passenger_actions'] if r[2] in ('CK','BD')]
            independent += [(bl[r[1]],{'ACC':'Bag accepted','LD':'Bag loaded'}[r[2]],r[3]) for r in after['bag_scans'] if r[2] in ('ACC','LD')]
            expected=Counter(independent)
            assert expected==Counter(c.execute(bsql))
            if b_reference is None: b_reference=expected
            else: assert b_reference==expected
            assert len(independent)==864
            # Q03/D wrong-source mutant: same remaining events, last LD replaces closure.
            mutant=Counter((f,a,latest_by_f[f] if a=='Baggage loading closed' else time) for f,a,time in dref.elements())
            tp=sum((mutant&dref).values())
            assert sum(mutant.values())==240 and tp==192 and mutant!=dref
            info['q03_max_ld_mutant']={'tp':tp,'fp':48,'fn':48,'f1':0.8,'exact':False}
        raw[v['table_count']]={t:{'columns':[r[1] for r in c.execute('PRAGMA table_info("'+t+'")')],'rows':after[t]} for t in after}
    if v['table_count']<15: assert sha(p)==old_hash
    dd=json.loads(ddp.read_text())
    for table,fields in patch.items():
        if table not in dd: continue
        for field,desc in fields.items():
            if field=='__table__': dd[table]['description']=desc
            else: dd[table]['columns'][field]['description']=desc
    ddp.write_text(json.dumps(dd,ensure_ascii=False,indent=2)+'\n')
    dictionaries[v['table_count']]=dd
    v['database_sha256']=sha(p); v['dictionary_sha256']=sha(ddp)
    info.update(database_after=v['database_sha256'],dictionary_before=old_dd_hash,dictionary_after=v['dictionary_sha256'])
    audit[level]=info
assert b_reference is not None
assert {r:n for r,n in old_b.items() if r[1]!='Bag loaded'}=={r:n for r,n in b_reference.items() if r[1]!='Bag loaded'}
savecsv(bpath,b_reference.elements())
mp.write_text(json.dumps(manifest,indent=2)+'\n')

# Replace raw-data payloads and only the affected dictionary sections in the scenario.
hp=root/'docs/scenario.html'; page=hp.read_text()
for size,data in raw.items():
    patt=r'(<script type="application/json" id="raw-data-'+str(size)+r'">)[\s\S]*?(</script>)'
    # Keep unchanged embedded data for L05/L10, including its existing row order.
    def update_raw(m):
        original=json.loads(m[0][len(m[1]):-len(m[2])])
        if 'bag_scans' in original:
            cols=original['bag_scans']['columns']; idx=cols.index('scanned_at'); sid=cols.index('scan_id')
            for row in original['bag_scans']['rows']:
                if row[sid] in updates: row[idx]=updates[row[sid]]
        for t in original:
            assert [tuple(x) for x in sorted(original[t]['rows'],key=lambda x:x[0])]==data[t]['rows'],(size,t)
        return m[1]+json.dumps(original,ensure_ascii=False,separators=(',',':'))+m[2]
    page,n=re.subn(patt,update_raw,page);assert n==1
for table,fields in patch.items():
    pattern=r'(<h3>'+re.escape(table)+r'</h3><p>)[\s\S]*?(</p><table class="dict-table">[\s\S]*?</table>)'
    def change(m):
        body=m[2]
        # Keep columns, declarations and all unrelated metadata intact.
        for field,desc in fields.items():
            if field=='__table__': continue
            p=r'(<tr><td>(?:<code>)?'+re.escape(field)+r'(?:</code>)?</td><td>[\s\S]*?</td><td>)[\s\S]*?(</td></tr>)'
            body,n=re.subn(p,lambda x:x[1]+html.escape(desc)+x[2],body)
            assert n==1,(table,field)
        return m[1]+html.escape(fields['__table__'])+body
    page,n=re.subn(pattern,change,page)
    assert n==(4 if table=='handling_jobs' else 2),(table,n)
hp.write_text(page)
rp=root/'README.md'; readme=rp.read_text()
readme=readme.replace('## Representation choices','## Baggage record revision (2026-11-25)\n\nIndividual bag loading observations in L15 and L20 now vary within the ground-handling work interval. The recorded completion of the baggage loading job is unchanged. The checked baggage records cover a sample of bags. The operation-level and individual-bag records have distinct granularity; the dictionaries describe their business meaning without specifying extraction rules. The five core tables and all schemas remain unchanged. See [revision audit](evaluation/baggage_revision_audit.json).\n\n## Representation choices')
rp.write_text(readme)
report={'seed':20261125,'old_gap_distribution':dict(Counter(old_gaps)),'new_gap_distribution':dict(sorted(Counter(new_gaps).items())),'variants':audit,'legacy_B_event_count':sum(b_reference.values()),'core_rows_unchanged':True,'schema_unchanged':True,'note':'Q03/D mutant uses legacy D activity labels. All 48 closure timestamps differ from last sampled LD; core pilot reference events unchanged.'}
(root/'evaluation/baggage_revision_audit.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS baggage revision',json.dumps(report))
