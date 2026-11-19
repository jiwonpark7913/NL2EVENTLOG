#!/usr/bin/env python3
"""Build offline, evaluation-only question/DFG/source-row inspection pages."""
import csv
import html
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/validation'))
import gold_source_rows

original_bindings = gold_source_rows.bindings


def bindings(base):
    if base.name == 'universityflow':
        # The checked-in persistence map covers all grading records; the legacy
        # U05 view alone filters ORIGINAL and misses rows used by other questions.
        authored = json.loads((base / 'private/persistence_mapping.json').read_text())
        result=[]
        for b in authored:
            activity=b['activity'].replace("'", "''")
            result.append(dict(b, timestamp_column=b['timestamp_column'].split('.')[-1],
                event_sql=f"SELECT {b['key_sql']} event_id, '{activity}' activity, {b['timestamp_column']} timestamp FROM {b['from_sql']} WHERE {b['timestamp_column']} IS NOT NULL"))
        result.extend(b for b in original_bindings(base) if 'activity' in b)
        return result
    return json.loads((base / 'private/persistence_mapping.json').read_text())


gold_source_rows.bindings = bindings
esc = lambda value: html.escape(str(value))

STYLE = '''
:root{color-scheme:light dark;--bg:light-dark(#fff,#0d1117);--text:light-dark(#1f2328,#e6edf3);--soft:light-dark(#f6f8fa,#161b22);--line:light-dark(#d1d9e0,#3d444d);--link:light-dark(#0969da,#79c0ff);--time:light-dark(#ddf4ff,#14344b)}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.55 system-ui,sans-serif}header{padding:20px 28px;border-bottom:1px solid var(--line)}h1{font-size:23px;margin:0}h2{font-size:18px}h3{font-size:16px;margin:0 0 12px}h4{margin:12px 0 4px}a{color:var(--link)}button,select{font:inherit;color:inherit;background:var(--bg);border:1px solid var(--line);border-radius:5px;padding:7px 10px}button{cursor:pointer}button:disabled{opacity:.4;cursor:default}.toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:12px}select{max-width:100%}main{padding:20px 28px}.question{padding:16px;background:var(--soft);border-left:3px solid var(--link);margin-bottom:20px}.question p{margin:7px 0}.meta{font-size:12px;opacity:.85}.split{display:grid;grid-template-columns:minmax(0,44fr) minmax(0,56fr);gap:20px}.graph{border-right:1px solid var(--line);padding-right:20px}.graph-scroll{overflow:auto;max-height:740px;min-height:240px;background:#fff;border:1px solid var(--line)}.graph-scroll svg{width:100%;height:auto;display:block}.source{max-height:800px;overflow:auto;padding-right:4px}.scroll{overflow:auto;max-width:100%}table{border-collapse:collapse;font-size:12px;width:100%;margin:8px 0 14px}th,td{border:1px solid var(--line);padding:7px 9px;white-space:nowrap;vertical-align:top}th{background:var(--soft);text-align:left}.timestamp{background:var(--time)}.mapped{white-space:normal;min-width:250px}.null{opacity:.6;font-style:italic}details{margin:12px 0}summary{cursor:pointer;color:var(--link)}pre{overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;background:var(--soft);padding:16px;font-size:12px}footer{margin-top:20px;border-top:1px solid var(--line);padding-top:12px}.warning{color:light-dark(#9a3412,#ffb38a)}#empty{padding:25px}nav{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}nav a{padding:3px 6px;border:1px solid var(--line);border-radius:4px}.current{font-weight:700;background:var(--soft)}@media(max-width:850px){.split{grid-template-columns:1fr}.graph{border:0;padding:0}.source{max-height:none}.graph-scroll{max-height:550px}header,main{padding:16px}} 
'''

