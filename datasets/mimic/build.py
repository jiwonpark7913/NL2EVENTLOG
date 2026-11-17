#!/usr/bin/env python3
"""Rebuild publicly available MIMIC-IV Demo 2.2 from official CSVs.

Only input/database.sqlite and input/data_dictionary.json are model inputs.
All review artifacts are separated from model input. No Gold is asserted.
"""
from __future__ import annotations
import argparse, csv, gzip, hashlib, html, json, re, sqlite3, xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
MAINTENANCE={"storetime","modifieddate","updated_at","created_at","recorded_at"}
TIMES={"admittime","dischtime","deathtime","intime","outtime","charttime","starttime","endtime",
       "startdate","enddate","chartdate","dod","edregtime","edouttime","transfertime",
       "schedtime","storetime","entertime","ordertime","verifiedtime","expirationtime",
       "scheduledtime","resulttime","specimentime","comments_date","comments_time"}
GROUPS={
 "Patient and admission":{"patients","admissions","transfers","services","diagnoses_icd","procedures_icd","drgcodes"},
 "Hospital orders and results":{"labevents","microbiologyevents","prescriptions","pharmacy","poe","poe_detail","emar","emar_detail","hcpcsevents","omr"},
 "ICU stay and observations":{"icustays","chartevents","inputevents","outputevents","procedureevents","datetimeevents","ingredientevents","caregiver"},
 "Reference dictionaries":{"d_items","d_labitems","d_icd_diagnoses","d_icd_procedures","d_hcpcs","provider"}}
REFS={"hadm_id":"admissions","subject_id":"patients","stay_id":"icustays",
      "caregiver_id":"caregiver"}
# A shared column name does not establish an FK to an arbitrary codebook.
# In particular, hospital lab itemid is NOT an ICU d_items itemid.
CONTEXT_REFS={"labevents":{"itemid":"d_labitems"},
              "chartevents":{"itemid":"d_items"},
              "inputevents":{"itemid":"d_items"},
              "outputevents":{"itemid":"d_items"},
              "procedureevents":{"itemid":"d_items"},
              "datetimeevents":{"itemid":"d_items"},
              "ingredientevents":{"itemid":"d_items"}}
def q(s):return '"'+s.replace('"','""')+'"'
def temporal(name):
 n=name.lower()
 if n in MAINTENANCE or n.endswith("_storetime"):return "maintenance"
 if n in TIMES or n.endswith(("_time","_date","time","date")) and not n.endswith(("_id","_code")):
  return "temporal"
 return "other"
def find_sources(root):
 found={}
 for p in root.rglob("*"):
  if not p.is_file() or not (p.name.endswith(".csv") or p.name.endswith(".csv.gz")):continue
  if p.stem=="demo_subject_id" or p.name.startswith("demo_subject_id."):continue
  name=p.name.removesuffix(".gz").removesuffix(".csv")
  if name in found:raise ValueError(f"Ambiguous CSV table: {name}")
  found[name]=p
 return found
def open_csv(path):
 return gzip.open(path,"rt",encoding="utf-8",newline="") if path.suffix==".gz" else path.open("r",encoding="utf-8",newline="")
def checksum(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()
def render(tables,cols,relationships):
 rows=defaultdict(list)
 for t in tables:
  if t.startswith("d_"): group="Reference dictionaries"
  else:group=next((g for g,members in GROUPS.items() if t in members),"Other")
  rows[group].append(t)
 order=list(GROUPS)+["Other"]
 positions={};width=450;head=48;line=20;gapx=85;gapy=52
 maxheight=0
 for j,grp in enumerate(order):
  y=85
  group_tables=sorted(rows[grp],key=lambda t:(not any(temporal(c)=="temporal" for c in cols[t]),t))
  for t in group_tables:
   h=head+line*len(cols[t])+14
   positions[t]=(35+j*(width+gapx),y,h);y+=h+gapy
  maxheight=max(maxheight,y)
 totalw=50+len(order)*(width+gapx);totalh=maxheight+70
 esc=lambda x:html.escape(str(x),quote=True)
 svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{totalw}" height="{totalh}" viewBox="0 0 {totalw} {totalh}">',
 '<rect width="100%" height="100%" fill="#f8fafc"/>']
 for j,g in enumerate(order):
  x=35+j*(width+gapx)
  svg.append(f'<text x="{x}" y="40" font-family="sans-serif" font-size="23" font-weight="bold" fill="#334155">{esc(g)}</text>')
 for a,b,key in relationships:
  if a not in positions or b not in positions:continue
  ax,ay,ah=positions[a];bx,by,bh=positions[b]
  svg.append(f'<path d="M{ax+width} {ay+22} L{bx} {by+22}" fill="none" stroke="#cbd5e1" stroke-width="1.5"><title>{esc(a+"."+key+" -> "+b)}</title></path>')
 for t,(x,y,h) in positions.items():
  svg.extend([f'<g class="table" data-table="{esc(t)}">',
   f'<rect x="{x}" y="{y}" width="{width}" height="{h}" rx="8" fill="white" stroke="#64748b" stroke-width="1.3"/>',
   f'<rect x="{x}" y="{y}" width="{width}" height="{head}" rx="8" fill="#dbeafe"/>',
   f'<text x="{x+13}" y="{y+31}" font-size="20" font-weight="bold" font-family="sans-serif" fill="#0f172a">{esc(t)}</text>'])
  for k,c in enumerate(cols[t]):
   kind=temporal(c);fill={"temporal":"#bae6fd","maintenance":"#fde68a","other":"transparent"}[kind]
   cy=y+head+k*line
   if kind!="other":svg.append(f'<rect x="{x+7}" y="{cy}" width="{width-14}" height="{line}" rx="3" fill="{fill}"/>')
   svg.append(f'<text x="{x+14}" y="{cy+15}" font-size="14" font-family="monospace" fill="#1e293b">{esc(c)}</text>')
  svg.append("</g>")
 svg.append("</svg>")
 return "\n".join(svg),positions,(totalw,totalh)
