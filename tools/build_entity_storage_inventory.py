"""Human-only inventory from executable SQLite schemas, not inferred ET labels."""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('universityflow','hospitalflow','warehouseflow','plateflow')
def q(s): return '"'+s.replace('"','""')+'"'
def build():
    result = {}
    for name in NAMES:
        base = ROOT/'datasets'/name
        con = sqlite3.connect('file:'+str(base/'input/database.sqlite')+'?mode=ro', uri=True)
        tables = []
        for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            cols = list(con.execute('PRAGMA table_info('+q(t)+')'))
            pk = [c[1] for c in sorted(cols, key=lambda c:c[5]) if c[5]]
            unique = []
            for ix in con.execute('PRAGMA index_list('+q(t)+')'):
                if ix[2]: unique.append([r[2] for r in con.execute('PRAGMA index_info('+q(ix[1])+')')])
            groups = {}
            for fk in con.execute('PRAGMA foreign_key_list('+q(t)+')'):
                groups.setdefault(fk[0],[]).append(fk)
            refs = []
            for group in groups.values():
                group.sort(key=lambda x:x[1])
                refs.append(dict(columns=[r[3] for r in group], target_table=group[0][2], target_columns=[r[4] for r in group]))
            tables.append(dict(table=t, rows=con.execute('SELECT COUNT(*) FROM '+q(t)).fetchone()[0], primary_key=pk,
                unique_indexes=unique, foreign_keys=refs,
                note='PK/UNIQUE identify rows. ET and entity-reference meanings require semantic review.'))
        result[name] = tables
        lines=['# '+name+' — 식별자와 대상 참조 목록','',
            '실제 SQLite의 전체 PK·UNIQUE·FK를 조사한 구조 목록이다. ET 예측이나 table→ET Gold가 아니다.', '',
            '[개념 설명](../../../docs/system/ENTITY_IDENTITY_AND_STORAGE.md) · [저장 사례](../../ENTITY_STORAGE_CASES.md)', '',
            '| Table | Rows | 완전한 PK | UNIQUE 인덱스 | 선언된 참조 |', '|---|---:|---|---|---|']
        for t in tables:
            refs=['('+', '.join(r['columns'])+') → '+r['target_table']+'('+', '.join(r['target_columns'])+')' for r in t['foreign_keys']]
            lines.append('| '+t['table']+' | '+str(t['rows'])+' | '+', '.join(t['primary_key'])+' | '+'; '.join('('+', '.join(u)+')' for u in t['unique_indexes'])+' | '+'; '.join(refs)+' |')
        lines += ['', 'UNIQUE 인덱스에는 PK 인덱스도 포함될 수 있다. NULL 허용 UNIQUE는 전체 행의 완전한 식별을 보장하지 않는다. FK가 없는 동일성은 이 구조 목록만으로 판별할 수 없다.']
        (base/'docs/entity_identifiers.md').write_text('\n'.join(lines)+'\n')
        con.close()
    (ROOT/'datasets/entity_identifier_inventory.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__ == '__main__': build()
