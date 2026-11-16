#!/usr/bin/env python3
"""Build a read-only SQLite snapshot from pinned Microsoft AdventureWorks OLTP exports.
No synthetic business records, event labels or Entity Type annotations are added.
"""
from __future__ import annotations
import argparse, concurrent.futures, hashlib, html, json, re, sqlite3, urllib.request
from pathlib import Path
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parent
COMMIT = '8fe3fd0c9a825fef3ae6d601e97537b612d7b214'
PREFIX = 'samples/databases/adventure-works/oltp-install-script/'
RAW = f'https://raw.githubusercontent.com/microsoft/sql-server-samples/{COMMIT}/'

def q(s): return '"' + s.replace('"', '""') + '"'
def names(s): return re.findall(r'\[([^]]+)\]', re.sub(r'--[^\n]*', '', s))
def write_json(path, data): path.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n')

def download(cache):
    files=json.loads((BASE/'source/upstream_files.json').read_text())
    cache.mkdir(parents=True,exist_ok=True)
    def one(item):
        path=cache/item['name']
        if not path.exists(): path.write_bytes(urllib.request.urlopen(RAW+item['path'], timeout=120).read())
        data=path.read_bytes()
        sha=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if sha != item['sha']: raise ValueError(f"Upstream hash mismatch: {path}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool: list(pool.map(one,files))
    return files

def parse(sql):
    tables={}
    for m in re.finditer(r'CREATE TABLE \[([^]]+)\]\.\[([^]]+)\]\s*\((.*?)\n\) ON',sql,re.S):
        schema,name,body=m.groups(); cols=[]
        for line in body.splitlines():
            cm=re.match(r'\s*\[([^]]+)\]\s+(.+)',line)
            if not cm: continue
            col,decl=cm.groups();decl=decl.rstrip().rstrip(',')
            computed=decl.startswith('AS ')
            tm=re.match(r'\[?([A-Za-z0-9_]+)\]?(\([^)]*\))?',decl)
            typ='computed' if computed else tm[1].lower()
            affinity='INTEGER' if typ in ('int','smallint','tinyint','bigint','bit','flag') else 'TEXT'
            # Keep decimal strings exact; do not silently introduce binary float rounding.
            if typ in ('varbinary','binary','image','geography'):affinity='BLOB'
            cols.append(dict(name=col,source_type=typ,source_declaration=decl,sql_type=affinity,computed=computed,required='NOT NULL' in decl,definition='',foreign_keys=[],primary_key_position=0,default=None))
        tables[name]=dict(table=name,source_schema=schema,definition='',columns=cols,primary_key=[],foreign_keys=[])
    for m in re.finditer(r'ALTER TABLE \[([^]]+)\]\.\[([^]]+)\](.*?)(?=\nGO\b)',sql,re.S):
        schema,name,body=m.groups()
        if name not in tables:continue
        pk=re.search(r'PRIMARY KEY (?:NON)?CLUSTERED\s*\((.*?)\)',body,re.S)
        if pk:tables[name]['primary_key']=names(pk[1])
        for fk in re.finditer(r'CONSTRAINT \[([^]]+)\] FOREIGN KEY\s*\((.*?)\) REFERENCES \[([^]]+)\]\.\[([^]]+)\]\s*\((.*?)\)',body,re.S):
            constraint,children,ps,pt,parents=fk.groups()
            tables[name]['foreign_keys'].append(dict(name=constraint,columns=names(children),referenced_table=pt,referenced_columns=names(parents)))
    # MS_Description is an actual upstream data dictionary, not an inferred row-grain oracle.
    pattern=r"sp_addextendedproperty\] N'MS_Description', N'((?:''|[^'])*)', N'SCHEMA', \[([^]]+)\], N'TABLE', \[([^]]+)\], (?:N'COLUMN', \[([^]]+)\]|NULL, NULL)"
    for m in re.finditer(pattern,sql):
        desc,schema,name,col=m.groups()
        if name not in tables:continue
        desc=desc.replace("''", "'")
        if col:
            next(c for c in tables[name]['columns'] if c['name']==col)['definition']=desc
        else:tables[name]['definition']=desc
    for t in tables.values():
        for c in t['columns']:
            if c['name'] in t['primary_key']:c['primary_key_position']=t['primary_key'].index(c['name'])+1;c['required']=True
            c['foreign_keys']=[dict(table=f['referenced_table'],column=f['referenced_columns'][f['columns'].index(c['name'])]) for f in t['foreign_keys'] if c['name'] in f['columns']]
    return tables

def records(path, spec, ncols):
    data=path.read_bytes()
    text=data.decode('utf-16') if data.startswith((b'\xff\xfe',b'\xfe\xff')) else data.decode('utf-8-sig')
    delim=re.search(r"FIELDTERMINATOR\s*=\s*'([^']*)'",spec)[1]
    term=re.search(r"ROWTERMINATOR\s*=\s*'([^']*)'",spec)[1]
    delim=delim.replace('\\t','\t');term=term.replace('0x0a','\n').replace('\\n','\n');text=text.replace('\r\n','\n')
    pos=0
    while pos<len(text):
        row=[]
        for i in range(ncols):
            separator=term if i==ncols-1 else delim
            end=text.find(separator,pos)
            if end<0:raise ValueError(f"Incomplete export record in {path} at {pos}")
            row.append(text[pos:end].removesuffix('\r') if i==ncols-1 else text[pos:end])
            pos=end+len(separator)
        yield row

def drawio(tables):
    # Shared human-only geometry; no changes to DB / data dictionary.
    from diagram import generate
    generate(tables)


def build(cache):
    files=download(cache)
    source=(cache/'instawdb.sql').read_bytes();(BASE/'source/instawdb.sql').write_bytes(source)
    sql=source.decode('utf-8-sig');tables=parse(sql)
    db=BASE/'input/database.sqlite'
    if db.exists():db.unlink()
    conn=sqlite3.connect(db);conn.execute('PRAGMA page_size=4096')
    ddls=[]
    for t in tables.values():
        defs=[]
        for c in t['columns']:
            decl=q(c['name'])+' '+c['sql_type']
            if c['required']:decl+=' NOT NULL'
            defs.append(decl)
        if t['primary_key']:defs.append('PRIMARY KEY ('+', '.join(map(q,t['primary_key']))+')')
        for f in t['foreign_keys']:defs.append('FOREIGN KEY ('+', '.join(map(q,f['columns']))+') REFERENCES '+q(f['referenced_table'])+' ('+', '.join(map(q,f['referenced_columns']))+')')
        ddl='CREATE TABLE '+q(t['table'])+' (\n  '+',\n  '.join(defs)+'\n)'
        conn.execute(ddl);t['sql_definition']=ddl;ddls.append(ddl+';')
    counts={};issues=[]
    bulk_sql=sql+"\nBULK INSERT [dbo].[AWBuildVersion] FROM 'AWBuildVersion.csv' WITH (FIELDTERMINATOR='\\t', ROWTERMINATOR='0x0a');"
    for m in re.finditer(r"BULK INSERT \[([^]]+)\]\.\[([^]]+)\] FROM '[^']*?([^/\\']+\.csv)'\s*WITH\s*\((.*?)\);",bulk_sql,re.S):
        schema,name,filename,spec=m.groups();filename=filename.replace('$(SqlSamplesSourceDataPath)','');t=tables[name];cols=t['columns']
        values=[]
        for rowno,row in enumerate(records(cache/filename,spec,len(cols)),1):
            if len(row)!=len(cols):raise ValueError((name,rowno,len(row),len(cols)))
            out=[]
            for c,v in zip(cols,row):
                if v=='\0':value=''
                elif not v and not c['required']:value=None
                elif c['sql_type']=='INTEGER':value=int(v)
                elif c['sql_type']=='BLOB':value=bytes.fromhex(v.removeprefix('0x')) if v else b''
                else:value=v
                out.append(value)
            values.append(out)
        conn.executemany('INSERT INTO '+q(name)+' ('+', '.join(q(c['name']) for c in cols)+') VALUES ('+','.join('?' for c in cols)+')',values)
        counts[name]=len(values);print(name,len(values),flush=True)
    for name in tables:counts.setdefault(name,0)
    conn.commit()
    # Exports do not include SQL Server setup-generated DDL/error log entries.
    conn.execute('PRAGMA foreign_keys=ON')
    fk=list(conn.execute('PRAGMA foreign_key_check'));integrity=conn.execute('PRAGMA integrity_check').fetchone()[0]
    if fk or integrity!='ok':raise ValueError((integrity,fk[:10]))
    for t in tables.values():
        if not t['definition']:issues.append('Missing table description: '+t['table'])
        for c in t['columns']:
            if not c['definition']:issues.append('Missing column description: '+t['table']+'.'+c['name'])
    dictionary=dict(name='Microsoft AdventureWorks OLTP',language='en',dbms='SQLite',description='Microsoft sample business data, converted from the official OLTP installation exports; not observed enterprise transactions.',tables=list(tables.values()))
    write_json(BASE/'input/data_dictionary.json',dictionary)
    (BASE/'evaluation/schema.sql').write_text('\n\n'.join(ddls)+'\n')
    manifest=dict(upstream_repository='microsoft/sql-server-samples',upstream_commit=COMMIT,upstream_path=PREFIX,table_count=len(tables),row_count=sum(counts.values()),row_counts=counts,foreign_key_count=sum(len(t['foreign_keys']) for t in tables.values()),integrity_check=integrity,foreign_key_violations=fk,missing_descriptions=issues,sqlite_sha256=hashlib.sha256(db.read_bytes()).hexdigest(),dictionary_sha256=hashlib.sha256((BASE/'input/data_dictionary.json').read_bytes()).hexdigest(),source_files=[dict(name=f['name'],git_blob_sha=f['sha']) for f in files])
    write_json(BASE/'source/provenance.json',manifest)
    doc=['# AdventureWorks data dictionary','','Descriptions below are extracted verbatim from Microsoft `MS_Description` extended properties. Missing descriptions remain explicitly absent; no event or Entity Type gold labels are added.','']
    for t in tables.values():
        doc+=['## '+t['source_schema']+'.'+t['table'],'',t['definition'] or '(No upstream description.)','','| Column | SQL Server type | SQLite type | Key | Description |','|---|---|---|---|---|']
        for c in t['columns']:doc+=['| '+' | '.join([c['name'],c['source_type'],c['sql_type'],'PK' if c['primary_key_position'] else 'FK' if c['foreign_keys'] else '',c['definition'].replace('|','\\|') or '(No upstream description.)'])+' |']
        doc+=['']
    (BASE/'docs/data_dictionary.md').write_text('\n'.join(line.rstrip() for line in doc).rstrip()+'\n');drawio(tables);conn.close()
    print(json.dumps({k:manifest[k] for k in ('table_count','row_count','foreign_key_count','missing_descriptions')},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);a=p.parse_args();build(a.cache)
