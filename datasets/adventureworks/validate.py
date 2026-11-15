#!/usr/bin/env python3
"""Check source completeness, model-input metadata and draw.io physical relationships."""
import hashlib, json, sqlite3, xml.etree.ElementTree as ET
from pathlib import Path
P=Path(__file__).resolve().parent
manifest=json.loads((P/'source/provenance.json').read_text())
dd=json.loads((P/'input/data_dictionary.json').read_text())
con=sqlite3.connect(f'file:{P / "input/database.sqlite"}?mode=ro',uri=True)
q=lambda s:'"'+s.replace('"','""')+'"'
assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
assert not list(con.execute('PRAGMA foreign_key_check'))
assert len(dd['tables'])==71
assert {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}=={t['table'] for t in dd['tables']}
for t in dd['tables']:
    name=t['table']; cols=list(con.execute('PRAGMA table_info('+q(name)+')'))
    assert [c[1] for c in cols]==[c['name'] for c in t['columns']],name
    assert con.execute('SELECT count(*) FROM '+q(name)).fetchone()[0]==manifest['row_counts'][name],name
    assert [c[1] for c in sorted(cols,key=lambda c:c[5]) if c[5]]==t['primary_key'],name
    actual={(r[0],r[2]) for r in con.execute('PRAGMA foreign_key_list('+q(name)+')')}
    assert len(actual)==len(t['foreign_keys']),name
assert sum(manifest['row_counts'].values())==759240
for path,key in [('input/database.sqlite','sqlite_sha256'),('input/data_dictionary.json','dictionary_sha256')]:
    assert hashlib.sha256((P/path).read_bytes()).hexdigest()==manifest[key],path
root=ET.parse(P/'docs/schema.drawio').getroot()
all_cells=root.find('diagram/mxGraphModel/root').findall('mxCell')
assert len([c for c in all_cells if c.get('vertex')=='1'])==71
assert len([c for c in all_cells if c.get('edge')=='1'])==90
assert len(root.findall('diagram'))==7
# Known source anchors catch wrong import delimiters / shifted columns.
assert con.execute('SELECT CustomerID,AccountNumber FROM Customer WHERE CustomerID=1').fetchone()==(1,'AW00000001')
assert con.execute('SELECT count(*) FROM ProductReview').fetchone()[0]==4
assert '\n' in con.execute('SELECT Comments FROM ProductReview WHERE ProductReviewID=1').fetchone()[0]
assert con.execute('SELECT count(*) FROM SalesOrderDetail').fetchone()[0]==121317
assert con.execute('SELECT count(*) FROM WorkOrderRouting').fetchone()[0]==67131
print('OK: 71 tables; 759240 records; 90 FKs; DB/DD hashes; 7 draw.io pages; source anchors')
