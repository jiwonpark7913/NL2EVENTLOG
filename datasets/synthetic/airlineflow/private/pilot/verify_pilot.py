"""Verify the frozen AirlineFlow pilot. Default read-only; --materialize writes Gold CSV/DFG only from matching v6 digest."""
import argparse, csv, hashlib, json, sqlite3, subprocess, shutil, re, html
from collections import Counter, defaultdict
from pathlib import Path
from strict_score import score, score_policy_c
from oracle import oracle

ROOT=Path(__file__).resolve().parent
DATASET=ROOT.parents[1]
COLS=['case_id','activity','timestamp']
CONTRACT=json.loads((ROOT/'gold_contract.json').read_text())['queries']

def dump(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def read_log(path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        assert reader.fieldnames==COLS,path
        return [tuple(row[k] for k in COLS) for row in reader]

def digest(rows):
    return hashlib.sha256(json.dumps(sorted(rows),ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def order(rows):
    return sorted(rows,key=lambda r:(r[0],r[2],r[1]))

def stats(rows):
    groups=defaultdict(lambda:defaultdict(list))
    for c,a,t in rows:groups[c][t].append(a)
    activities=Counter(a for _,a,_ in rows);nodes=Counter();edges=Counter();starts=Counter();ends=Counter();variants=Counter()
    ties=tie_groups=tie_cases=0
    for times in groups.values():
        seq=[tuple(sorted(times[t])) for t in sorted(times)]
        ties+=sum(len(x)-1 for x in seq);tie_groups+=sum(len(x)>1 for x in seq);tie_cases+=any(len(x)>1 for x in seq)
        labels=[' ∥ '.join(x) for x in seq];nodes.update(labels);starts[labels[0]]+=1;ends[labels[-1]]+=1;edges.update(zip(labels,labels[1:]));variants[tuple(seq)]+=1
    return dict(cases=len(groups),events=len(rows),activities=len(activities),activity_counts=dict(activities),variants=len(variants),singleton_cases=sum(sum(map(len,v.values()))==1 for v in groups.values()),duplicate_event_rows=len(rows)-len(set(rows)),adjacent_timestamp_ties=ties,tie_groups=tie_groups,tie_cases=tie_cases,graph_type='timestamp_bucket_dfg',nodes=dict(nodes),edges=[{'source':a,'target':b,'count':n} for (a,b),n in sorted(edges.items())],starts=dict(starts),ends=dict(ends),variant_counts=[{'timestamp_buckets':[list(x) for x in a],'count':n} for a,n in variants.most_common()])

def render_dot(st):
    ids={a:f'n{i}' for i,a in enumerate(st['nodes'])}
    q=lambda x:json.dumps(x,ensure_ascii=False)
    lines=['digraph D {','graph [rankdir=TB, bgcolor="transparent", pad=0.25, nodesep=0.35, ranksep=0.38];','node [shape=box, style="rounded,filled", color="#8ba6b6", fillcolor="#edf4f7", fontname="Arial", fontsize=11, margin="0.16,0.1"];','edge [color="#667d8b", fontname="Arial", fontsize=10, arrowsize=0.65];','start [shape=ellipse,label="Start",fillcolor="#e3f3e8"];','end [shape=ellipse,label="End",fillcolor="#f7e5e1"];']
    for a,n in st['nodes'].items():lines.append(f'{ids[a]} [label={q(a+chr(10)+str(n)+" buckets")}];')
    for a,n in st['starts'].items():lines.append(f'start -> {ids[a]} [label="{n}"];')
    for e in st['edges']:lines.append(f'{ids[e["source"]]} -> {ids[e["target"]]} [label="{e["count"]}"];')
    for a,n in st['ends'].items():lines.append(f'{ids[a]} -> end [label="{n}"];')
    return '\n'.join(lines+['}'])

def write_gold(q,rr):
    path=ROOT/'gold'/q
    with (path/'events.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(COLS);w.writerows(order(rr))
    st=stats(order(rr));dump(path/'dfg.json',st)
    dot=render_dot(st);(path/'dfg.dot').write_text(dot,encoding='utf-8')
    if shutil.which('dot'):
        svg=subprocess.run(['dot','-Tsvg'],input=dot,text=True,capture_output=True,check=True).stdout
        (path/'dfg.svg').write_text(svg[svg.index('<svg'):],encoding='utf-8')

def from_spec(c,spec):
    result=[]
    for r in spec['rules']:
        sql=(f"SELECT {r['case_expression']}, ?, {r['source_alias']}.{r['timestamp_column']} FROM {r['source_table']} {r['source_alias']} "
             +' '.join(r['joins'])+(' WHERE '+r['where'] if r['where'] else ''))
        result.extend(tuple(x) for x in c.execute(sql,(r['activity'],)))
    return result

def validate_policy(c,g):
    turn={f:t for t,f in c.execute('SELECT turn_id,outbound_id FROM turnarounds')}
    sessions={f:s for s,f in c.execute('SELECT session_id,flight_id FROM boarding_sessions')}
    for q in ['Q09','Q12']:
        gold=g[q];t=[(turn[f],a,ts) for f,a,ts in gold];s=[(sessions[f],a,ts) for f,a,ts in gold]
        assert score_policy_c(q,gold,gold,c)['primary']['exact']
        out=score_policy_c(q,gold,t,c);assert out['primary']['f1']==0 and out['turnaround_equivalent'] is True
        for bad in [t+t[:1],t[1:],[(t[0][0],t[0][1],'2000-01-01 00:00:00')]+t[1:],gold[:1]+t[1:]]:
            assert not score_policy_c(q,gold,bad,c)['turnaround_equivalent']
        res=score_policy_c(q,gold,s,c)
        assert not res['turnaround_equivalent'] and res['boarding_session_equivalent_diagnostic']==(True if q=='Q12' else None)
    assert score_policy_c('Q06',g['Q06'],[(turn[f],a,t) for f,a,t in g['Q06']],c)['turnaround_equivalent'] is None
    # A duplicate mapping (even with a declared FK) must fail closed.
    with sqlite3.connect(':memory:') as x:
        x.execute('CREATE TABLE flights(flight_id PRIMARY KEY)')
        x.execute('CREATE TABLE turnarounds(turn_id PRIMARY KEY,outbound_id REFERENCES flights(flight_id))')
        x.executemany('INSERT INTO flights VALUES (?)',[(f,) for f in turn])
        x.executemany('INSERT INTO turnarounds VALUES (?,?)',[(t,f) for f,t in turn.items()])
        x.execute('INSERT INTO turnarounds VALUES (?,?)',('duplicate-turn',next(iter(turn))))
        assert not score_policy_c('Q09',g['Q09'],[(turn[f],a,t) for f,a,t in g['Q09']],x)['turnaround_mapping_eligible']
    # Q02 posted events; strict ID, timestamp and multiplicity.
    posted=dict(c.execute('SELECT job_id,posted_at FROM handling_jobs'))
    p=g['Q02']+[(k,'Job Posted',v) for k,v in posted.items()]
    assert abs(score(g['Q02'],p)['f1']-.8)<1e-9
    p=[(k,a,posted[k] if a=='Job Complete' else t) for k,a,t in g['Q02']]
    assert abs(score(g['Q02'],p)['f1']-.5)<1e-9
    assert not score(g['Q01'],g['Q01']+g['Q01'][:1])['exact']

def validate_mutants(c,g,manifest):
    results=[]
    mutants=json.loads((ROOT/'mutants.json').read_text())
    names=set(manifest['table_rows'])
    for m in mutants:
        if not set(m.get('requires',[]))<=names:continue
        pred=[tuple(r) for r in c.execute(m['sql'])]
        result=score_policy_c(m['query_id'],g[m['query_id']],pred,c)
        assert result['primary']['exact'] is False and result['primary']['f1']<1,(m['id'],result)
        if m['id']=='M7':assert result['turnaround_equivalent'] is True
        if m['id']=='M7c':assert result['boarding_session_equivalent_diagnostic'] is True and not result['turnaround_equivalent']
        if m['id']=='M11':
            assert result['primary']['tp']==192 and result['primary']['fp']==result['primary']['fn']==48
        results.append(m['id'])
    return results

def verify(materialize=False):
    manifest=json.loads((DATASET/'evaluation/variant_manifest.json').read_text())
    registry=json.loads((DATASET/'evaluation/query_registry.json').read_text())
    model=[json.loads(line) for line in (DATASET/'evaluation/model_questions.jsonl').read_text().splitlines() if line.strip()]
    assert model==[{'question_id':q['question_id'],'text':q['question_en']} for q in registry]
    assert [q['question_id'] for q in registry]==list(CONTRACT)
    q3=next(q for q in registry if q['question_id']=='Q03')
    assert 'confirmed closure of the baggage loading operation' in q3['question_en']
    assert '수하물 적재 작업의 마감 확인' in q3['question_kr']
    page=(DATASET/'docs/scenario.html').read_text()
    for q in registry:
        match=re.search(r'<tr id="request-'+q['question_id'].lower()+r'">([\s\S]*?)</tr>',page)
        assert match and q['question_en'] in html.unescape(match[1]),q['question_id']
    assert 'Q03 wording is pending final approval' not in page
    result={};base=None
    for variant in manifest:
        ident=variant['variant_id']; p=DATASET/variant['database_path']
        assert variant['question_ids']==list(CONTRACT)
        assert variant['query_registry_version']=='v7'
        assert hashlib.sha256(p.read_bytes()).hexdigest()==variant['database_sha256']
        assert hashlib.sha256((DATASET/variant['dictionary_path']).read_bytes()).hexdigest()==variant['dictionary_sha256']
        with sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True) as c:
            c.row_factory=sqlite3.Row
            assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            assert not c.execute('PRAGMA foreign_key_check').fetchall()
            independent=oracle(c);g={}
            for q,expected in CONTRACT.items():
                d=ROOT/'gold'/q
                pi=json.loads((d/'pi.json').read_text());espec=json.loads((d/'espec.json').read_text())
                cur=c.execute((d/'gold.sql').read_text())
                assert [x[0] for x in cur.description]==COLS
                actual=[tuple(r) for r in cur]
                assert Counter(actual)==Counter(independent[q])==Counter(from_spec(c,espec)),(ident,q,'SQL/oracle/ESpec')
                assert digest(actual)==expected['multiset_sha256'],(ident,q,'Gold v6 changed')
                assert len(actual)==expected['events'] and len({r[0] for r in actual})==expected['cases']
                assert pi['expected_case_count']==expected['cases'] and pi['expected_event_count']==expected['events']
                assert set(pi['activities'])=={r[1] for r in actual}=={r['activity'] for r in espec['rules']}
                assert pi['case_identity']==espec['case_identity'] and pi['case_scope']==espec['case_scope']
                if materialize and base is None:write_gold(q,actual)
                stored=read_log(d/'events.csv')
                assert Counter(stored)==Counter(actual),(ident,q,'stored Gold')
                st=stats(order(stored))
                assert json.loads((d/'dfg.json').read_text())==st
                assert (d/'dfg.dot').read_text()==render_dot(st)
                assert (d/'dfg.svg').exists(),q
                g[q]=stored
            if base is None:base=g
            else:assert all(Counter(g[q])==Counter(base[q]) for q in g)
            assert Counter(g['Q01'])==Counter(g['Q11'])
            assert Counter(g['Q06'])==Counter(g['Q12'])
            assert Counter(g['Q09'])==Counter(r for r in g['Q06'] if r[1] in ('Off-block','Take-off'))
            validate_policy(c,g)
            mutants=validate_mutants(c,g,variant)
            result[ident]={'queries':len(g),'cases':sum(len({r[0] for r in v}) for v in g.values()),'events':sum(map(len,g.values())),'mutants':mutants,'policy_c':'PASS'}
            print(f"PASS: {ident}: {len(g)} Gold SQL/oracle/ESpec/CSV/DFG comparisons; {len(mutants)} negative controls; Policy C")
    assert len(result)==4 and len(result['l20']['mutants'])==19
    if materialize:
        with (ROOT/'gold_summary.csv').open('w',encoding='utf-8',newline='') as f:
            w=csv.writer(f);w.writerow(['query_id','cases','events','v6_multiset_sha256'])
            for q,v in CONTRACT.items():w.writerow([q,v['cases'],v['events'],v['multiset_sha256']])
        dump(ROOT/'regression_report.json',{'query_registry_version':'v7','unique_queries':12,'db_query_combinations':48,'gold_event_multisets_unchanged_from_v6':True,'variants':result})
    else:
        assert json.loads((ROOT/'regression_report.json').read_text())['variants']==result
    print('PASS: 48 DB–query Gold comparisons, all four databases, 12 unique requests; 19 L20 mutants; strict scorer and Policy C.')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--materialize',action='store_true')
    verify(p.parse_args().materialize)
