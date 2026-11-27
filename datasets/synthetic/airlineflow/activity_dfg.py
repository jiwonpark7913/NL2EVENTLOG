"""Rebuild activity-level, strict-time adjacency graphs; never edit canonical Gold."""
from pathlib import Path
from collections import Counter,defaultdict
from itertools import groupby
import csv,json,subprocess,xml.etree.ElementTree as ET,hashlib
R=Path(__file__).resolve().parent
p=R/'docs/scenario.html'
old=p.read_text(encoding='utf-8')
prefix='const DATA='; suffix=';\nconst $='
head,tail=old.split(prefix,1);payload,end=tail.split(suffix,1)
data=json.loads(payload)
with (R/'evaluation/query_registry.csv').open(encoding='utf-8-sig',newline='') as f:registry=list(csv.DictReader(f))
assert data['registry']==registry
assert len(registry)==72
def non_graph_hash(d):
    return hashlib.sha256(json.dumps({**d,'queries':{q:{k:v for k,v in m.items() if k!='dfg'} for q,m in d['queries'].items()}},sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
before=non_graph_hash(data)
audit=[]
ns={'s':'http://www.w3.org/2000/svg'}
for r in registry:
    q=r['QUERY ID'];g=R/'gold'/q;m=data['queries'][q]
    with (g/'events.csv').open(encoding='utf-8-sig',newline='') as f:
        rows=[(x['case_id'],x['activity'],x['timestamp']) for x in csv.DictReader(f)]
    assert Counter(rows)==Counter(tuple(e[:3]) for e in data['events'][q]),(q,'HTML Gold stale')
    assert m['query']==r['QUERY (EN / KR)'],(q,'HTML query stale')
    assert m['pi']==json.loads((g/'pi.json').read_text()) and m['espec']==json.loads((g/'espec.json').read_text()) and m['sql']==(g/'gold.sql').read_text(),(q,'HTML reference stale')
    nodes=Counter(a for c,a,t in rows);edges=Counter();traces=defaultdict(lambda:defaultdict(Counter))
    for c,a,t in rows:traces[c][t][a]+=1
    ties=0;tie_groups=0;variants=Counter()
    for times in traces.values():
        buckets=[times[t] for t in sorted(times)]
        ties+=any(sum(x.values())>1 for x in buckets)
        tie_groups+=sum(sum(x.values())>1 for x in buckets)
        variants[tuple(tuple(sorted(x.elements())) for x in buckets)]+=1
        for a,n in buckets[0].items():edges['Start',a]+=n
        for left,right in zip(buckets,buckets[1:]):
            for a,n in left.items():
                for z,k in right.items():edges[a,z]+=n*k
        for a,n in buckets[-1].items():edges[a,'End']+=n
    assert set(nodes)==set(r['EXPECTED ACTIVITIES'].split('; '))==set(m['pi']['activities'])=={x['activity'] for x in m['espec']['rules']}
    assert len(nodes)==int(r['ACT COUNT'])==m['activity_count'] and sum(nodes.values())==int(r['EXPECTED EVENT COUNT'])==m['events']
    assert len(traces)==int(r['EXPECTED CASE COUNT'])==m['cases'] and ties==m['ties'] and len(variants)==m['variants']
    # Independent occurrence-level reconstruction (not aggregated multiplication).
    expected=Counter()
    ordered=sorted(rows,key=lambda x:(x[0],x[2],x[1]))
    for c,trace in groupby(ordered,key=lambda x:x[0]):
        prev=['Start']
        for t,batch in groupby(trace,key=lambda x:x[2]):
            curr=[x[1] for x in batch]
            expected.update((a,z) for a in prev for z in curr)
            prev=curr
        expected.update((a,'End') for a in prev)
    assert edges==expected,(q,'edge counts')
    ids={'Start':'start','End':'end',**{a:'n'+str(i) for i,a in enumerate(sorted(nodes))}}
    assert len(ids)==len(nodes)+2
    lines=['digraph G {','rankdir=LR; graph [bgcolor="white",pad=0.2,nodesep=0.35,ranksep=0.6]; node [shape=box,style="rounded,filled",fillcolor="#eaf2f6",color="#607b8b",fontname="Arial",fontsize=11]; edge [color="#728899",fontname="Arial",fontsize=10];','start [label="Start",shape=oval,fillcolor="#e1f2e7"]; end [label="End",shape=oval,fillcolor="#f7e4e4"];']
    for a,n in sorted(nodes.items()):lines.append(f'{ids[a]} [label={json.dumps(a+chr(10)+str(n),ensure_ascii=False)}];')
    for (a,z),n in sorted(edges.items()):lines.append(f'{ids[a]} -> {ids[z]} [label="{n}"];')
    lines.append('}')
    dot='\n'.join(lines)+'\n'
    (g/'dfg.dot').write_text(dot,encoding='utf-8')
    subprocess.run(['dot','-Tsvg',str(g/'dfg.dot'),'-o',str(g/'dfg.svg')],check=True)
    svg=(g/'dfg.svg').read_text();xml=ET.fromstring(svg);back={v:k for k,v in ids.items()}
    sn=Counter();se=Counter();endpoints=set()
    for group in xml.findall('.//s:g',ns):
        kind=group.get('class');title=group.find('s:title',ns)
        if title is None:continue
        ident=title.text;labels=[''.join(x.itertext()) for x in group.findall('s:text',ns)]
        if kind=='node':
            if ident in ('start','end'):endpoints.add(ident);continue
            assert len(labels)==2 and labels[0]==back[ident],(q,ident,labels)
            sn[labels[0]]+=int(labels[1])
        elif kind=='edge':
            a,z=ident.split('->');assert len(labels)==1,(q,ident,labels)
            se[back[a],back[z]]+=int(labels[0])
    assert sn==nodes and se==expected and endpoints=={'start','end'},(q,'SVG mismatch')
    m['dfg']=svg
    audit.append(dict(query_id=q,activities=len(nodes),activity_nodes=len(sn),start_end_nodes=2,total_nodes=len(sn)+2,events=sum(nodes.values()),tie_cases=ties,tie_groups=tie_groups,edges=len(edges),status='PASS'))
assert non_graph_hash(data)==before,'non-graph payload changed'
p.write_text(head+prefix+json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')+suffix+end,encoding='utf-8')
with (R/'evaluation/dfg_consistency_audit.csv').open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(audit[0]));w.writeheader();w.writerows(audit)
receipt=R/'evaluation/verification.json';v=json.loads(receipt.read_text())
v['activity_dfg']={'status':'PASS','queries':len(audit),'policy':'one node per activity; adjacent distinct timestamp groups, occurrence-pair counts; no within-tie edge','non_graph_payload_sha256':before,'query_gold_pi_espec_sql_html_match':True,'node_and_edge_svg_checks':True}
receipt.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
print('PASS: 72/72 query, PI, ESpec, SQL, CSV and HTML match; 72/72 activity-level SVG node/edge checks; non-graph payload unchanged.')