SCRIPT = '''
const records=JSON.parse(document.getElementById('review-data').textContent);
const picker=document.getElementById('picker'),panel=document.getElementById('panel');
function show(i){i=Math.max(0,Math.min(records.length-1,i));picker.value=String(i);const r=records[i];panel.innerHTML=r.html;document.getElementById('prev').disabled=i===0;document.getElementById('next').disabled=i===records.length-1;document.getElementById('position').textContent=(i+1)+' / '+records.length;document.querySelectorAll('nav a').forEach((a,j)=>a.classList.toggle('current',i===j));history.replaceState(null,'','#'+encodeURIComponent(r.id));}
picker.addEventListener('change',()=>show(Number(picker.value)));
document.getElementById('prev').onclick=()=>show(Number(picker.value)-1);
document.getElementById('next').onclick=()=>show(Number(picker.value)+1);
document.querySelector('nav').onclick=e=>{const a=e.target.closest('a');if(a){e.preventDefault();show(Number(a.dataset.index));}};
panel.addEventListener('click',e=>{const b=e.target.closest('[data-zoom]');if(b){const svg=panel.querySelector('.graph-scroll svg');let n=Number(svg.dataset.zoom||1);n=b.dataset.zoom==='reset'?1:Math.max(.5,Math.min(4,n+Number(b.dataset.zoom)));svg.dataset.zoom=n;svg.style.width=(100*n)+'%';}});
panel.addEventListener('click',e=>{if(e.target.closest('a[href="#full-database"]'))document.getElementById('full-database').open=true;});
const initial=records.findIndex(r=>r.id===decodeURIComponent(location.hash.slice(1)));show(initial<0?0:initial);
'''


def graph(rows):
    nodes = Counter(r['activity'] for r in rows)
    edges, ties = Counter(), Counter()
    cases = defaultdict(list)
    for row in rows:
        cases[row['case_id']].append(row)
    for trace in cases.values():
        trace.sort(key=lambda r: (r['timestamp'], r['event_id']))
        for a, b in zip(trace, trace[1:]):
            key = a['activity'], b['activity']
            edges[key] += 1
            ties[key] += a['timestamp'] == b['timestamp']
    ids = {a: 'n'+str(i) for i, a in enumerate(sorted(nodes))}
    dot = ['digraph G { graph [rankdir=TB, bgcolor="white", pad="0.2", nodesep="0.4", ranksep="0.5"]; node [shape=box,style="rounded,filled",fillcolor="#eef6ff",color="#64748b",fontname="sans-serif",fontsize=12]; edge [fontname="sans-serif",fontsize=11,color="#64748b"];']
    for a, ident in ids.items():
        dot.append(f'{ident} [label={json.dumps(a+chr(10)+str(nodes[a]))}];')
    for (a, b), n in sorted(edges.items()):
        attrs = ',style=dashed,color="#b45309"' if ties[(a,b)] else ''
        dot.append(f'{ids[a]} -> {ids[b]} [label="{n}"{attrs}];')
    dot.append('}')
    result = subprocess.run(['dot','-Tsvg'],input='\n'.join(dot),text=True,capture_output=True,check=True).stdout
    return result[result.index('<svg'):], len(cases), len(nodes)


def cell(v):
    return '<span class="null">NULL</span>' if v is None else esc(v)


def table(columns, rows, timestamps=(), labels=None):
    heads = ''.join('<th class="'+('timestamp' if c in timestamps else '')+'">'+esc(c)+'</th>' for c in columns)
    if labels is not None: heads += '<th>Gold 이벤트 · case · timestamp 컬럼</th>'
    body=[]
    for i, row in enumerate(rows):
        cells=''.join('<td class="'+('timestamp' if c in timestamps else '')+'">'+cell(v)+'</td>' for c,v in zip(columns,row))
        if labels is not None:
            cells += '<td class="mapped">'+'<br>'.join(esc(f'{eid} → {act} · case {case} · time: {ts}') for eid,act,ts,case in labels[i])+'</td>'
        body.append('<tr>'+cells+'</tr>')
    return '<div class="scroll"><table><thead><tr>'+heads+'</tr></thead><tbody>'+''.join(body)+'</tbody></table></div>'


