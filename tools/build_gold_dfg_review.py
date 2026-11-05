"""Build evaluation-only query + Gold DFG review pages; never modifies model inputs."""
import argparse
import csv
import hashlib
import html
import json
import math
import re
import subprocess
import textwrap
import zipfile
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'review/gold_dfg'
DATASETS = ('warehouseflow','warehouseflow_new','universityflow','plateflow','hospitalflow','plateflow_new')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def input_snapshot():
    return {str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/'datasets').glob('*/input/**/*')) if p.is_file()}


def loadjl(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()]


def identity(q):
    return q.get('question_id',q.get('id'))



def dataset_overview(name, questions):
    rows = []
    for q in questions:
        ident = identity(q)
        typ = q['question_type']
        question = html.escape(q.get('text', q.get('question')))
        anchor = f'{ident.lower()}--{typ.lower()}'
        rows.append(f'<tr><td><a href="#{anchor}">{ident}</a></td><td>{typ}</td><td>{question}</td></tr>')

    dataset = f'../../../datasets/{name}'
    schema = (
        f'<h3>Database schema</h3><p><a href="{dataset}/docs/schema.png">'
        f'<img src="{dataset}/docs/schema.png" alt="{name} database schema"></a></p>'
        f'<p><a href="{dataset}/docs/schema.png">Full-size diagram</a> · '
        f'<a href="{dataset}/input/schema.sql">Full SQL schema</a></p>'
    )
    provenance = ''
    generators = {'hospitalflow': 'simulation.py', 'universityflow': 'build.py'}
    if name in generators:
        provenance = (
            f'Row examples in this review come from the [synthetic dataset generator]'
            f'({dataset}/{generators[name]}).\n\n'
        )
    return (
        '\n## Dataset overview\n\n'
        f'[Full DB schema]({dataset}/docs/schema_overview.md) · '
        f'[Full-size ER diagram]({dataset}/docs/schema.png) · '
        f'[SQL DDL]({dataset}/input/schema.sql)\n\n'
        f'{provenance}'
        f'<details><summary>Show all {len(rows)} questions and the schema preview</summary>\n\n'
        f'<table><tr><td width="50%" valign="top"><h3>All questions ({len(rows)})</h3>'
        '<table><thead><tr><th>ID</th><th>Type</th><th>Question</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></td>'
        f'<td width="50%" valign="top">{schema}</td></tr></table>\n\n</details>\n'
    )

def stamp(s):
    return datetime.fromisoformat(s.replace('Z','+00:00'))


def extract(rows):
    bycase = defaultdict(list)
    for index,r in enumerate(rows):
        bycase[r['case_id']].append((index,r))
    nodes, edges, starts, ends, ambiguous = Counter(),Counter(),Counter(),Counter(),Counter()
    ties, traces, positions = 0,[],defaultdict(list)
    for cid,entries in sorted(bycase.items()):
        ordered = [r for _,r in sorted(entries,key=lambda ir:(stamp(ir[1]['timestamp']),ir[1]['event_id'],ir[0]))]
        times = Counter(r['timestamp'] for r in ordered)
        ties += sum(n>1 for n in times.values())
        starts[ordered[0]['activity']] += 1; ends[ordered[-1]['activity']] += 1
        for i,r in enumerate(ordered):
            nodes[r['activity']] += 1
            positions[r['activity']].append(i/max(1,len(ordered)-1))
        for a,b in zip(ordered,ordered[1:]):
            edge = a['activity'],b['activity'];edges[edge] += 1
            if times[a['timestamp']]>1 or times[b['timestamp']]>1:
                ambiguous[edge] += 1
        traces.append(dict(case_id=cid,events=ordered))
    return dict(nodes=nodes,edges=edges,starts=starts,ends=ends,ambiguous=ambiguous,tied_timestamp_groups=ties,traces=traces,positions=positions)


