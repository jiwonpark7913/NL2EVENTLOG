"""Render ordinary dictionary metadata separately from author-only README answers."""
from pathlib import Path
from collections import defaultdict
import json,csv,html,xml.etree.ElementTree as ET

def mdtable(headers,rows):
 esc=lambda v:str(v).replace('|','\\|').replace('\n',' ')
 return '| '+' | '.join(headers)+' |\n| '+' | '.join('---' for _ in headers)+' |\n'+''.join('| '+' | '.join(esc(v) for v in row)+' |\n' for row in rows)
def save_csv(path,rows):
 with path.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def render_dictionary(p,con,d):
 # This document is model input. Only ordinary schema/business metadata is rendered.
 basic=dict(dictionary_id='NL2EVENTLOG:'+p.name,name=d['name'],version='2026-10-29',language='en',dbms='SQLite',timezone='UTC',description=d['description'],status='Project-maintained synthetic business-data definitions',standards_profile='Three-part project profile informed by public ISO/IEC 11179-3 and 11179-4 scope statements; not a certification or full conformance assessment.',source_policy=('Schema-informed manufacturing simulation; authored additions are documented separately.' if p.name=='plateflow_new' else 'Schema-informed warehouse simulation; authored additions are documented separately.'))
 tabledefs=[];coldefs=[]
 for t in d['tables']:
  name=t['table'];fks=list(con.execute('PRAGMA foreign_key_list('+name+')'));groups=defaultdict(list)
  for f in fks:groups[f['id']].append(f)
  refs=['('+','.join(f['from'] for f in sorted(g,key=lambda f:f['seq']))+') → '+g[0]['table']+'('+','.join(f['to'] for f in sorted(g,key=lambda f:f['seq']))+')' for g in groups.values()]
  tabledefs.append(dict(table_id=p.name+'.'+name,physical_name=name,logical_name=name.replace('_',' ').title(),definition=t['definition'],primary_key=', '.join(t['primary_key']),foreign_keys='; '.join(refs) or 'None declared',sql_definition=t['sql_definition']))
  info=list(con.execute('PRAGMA table_info('+name+')'))
  for c,r in zip(t['columns'],info):
   coldefs.append(dict(element_id=p.name+'.'+name+'.'+c['name'],table=name,ordinal=r['cid']+1,column=c['name'],definition=c['definition'],sql_type=c['sql_type'],required=c['required'],primary_key_position=c['primary_key_position'] or '',foreign_key='; '.join(f['table']+'.'+f['column'] for f in c['foreign_keys']),default=c['default'] if c['default'] is not None else 'No SQL default',length='Unbounded SQLite TEXT' if c['sql_type']=='TEXT' else 'Not applicable',unit=c['unit'] or 'Not applicable',value_domain='Declared SQL type and constraints; see table DDL'))
 doc='# '+d['name']+' — data dictionary\n\n## 1. Dictionary basic information\n\n'+mdtable(['Field','Value'],basic.items())+'\n- The three-part layout is a project choice. ISO/IEC 11179-3 concerns registry facilities and 11179-4 concerns semantic definitions; the public scope statements do not mandate this template.\n- A composite primary key is one key over its full tuple. All SQL constraints below are taken from the executable schema.\n- References: [ISO/IEC 11179-3](https://www.iso.org/standard/78915.html), [ISO/IEC 11179-4](https://www.iso.org/standard/35346.html).\n\n## 2. Table definitions\n\n'+mdtable(['Table ID','Logical / physical name','PK','FK','Business definition'],[[t['table_id'],t['logical_name']+' / '+t['physical_name'],t['primary_key'],t['foreign_keys'],t['definition']] for t in tabledefs])+'\n## 3. Column definitions\n'
 for t in tabledefs:
  doc+='\n### '+t['physical_name']+'\n\n'+mdtable(['Element ID','Column','SQL type','Required','PK position','FK','Default','Length','Unit','Definition'],[[c[k] for k in ['element_id','column','sql_type','required','primary_key_position','foreign_key','default','length','unit','definition']] for c in coldefs if c['table']==t['physical_name']])+'\n```sql\n'+t['sql_definition']+';\n```\n'
 doc+='\n### Business codes\n\n'+mdtable(['Process group' if p.name=='plateflow_new' else 'Code family','Code','Business meaning'],[[c.get('process_group',c.get('code_family')),c['code'],c['meaning']] for c in d['code_values']])+'\n### Business rules\n\n'+''.join('- '+x+'\n' for x in d['business_rules'])
 for f in ['input/data_dictionary.md','docs/data_dictionary.md']:(p/f).write_text(doc)
 (p/'docs/dictionary_basic_information.json').write_text(json.dumps(basic,indent=2)+'\n');save_csv(p/'docs/table_definitions.csv',tabledefs);save_csv(p/'docs/data_dictionary.csv',coldefs)
 return basic

