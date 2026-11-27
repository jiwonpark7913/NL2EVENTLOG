"""Publish additive operational attributes while preserving existing event occurrences."""
from pathlib import Path
import json,csv,sqlite3,hashlib,subprocess,tempfile,shutil,sys,re,html
from collections import Counter
R=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def blob(p):
    b=p.read_bytes();return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def gold(q):
    with (R/'gold'/q/'events.csv').open(encoding='utf-8-sig',newline='') as f:return Counter((r['case_id'],r['activity'],r['timestamp']) for r in csv.DictReader(f))
fields=load(R/'source/operational_fields_v1.json')
old=load(R/'source/records.json')
with tempfile.TemporaryDirectory() as t:
    out=Path(t)/'out'
    subprocess.run(['node',str(R/'source/generate_records_v2.mjs'),str(out)],check=True)
    records=load(out/'records.json');summary=load(out/'generator_summary.json')
assert set(old)==set(records)
for t,o in old.items():
    n=records[t];assert len(o['rows'])==len(n['rows'])
    inds=[n['columns'].index(c) for c in o['columns']]
    for a,b in zip(o['rows'],n['rows']):
        assert all(a[j]==b[k] or (t=='passengers' and o['columns'][j]=='display_name') for j,k in enumerate(inds)),(t,a[0])
    if t not in fields:assert o==n,t
# Additional checks over logical attributes: no fabricated activity timestamps.
T={t:[dict(zip(x['columns'],r)) for r in x['rows']] for t,x in records.items()}
def by(t,k):return {x[k]:x for x in T[t]}
tickets=by('tickets','ticket_id');bookings=by('bookings','booking_id');legs=by('passenger_legs','leg_id')
for x in T['passengers']:assert x['display_name']==x['given_name']+' '+x['family_name']
for t,col in [('bookings','record_locator'),('tickets','ticket_number'),('bag_legs','tag_license_plate')]:assert len({x[col] for x in T[t]})==len(T[t])
for t in ('tickets','bookings'):
    for x in T[t]:assert x['total_amount']==x['base_fare_amount']+x['tax_amount'] and x['currency_code']=='KRW'
from collections import defaultdict
lbase=Counter();ltax=Counter();bbase=Counter();btax=Counter();seats=set();seq=set();coupons=defaultdict(list)
for x in T['passenger_legs']:
    lbase[x['ticket_id']]+=x['segment_base_fare'];ltax[x['ticket_id']]+=x['segment_tax'];coupons[x['ticket_id']].append(x['coupon_no'])
    for col,s in [('seat_no',seats),('checkin_sequence',seq)]:
        if x[col] is not None:
            key=(x['flight_id'],x[col]);assert key not in s,key;s.add(key)
for x in T['tickets']:
    assert lbase[x['ticket_id']]==x['base_fare_amount'] and ltax[x['ticket_id']]==x['tax_amount']
    assert sorted(coupons[x['ticket_id']])==list(range(1,len(coupons[x['ticket_id']])+1))
    bbase[x['booking_id']]+=x['base_fare_amount'];btax[x['booking_id']]+=x['tax_amount']
