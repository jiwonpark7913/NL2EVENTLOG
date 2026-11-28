"""Refresh the review UI while preserving the released fixture payload byte-for-byte."""
from pathlib import Path
import hashlib, json, subprocess, tempfile, csv
R=Path(__file__).resolve().parent
p=R/'docs/scenario.html'
old=p.read_text(encoding='utf-8')
prefix='const DATA='
suffix=';\nconst $='
payload=old.split(prefix,1)[1].split(suffix,1)[0]
data=json.loads(payload)
assert len(data['queries'])==72 and len(data['events'])==72
with (R/'evaluation/query_registry.csv').open(encoding='utf-8-sig',newline='') as f:
    released_registry=list(csv.DictReader(f))
assert data['registry']==released_registry,'HTML registry differs from released CSV'
classification_discrepancies=[]
for r in released_registry:
    q=r['QUERY ID']; m=data['queries'][q]; pi=m['pi']
    actual={e[1] for e in data['events'][q]}
    assert int(r['ACT COUNT'])==len(actual)==m['activity_count'],q
    assert set(r['EXPECTED ACTIVITIES'].split('; '))==actual,q
    assert int(r['EXPECTED CASE COUNT'])==m['cases'] and int(r['EXPECTED EVENT COUNT'])==m['events'],q
    assert r['CASE MODE'] in ('Explicit','Implicit') and r['REQUEST MODE'] in ('Explicit','Implicit'),q
    if r['CASE MODE']!=pi.get('case_mode') or r['REQUEST MODE']!=pi.get('activity_mode'):
        classification_discrepancies.append(q)
print('PASS: 72 query summary metrics and activity sets match released Registry and Gold; Registry/PI mode discrepancies:',classification_discrepancies)
for v in data['manifest']:
    original=json.loads((R/v['dictionary_path']).read_text())
    assert data['dictionaries'][v['variant_id']]==original
    assert set(original)==set(v['table_rows'])
for q,events in data['events'].items():
    for e in events:
        assert len(e)==6
# Preserve the exact data, including source occurrence IDs and all review state versioning.
template=(R/'docs/review_v2_template.html').read_text(encoding='utf-8')
assert template.count('/*__PAYLOAD__*/null')==1
new=template.replace('/*__PAYLOAD__*/null',payload)
assert new.split(prefix,1)[1].split(suffix,1)[0]==payload
# Check JS syntax without parsing the huge literal twice in Node.
script=template.split('<script>',1)[1].split('</script>',1)[0]
with tempfile.TemporaryDirectory() as t:
    js=Path(t)/'review.js';js.write_text(script,encoding='utf-8')
    subprocess.run(['node','--check',str(js)],check=True)
# Validate the exact source cell for every embedded occurrence against the physical record.
idx={t:({str(r[0]):r for r in x['rows']},dict(zip(x['columns'],range(len(x['columns']))))) for t,x in data['records'].items()}
count=0
for q,events in data['events'].items():
    for case,activity,ts,t,pk,col in events:
        rows,columns=idx[t]
        assert rows[pk][columns[col]]==ts,(q,t,pk,col)
        count+=1