def diagram(p,con,d,order=None):
 import fitz
 if order is None:order=[['slab_material','planned_rolling_instruction','rolling_instruction'],['as_rolled_material','process_code','equipment'],['furnace_operation_history','rolling_operation_history','plate_material'],['finishing_operation_history','dimension_inspection','plate_quality_review']]
 grid={t:(c,r) for r,row in enumerate(order) for c,t in enumerate(row)};width=1980;bw=600;kw=90
 info={t['table']:dict(cols=list(con.execute('PRAGMA table_info('+t['table']+')')),fks=list(con.execute('PRAGMA foreign_key_list('+t['table']+')')),rows=con.execute('SELECT COUNT(*) FROM '+t['table']).fetchone()[0]) for t in d['tables']}
 heights={t:116+32*len(i['cols']) for t,i in info.items()};yrow={};cursor=140
 for r,row in enumerate(order):yrow[r]=cursor;cursor+=max(heights[t] for t in row)+90
 height=cursor;pos={t:(40+c*650,yrow[r]) for t,(c,r) in grid.items()};relationships=[]
 for t,i in info.items():
  groups=defaultdict(list)
  for f in i['fks']:groups[f['id']].append(f)
  unique=[{r['name'] for r in con.execute('PRAGMA index_info('+ix['name']+')')} for ix in con.execute('PRAGMA index_list('+t+')') if ix['unique']]
  for group in groups.values():
   group.sort(key=lambda f:f['seq']);cols={f['from'] for f in group};relationships.append(dict(parent=group[0]['table'],child=t,columns=[f['from'] for f in group],parent_columns=[f['to'] for f in group],cardinality='1 : 0..1' if any(u<=cols for u in unique) else '1 : 0..N'))
 esc=lambda x:html.escape(str(x))
 svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="white"/>', f'<text x="40" y="48" font-family="sans-serif" font-size="34" font-weight="bold">{esc(d["name"])} · {len(info)} business tables</text>','<text x="40" y="82" font-family="sans-serif" font-size="22" fill="#53647c">PK/FK are declared keys. Arrows: parent → child. Full column lists; editable relationships in schema.drawio.</text>']
 mx=ET.Element('mxfile',host='app.diagrams.net');di=ET.SubElement(mx,'diagram',name=d['name'],id=p.name);model=ET.SubElement(di,'mxGraphModel',grid='1',page='1',pageWidth=str(width),pageHeight=str(height));root=ET.SubElement(model,'root');ET.SubElement(root,'mxCell',id='0');ET.SubElement(root,'mxCell',id='1',parent='0')
 edges=[]
 for idx,r in enumerate(relationships):
  par,ch=r['parent'],r['child'];x1,y1=pos[par];x2,y2=pos[ch];h1=heights[par];diff=grid[ch][1]-grid[par][1];way=[]
  if diff==1:
   sx,sy,tx,ty=x1+bw/2,y1+h1,x2+bw/2,y2;way=[(sx,ty-35),(tx,ty-35)];ports='exitX=0.5;exitY=1;entryX=0.5;entryY=0;'
  elif diff==0:
   sx,sy,tx,ty=x1+bw/2,y1,x2+bw/2,y2;way=[(sx,y1-30),(tx,y1-30)];ports='exitX=0.5;exitY=0;entryX=0.5;entryY=0;'
  else:
   left=grid[par][0]==0;sx=x1 if left else x1+bw;sy=y1+h1/2;tx=x2+bw/2;ty=y2;gutter=20 if left else x1+bw+25;way=[(gutter,sy),(gutter,ty-35),(tx,ty-35)];ports=f'exitX={0 if left else 1};exitY=0.5;entryX=0.5;entryY=0;'
  path=f'M {sx} {sy} '+' '.join(f'L {x} {y}' for x,y in way)+f' L {tx} {ty}'
  edges.append(f'<path d="{path}" fill="none" stroke="#69788e" stroke-width="2"/>');points=f'{tx},{ty} {tx-5},{ty-10} {tx+5},{ty-10}' if diff else f'{tx},{ty} {tx-5},{ty-10} {tx+5},{ty-10}';edges.append(f'<polygon points="{points}" fill="#69788e"/>')
  edge=ET.SubElement(root,'mxCell',id='e'+str(idx),value=', '.join(r['columns'])+'; '+r['cardinality'],style='edgeStyle=orthogonalEdgeStyle;rounded=0;endArrow=block;html=1;'+ports,edge='1',parent='1',source=par,target=ch);geo=ET.SubElement(edge,'mxGeometry',relative='1',attrib={'as':'geometry'});arr=ET.SubElement(geo,'Array',attrib={'as':'points'})
  for x,y in way:ET.SubElement(arr,'mxPoint',x=str(x),y=str(y))
 for name,i in info.items():
  x,y=pos[name];bh=heights[name];divider=74+32*len(i['cols']);pk={r['name'] for r in i['cols'] if r['pk']};fk={r['from'] for r in i['fks']}
  svg.extend([f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="white" stroke="#9a9a9a"/>',f'<rect x="{x}" y="{y}" width="{bw}" height="58" fill="#eeeeee" stroke="#9a9a9a"/>',f'<text x="{x+14}" y="{y+38}" font-family="sans-serif" font-size="26" font-weight="bold">{esc(name)}</text>',f'<path d="M {x+kw} {y+58} L {x+kw} {y+divider} M {x} {y+divider} L {x+bw} {y+divider}" stroke="#9a9a9a" fill="none"/>'])
  node=ET.SubElement(root,'mxCell',id=name,value=name,style='shape=swimlane;startSize=58;rounded=0;html=1;align=left;spacingLeft=14;fillColor=#eeeeee;swimlaneFillColor=#ffffff;strokeColor=#9a9a9a;fontSize=26;fontStyle=1;collapsible=0;',vertex='1',parent='1');ET.SubElement(node,'mxGeometry',x=str(x),y=str(y),width=str(bw),height=str(bh),attrib={'as':'geometry'})
  for suffix,a,b,c,e in [('key_divider',kw,58,kw,divider),('footer_divider',0,divider,bw,divider)]:
   line=ET.SubElement(root,'mxCell',id=name+'_'+suffix,style='endArrow=none;startArrow=none;strokeColor=#9a9a9a;',edge='1',parent=name);geo=ET.SubElement(line,'mxGeometry',relative='1',attrib={'as':'geometry'});ET.SubElement(geo,'mxPoint',x=str(a),y=str(b),attrib={'as':'sourcePoint'});ET.SubElement(geo,'mxPoint',x=str(c),y=str(e),attrib={'as':'targetPoint'})
  for j,c in enumerate(i['cols']):
   tags=', '.join(k for k,yes in [('PK',c['name'] in pk),('FK',c['name'] in fk)] if yes)
   svg.extend([f'<text x="{x+kw/2}" y="{y+92+j*32}" text-anchor="middle" font-family="sans-serif" font-size="20" fill="#26384e">{tags}</text>',f'<text x="{x+kw+14}" y="{y+92+j*32}" font-family="sans-serif" font-size="24" fill="#26384e">{esc(c["name"])}</text>'])
   for part,value,cx,cw,fs,align in [('key',tags,0,kw,20,'center'),('name',c['name'],kw,bw-kw,24,'left')]:
    cell=ET.SubElement(root,'mxCell',id=name+'_'+part+str(j),value=value,style=f'text;html=1;align={align};verticalAlign=middle;spacingLeft={14 if part=="name" else 0};fontSize={fs};fontStyle=0;fillColor=none;strokeColor=none;',vertex='1',parent=name,connectable='0');ET.SubElement(cell,'mxGeometry',x=str(cx),y=str(74+j*32),width=str(cw),height='32',attrib={'as':'geometry'})
  footer=str(i['rows'])+' rows · '+str(len(i['cols']))+' columns';svg.append(f'<text x="{x+14}" y="{y+bh-13}" font-family="sans-serif" font-size="21" fill="#555555">{footer}</text>');cell=ET.SubElement(root,'mxCell',id=name+'_footer',value=footer,style='text;align=left;spacingLeft=14;fontSize=21;fontStyle=0;fillColor=none;strokeColor=none;',vertex='1',parent=name,connectable='0');ET.SubElement(cell,'mxGeometry',x='0',y=str(divider),width=str(bw),height=str(bh-divider),attrib={'as':'geometry'})
 svg.extend(edges);svg.append('</svg>');ET.ElementTree(mx).write(p/'docs/schema.drawio',encoding='utf-8',xml_declaration=True);doc=fitz.open(stream=''.join(svg).encode(),filetype='svg');doc[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(p/'docs/schema.png')
 summary=dict(table_count=len(info),tables={n:dict(rows=i['rows'],columns=len(i['cols']),primary_key=[c['name'] for c in i['cols'] if c['pk']]) for n,i in info.items()},relationships=relationships);(p/'docs/schema_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 (p/'docs/schema_overview.md').write_text('# '+d['name']+' — schema overview\n\n- [Editable draw.io diagram](schema.drawio) · [Data dictionary](data_dictionary.md)\n\n'+mdtable(['Table','Rows','Columns','Business role'],[[t['table'],info[t['table']]['rows'],len(info[t['table']]['cols']),t['definition']] for t in d['tables']])+'\n'+mdtable(['Parent','Child','FK columns','Referenced columns','Cardinality'],[[r['parent'],r['child'],', '.join(r['columns']),', '.join(r['parent_columns']),r['cardinality']] for r in relationships]))

def render(p,con,d,report,questions,coverage,encoding):
 render_dictionary(p,con,d);diagram(p,con,d)
 stats=[]
 for typ in ['Q1','Q2','Q3','Q4']:
  qs=[q for q in questions if q['question_type']==typ];stats.append([typ,len(qs),sum(q['answerability']=='answerable' for q in qs),sum(q['answerability']!='answerable' for q in qs),f"{sum(q['requested_activity_count'] for q in qs)/len(qs):.2f}"])
 statstable=mdtable(['Type','Questions','Answerable','Non-answerable','Avg. requested activity types'],stats)
 questiondoc='# PlateFlow New questions\n\n## Question types and pairs\n\n'+statstable+'\n- Requested activity averages include unavailable requests. Process View includes its activity scope.\n- Seeds are frozen before assistant-LLM paraphrasing; exact paired scopes and Gold are checked.\n\n'+mdtable(['ID','Type','Paired with','Answerability','Requested activities','Extractable activities','Question'],[[q['question_id'],q['question_type'],q['pair_of'],q['answerability'],q['requested_activity_count'],q['extractable_activity_count'],q['text']] for q in questions]);(p/'docs/questions.md').write_text(questiondoc)
 scope=mdtable(['Object / case type','Cases','Activity types','Cases without events','Recorded activity scope'],[[c['case_concept'],c['case_count'],c['activity_count'],c['cases_without_events'],', '.join(c['activities'])] for c in coverage]);(p/'docs/object_activity_design.md').write_text('# Objects, activities and situations\n\n'+scope+'\n- Main material cases follow genealogy and actual business-key paths. Auxiliary occurrence cases retain a single completion per completed record. Equipment timelines aggregate its completed work, not its maintenance times.\n')
 (p/'docs/object_event_logs.md').write_text('# Object-specific full lifecycle Gold logs\n\n'+mdtable(['Case type','Q3','Q4','Cases','Event rows'],[[c['case_concept'],'NF'+str(i).zfill(2),'NF'+str(i).zfill(2)+'P',c['case_count'],c['event_rows']] for i,c in enumerate(coverage,1)])+'\n- Empty and unfinished cases remain in private/case_population.json and ES.case_population even when they have no CSV rows.\n- These are case-based CSV logs, not OCEL. A shared event may appear in different case views, never twice within the same case.\n')
 inv=json.loads((p/'docs/timestamp_columns.json').read_text());(p/'docs/timestamp_columns.md').write_text('# Timestamp inventory\n\n- This is author evaluation material; it is excluded from the model-input manifest.\n\n'+mdtable(['Table','Column','Role','Selected as Gold time','Non-null rows'],[[r['table'],r['column'],r['role'],r['used_as_event_time'],r['non_null_rows']] for r in inv['columns']]))
 r=report;ts=r['timestamp_summary'];counts=mdtable(['Dataset','Tables','Object / case types','Activity types','Timestamp columns','Event timestamp columns','Distinct events','Questions','Gold CSVs'],[['PlateFlow New',len(r['table_rows']),r['semantic_object_types'],len(r['activity_counts']),ts['timestamp_columns'],ts['event_timestamp_columns'],r['events'],r['total_questions'],r['answerable_questions']]])
 classification=mdtable(['Table','Base activity identity','Activity carrier','Stored time columns','Gold time columns','Emitted phase profile'],[[t,encoding[t][0],encoding[t][1] or '—',', '.join(c['name'] for c in con.execute('PRAGMA table_info('+t+')') if c['name'].endswith('_at')) or '—',', '.join(sorted({s['timestamp_column'] for s in json.loads((p/'private/persistence_mapping.json').read_text()) if s['table']==t})) or '—','completion only' if encoding[t][0]=='Row' or t=='plate_quality_review' else 'point milestones' if encoding[t][0]=='Column' else 'none'] for t in d_table_names(d)])
 readme='''# PlateFlow New dataset

- **Purpose:** test event-source discovery and activity-carrier-based row/column classification from the database and an ordinary business dictionary.
- **Domain:** synthetic plate production informed by the existing Korean manufacturing-company metadata adaptation. This is an independent authored variant, not observed production data or a lossless copy of the original schema.
- **Build:** `python datasets/plateflow_new/build.py` from the repository root. **Validate:** `python datasets/plateflow_new/validate.py`.
- Simulation uses the standard library; PNG rendering additionally uses PyMuPDF. No external LLM API is needed to rebuild frozen question pairs.

'''+counts+'''
## Event storage answers — author reference only

- Candidate discovery considers timestamp presence, then distinguishes actual business times from plans and database maintenance.
- Row encoding means activity kind is selected by a carrier value. Having both start and finish times does not change that classification.
- Column encoding means no activity-kind carrier exists; the table or timestamp-column business meaning determines the activity. Repeated records or a single timestamp do not make a table row encoded.
- Timestamp count alone does not establish a mixed representation. The table below classifies base activity identity and states the emitted phase profile separately. This variant contains 3 row tables, 6 column tables and 3 tables with no direct business events.
- Only this README explicitly lists table classification and activity carriers. Dictionary JSON, Markdown and CSV have no such annotations or table-to-activity extraction answers.

'''+classification+'''
- `operation_code=HT` means furnace heating in FURNACE and heat treatment in FINISHING. Process context resolves the meaning; it is not a globally unique activity code.
- `equipment_code` identifies a machine, and `steel_grade` identifies a grade. Neither selects an activity kind.
- PASS and FAIL are outcomes of the same dimensional-inspection activity. APPROVED and REWORK are outcomes of the same quality-review activity. They are not activity carriers.
- `dimension_inspection` has one actual timestamp and a fixed activity meaning; reinspections remain column encoded. `plate_quality_review` has start/finish times and outcome codes but no activity carrier; it is also column encoded.
- Instruction issue has a single timestamp and no carrier. All three work histories have coded activity kinds plus start/finish times and are row encoded.

## Completion policy and scenarios

- Gold logs emit actual point milestones and completed work only. Work/review `started_at` values do not create additional start activity labels; NULL finish produces no completion.
- Scenarios include received-only slabs, draft plans, issued instructions awaiting work, unfinished heating/rolling, multiple pieces per mother, failed inspections, completed rework reviews, repeat heat treatment, reinspections, pending reviews and unpacked pieces.
- Every repeat work or inspection/review round keeps its own occurrence ID. No completed work is inferred from plans, equipment maintenance or mother-record timestamps.
- Main material and instruction logs require joins across business tables. Mother/slab views include descendant-piece work. Record cases preserve their own identities, and equipment cases use the actual equipment FK.

## Objects, activities and situations

'''+scope+'''
- Case scopes are fixed before query construction; a full-lifecycle request means all recorded business events in that declared scope, not inferred upstream casting or downstream dispatch.
- The 11 case types include independent work/inspection/review occurrence records and equipment. process_code is reference data and has no case log. A directly non-event table may still define a case with logs from related work tables.
- [Full lifecycle Gold files](docs/object_event_logs.md)

## Question types and pairs

'''+statstable+'''
- Q1 seeds are paraphrased by the assistant LLM into Q2; Q3 seeds are paraphrased into Q4. Prompts, outputs and author review notes are saved in source/llm_paraphrases.json; no separate model/API call is claimed.
- Pairs share exactly the same Process View, ES, case population and Gold CSV content. Q3/Q4 mention only their case concept and use its fixed default recorded scope.
- Requested-activity averages include the two unsupported semantic requests and their paraphrases. Casting and truck dispatch cannot be reconstructed from this database.
- [Questions and requested/extractable activity counts](docs/questions.md)

## Model input boundary

- `input/model_input_manifest.json` is an allowlist of model inputs. Feed only the files listed there.
- Inputs contain the SQLite database, SQL schema, business dictionary and question text. input/task_context.md supplies a source-agnostic recorded-lifecycle scope convention, not table bindings or enumerated activities.
- README, source, design, docs, private, build code and validation reports are author/evaluation material. Exclude these from model context; in particular, the ordinary dictionary excludes both classification and extraction-selection answers.
- private/questions.jsonl has question types, answerability and activity-count annotations. private/gold.jsonl, persistence_mapping.json, case_paths.json and canonical_history.jsonl contain extraction answers. None are model inputs.
- **Gold CSV columns:** event_id, case_id, activity, timestamp. Event IDs and physical-source provenance are maintained separately; the same case/event pair is emitted once.

## Schema and documentation

![Schema](docs/schema.png)

- [Editable draw.io](docs/schema.drawio)
- [Table inventory and FK relationships](docs/schema_overview.md)
- [Three-part English data dictionary](docs/data_dictionary.md)
- [Dictionary CSV](docs/data_dictionary.csv) · [Table definitions CSV](docs/table_definitions.csv)
- [Author timestamp inventory](docs/timestamp_columns.md)
- [Source adaptation](design/source_mapping.json)
- [Validation report](validation_report.json)

## Validation scope

- Independent generation-time histories are compared with all SQL results and Gold CSVs. Checks cover completion-only times, group-qualified codes, outcome/machine-code distractors, genealogy, repetition, unfinished/empty cases, PK/FK integrity, dictionary leakage and exact question pairs.
- Tests establish dataset consistency. They do not measure an LLM's event-table discovery or classification accuracy. The separate NL2EventLog classifier must still be evaluated using the allowlisted inputs.
'''
 readme+='\n## Activity identity × timestamp phase audit\n\n- Classification has two axes: how base activity identity is represented, and which occurrence phases are stored/emitted. A code is an activity carrier only when it selects the work kind; outcome, grade and machine codes are not carriers.\n- This dataset retains the previously agreed completion-only Gold policy. It is not an all-four-cases phase benchmark.\n\n| Requested case | Physical representation in PlateFlow New | Current Gold coverage |\n|---|---|---|\n| A: no carrier, one timestamp | rolling_instruction and dimension_inspection | Covered: one fixed milestone/completion |\n| B: no carrier, multiple timestamps | slab/plan/plate milestones; plate_quality_review start/finish | Multiple point milestones are covered, but quality-review start is not emitted; paired-phase coverage is partial |\n| C: activity carrier, one timestamp | None: each coded work history stores both start and finish | Not physically covered; selecting finish alone does not make a one-timestamp table |\n| D: activity carrier, multiple timestamps | All three coded work-history tables | Base activity is row-carried, but only completion is emitted; paired-phase coverage is partial |\n\n- The history tables are **Row activity identity × stored start/complete phases × completion-only extraction**. Their two timestamps do not imply two different base activities. A mixed representation label is acceptable only when these two axes remain explicit.\n- WarehouseFlow New provides all four cases with phased Gold. PlateFlow New retains its DB, occurrence IDs and completion logs.\n'
 (p/'README.md').write_text(readme)
def d_table_names(d):return [t['table'] for t in d['tables']]

if __name__=='__main__':
 import sqlite3
 from build import ENCODING
 p=Path(__file__).resolve().parent
 con=sqlite3.connect(p/'input/database.sqlite');con.row_factory=sqlite3.Row
 d=json.loads((p/'input/data_dictionary.json').read_text());r=json.loads((p/'validation_report.json').read_text());q=[json.loads(s) for s in (p/'private/questions.jsonl').read_text().splitlines()]
 render(p,con,d,r,q,r['object_view_coverage'],ENCODING)
 con.close()