def build(base):
    out=base/'review/gold_dfg'
    qp=next(p for p in [base/'private/questions.jsonl',base/'evaluation/questions.jsonl'] if p.exists())
    questions=[json.loads(s) for s in qp.read_text().splitlines() if s.strip()]
    sources=gold_source_rows.SourceRows(base)
    all_tables=[r[0] for r in sources.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    records=[]; total_missing=0
    for q in questions:
        ident=q.get('question_id',q.get('id')); text=q.get('text',q.get('question'))
        csvpath=base/'private/gold_logs'/f'{ident}.csv'; sqlpath=base/'private/gold_sql'/f'{ident}.sql'
        section=f'<section class="question"><h2>{esc(ident)} · {esc(q.get("question_type",""))}</h2><p>{esc(text)}</p><p class="meta">Case: {esc(q.get("case_concept","See Gold SQL"))}</p></section>'
        if not csvpath.exists() or not sqlpath.exists():
            section+='<p id="empty">이 질의에는 Gold CSV 또는 SQL이 없습니다. 비응답 가능 질의인지 원본 정의를 확인하세요.</p>'
            records.append(dict(id=ident,html=section));continue
        rows=list(csv.DictReader(csvpath.open()));sql=sqlpath.read_text()
        svg,cases,activities=graph(rows)
        tables,reads,missing,related=sources.inspect(sql,rows);total_missing+=missing
        section+=f'<p class="meta">{len(rows)} events · {cases} cases with events · {activities} activities</p><div class="split"><section class="graph"><h3>Gold DFG</h3><div class="toolbar"><button data-zoom="0.25">＋</button><button data-zoom="-0.25">−</button><button data-zoom="reset">맞춤</button></div><div class="graph-scroll">{svg}</div><p class="meta">노드: 발생 횟수 · 간선: 직접 후속 횟수<br>점선: 동일 timestamp의 event_id 정렬에 영향받는 전이. 인과관계를 의미하지 않습니다.</p></section><section class="source"><h3>원본 테이블 · 추출 근거</h3>'
        if missing:section+=f'<p class="warning">원본 행 미매칭: {missing} Gold 이벤트. 추측한 행으로 대체하지 않았습니다.</p>'
        for name,columns,matches in tables:
            timestamps={event[2].split('.')[-1] for _,events in matches for event in events}
            section+=f'<h4>{esc(name)} · 매칭 원본 {len(matches)}행</h4>'
            section+=table(columns,[v for v,_ in matches[:10]],timestamps,[e for _,e in matches[:10]])
            if len(matches)>10:
                section+=f'<details><summary>나머지 {len(matches)-10}행</summary>'+table(columns,[v for v,_ in matches[10:]],timestamps,[e for _,e in matches[10:]])+'</details>'
        section+='<details><summary>Case 연결에 사용된 FK 원본 행</summary>'
        for name,examples in sorted(related.items()):
            columns=list(examples[0][0]);section+=f'<h4>{esc(name)}</h4>'+table(columns+['Join from'],[[*(r[c] for c in columns),child+' ('+', '.join(keys)+')'] for r,child,keys in examples])
        section+='</details><p><a href="#full-database">전체 원본 테이블 · 전체 컬럼·행 보기</a></p></section></div>'
        section+=f'<footer><a href="../../private/gold_logs/{esc(ident)}.csv">Gold CSV</a> · <a href="../../private/gold_sql/{esc(ident)}.sql">Gold SQL</a> · <a href="../../input/database.sqlite">원본 SQLite</a><details><summary>Gold SQL 전문</summary><pre>{esc(sql)}</pre></details></footer>'
        records.append(dict(id=ident,html=section,events=len(rows),unmatched=missing))
    database_html='<details id="full-database"><summary>전체 원본 테이블 · 전체 컬럼·행</summary>'
    for name in all_tables:
        columns=[r['name'] for r in sources.db.execute('PRAGMA table_info('+gold_source_rows.quote(name)+')')]
        original=sources.db.execute('SELECT * FROM '+gold_source_rows.quote(name)).fetchall()
        database_html+=f'<details><summary>{esc(name)} · {len(original)}행</summary>'+table(columns,original)+'</details>'
    database_html+='</details>'
    sources.db.close()
    data=json.dumps(records,ensure_ascii=False).replace('<','\\u003c')
    options=''.join(f'<option value="{i}">{esc(r["id"])}</option>' for i,r in enumerate(records))
    nav=''.join(f'<a href="#{esc(r["id"])}" data-index="{i}">{esc(r["id"])}</a>' for i,r in enumerate(records))
    document=f'<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(base.name)} Gold 검수</title><style>{STYLE}</style><header><h1>{esc(base.name)} · 질의별 Gold 검수</h1><p class="meta">평가·수동 검수용 · Gold 자료를 모델 입력에 포함하지 마세요.</p><div class="toolbar"><label for="picker">질의</label><select id="picker">{options}</select><button id="prev">이전</button><button id="next">다음</button><span id="position"></span></div><nav aria-label="질의 바로가기">{nav}</nav></header><main id="panel" aria-live="polite"></main><script type="application/json" id="review-data">{data}</script><script>{SCRIPT}</script></html>'
    document=document.replace('<script type="application/json"', '<aside style="padding:20px 28px">'+database_html+'</aside><script type="application/json"',1)
    (out/'index.html').write_text(document)
    return dict(dataset=base.name,questions=len(records),unmatched_gold_rows=total_missing,bytes=len(document.encode()))


if __name__=='__main__':
    for folder in sorted((ROOT/'datasets').glob('*/review/gold_dfg')):
        print(json.dumps(build(folder.parents[1])),flush=True)
