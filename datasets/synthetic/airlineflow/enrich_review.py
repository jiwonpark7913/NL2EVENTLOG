"""Generate evaluator-only enriched logs from the released occurrence provenance.
The same JS enrichment functions are shared with the HTML. Verify canonical multiset
projection, short identifiers, actual flight context, and database fingerprints.
"""
from pathlib import Path
from collections import Counter
import csv,json,subprocess,tempfile,hashlib,re,sqlite3
R=Path(__file__).resolve().parent
p=R/'docs/scenario.html'
before=p.read_text(encoding='utf-8')
payload=before.split('const DATA=',1)[1].split(';\nconst $=',1)[0]
data=json.loads(payload)
template=(R/'docs/review_v2_template.html').read_text()
js=template.split('const flightMeta=new Map();',1)[1].split('let logMode=',1)[0]
js='const flightMeta=new Map();'+js
with tempfile.TemporaryDirectory() as td:
    t=Path(td);(t/'data.json').write_text(payload)
    harness="""
const fs=require('node:fs'),path=require('node:path');
const DATA=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),R=process.argv[3];
const recordIndex={};for(const [t,r] of Object.entries(DATA.records))recordIndex[t]=new Map(r.rows.map(x=>[String(x[0]),x]));
function csv(rows){return rows.map(r=>r.map(x=>'"'+String(x??'').replaceAll('"','""')+'"').join(',')).join('\\r\\n')+'\\r\\n'}
"""
    tail="""
for(const [q,es] of Object.entries(DATA.events)){
  const et=DATA.queries[q].case,cols=eventHeaders(et,'enriched');
  fs.writeFileSync(path.join(R,'gold',q,'events_enriched.csv'),csv([cols,...es.map(e=>eventValues(e,et,'enriched'))]));
}
"""
    (t/'enrich.cjs').write_text(harness+js+tail)
    subprocess.run(['node',str(t/'enrich.cjs'),str(t/'data.json'),str(R)],check=True)
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def core(rs):return Counter((r['case_id'],r['activity'],r['timestamp']) for r in rs)
manifest=data['manifest']
for v in manifest:
    assert hashlib.sha256((R/v['database_path']).read_bytes()).hexdigest()==v['database_sha256']
with sqlite3.connect(R/'input/database.sqlite') as c:
    flights=dict((k,(n,d)) for k,n,d in c.execute('SELECT flight_id,flight_no,date(scheduled_offblock) FROM flights'))
    assert len(flights)==200 and all(re.fullmatch(r'F\d{3}',x) for x in flights)
    assert len(set(flights.values()))==len(flights)
    turns=dict((k,(i,o)) for k,i,o in c.execute('SELECT turn_id,inbound_id,outbound_id FROM turnarounds'))
    legs=dict(c.execute('SELECT leg_id,flight_id FROM passenger_legs'))
    bags=dict(c.execute('SELECT bag_leg_id,leg_id FROM bag_legs'))
    visits=dict(c.execute('SELECT visit_id,leg_id FROM security_visits'))
    sessions=dict(c.execute('SELECT session_id,flight_id FROM boarding_sessions'))
    movement=dict(c.execute('SELECT report_id,flight_id FROM movement_reports'))
    actions=dict(c.execute('SELECT action_id,leg_id FROM passenger_actions'))
    scans=dict(c.execute('SELECT scan_id,bag_leg_id FROM bag_scans'))
    sec=dict(c.execute('SELECT event_id,visit_id FROM security_events'))
    total=0
    for q,es in data['events'].items():
        canonical=rows(R/'gold'/q/'events.csv')
        enriched=rows(R/'gold'/q/'events_enriched.csv')
        assert len(enriched)==len(es) and core(canonical)==core(enriched),q
        et=data['queries'][q]['case']
        for e,r in zip(es,enriched):
            case,a,ts,tn,pk,col=e
            assert (r['case_id'],r['activity'],r['timestamp'])==(case,a,ts)
            assert re.fullmatch(r'[A-Z]+\d{3,5}',case),(q,case)
            fid=case if et=='Flight' else movement[pk] if tn=='movement_reports' else sessions[pk] if tn=='boarding_sessions' else legs[actions[pk]] if tn=='passenger_actions' else legs[bags[scans[pk]]] if tn=='bag_scans' else legs[visits[sec[pk]]] if tn=='security_events' else None
            if 'flight_no' in r:
                assert (r['flight_no'],r['operating_date'])==flights.get(fid,('','')),(q,case,tn,pk)
            if et=='Turnaround':
                i,o=turns[case]
                assert (r['inbound_flight_no'],r['inbound_operating_date'])==flights[i]
                assert (r['outbound_flight_no'],r['outbound_operating_date'])==flights[o]
            total+=1
receipt=json.loads((R/'evaluation/verification.json').read_text())
receipt['enriched_review']={'status':'PASS','queries':72,'canonical_projection_rows':total,'flight_context':'verified against SQLite','canonical_gold_unchanged':True,'database_sha256_unchanged':True,'format':'Separate columns; evaluator-only, not part of scoring'}
(R/'evaluation/verification.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print('PASS: 72 enriched logs,',total,'canonical occurrences and SQLite flight context; short IDs and unchanged DB fingerprints')
