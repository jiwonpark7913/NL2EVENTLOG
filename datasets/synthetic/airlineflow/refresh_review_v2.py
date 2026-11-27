"""Refresh the review UI while preserving the released fixture payload byte-for-byte."""
from pathlib import Path
import hashlib, json, subprocess, tempfile
R=Path(__file__).resolve().parent
p=R/'docs/scenario.html'
old=p.read_text(encoding='utf-8')
prefix='const DATA='
suffix=';\nconst $='
payload=old.split(prefix,1)[1].split(suffix,1)[0]
data=json.loads(payload)
assert len(data['queries'])==72 and len(data['events'])==72
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
    subset={k:data[k] for k in ('version','manifest','records','queries','events')}
    subset['queries']={q:subset['queries'][q] for q in ('Q01','Q05','Q18','Q56')}
    subset['events']={q:subset['events'][q] for q in subset['queries']}
    # Only the function declarations, not the boot-up DOM handlers.
    body=script.split('function drawRules()',1)[0]
    body=body.replace('const DATA=/*__PAYLOAD__*/null;', 'const DATA='+json.dumps(subset,ensure_ascii=False,separators=(',',':'))+';')
    stub="""
const assert=require('node:assert/strict');
const elements=new Map();
global.localStorage={getItem:()=>null,setItem:()=>{}};
function elem(id){if(!elements.has(id))elements.set(id,{value:'',checked:id==='related',innerHTML:'',textContent:'',scrollTop:0,scrollLeft:0,closest:()=>({scrollTop:0}),querySelector:()=>null});return elements.get(id)}
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
}
const pair=DATA.events.Q01.slice(0,2);
assert.equal(pair[0][4],pair[1][4]);
check('Q01',pair[0]);check('Q01',pair[1]);
check('Q05',DATA.events.Q05.find(e=>e[1]==='Cabin Cleaning Start'));
assert.equal(rawRows.length,6);
check('Q05',DATA.events.Q05.find(e=>e[1]==='Aircraft Ready'));
assert.equal(rawRows.length,1);
check('Q18',DATA.events.Q18[0]);check('Q56',DATA.events.Q56[0]);
elem('related').checked=false;renderRaw(true);assert.equal(rawRows.length,DATA.records[rawTableName].rows.length);
console.log('PASS: original-table UI source selection, green row and exact clock, case scope and full-table toggle (Node DOM stub)');
"""
    js.write_text(stub+body+tests,encoding='utf-8')
    subprocess.run(['node',str(js)],check=True)

p.write_text(new,encoding='utf-8')
print('PASS: review payload unchanged; exact physical timestamp verified for',count,'event occurrences; JavaScript syntax valid; payload SHA256',hashlib.sha256(payload.encode()).hexdigest())
