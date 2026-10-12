"""Project dictionary profile informed by ISO/IEC 11179 public scope statements."""
import json,csv,sqlite3,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SOURCES=[('ISO/IEC 11179-3:2023','https://www.iso.org/standard/78915.html','Registry identification, administration and definition concepts'),('ISO/IEC 11179-4:2004','https://www.iso.org/standard/35346.html','Semantic formulation of data definitions')]
def mdtable(headers,rows):
 esc=lambda x:str(x).replace('|','\\|').replace('\n',' ')
 return '| '+' | '.join(headers)+' |\n| '+' | '.join('---' for _ in headers)+' |\n'+''.join('| '+' | '.join(esc(x) for x in row)+' |\n' for row in rows)
def render(p):
 d=json.loads((p/'input/data_dictionary.json').read_text());con=sqlite3.connect(p/'input/database.sqlite');con.row_factory=sqlite3.Row
 basic=dict(dictionary_id='NL2EVENTLOG:'+p.name,version='2026-10-12',name=d['name'],description='English synthetic relational database for query-conditioned process-view and event-log extraction.',language='en',timezone='UTC',dbms='SQLite',namespace=p.name,maintainer='NL2EVENTLOG project maintainers',registration_status='Project-maintained draft; not ISO-registered or certified',source_policy='Source definitions are retained and authored lifecycle additions are identified in source/design documents.',standards_profile='Project profile informed by ISO/IEC 11179-3 and 11179-4 public abstracts; no full clause-by-clause conformance assessment.',layout='1 Dictionary basic information; 2 Table definitions; 3 Column definitions')
 d['dictionary_basic_information']=basic;tabledefs=[];coldefs=[]
 for t in d['tables']:
  n=t['table'];cols=list(con.execute('PRAGMA table_info('+n+')'));pk=[x['name'] for x in sorted(cols,key=lambda x:x['pk']) if x['pk']];fks=list(con.execute('PRAGMA foreign_key_list('+n+')'));ddl=con.execute('SELECT sql FROM sqlite_master WHERE name=?',(n,)).fetchone()[0]
  tr=dict(table_id=p.name+'.'+n,physical_name=n,logical_name=n.replace('_',' ').title(),definition=t['definition'],primary_key=', '.join(pk),foreign_keys='; '.join(x['from']+' → '+x['table']+'.'+x['to'] for x in fks) or 'None declared',event_encoding=t['event_encoding'],encoding_detail=t['encoding_detail'],rows=con.execute('SELECT COUNT(*) FROM '+n).fetchone()[0],origin='Authored lifecycle extension' if n.endswith('_activity') or n=='lifecycle_case_link' else 'Source-based table; adaptations documented in design/source_mapping.json',sql_constraints=ddl)
  tabledefs.append(tr);t['metadata_id']=tr['table_id']
  for c,r in zip(t['columns'],cols):
   cn=c['name'];unique=[]
   for ix in con.execute('PRAGMA index_list('+n+')'):
    if ix['unique']:unique.append(','.join(x['name'] for x in con.execute('PRAGMA index_info('+ix['name']+')')))
   constraints=c.get('constraints','') or 'See table DDL';samples=[x[0] for x in con.execute('SELECT DISTINCT '+cn+' FROM '+n+' WHERE '+cn+' IS NOT NULL LIMIT 3')];length='Not bounded by declared SQLite type' if r['type']=='TEXT' else 'Not applicable'
   rep='Identifier' if r['pk'] or any(f['from']==cn for f in fks) else 'Number' if r['type'] in ['INTEGER','REAL'] else 'Text'
   if any(x in cn for x in ['_at','_time','_date','timestamp']):rep='Date/time text'
   cr=dict(data_element_id=p.name+'.'+n+'.'+cn,table=n,ordinal=r['cid']+1,column=cn,logical_name=cn.replace('_',' ').title(),definition=c['definition'],object_class=n,property=cn,representation_class=rep,sql_type=r['type'],declared_length=length,required='yes' if r['pk'] or r['notnull'] else 'no',primary_key_position=r['pk'] or '',foreign_key='; '.join(f['table']+'.'+f['to'] for f in fks if f['from']==cn) or '',unique_key_memberships='; '.join(k for k in unique if cn in k.split(',')),default_value=r['dflt_value'] if r['dflt_value'] is not None else 'No SQL default',value_domain='SQL type and declared constraints: '+constraints,unit='UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning' if rep=='Date/time text' else 'See column definition; no implicit unit',example_values=json.dumps(samples),event_encoding=t['event_encoding'],origin=json.dumps(c.get('source_references',c.get('source_attribute',c.get('source_column','Authored / see source mapping')))),constraints=constraints)
   coldefs.append(cr);c.update(metadata_id=cr['data_element_id'],representation_class=rep,value_domain=cr['value_domain'],declared_length=length,default_value=cr['default_value'])
 d['standards_references']=[dict(standard=a,url=b,application=c) for a,b,c in SOURCES];(p/'input/data_dictionary.json').write_text(json.dumps(d,indent=2)+'\n')
 doc='# '+d['name']+' — data dictionary\n\n## 1. Dictionary basic information\n\n'+mdtable(['Field','Value'],basic.items())+'\n- The three-part layout is a project documentation choice, not a mandated ISO/IEC template.\n- ISO/IEC 11179-4 addresses semantic definitions rather than prescribing their formatting. Only public standard scope descriptions were consulted.\n- SQL keys and constraints are taken from the executable DB. SQLite TEXT has no declared maximum length unless an explicit constraint says otherwise. Examples are observed synthetic values, not additional allowed-value constraints.\n'+''.join('- ['+a+']('+b+'): '+c+'.\n' for a,b,c in SOURCES)
 doc+='\n## 2. Table definitions\n\n'+mdtable(['Metadata ID','Logical name','Physical name','Rows','PK','FK','Event encoding','Definition'],[[t[k] for k in ['table_id','logical_name','physical_name','rows','primary_key','foreign_keys','event_encoding','definition']] for t in tabledefs])
 doc+='\n- Row encoding: an event occurrence is represented by a row.\n- Column encoding: an object row stores one or more actual business milestone timestamps in dedicated columns.\n- No event encoding: contextual, reference, planned or relationship/index data; this does not mean the related business object lacks an event log.\n'
 for t in tabledefs:doc+='- **'+t['physical_name']+':** '+t['encoding_detail']+'\n'
 doc+='\n## 3. Column definitions\n'
 for t in tabledefs:
  doc+='\n### '+t['physical_name']+'\n\n'+mdtable(['Element ID','Logical / physical name','Definition','Representation / SQL type','Length','Required','PK / FK','Default','Value domain / constraints','Unit','Examples'],[[c['data_element_id'],c['logical_name']+' / '+c['column'],c['definition'],c['representation_class']+' / '+c['sql_type'],c['declared_length'],c['required'],str(c['primary_key_position'])+' / '+c['foreign_key'],c['default_value'],c['value_domain'],c['unit'],c['example_values']] for c in coldefs if c['table']==t['physical_name']])
  doc+='\n- **Declared table constraints:** `'+t['sql_constraints'].replace('`','')+'`\n'
 doc+='\n### Business meanings and extraction rules\n\n'+''.join('- '+x+'\n' for x in d['business_rules'])
 if (p/'docs/object_activity_design.md').exists():doc+='\n'+(p/'docs/object_activity_design.md').read_text().replace('# ','### ',1)
 for f in ['docs/data_dictionary.md','input/data_dictionary.md']:(p/f).write_text(doc)
 for filename,rows in [('table_definitions.csv',tabledefs),('data_dictionary.csv',coldefs)]:
  with (p/'docs'/filename).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 (p/'docs/dictionary_basic_information.json').write_text(json.dumps(basic,indent=2)+'\n');con.close()
if __name__=='__main__':
 for p in (ROOT/'datasets').iterdir():render(p)