def build(src,make_png=False):
 files=find_sources(src)
 if not files:raise RuntimeError(f"No source CSVs found under {src}")
 (ROOT/"input").mkdir(exist_ok=True);(ROOT/"docs").mkdir(exist_ok=True);(ROOT/"review").mkdir(exist_ok=True)
 db=ROOT/"input/database.sqlite"
 if db.exists():db.unlink()
 conn=sqlite3.connect(db)
 dd={"dataset":"MIMIC-IV Clinical Database Demo","version":"2.2","source":"https://physionet.org/content/mimic-iv-demo/2.2/",
     "note":"CSV source has no declared PK/FK. Identifiers and connections are candidate relationships, not enforced keys.",
     "tables":{}}
 cols={};count=0
 for name,path in sorted(files.items()):
  with open_csv(path) as f:
   reader=csv.reader(f);header=next(reader)
   if len(header)!=len(set(header)):raise ValueError("Duplicated column name in "+name)
   cols[name]=header
   conn.execute("CREATE TABLE "+q(name)+"("+",".join(q(c)+" TEXT" for c in header)+")")
   batch=[];n=0
   for row in reader:
    if len(row)!=len(header):raise ValueError(f"{name}: row {n} has {len(row)} fields")
    batch.append(tuple(v if v!="" else None for v in row))
    if len(batch)>=5000:
     conn.executemany("INSERT INTO "+q(name)+" VALUES ("+",".join("?" for _ in header)+")",batch);batch=[]
    n+=1
   if batch:conn.executemany("INSERT INTO "+q(name)+" VALUES ("+",".join("?" for _ in header)+")",batch)
  count+=n
  dd["tables"][name]={"row_count":n,"source_sha256":checksum(path),"columns":[
   {"name":c,"sql_type":"TEXT","temporal_role":temporal(c),"definition":None,
    "timestamp_semantics":"unverified_candidate" if temporal(c)!="other" else None} for c in header],
    "primary_key":None,"foreign_keys_declared":[]}
 conn.commit()
 if conn.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise RuntimeError("SQLite integrity_check failed")
 refs=[]
 for t,columns in cols.items():
  for c in columns:
   target=CONTEXT_REFS.get(t,{}).get(c,REFS.get(c))
   if target and target!=t and target in cols and c in cols[target]:
    refs.append((t,target,c))
 dd["candidate_relationships"]=[{"source_table":a,"target_table":b,"column":c,"status":"inferred_not_declared"} for a,b,c in refs]
 dd["statistics"]={"tables":len(files),"rows":count,"columns":sum(map(len,cols.values()))}
 (ROOT/"input/data_dictionary.json").write_text(json.dumps(dd,indent=2,ensure_ascii=False)+"\n")
 lines=["# MIMIC-IV Demo 2.2 — Data Dictionary","","Candidate relationships are not declared PK/FK constraints. Timestamp colors indicate candidates, not Gold events.","",
        f"Tables: {len(files)} · Rows: {count} · Columns: {sum(map(len,cols.values()))}",""]
 for t,columns in cols.items():
  lines.extend([f"## {t}",f"Rows: {dd['tables'][t]['row_count']}","","| Column | SQLite type | Temporal class |","|---|---|---|"])
  lines += [f"| {c} | TEXT | {temporal(c)} |" for c in columns];lines.append("")
 (ROOT/"docs/data_dictionary.md").write_text("\n".join(lines)+"\n")
 svg,coords,(w,h)=render(files,cols,refs)
 (ROOT/"docs/schema.svg").write_text(svg)
 graph=ET.Element("mxfile",host="app.diagrams.net")
 diagram=ET.SubElement(graph,"diagram",name="MIMIC-IV Demo")
 model=ET.SubElement(diagram,"mxGraphModel",page="1",pageWidth=str(w),pageHeight=str(h))
 root=ET.SubElement(model,"root");ET.SubElement(root,"mxCell",id="0");ET.SubElement(root,"mxCell",id="1",parent="0")
 for i,(t,(x,y,height)) in enumerate(coords.items(),start=2):
  def colored(c):
   color={"temporal":"#bae6fd","maintenance":"#fde68a","other":"#ffffff"}[temporal(c)]
   return '<div style="background-color:'+color+';padding:2px 6px">'+html.escape(c)+'</div>'
  label="<b>"+html.escape(t)+"</b><hr/>"+"".join(colored(c) for c in cols[t])
  cell=ET.SubElement(root,"mxCell",id="table_"+t,value=label,style="rounded=1;whiteSpace=wrap;html=1;fillColor=#EFF6FF;align=left;verticalAlign=top;spacing=9;",vertex="1",parent="1")
  ET.SubElement(cell,"mxGeometry",x=str(x),y=str(y),width="450",height=str(height),**{"as":"geometry"})
 for i,(child,parent,key) in enumerate(refs):
  edge=ET.SubElement(root,"mxCell",id=f"link_{i}",value=key+" → "+parent,
     style="edgeStyle=orthogonalEdgeStyle;rounded=1;endArrow=block;html=1;strokeColor=#94a3b8;",
     edge="1",parent="1",source="table_"+child,target="table_"+parent)
  ET.SubElement(edge,"mxGeometry",relative="1",**{"as":"geometry"})
 ET.ElementTree(graph).write(ROOT/"docs/schema.drawio",encoding="utf-8",xml_declaration=True)
 # Offline scrollable viewer. The embedded SVG is the same source as the PNG/draw.io layout.
 viewer="""<!doctype html><meta charset="utf-8"><title>MIMIC-IV Schema Explorer</title>
 <style>body{margin:0;font:15px Arial;background:#f1f5f9}header{position:sticky;top:0;background:#fff;padding:12px;z-index:2;box-shadow:0 1px 3px #bbb}
 #view{height:calc(100vh - 95px);overflow:auto}#drawing{transform-origin:top left}input{padding:8px;width:260px}button{padding:8px}</style>
 <header><b>MIMIC-IV Demo ERD</b> &nbsp; blue: time candidate · yellow: storage time &nbsp;
 <input id="find" placeholder="Find table..." list="names"><datalist id="names"></datalist>
 <button onclick="zoom(.85)">−</button><button onclick="zoom(1.15)">+</button><span id="scale"></span></header>
 <div id="view"><div id="drawing">__SVG__</div></div>
 <script>let z=1;const e=document.getElementById('drawing'),v=document.getElementById('view');
 const tables=[...document.querySelectorAll('g[data-table]')],d=document.querySelector('#names');
 tables.forEach(t=>{const o=document.createElement('option');o.value=t.dataset.table;d.append(o)});
 function zoom(m){z*=m;e.style.transform='scale('+z+')';e.style.width=(__W__*z)+'px';e.style.height=(__H__*z)+'px';document.querySelector('#scale').textContent=Math.round(z*100)+'%'}
 document.querySelector('#find').addEventListener('input',ev=>{const t=tables.find(x=>x.dataset.table.toLowerCase()===ev.target.value.toLowerCase());
 if(t){t.scrollIntoView({block:'center',inline:'center'});t.querySelector('rect').setAttribute('stroke','#ef4444')}});
 zoom(1);</script>"""
 (ROOT/"docs/schema.html").write_text(viewer.replace("__SVG__",svg).replace("__W__",str(w)).replace("__H__",str(h)))
 if make_png:
  import cairosvg
  cairosvg.svg2png(bytestring=svg.encode(),write_to=str(ROOT/"docs/schema.png"),scale=1)
 # Human-only preview for each table; avoid writing source rows to model input.
 review=ROOT/"review/database";(review/"tables").mkdir(parents=True,exist_ok=True)
 listing=["# MIMIC-IV Demo — database inspection","","[Scrollable ERD](../../docs/schema.html) · [Dictionary](../../docs/data_dictionary.md) · [draw.io](../../docs/schema.drawio)","",
          "![Schema](../../docs/schema.svg)","","| Table | Rows | Preview |","|---|---:|---|"]
 for t in sorted(files):
  rows=conn.execute("SELECT * FROM "+q(t)+" LIMIT 10").fetchall()
  values=lambda x:str(x).replace("|","\\|").replace("\n"," ") if x is not None else "NULL"
  content=["# "+t,"","Human-only sample; **not** Gold.","","| "+" | ".join(cols[t])+" |","|"+"|".join("---" for _ in cols[t])+"|"]
  content += ["| "+" | ".join(values(x) for x in row)+" |" for row in rows]
  (review/"tables"/(t+".md")).write_text("\n".join(content)+"\n")
  listing.append(f"| {t} | {dd['tables'][t]['row_count']} | [First ten rows](tables/{t}.md) |")
 (review/"README.md").write_text("\n".join(listing)+"\n")
 conn.close()
 print(json.dumps(dd["statistics"],indent=2))
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--source",required=True,type=Path);p.add_argument("--png",action="store_true")
 a=p.parse_args();build(a.source,a.png)