# Exercise actual UI rendering logic with the real release payload, in a Node DOM stub.
# No fake data: test Q01 (same row, different clock), Q05 (two tables), Q18 (aggregate) and Q56 (visit).
with tempfile.TemporaryDirectory() as t:
    js=Path(t)/'review_test.js'
    subset={k:data[k] for k in ('version','manifest','records','queries','events','dictionaries','registry')}
    subset['queries']={q:subset['queries'][q] for q in ('Q01','Q02','Q05','Q18','Q56')}
    subset['events']={q:subset['events'][q] for q in subset['queries']}
    # Only the function declarations, not the boot-up DOM handlers.
    body=script.split('function drawRules()',1)[0]
    body=body.replace('const DATA=/*__PAYLOAD__*/null;', 'const DATA='+json.dumps(subset,ensure_ascii=False,separators=(',',':'))+';')
    stub="""
const assert=require('node:assert/strict');
const elements=new Map();
const storage=new Map();global.localStorage={getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)};
function elem(id){if(!elements.has(id))elements.set(id,{value:'',checked:id==='related',innerHTML:'',textContent:'',scrollTop:0,scrollLeft:0,closest:()=>({scrollTop:0}),querySelector:()=>null,style:{},handlers:{},children:[{}],querySelectorAll:()=>[{checked:true}],addEventListener:function(k,fn){this.handlers[k]=fn}});return elements.get(id)}
global.document={getElementById:elem};
"""
    tests="""
function check(qid,event){
    q=qid;drawSource(event);
    const html=elem('rawTable').innerHTML, rec=DATA.records[event[3]];
    assert.equal(rawTableName,event[3]);
    assert.equal(elem('tableSelect').value,event[3]);
    assert.ok(html.includes('<tr class="sel">'));
    assert.ok(html.includes('<td class="mark" title="'+event[2]+'">'+event[2]+'</td>'));
    assert.ok(html.includes('<th class="mark">'+event[5]+'</th>'));
    assert.ok(rec.columns.every(x=>html.includes('>'+x+'</th>')));
    assert.ok(rawRows.some(r=>r[0]===event[4]));
    assert.equal(elem('dictionaryTitle').textContent,'Data Dictionary · '+event[3]);
    assert.ok(elem('dictionaryBody').innerHTML.includes('<tr class="dd-hit"><td>'+event[5]+'</td>'));
    assert.ok(rec.columns.every(x=>elem('dictionaryBody').innerHTML.includes('>'+x+'</td>')));
}
bindReviewControls();
q='Q01';variant='l15';restoreReview();
const note=[String.fromCodePoint(0xd55c,0xae00)+' review note: Case/Activity','Second line'].join(String.fromCharCode(10));
elem('notes').value=note;elem('verdict').value='Revise';elem('notes').handlers.input();
assert.equal(decisions['l15:Q01'].notes,note);
assert.equal(JSON.parse(storage.get(storageKey()))['l15:Q01'].notes,note);
assert.equal(elem('notes').value,note);assert.equal(elem('notes').readOnly,false);
q='Q05';restoreReview();assert.equal(elem('notes').value,'');
elem('notes').value='Q05 separate note';elem('notes').handlers.compositionend();
q='Q01';restoreReview();assert.equal(elem('notes').value,note);
variant='l05';restoreReview();assert.equal(elem('notes').value,'');elem('notes').value='L05 separate';elem('saveNote').onclick();
variant='l15';restoreReview();assert.equal(elem('notes').value,note);
const saved=JSON.parse(storage.get(storageKey()));decisions={};restoreReview();assert.equal(elem('notes').value,'');
assert.equal(importReviewData({version:DATA.version,decisions:saved}),true);restoreReview();assert.equal(elem('notes').value,note);
const realSet=localStorage.setItem;localStorage.setItem=()=>{throw Error('blocked')};
elem('notes').value='storage blocked but retained';elem('notes').handlers.input();assert.equal(decisions['l15:Q01'].notes,'storage blocked but retained');
assert.ok(elem('noteSaveStatus').textContent.includes('Export review JSON'));localStorage.setItem=realSet;
console.log('PASS: Korean/multiline notes, input autosave, query/variant isolation, reload/import restoration, and storage-blocked fallback (Node DOM stub)');

assert.ok(dfgLegend('Q02').includes('14 unique activities · 14 activity nodes'));assert.equal(dfgSummary('Q02').freq.get('Catering Loading Start'),100);
const fullGraph=graphCounts(DATA.events.Q02);
assert.equal(fullGraph.nodes.size,14);assert.equal(fullGraph.events,1400);assert.equal(fullGraph.edges.size,71);
assert.equal(fullGraph.nodes.get('Catering Loading Start'),100);
const caseGraph=graphCounts(DATA.events.Q02,'TU046');assert.equal(caseGraph.events,14);assert.equal(caseGraph.nodes.size,14);
assert.equal(caseGraph.edges.has(edgeKey('Catering Loading Start','Refuelling Start')),false);
assert.equal(caseGraph.edges.has(edgeKey('Refuelling Start','Catering Loading Start')),false);
assert.ok(caseGraph.trace.some(x=>x[0]==='2026-12-15 08:27:54'&&x[2]===2));
const filteredGraph=visibleGraph(fullGraph,10,'Handling Start');assert.ok(filteredGraph.edges.size<71);assert.ok([...filteredGraph.edges.values()].every(n=>n>=10));assert.ok(filteredGraph.adjacent.has('Handling Start'));assert.equal(fullGraph.edges.size,71);
console.log('PASS: interactive DFG aggregation, case trace, tie handling, frequency filtering and highlighting logic');
const summary=querySummary('Q01');
assert.ok(summary.includes('Case mode')&&summary.includes('Activity mode')&&summary.includes('Explicit'));
assert.ok(summary.includes('Gold activities (2)'));
const summary2=querySummary('Q05');
assert.ok(summary2.includes('Gold activities (6)'));
assert.ok(summary2.includes('Review focus'));
const pair=DATA.events.Q01.slice(0,2);
assert.equal(pair[0][4],pair[1][4]);
check('Q01',pair[0]);check('Q01',pair[1]);
check('Q05',DATA.events.Q05.find(e=>e[1]==='Cabin Cleaning Start'));
assert.equal(rawRows.length,6);
check('Q05',DATA.events.Q05.find(e=>e[1]==='Aircraft Ready'));
assert.equal(rawRows.length,1);
check('Q18',DATA.events.Q18[0]);check('Q56',DATA.events.Q56[0]);
elem('related').checked=false;renderRaw(true);assert.equal(rawRows.length,DATA.records[rawTableName].rows.length);
console.log('PASS: original-table UI selection, green source cell, Data Dictionary and full-table toggle (Node DOM stub)');
"""
    js.write_text(stub+body+tests,encoding='utf-8')
    subprocess.run(['node',str(js)],check=True)