for x in T['bookings']:assert bbase[x['booking_id']]==x['base_fare_amount'] and btax[x['booking_id']]==x['tax_amount']
checkpoints=by('checkpoints','checkpoint_id')
for v in T['security_visits']:assert v['lane_no'] is None or 1<=v['lane_no']<=checkpoints[v['checkpoint_id']]['lane_count']
for x in T['flight_dispatch']:assert x['planned_fuel_kg']>=x['minimum_fuel_kg'] and x['origin']!=x['destination']
manifest=load(R/'evaluation/variant_manifest.json')
std=load(R/'evaluation/dictionary_review/standard_manifest.json')
prev={};conditions=0
for v in manifest:
    l=v['variant_id'];p=R/v['database_path'];ddl=p.with_name('schema.sql')
    original=load(R/v['dictionary_path']);standard=load(p.with_name('data_dictionary_standard.json'))
    # Rebuild schema deterministically: append declarations inside original CREATE TABLE, before table constraints.
    text=ddl.read_text().split('-- Operational attributes v1',1)[0].rstrip()+'\n'
    for t in v['table_rows']:
        if t not in fields:continue
        for name,decl,desc in fields[t]:
            for dictionary in (original,standard):
                dictionary[t]['columns'][name]={'declaration':decl,'description':desc}
    # SQLite ALTER cannot add NOT NULL without a default on nonempty tables; use inline definitions in fresh DDL.
    for t in v['table_rows']:
        if t not in fields:continue
        pattern=r'(CREATE TABLE '+re.escape(t)+r' \()(.*?)(\);)'
        def add(m):
            body=m.group(2)
            if all(re.search(r'\b'+re.escape(n)+r'\b',body) for n,_,_ in fields[t]):return m.group(0)
            split=re.search(r',\s*(?:UNIQUE|CHECK|PRIMARY KEY|FOREIGN KEY)\s*\(',body)
            i=split.start() if split else len(body)
            return m.group(1)+body[:i]+', '+', '.join(n+' '+d for n,d,_ in fields[t])+body[i:]+m.group(3)
        text,n=re.subn(pattern,add,text,count=1,flags=re.S);assert n==1,t
    if l!='l05':
        ddl.write_text(text,encoding='utf-8');save(R/v['dictionary_path'],original);save(p.with_name('data_dictionary_standard.json'),standard)
        p.unlink()
        with sqlite3.connect(p) as c:
            c.execute('PRAGMA foreign_keys=ON');c.executescript(text)
            for t in v['table_rows']:
                rec=records[t];c.executemany('INSERT INTO '+t+' ('+','.join(rec['columns'])+') VALUES ('+','.join('?' for _ in rec['columns'])+')',rec['rows'])
    with sqlite3.connect(p) as c:
        assert c.execute('pragma integrity_check').fetchone()[0]=='ok' and not c.execute('pragma foreign_key_check').fetchall()
        actual={t:c.execute('SELECT * FROM '+t+' ORDER BY 1').fetchall() for t in v['table_rows']}
        assert all(actual[t]==r for t,r in prev.items());prev=actual
        for t in actual:
            assert [x[1] for x in c.execute('pragma table_info('+t+')')]==records[t]['columns']
            assert list(original[t]['columns'])==records[t]['columns'] and list(standard[t]['columns'])==records[t]['columns']
        for q in v['question_ids']:
            assert Counter(c.execute((R/'gold'/q/'gold.sql').read_text()).fetchall())==gold(q),(l,q)
            conditions+=1
    v['database_sha256']=sha(p);v['dictionary_sha256']=sha(R/v['dictionary_path']);v['schema_revision']='operational-v1'
    sm=next(x for x in std['variants'] if x['variant_id']==l)
    sm.update(original_git_blob_sha=blob(R/v['dictionary_path']),standard_git_blob_sha=blob(p.with_name('data_dictionary_standard.json')),database_git_blob_sha=blob(p))
    # ERD from actual dictionary and declared FK metadata, preserving layer colors.
    if l!='l05':
        colors=['#cbe6ff','#d9efdc','#ffe8b9','#e7dbfa'];layer={}
        for i,sv in enumerate(manifest):
            for t in sv['table_rows']:layer.setdefault(t,i)
        lines=['digraph ER {','graph [rankdir=LR,bgcolor="white",pad=0.2,nodesep=0.35,ranksep=0.7]; node [shape=plain,fontname="Arial"]; edge [color="#748695",fontsize=9,fontname="Arial"];']
        for t,entry in original.items():
            cells=[f'<TR><TD COLSPAN="2" BGCOLOR="{colors[layer[t]]}"><B>{html.escape(t)}</B></TD></TR>']
            for col,d in entry['columns'].items():
                decl=d['declaration'];key='PK' if 'PRIMARY KEY' in decl else 'FK' if 'REFERENCES' in decl else ''
                cells.append(f'<TR><TD BGCOLOR="#f1f5f8">{key}</TD><TD ALIGN="LEFT" PORT="{col}">{html.escape(col)}</TD></TR>')
            lines.append(t+' [label=<<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">'+''.join(cells)+'</TABLE>>];')
        with sqlite3.connect(p) as c:
            for t in original:
                for fk in c.execute('pragma foreign_key_list('+t+')'):
                    lines.append(f'{t}:{fk[3]} -> {fk[2]}:{fk[4]} [label="{fk[3]}"];')
        lines.append('}')
        subprocess.run(['dot','-Tsvg','-o',str(p.parent.parent/'docs/schema.svg')],input='\n'.join(lines),text=True,check=True)
assert conditions==108
std['edition']='standard-v1-operational-v1';std['base_commit']='operational-v1 schema revision';save(R/'evaluation/dictionary_review/standard_manifest.json',std)
save(R/'source/records.json',records);save(R/'source/stochastic_v2_generator_preview.json',summary);save(R/'evaluation/variant_manifest.json',manifest)
shutil.copy2(R/'variants/l15/input/database.sqlite',R/'input/database.sqlite')
for file in ('schema.sql','data_dictionary.json','data_dictionary_standard.json'):
    target=R/'input'/file
    if target.exists():shutil.copy2(R/'variants/l15/input'/file,target)
p=R/'docs/scenario.html';head,tail=p.read_text().split('const DATA=',1);payload,end=tail.split(';\nconst $=',1)
d=json.loads(payload);d['records']=records;d['manifest']=manifest;d['summary']=summary;d['dictionaries']={v['variant_id']:load(R/v['dictionary_path']) for v in manifest};d['schema_revision']='operational-v1'
p.write_text(head+'const DATA='+json.dumps(d,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')+';\nconst $='+end,encoding='utf-8')
receipt=load(R/'evaluation/verification.json');receipt['generator_summary']=summary
receipt['operational_schema']={'revision':'operational-v1','status':'PASS','tables_extended':15,'columns_added':sum(len(x) for x in fields.values()),'old_column_projection':'unchanged except fictional passenger display_name','gold_sql_conditions':conditions,'first_five_tables':'unchanged','new_event_timestamps':0}
save(R/'evaluation/verification.json',receipt)
save(R/'docs/dataset_statistics.json',json.loads(subprocess.check_output([sys.executable,str(R/'docs/analyze_dataset.py')],text=True)))
subprocess.run([sys.executable,str(R/'docs/render_readme.py')],check=True)
print('PASS: 15 operational tables enriched, 108 Gold SQL comparisons, nested schemas, dictionary columns, financial sums, seat/sequence uniqueness and source projections.')
