"""Read-only, stdlib-only verification of the revised frozen fixture and reference logs."""
from pathlib import Path
from collections import Counter
import sqlite3,csv,json,hashlib
from normalize_case_keys import evaluate,strict_score
R=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text())
def events(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return [tuple(r[k] for k in ('case_id','activity','timestamp')) for r in csv.DictReader(f)]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prev={};n=0;legacy=0
for v in read(R/'evaluation/variant_manifest.json'):
 p=R/v['database_path'];assert sha(p)==v['database_sha256'] and sha(R/v['dictionary_path'])==v['dictionary_sha256']
 with sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True) as c:
  assert c.execute('pragma integrity_check').fetchone()[0]=='ok' and not c.execute('pragma foreign_key_check').fetchall()
  actual={t:c.execute(f'SELECT * FROM "{t}" ORDER BY 1').fetchall() for t in v['table_rows']};assert all(len(actual[t])==v['table_rows'][t] for t in actual);assert all(actual[t]==r for t,r in prev.items());prev=actual
  for q in v['question_ids']:
   g=R/'gold'/q;assert Counter(c.execute((g/'gold.sql').read_text()).fetchall())==Counter(events(g/'events.csv'));n+=1
  for q in {'l05':'TD','l10':'TDP','l15':'TDPSB','l20':'TDPSB'}[v['variant_id']]:
   assert Counter(c.execute((R/f'private/{q}.sql').read_text()).fetchall())==Counter(events(R/f'private/{q}_events.csv'));legacy+=1
assert n==108 and legacy==15
with sqlite3.connect(R/'input/database.sqlite') as c:
 def get(q):return events(R/f'gold/{q}/events.csv')
 for q,et,columns,sql in [('Q18','Flight',('flight_no','operating_date'),'select flight_id,flight_no,date(scheduled_offblock) from flights'),('Q59','Passenger Leg',('passenger_id','flight_id'),'select l.leg_id,t.passenger_id,l.flight_id from passenger_legs l join tickets t using(ticket_id)'),('Q59','Passenger Leg',('ticket_id','flight_id'),'select leg_id,ticket_id,flight_id from passenger_legs'),('Q49','Bag Leg',('bag_tag','flight_id'),'select b.bag_leg_id,b.bag_tag,l.flight_id from bag_legs b join passenger_legs l using(leg_id)')]:
  g=get(q);d={r[0]:tuple(r[1:]) for r in c.execute(sql)};p=[(d[k],a,t) for k,a,t in g];assert evaluate(c,q,g,p,et,et,columns)['primary']['exact'];assert not evaluate(c,q,g,p+p[:1],et,et,columns)['primary']['exact']
 for q,et,other,key,sql in [('Q09','Flight','Turnaround','turn_id','select outbound_id,turn_id from turnarounds'),('Q12','Flight','Boarding Session','session_id','select flight_id,session_id from boarding_sessions'),('Q51','Bag Leg','Bag','bag_tag','select bag_leg_id,bag_tag from bag_legs'),('Q55','Security Visit','Passenger Leg','leg_id','select visit_id,leg_id from security_visits')]:
  g=get(q);d=dict(c.execute(sql));p=[(d[k],a,t) for k,a,t in g];res=evaluate(c,q,g,p,et,other,(key,));assert not res['primary']['exact'] and (res['secondary_exact'] or res['diagnostic_exact']);assert not evaluate(c,q,g,p[:-1],et,other,(key,))['secondary_exact']
 # Multiplicity must remain meaningful even where the revised fixture has few exact ties.
 g=get('Q18');assert not strict_score(g,list(set(g)))['exact'];assert strict_score(g,g)['exact']
 assert len(get('Q57'))==1488 and all(Counter(get('Q57'))==Counter(get(q)) for q in ['Q58','Q59','Q60'])
print('PASS: 108 current DB-query comparisons; 15 legacy; nested rows, checksums and FK; structured key policy; Policy C/secondary; multiplicity; D-F3.')
# Semantic-DD revision: check evidence isolation and diagnostic ground truth.
full=read(R/'input/data_dictionary.json'); reduced=read(R/'semantic_check/input/data_dictionary_reduced.json')
assert 'B204' in full['bag_scans']['columns']['scan_code']['description']
assert 'B204' not in (R/'semantic_check/input/data_dictionary_reduced.json').read_text()
full['bag_scans']['columns']['scan_code']['description']=reduced['bag_scans']['columns']['scan_code']['description'];assert full==reduced
with sqlite3.connect(R/'input/database.sqlite') as c:
 assert dict(c.execute('SELECT scan_code,count(*) FROM bag_scans GROUP BY scan_code'))=={'B101':144,'B204':144}
 import re
 ids=[r[0] for r in c.execute('SELECT scan_id FROM bag_scans')];assert len(set(ids))==288 and all(re.fullmatch(r'SC-[0-9]{6}',x) for x in ids)
 with (R/'semantic_check/evaluation/scan_id_mapping.csv').open(newline='') as f:
  maps=list(csv.DictReader(f))
 assert len({r['old_scan_id'] for r in maps})==len({r['new_scan_id'] for r in maps})==288
 assert Counter(c.execute('SELECT scan_id,bag_leg_id,scan_code,scanned_at FROM bag_scans').fetchall())==Counter((r['new_scan_id'],r['bag_leg_id'],r['new_code'],r['scanned_at']) for r in maps)
 for q in ['B01','B02','B03']:
  p=R/'semantic_check/evaluation'/q;assert Counter(c.execute((p/'gold.sql').read_text()).fetchall())==Counter(events(p/'events.csv'))
  assert read(p/'expected.json')['reduced_dd']==('unresolved' if q=='B03' else 'extract')
print('PASS: Full/Reduced DD isolation, opaque ID mapping, 3 diagnostic reference logs and expected statuses.')