def layout(names, edges, positions):
    """Deterministic layout only; positions do not assert causal/process order."""
    import numpy as np
    n = len(names)
    if n==1:
        return {names[0]:(220,170)},440,330
    rng = np.random.default_rng(42)
    index = {a:i for i,a in enumerate(names)}
    xy = rng.uniform(-1,1,(n,2))
    target = np.array([sum(positions[a])/len(positions[a]) for a in names])
    xy[:,0] = (target-.5)*3
    adjacency = np.zeros((n,n))
    for (a,b),count in edges.items():
        if a!=b:
            adjacency[index[a],index[b]] += 1+math.log1p(count)*.1
    adjacency = np.maximum(adjacency,adjacency.T)
    k = 1.3
    for step in range(500):
        delta = xy[:,None,:]-xy[None,:,:]
        dist = np.maximum(np.linalg.norm(delta,axis=2),.05)
        force = (delta*(k*k/(dist**2))[:,:,None]).sum(axis=1)
        force -= (delta*(adjacency*dist/k)[:,:,None]).sum(axis=1)
        force[:,0] += ((target-.5)*4-xy[:,0])*.25
        force -= xy*.02
        norm = np.maximum(np.linalg.norm(force,axis=1),1)
        xy += force/norm[:,None]*(.12*(1-step/500)+.005)
    # Keep node boxes disjoint; all edges remain present.
    xy[:,0] *= 210;xy[:,1] *= 150
    for step in range(300):
        moved = False
        for i in range(n):
            for j in range(i):
                dx,dy = xy[i]-xy[j]
                ox,oy = 285-abs(dx),130-abs(dy)
                if ox>0 and oy>0:
                    axis = 0 if ox/285<oy/130 else 1
                    shift = (ox if axis==0 else oy)/2+.5
                    direction = 1 if (dx if axis==0 else dy)>=0 else -1
                    xy[i,axis] += direction*shift;xy[j,axis] -= direction*shift;moved = True
        if not moved:
            break
    xy -= xy.min(axis=0);xy += [210,180]
    width,height = max(550,float(xy[:,0].max()+210)),max(380,float(xy[:,1].max()+200))
    return {a:tuple(xy[i]) for i,a in enumerate(names)},width,height


def graph_svg(d):
    names = sorted(d['nodes'])
    if not names:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="160"><text x="30" y="80">No observed events</text></svg>'
    xy,width,height = layout(names,d['edges'],d['positions'])
    esc = html.escape
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" width="{width:.0f}" height="{height:.0f}" role="img" aria-label="Gold directly follows graph">', '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#66778c"/></marker></defs>',f'<rect width="{width}" height="{height}" fill="#fff"/>']
    for (a,b),count in sorted(d['edges'].items()):
        x1,y1 = xy[a];x2,y2 = xy[b]
        color = '#b16b0a' if d['ambiguous'][(a,b)] else '#66778c'
        dash = 'stroke-dasharray="8 5"' if d['ambiguous'][(a,b)] else ''
        thickness = 1.2+min(4,math.log1p(count)*.7)
        if a==b:
            path=f'M {x1+85} {y1-51} C {x1+210} {y1-165}, {x1-80} {y1-165}, {x1-60} {y1-52}'
            lx,ly=x1+40,y1-132
        else:
            dx,dy=x2-x1,y2-y1
            scale=max(abs(dx)/130,abs(dy)/52)
            sx,sy=x1+dx/scale,y1+dy/scale;ex,ey=x2-dx/scale,y2-dy/scale
            norm=max(1,math.hypot(dx,dy));bend=38 if (b,a) in d['edges'] else 0
            cx,cy=(sx+ex)/2-dy/norm*bend,(sy+ey)/2+dx/norm*bend
            path=f'M {sx} {sy} Q {cx} {cy}, {ex} {ey}'
            lx,ly=(sx+2*cx+ex)/4,(sy+2*cy+ey)/4
        svg += [f'<g data-source="{esc(a,quote=True)}" data-target="{esc(b,quote=True)}" data-edge="{esc(a+" → "+b,quote=True)}"><title>{esc(a)} → {esc(b)}: {count} transitions; {d["ambiguous"][(a,b)]} touch a timestamp tie</title><path d="{path}" fill="none" stroke="{color}" stroke-width="{thickness}" {dash} marker-end="url(#arr)"/>',f'<rect x="{lx-10-len(str(count))*5}" y="{ly-18}" width="{20+len(str(count))*10}" height="24" rx="4" fill="white"/><text x="{lx}" y="{ly}" text-anchor="middle" font-family="Arial,sans-serif" font-size="18" font-weight="700" fill="{color}">{count}</text></g>']
    for a in names:
        x,y=xy[a];lines=textwrap.wrap(a,width=26)
        fill = '#e8f2fc' if d['starts'][a] else '#f4f7fb'
        stroke = '#438a65' if d['ends'][a] else '#345b80'
        svg += [f'<g data-activity="{esc(a,quote=True)}"><title>{esc(a)}: {d["nodes"][a]} events; starts {d["starts"][a]}, ends {d["ends"][a]}</title><rect x="{x-130}" y="{y-52}" width="260" height="104" rx="12" fill="{fill}" stroke="{stroke}" stroke-width="2"/>']
        for j,line in enumerate(lines):
            svg.append(f'<text x="{x}" y="{y-22+(j-(len(lines)-1)/2)*18}" text-anchor="middle" font-family="Arial,sans-serif" font-size="16" font-weight="600" fill="#18344e">{esc(line)}</text>')
        svg.append(f'<text x="{x}" y="{y+28}" text-anchor="middle" font-family="Arial,sans-serif" font-size="14" fill="#486072">events {d["nodes"][a]} · start {d["starts"][a]} · end {d["ends"][a]}</text></g>')
    svg.append('</svg>')
    return ''.join(svg)


