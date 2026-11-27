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
p.write_text(new,encoding='utf-8')
print('PASS: review payload unchanged; exact physical timestamp verified for',count,'event occurrences; JavaScript syntax valid; payload SHA256',hashlib.sha256(payload.encode()).hexdigest())
