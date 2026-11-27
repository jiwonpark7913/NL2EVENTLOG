"""Read-only verification of stochastic fixture."""
from pathlib import Path
from collections import Counter
import csv,json,hashlib,sqlite3
R=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return [tuple(x[k] for k in ('case_id','activity','timestamp')) for x in csv.DictReader(f)]
manifest=read(R/'evaluation/variant_manifest.json');prev={};n=0
for v in manifest:
    p=R/v['database_path'];assert sha(p)==v['database_sha256'] and sha(R/v['dictionary_path'])==v['dictionary_sha256']
    with sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True) as c:
        assert c.execute('pragma integrity_check').fetchone()[0]=='ok' and not c.execute('pragma foreign_key_check').fetchall()
        actual={t:c.execute(f'SELECT * FROM "{t}" ORDER BY 1').fetchall() for t in v['table_rows']}
        assert all(len(actual[t])==v['table_rows'][t] for t in actual) and all(actual[t]==r for t,r in prev.items());prev=actual
        for q in v['question_ids']:
            g=R/'gold'/q;assert Counter(c.execute((g/'gold.sql').read_text()).fetchall())==Counter(rows(g/'events.csv')),(v['variant_id'],q);n+=1
assert n==108
assert sha(R/'input/database.sqlite')==next(v['database_sha256'] for v in manifest if v['variant_id']=='l15')
for a in (49,53,57):
    g=Counter(rows(R/'gold'/f'Q{a:02d}'/'events.csv'))
    assert all(g==Counter(rows(R/'gold'/f'Q{k:02d}'/'events.csv')) for k in range(a,a+4))
with sqlite3.connect((R/'input/database.sqlite').resolve().as_uri()+'?mode=ro',uri=True) as c:
    for sql in ["SELECT count(*) FROM (SELECT leg_id FROM security_visits GROUP BY leg_id HAVING count(*)>1)","SELECT count(*) FROM (SELECT leg_id FROM bag_legs GROUP BY leg_id HAVING count(*)>1)","SELECT count(*) FROM passenger_legs WHERE leg_id NOT IN (SELECT leg_id FROM passenger_actions)","SELECT count(*) FROM (SELECT leg_id FROM passenger_actions WHERE action_code='RJ' GROUP BY leg_id HAVING count(*)>1)","SELECT count(*) FROM passenger_legs l JOIN turnarounds t ON l.flight_id=t.inbound_id"]:
        assert c.execute(sql).fetchone()[0]>0
    for q in ('B01','B02','B03'):
        g=R/'semantic_check/evaluation'/q;assert Counter(c.execute((g/'gold.sql').read_text()).fetchall())==Counter(rows(g/'events.csv'))
assert any(len(rows(R/'gold'/q/'events.csv'))>len(set(rows(R/'gold'/q/'events.csv'))) for q in ('Q18','Q35','Q45'))
# Reparse embedded evidence and compare all event multisets with CSV.
html=(R/'docs/scenario.html').read_text()
payload=json.loads(html.split('const DATA=',1)[1].split(';\nconst $=',1)[0])
for q,es in payload['events'].items():
    assert Counter(tuple(e[:3]) for e in es)==Counter(rows(R/'gold'/q/'events.csv')),q
assert len(payload['events'])==72
print('PASS: 108 SQL comparisons; HTML evidence 72/72; hashes, nested data, FK, semantic families, multiplicity and population coverage. Production scorer not tested.')