# Exercise the actual controls in Chrome when installed on the runner.
# Use the same template and a small real-payload subset to keep the smoke test fast.
import shutil
chrome=shutil.which('google-chrome') or shutil.which('chromium') or shutil.which('chromium-browser')
if chrome:
    with tempfile.TemporaryDirectory() as td:
        temp=Path(td); page=temp/'review_browser.html'
        small={k:data[k] for k in ('version','manifest','records','queries','events','dictionaries','registry')}
        small['queries']={q:data['queries'][q] for q in ('Q01','Q02')}
        small['events']={q:data['events'][q] for q in small['queries']}
        small['manifest']=[{**v,'question_ids':['Q01','Q02']} for v in data['manifest']]
        browser_test="""
<script>
try{
  function check(v,m){if(!v)throw Error(m)}
  function visible(sel){return [...document.querySelectorAll(sel)].filter(g=>g.style.display!=='none').length}
  document.querySelector('[data-q="Q02"]').click();
  check(visible('#dfg g.node')===16,'full graph must have 14 activities plus endpoints');
  check(visible('#dfg g.edge')===71,'full graph edge count');
  const min=document.getElementById('dfgMin');min.value=10;min.dispatchEvent(new Event('input'));
  check(visible('#dfg g.edge')<71,'frequency filter');
  document.getElementById('dfgReset').click();
  document.querySelector('#dfg g.node[data-activity="Handling Start"]').dispatchEvent(new MouseEvent('click',{bubbles:true}));
  check(document.getElementById('dfgActivity').value==='Handling Start','node highlight');
  check(document.querySelectorAll('#dfg g.edge.dfg-muted').length>0,'edge de-emphasis');
  const select=document.getElementById('dfgCase');select.value='TU046';select.dispatchEvent(new Event('change'));
  check(document.getElementById('dfgViewStatus').textContent.includes('14 events'),'case count');
  check(!document.getElementById('dfgCaseTrace').hidden,'case trace');
  document.getElementById('dfgExpand').click();
  check(document.getElementById('dfgDialog').open&&document.querySelector('#dfgDialog #dfgWorkspace'),'enlarge');
  document.getElementById('dfgPlus').click();check(document.getElementById('dfg').style.width==='110%','zoom');
  document.getElementById('dfgClose').click();
  document.getElementById('dfgDialog').dispatchEvent(new Event('close'));
  check(document.querySelector('#dfgHome #dfgWorkspace'),'return to panel');
  document.getElementById('dfgReset').click();check(visible('#dfg g.edge')===71,'reset restores all edges');
  document.body.setAttribute('data-browser-test','PASS');
}catch(e){document.body.setAttribute('data-browser-test','FAIL: '+e.message)}
</script>
"""
        page.write_text(template.replace('/*__PAYLOAD__*/null',json.dumps(small,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')).replace('</body>',browser_test+'</body>'),encoding='utf-8')
        result=subprocess.run([chrome,'--headless','--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--no-first-run','--user-data-dir='+str(temp/'profile'),'--dump-dom',page.as_uri()],capture_output=True,text=True,timeout=90)
        if result.returncode or 'data-browser-test="PASS"' not in result.stdout:
            import re
            raise AssertionError('Browser DFG test failed: '+str(re.findall(r'data-browser-test="[^"]*"',result.stdout)[:2])+result.stderr[-1000:])
        print('PASS: Chrome interactive DFG controls, filter, case selection, highlighting, enlargement, zoom and reset')
else:
    print('SKIP: Chrome not available; Node DFG logic tests completed')

p.write_text(new,encoding='utf-8')
print('PASS: review payload unchanged; exact physical timestamp verified for',count,'event occurrences; JavaScript syntax valid; payload SHA256',hashlib.sha256(payload.encode()).hexdigest())