STYLE='''body{font:16px system-ui,sans-serif;background:#f1f5f9;color:#172b43;margin:0}header{background:#142e48;color:white;padding:28px 4vw}header p{max-width:1100px;line-height:1.6}main{max-width:1500px;margin:auto;padding:24px}nav{position:sticky;top:0;background:#fff;padding:14px;z-index:2;border-bottom:1px solid #cbd5e1;display:flex;gap:16px;flex-wrap:wrap}input,select,button,textarea{font:inherit;padding:8px;border:1px solid #aab9c9;border-radius:6px}article{background:white;border:1px solid #d6e0eb;border-radius:12px;margin:24px 0;padding:24px}h2{margin-top:0}.question{font-size:21px;line-height:1.5;background:#eef5fc;padding:18px;border-left:5px solid #367fb6}.stats{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}.stats span{background:#edf2f7;padding:8px 12px;border-radius:8px}.graph{overflow:auto;border:1px solid #dfe5ed;max-height:900px;resize:vertical}.graph svg{display:block;max-width:none}.warning{color:#8c4f05;background:#fff4df;padding:12px}.note{display:flex;gap:12px;flex-wrap:wrap;margin-top:18px}.note textarea{flex:1;min-width:300px}table{border-collapse:collapse;font-size:14px;margin:12px 0}td,th{border:1px solid #d0dae4;padding:7px;text-align:left}summary{cursor:pointer;padding:10px;font-weight:600}a{color:#2367a4}.muted{color:#5e7084}.trace{overflow:auto;max-height:700px}code{font-family:monospace}article[hidden]{display:none}'''
STYLE += '.review-split{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px}.review-split .graph svg{width:100%;height:auto}.source-panel{min-width:0;max-height:900px;overflow:auto;padding:0 12px;background:#f7fafc;border:1px solid #dfe5ed}.source-scroll{overflow:auto}.source-scroll td{white-space:nowrap}@media(max-width:800px){.review-split{grid-template-columns:1fr}}'
SCRIPT='''const DATA=__DATA__;const KEY=__KEY__;let notes={};try{notes=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}function save(id,status,note){notes[id]={status,note};try{localStorage.setItem(KEY,JSON.stringify(notes))}catch(e){}}document.querySelectorAll('article').forEach(el=>{const id=el.dataset.id;const s=el.querySelector('select.review-status'),n=el.querySelector('textarea');const focus=el.querySelector('select.focus');if(focus){focus.onchange=()=>{const a=focus.value,near=new Set([a]);el.querySelectorAll('[data-source]').forEach(g=>{const active=!a||g.dataset.source===a||g.dataset.target===a;g.style.display=active?'':'none';if(active){near.add(g.dataset.source);near.add(g.dataset.target)}});el.querySelectorAll('[data-activity]').forEach(g=>g.style.opacity=!a||near.has(g.dataset.activity)?'1':'.1')}}if(notes[id]){s.value=notes[id].status;n.value=notes[id].note}s.onchange=n.oninput=()=>save(id,s.value,n.value)});function filter(){const q=document.querySelector('#search').value.toLowerCase(),pairs=document.querySelector('#pairs').checked;let count=0;document.querySelectorAll('article').forEach(el=>{el.hidden=(!pairs&&['Q2','Q4'].includes(el.dataset.type))||!el.textContent.toLowerCase().includes(q);if(!el.hidden)count++});document.querySelector('#visible').textContent=count+' questions visible'}document.querySelector('#search').oninput=filter;document.querySelector('#pairs').onchange=filter;filter();document.querySelector('#export').onclick=()=>{const b=new Blob([JSON.stringify({source:KEY,notes},null,2)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=KEY.replaceAll('/','_')+'_review_notes.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};'''


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--commit',default='HEAD');args=parser.parse_args()
    commit=subprocess.check_output(['git','rev-parse',args.commit],cwd=ROOT,text=True).strip()
    sys.path.insert(0, str(ROOT))
    from gold_source_rows import SourceRows, render_review_evidence, render_source_panel
    from gold_event_graph_overview import render_event_graph
    audit = {row["dataset"]: row["tables"] for row in json.loads((ROOT/'event_scope_audit.json').read_text())['datasets']}
    before=input_snapshot();OUT.mkdir(parents=True,exist_ok=True)
    all_data=[];all_changes=[];index=[];total=Counter()
    for name in DATASETS:
        p=ROOT/'datasets'/name;folder=OUT/name;folder.mkdir(exist_ok=True);(folder/'graphs').mkdir(exist_ok=True)
        qpath=p/('private/questions.jsonl' if name.endswith('_new') else 'input/questions.jsonl')
        questions=loadjl(qpath);gold={identity(g):g for g in loadjl(p/'private/gold.jsonl')}
        cards=[];markdown=[f'# {name}: questions and Gold DFGs\n\n**EVALUATION ONLY — NEVER PROVIDE TO A MODEL.**\n\nSource commit: `{commit}`. Open index.html for search, review notes and complete case traces.\n\nNode counts = event occurrences. Edge counts = adjacent selected events within a case. Dashed amber edges touch timestamp ties and depend on the tie-break rule. DFGs are projections of the selected log, not causal models.\n']
        if name == 'hospitalflow':
            markdown.append(
                '\nAll HospitalFlow records and row examples are synthetic. See the '
                '[dataset provenance](../../../datasets/hospitalflow/README.md) and '
                '[simulation code](../../../datasets/hospitalflow/simulation.py).\n'
            )
        markdown.append('\n[Event graph inventory · tables, objects, OTs and activities](event_graph.md)\n')
        markdown.append('\n**Source tables** produced matched Gold events. **SQL tables** are all physical tables read by the Gold SQL, including join tables and shared CTE branches.\n')
        markdown.append(dataset_overview(name, questions))
        cache={};records=[]
        sources = SourceRows(p)
        (folder/'event_graph.md').write_text(render_event_graph(p, sources.db, audit[name]))
        for q in questions:
            ident=identity(q);g=gold[ident];question=q.get('text',q.get('question'));typ=q['question_type'];answerable=g.get('answerable',g.get('answerability')=='answerable');total[typ]+=1
            record=dict(dataset=name,id=ident,type=typ,question=question,answerable=answerable,pair_of=q.get('pair_of'),gold_sha256=None,chart=None)
            body=f'<article data-id="{html.escape(ident)}" data-type="{typ}"><h2>{ident} · {typ}</h2><div class="question">{html.escape(question)}</div>'
            markdown.append(f'\n## {ident} — {typ}\n\n{question}\n')
            if answerable:
                csvpath=p/'private/gold_logs'/f'{ident}.csv';rows=list(csv.DictReader(csvpath.open()));sha=digest(csvpath);d=extract(rows)
                record['gold_sha256']=sha
                if sha not in cache:
                    svg=graph_svg(d);target=folder/'graphs'/f'{ident}.svg';target.write_text(svg);cache[sha]=(target.name,svg)
                filename,svg=cache[sha];record['chart']='graphs/'+filename
                activities=sorted(d['nodes']);cases=len(d['traces']);duplicates=len(rows)-len({(r['case_id'],r['event_id']) for r in rows})
                wanted=(g.get('process_view') or {}).get('activities',[]);missing=sorted(set(wanted)-set(activities));extra=sorted(set(activities)-set(wanted)) if wanted else []
                stats=dict(events=len(rows),observed_cases=cases,activities=len(activities),dfg_edges=len(d['edges']),duplicate_case_event_pairs=duplicates,tied_timestamp_groups=d['tied_timestamp_groups'],requested_but_not_observed=missing,observed_outside_gold_scope=extra)
                record.update(stats=stats,activity_counts=dict(d['nodes']),edges=[dict(source=a,target=b,count=n,tie_affected=d['ambiguous'][(a,b)]) for (a,b),n in sorted(d['edges'].items())])
                body+='<div class="stats">'+''.join(f'<span>{k}: <b>{stats[k]}</b></span>' for k in ('events','observed_cases','activities','dfg_edges'))+'</div>'
                if duplicates or d['tied_timestamp_groups'] or missing or extra:
                    body+='<div class="warning">Review flags: '+html.escape(json.dumps({k:v for k,v in stats.items() if k in ('duplicate_case_event_pairs','tied_timestamp_groups','requested_but_not_observed','observed_outside_gold_scope') and v},ensure_ascii=False))+'</div>'
                source_tables, sql_reads, unmatched, related = sources.inspect(
                    (p/'private/gold_sql'/f'{ident}.sql').read_text(), rows,
                )
                record['source_tables'] = {table:len(matches) for table, _, matches in source_tables}
                record['unmatched_gold_rows'] = unmatched
                body += '<div class="review-split"><section>'
                # Use unique SVG marker IDs when several diagrams share a page.
                body+='<p>Focus activity: <select class="focus"><option value="">All activities</option>'+''.join('<option>'+html.escape(a)+'</option>' for a in activities)+'</select></p>'
                body+='<div class="graph">'+svg.replace('id="arr"',f'id="arr-{ident}"').replace('url(#arr)',f'url(#arr-{ident})')+'</div>'
                body+='<p class="muted">Blue fill: observed start activity. Green outline: observed end activity. Scroll inside the graph; open the SVG separately for browser zoom.</p>'
                body+=f'<p><a href="graphs/{filename}" target="_blank">Open full-size DFG</a> · <a href="https://github.com/jiwonpark7913/NL2EVENTLOG/blob/{commit}/datasets/{name}/private/gold_logs/{ident}.csv">Gold CSV</a></p>'
                body += '</section><section class="source-panel">'+render_source_panel(source_tables, unmatched, related)+'</section></div>'
                body+='<details><summary>All directly-follows edges and counts</summary><table><tr><th>From</th><th>To</th><th>Transitions</th><th>Tie-affected</th></tr>'+''.join('<tr><td>'+html.escape(a)+'</td><td>'+html.escape(b)+f'</td><td>{n}</td><td>{d["ambiguous"][(a,b)]}</td></tr>' for (a,b),n in sorted(d['edges'].items()))+'</table></details>'
                body+='<details><summary>Activity counts and boundary counts</summary><table><tr><th>Activity</th><th>Events</th><th>Start cases</th><th>End cases</th></tr>'+''.join(f'<tr><td>{html.escape(a)}</td><td>{d["nodes"][a]}</td><td>{d["starts"][a]}</td><td>{d["ends"][a]}</td></tr>' for a in activities)+'</table></details>'
                body+='<details><summary>Every case trace with timestamps (expand for event-level inspection)</summary><div class="trace">'
                for trace in d['traces']:
                    body+='<details><summary>'+html.escape(trace['case_id'])+f' · {len(trace["events"])} events</summary><table><tr><th>Time</th><th>Activity</th><th>Event ID</th></tr>'+''.join('<tr><td>'+html.escape(r['timestamp'])+'</td><td>'+html.escape(r['activity'])+'</td><td>'+html.escape(r['event_id'])+'</td></tr>' for r in trace['events'])+'</table></details>'
                body+='</div></details>'
                source_count, sql_count = len(source_tables), len(sql_reads)
                body += f'<p>Source tables: {source_count} · SQL tables: {sql_count}</p>'
                evidence = render_review_evidence(
                    source_tables, unmatched, related,
                    dataset_path=f'../../../datasets/{name}', question_id=ident,
                )
                markdown.append(
                    f'\nEvents: **{len(rows)}** · Cases with events: **{cases}** · Activities: **{len(activities)}** '
                    f'· Edges: **{len(d["edges"])}** · Source tables: **{source_count}** · SQL tables: **{sql_count}**\n\n'
                    f'<table><tr><td width="42%" valign="top"><a href="graphs/{filename}">'
                    f'<img src="graphs/{filename}" width="390" alt="{ident} Gold DFG"></a></td>'
                    f'<td width="58%" valign="top">{evidence}</td></tr></table>\n'
                )
                total['gold_logs']+=1
                if d['tied_timestamp_groups']:total['logs_with_ties']+=1
            else:
                reason=g.get('reason','Unsupported by design; no Gold log is present.')
                body+='<p class="warning">No Gold log: '+html.escape(reason)+'</p>'
                markdown.append('\n**No Gold log:** '+reason+'\n')
                record['reason']=reason;total['unsupported']+=1
            body+='<div class="note"><select class="review-status" aria-label="Review status"><option>미검토</option><option>정상</option><option>수정 필요</option><option>보류</option></select><textarea rows="2" placeholder="검수 메모: 빠진 활동, 잘못된 case 연결, 시각/순서 문제 등"></textarea></div></article>'
            cards.append(body);records.append(record)
        title=name+' · Gold DFG review'
        header='<header><h1>'+title+'</h1><p>EVALUATION ONLY / PRIVATE GOLD. 모델 입력 금지. 질의별 gold log를 검수하는 자료입니다. 기본 화면에는 Q1·Q3만 표시하며, 현재 소스의 Q2·Q4는 체크박스로 볼 수 있습니다.</p><p>Nodes = event occurrences; arrows = directly-follows counts within the selected case log. Order: timestamp, then event_id. Dashed amber arrows touch timestamp ties. A filtered question can create projected adjacency; edges do not establish causality. Graph positions are for readability only.</p><p>Source commit: '+commit+'</p></header>'
        script=SCRIPT.replace('__DATA__','[]').replace('__KEY__',json.dumps('gold-dfg/'+commit+'/'+name))
        page='<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+'</title><style>'+STYLE+'</style>'+header+'<nav><input id="search" type="search" placeholder="질문 ID / activity / case 검색"><label><input id="pairs" type="checkbox"> Q2·Q4도 표시</label><button id="export">검수 메모 JSON 내려받기</button><span id="visible"></span><a href="../index.html">All datasets</a></nav><main>'+''.join(cards)+'</main><script>'+script+'</script></html>'
        (folder/'index.html').write_text(page);(folder/'README.md').write_text(''.join(markdown));(folder/'review_data.json').write_text(json.dumps(records,indent=2)+'\n')
        sources.db.close()
        all_data.extend(records);index.append(dict(dataset=name,questions=len(questions),gold_logs=sum(r['answerable'] for r in records),graphs=len(cache)))
    assert before==input_snapshot(),'Model input bytes changed'
    manifest=dict(evaluation_only=True,model_input=False,source_commit=commit,input_files_unchanged=True,input_file_sha256=before,datasets=index,counts=dict(total),tie_policy='Per case sort by parsed timestamp, event_id, CSV row index. Mark transitions touching tied timestamp groups as ambiguous. Start/end counts also use this linearization.',scope='Actual Gold CSVs from the stated Git commit; no Gold is corrected by this renderer.')
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    links=''.join(f'<article><h2>{r["dataset"]}</h2><p>{r["questions"]} questions · {r["gold_logs"]} Gold logs · {r["graphs"]} distinct DFGs</p><a href="{r["dataset"]}/index.html">Open interactive review</a> · <a href="{r["dataset"]}/README.md">GitHub Markdown view</a></article>' for r in index)
    (OUT/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>Gold DFG review</title><style>'+STYLE+'</style><header><h1>Gold event log · DFG 검수</h1><p>EVALUATION ONLY — 모델 입력 금지. 각 질의와 DFG, 전체 case trace를 나란히 확인하세요. 메모는 브라우저에 저장되며 JSON으로 내보낼 수 있습니다.</p></header><main>'+links+'</main></html>')
    readme='# Gold event log DFG review\n\n**EVALUATION ONLY / PRIVATE GOLD — NEVER PASS THESE FILES TO ANY MODEL.**\n\nThis folder is separate from datasets/*/input and is absent from every model-input allowlist. No model-input bytes or manifests were changed. Keep it out of repository-wide retrieval/RAG/evaluation prompts.\n\nSource commit: `'+commit+'`. The current remote snapshot still includes Q2/Q4; each HTML page defaults to Q1/Q3 and optionally reveals those existing pairs. This renderer does not delete or regenerate questions.\n\n| Dataset | Questions | Gold logs | Distinct DFGs | GitHub view | Event graph |\n|---|---:|---:|---:|---|---|\n'+''.join(f'| {r["dataset"]} | {r["questions"]} | {r["gold_logs"]} | {r["graphs"]} | [Questions + DFGs]({r["dataset"]}/README.md) | [Inventory]({r["dataset"]}/event_graph.md) |\n' for r in index)+'\n## Local interactive review\n\nDownload and extract [review_bundle.zip](review_bundle.zip), then open index.html. To generate HTML pages from a local checkout, run the renderer first. Alternatively run `python -m http.server 8000` at the repository root and visit http://localhost:8000/review/gold_dfg/. Each dataset page has search, optional Q2/Q4 display, per-case timestamped traces, review status and notes, and JSON export. Review notes remain on that browser/device until exported. GitHub renders the dataset Markdown pages with SVG graphs; it does not execute HTML/JavaScript.\n\n## Reading the graph\n\n- The right panel shows original SQLite rows matched to Gold events. On GitHub, open a source table to compare up to three original rows (all columns) with their Gold events. The links above each preview open the exact SQL, Gold CSV and full SQLite database.\n- Nodes: activity label, event occurrences, observed start/end case counts. Blue fill = starts; green outline = ends.\n- Edges: adjacent selected events per case, with transition counts. All observed edges and activities are included; no frequency threshold hides rare behavior. Identical paired logs reuse the same DFG asset.\n- Order: timestamp, then event_id (then original row index). Dashed amber edges touch tied timestamp groups and depend on tie-breaking. Start/end assignments at tied boundaries are also ambiguous. This is a display convention, not proof of order.\n- Adjacency is measured in the question-specific projection. Removing intermediate activities can create a new edge. DFGs describe the selected traces, not a causal model or evidence that all cases follow one process.\n- Unsupported requests have no DFG. Requested-but-unobserved labels, timestamp ties and duplicate case/event IDs are review flags, not automatic judgments of correctness.\n\nRegenerate with `python tools/build_gold_dfg_review.py --commit HEAD` from a clean checkout of the intended source snapshot. The script verifies all input-file hashes before/after. Gold CSVs are read only.\n'
    (OUT/'README.md').write_text(readme)
    with zipfile.ZipFile(OUT/'review_bundle.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as bundle:
        for path in sorted(OUT.rglob('*')):
            if path.is_file() and path.name!='review_bundle.zip':
                bundle.write(path,path.relative_to(OUT))
    print(json.dumps(manifest['counts']));print(json.dumps(index))


if __name__=='__main__':
    main()
