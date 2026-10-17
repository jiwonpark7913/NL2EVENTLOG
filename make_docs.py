"""Generate schema documentation and editable diagrams from actual SQLite schemas."""
from pathlib import Path
import sqlite3,json,html,re,xml.etree.ElementTree as ET
from event_encoding import annotate
import fitz
from readability import format_documents
ROOT=Path(__file__).resolve().parent
def esc(s):return html.escape(str(s))
def build(name,positions,title):
 p=ROOT/"datasets"/name;out=p/"docs";out.mkdir(exist_ok=True)
 d=annotate(p);tables=d["tables"]
 con=sqlite3.connect(p/"input/database.sqlite");con.row_factory=sqlite3.Row
 info={t["table"]:dict(cols=list(con.execute("PRAGMA table_info("+t["table"]+")")),fk=list(con.execute("PRAGMA foreign_key_list("+t["table"]+")")),rows=con.execute("SELECT COUNT(*) FROM "+t["table"]).fetchone()[0]) for t in tables}
 docs="# "+title+" — table and column dictionary\n\nGenerated from the executable SQLite schema and English metadata.\n\n"
 docs+="| Table | Rows | Columns | Event encoding | Primary key | Role |\n|---|---:|---:|---|---|---|\n"
 for t in tables:
  n=t["table"];i=info[n];pk=[r["name"] for r in i["cols"] if r["pk"]]
  docs+="| "+n+" | "+str(i["rows"])+" | "+str(len(i["cols"]))+" | "+t["event_encoding"]+" | "+", ".join(pk)+" | "+t["definition"]+" |\n"
 docs+="\n- Row encoding: each occurrence is a separate row; its activity comes from a code, label or the table meaning.\n- Column encoding: an object row stores actual milestone times in dedicated columns. It can contain one or several milestones.\n- No event encoding: the table supplies context, plans, identities or links rather than direct events.\n- Planned dates, snapshots and technical timestamps do not automatically become events.\n\n## Columns\n"
 flat=[]
 for t in tables:
  n=t["table"];docs+="\n### "+n+"\n\n"+t["definition"]+"\n\n- Event encoding: "+t["event_encoding"]+". "+t["encoding_detail"]+"\n\n| Column | Type | Required | Key / relationship | Definition |\n|---|---|---|---|---|\n"
  for c,r in zip(t["columns"],info[n]["cols"]):
   fk=[f for f in info[n]["fk"] if f["from"]==c["name"]];key=("PK" if r["pk"] else "")+"".join(("; " if r["pk"] else "")+"FK → "+f["table"]+"."+f["to"] for f in fk)
   row=dict(table=n,column=c["name"],sql_type=r["type"],required="yes" if r["notnull"] or r["pk"] else "no",key_relationship=key,definition=c["definition"],event_encoding=t["event_encoding"],encoding_detail=t["encoding_detail"])
   flat.append(row);docs+="| "+row["column"]+" | "+row["sql_type"]+" | "+row["required"]+" | "+key+" | "+c["definition"]+" |\n"
 if name=="plateflow":
  docs+="\n## Logical history identity reference\n\nmaterial_operation_history.material_id refers to either as_rolled_material.material_id or plate_material.plate_material_id. This is not a single-table SQLite FK. The builder validates the two disjoint identity sets with an insert trigger and an orphan check. Dashed diagram edges show this logical reference.\n"
 docs+="\n## Value domains and business rules\n\n"
 domain=d.get("value_domain",d.get("code_domain",{}))
 docs+="\n".join("- "+k+": "+v for k,v in domain.items())+"\n\n"+"\n".join("- "+r for r in d["business_rules"])+"\n"
 if (out/"object_activity_design.md").exists():docs+="\n"+(out/"object_activity_design.md").read_text()
 (p/"input/data_dictionary.md").write_text(docs)
 (out/"data_dictionary.md").write_text(docs)
 import csv
 with (out/"data_dictionary.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
 relationships=[]
 for n,i in info.items():
  for fk in i["fk"]:
   idx=list(con.execute("PRAGMA index_list("+n+")"));unique_sets=[]
   for ix in idx:
    if ix["unique"]:unique_sets.append([r["name"] for r in con.execute("PRAGMA index_info("+ix["name"]+")")])
   card="0..1" if [fk["from"]] in unique_sets else "0..N"
   relationships.append(dict(parent=fk["table"],child=n,label="1 : "+card,logical=False,from_col=fk["from"],to_col=fk["to"]))
 if name=="plateflow":
  relationships += [dict(parent=t,child="material_operation_history",label="logical 1 : 0..N",logical=True,from_col="material_id",to_col="material_id" if t=="as_rolled_material" else "plate_material_id") for t in ["as_rolled_material","plate_material"]]
 js=lambda n,o:(out/n).write_text(json.dumps(o,indent=2)+"\n")
 js("schema_summary.json",dict(table_count=len(tables),tables={n:dict(row_count=i["rows"],column_count=len(i["cols"]),primary_key=[r["name"] for r in i["cols"] if r["pk"]]) for n,i in info.items()},relationships=relationships))
 width,bw,key_width=1980,600,90
 heights={n:116+32*len(i["cols"]) for n,i in info.items()}
 grid={n:(round((x-65)/510),round((y-130)/350)) for n,(x,y) in positions.items()}
 next_row=1+max(r for _,r in grid.values())
 for i,n in enumerate(n for n in info if n not in grid):grid[n]=(i%3,next_row+i//3)
 row_y={};cursor=140
 for row in sorted({r for _,r in grid.values()}):
  row_y[row]=cursor
  cursor+=max(heights[n] for n,(_,r) in grid.items() if r==row)+80
 positions={n:(40+col*650,row_y[row]) for n,(col,row) in grid.items()}
 height=cursor-10
 svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="#ffffff"/>',
 '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#69788e"/></marker></defs>',
 f'<text x="45" y="45" font-family="sans-serif" font-size="34" font-weight="bold" fill="#12233c">{esc(title)} · {len(tables)} tables</text>',
 '<text x="45" y="76" font-family="sans-serif" font-size="22" fill="#53647c">Arrows: parent → child. PK/FK: declared keys. Dashed: logical reference. Column list is complete.</text>']
 mx=ET.Element("mxfile",host="app.diagrams.net");diagram=ET.SubElement(mx,"diagram",name=title,id=name)
 model=ET.SubElement(diagram,"mxGraphModel",dx=str(width),dy=str(height),grid="1",page="1",pageWidth=str(width),pageHeight=str(height))
 root=ET.SubElement(model,"root");ET.SubElement(root,"mxCell",id="0");ET.SubElement(root,"mxCell",id="1",parent="0")
 # Edges first; boxes cover crossing paths. Layout can be refined in draw.io.
 edge_svg=[]
 for j,r in enumerate(relationships):
  x1,y1=positions[r["parent"]];x2,y2=positions[r["child"]]
  h1,h2=heights[r["parent"]],heights[r["child"]]
  if y2>y1: sx,sy,tx,ty=x1+bw/2,y1+h1,x2+bw/2,y2
  elif y2<y1:sx,sy,tx,ty=x1+bw/2,y1,x2+bw/2,y2+h2
  elif x2>x1:sx,sy,tx,ty=x1+bw,y1+min(h1,h2)/2,x2,y2+min(h1,h2)/2
  else:sx,sy,tx,ty=x1,y1+min(h1,h2)/2,x2+bw,y2+min(h1,h2)/2
  mid=(sy+ty)/2
  waypoints=[];port_style=""
  if name=="universityflow" and abs(grid[r["child"]][1]-grid[r["parent"]][1])>1 and y2>y1:
   left=grid[r["parent"]][0]==0
   sx=x1 if left else x1+bw;sy=y1+h1/2;tx=x2+bw/2;ty=y2
   gutter=20 if left else width-20;mid=ty-35
   waypoints=[(gutter,sy),(gutter,mid),(tx,mid)]
   port_style=f"exitX={0 if left else 1};exitY=0.5;entryX=0.5;entryY=0;"
  path=f"M {sx} {sy} "+(" ".join(f"L {px} {py}" for px,py in waypoints) if waypoints else f"L {sx} {mid} L {tx} {mid}")+f" L {tx} {ty}"
  dash=' stroke-dasharray="7 5"' if r["logical"] else ""
  edge_svg.append(f'<path d="{path}" fill="none" stroke="#69788e" stroke-width="2"{dash}/>')
  if ty>mid:points=f"{tx},{ty} {tx-5},{ty-10} {tx+5},{ty-10}"
  elif ty<mid:points=f"{tx},{ty} {tx-5},{ty+10} {tx+5},{ty+10}"
  elif tx>sx:points=f"{tx},{ty} {tx-10},{ty-5} {tx-10},{ty+5}"
  else:points=f"{tx},{ty} {tx+10},{ty-5} {tx+10},{ty+5}"
  edge_svg.append(f'<polygon points="{points}" fill="#69788e"/>')
  edge=ET.SubElement(root,"mxCell",id="e"+str(j),value=r["from_col"]+"; "+r["label"],style="edgeStyle=orthogonalEdgeStyle;rounded=0;endArrow=block;html=1;"+port_style+("dashed=1;" if r["logical"] else ""),edge="1",parent="1",source=r["parent"],target=r["child"])
  geometry=ET.SubElement(edge,"mxGeometry",relative="1",attrib={"as":"geometry"})
  if waypoints:
   points=ET.SubElement(geometry,"Array",attrib={"as":"points"})
   for px,py in waypoints:ET.SubElement(points,"mxPoint",x=str(px),y=str(py))
 for t in tables:
  n=t["table"];i=info[n];x,y=positions[n];bh=heights[n];pk={r["name"] for r in i["cols"] if r["pk"]};fk={r["from"] for r in i["fk"]}
  svg.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="white" stroke="#9a9a9a" stroke-width="1.5"/>')
  svg.append(f'<rect x="{x}" y="{y}" width="{bw}" height="58" fill="#eeeeee" stroke="#9a9a9a"/>')
  svg.append(f'<text x="{x+14}" y="{y+38}" font-family="sans-serif" font-size="26" font-weight="bold" fill="#222222">{esc(n)}</text>')
  divider_y=58+16+32*len(i["cols"])
  svg.append(f'<path d="M {x+key_width} {y+58} L {x+key_width} {y+divider_y} M {x} {y+divider_y} L {x+bw} {y+divider_y}" fill="none" stroke="#9a9a9a" stroke-width="1"/>')
  node=ET.SubElement(root,"mxCell",id=n,value=n,style="shape=swimlane;startSize=58;rounded=0;whiteSpace=wrap;html=1;align=left;spacingLeft=16;fillColor=#eeeeee;swimlaneFillColor=#ffffff;strokeColor=#9a9a9a;fontColor=#222222;fontSize=26;fontStyle=1;collapsible=0;",vertex="1",parent="1")
  ET.SubElement(node,"mxGeometry",x=str(x),y=str(y),width=str(bw),height=str(bh),attrib={"as":"geometry"})
  for suffix,x1,y1,x2,y2 in [("key_divider",key_width,58,key_width,divider_y),("footer_divider",0,divider_y,bw,divider_y)]:
   line=ET.SubElement(root,"mxCell",id=n+"_"+suffix,style="endArrow=none;startArrow=none;rounded=0;strokeColor=#9a9a9a;",edge="1",parent=n)
   geo=ET.SubElement(line,"mxGeometry",relative="1",attrib={"as":"geometry"})
   ET.SubElement(geo,"mxPoint",x=str(x1),y=str(y1),attrib={"as":"sourcePoint"})
   ET.SubElement(geo,"mxPoint",x=str(x2),y=str(y2),attrib={"as":"targetPoint"})
  for j,c in enumerate(i["cols"]):
   tags=[]
   if c["name"] in pk:tags.append("PK")
   if c["name"] in fk:tags.append("FK")
   key=", ".join(tags)
   svg.append(f'<text x="{x+key_width/2}" y="{y+92+j*32}" text-anchor="middle" font-family="sans-serif" font-size="20" fill="#26384e">{esc(key)}</text>')
   svg.append(f'<text x="{x+key_width+14}" y="{y+92+j*32}" font-family="sans-serif" font-size="24" fill="#26384e">{esc(c["name"])}</text>')
   for part,value,cx,cw,fs,align in [("key",key,0,key_width,20,"center"),("name",c["name"],key_width,bw-key_width,24,"left")]:
    cell=ET.SubElement(root,"mxCell",id=n+"_"+part+"_"+str(j),value=value,style=f"text;rounded=0;whiteSpace=wrap;html=1;align={align};verticalAlign=middle;spacingLeft={14 if part=='name' else 0};fontColor=#26384e;fontSize={fs};fontStyle=0;fillColor=none;strokeColor=none;",vertex="1",parent=n,connectable="0")
    ET.SubElement(cell,"mxGeometry",x=str(cx),y=str(74+j*32),width=str(cw),height="32",attrib={"as":"geometry"})
  footer=f'{i["rows"]} rows · {len(i["cols"])} columns'
  svg.append(f'<text x="{x+14}" y="{y+bh-13}" font-family="sans-serif" font-size="21" fill="#555555">{footer}</text>')
  cell=ET.SubElement(root,"mxCell",id=n+"_footer",value=footer,style="text;rounded=0;whiteSpace=wrap;html=1;align=left;verticalAlign=middle;spacingLeft=14;fontColor=#555555;fontSize=21;fillColor=none;strokeColor=none;",vertex="1",parent=n,connectable="0")
  ET.SubElement(cell,"mxGeometry",x="0",y=str(divider_y),width=str(bw),height=str(bh-divider_y),attrib={"as":"geometry"})
 svg.extend(edge_svg)
 svg.append(f'<text x="45" y="{height-30}" font-family="sans-serif" font-size="20" fill="#53647c">Editable relationships and relationship-count labels: schema.drawio. Exact FK endpoints: data_dictionary.md.</text></svg>')
 ET.ElementTree(mx).write(out/"schema.drawio",encoding="utf-8",xml_declaration=True)
 (out/"schema.svg").unlink(missing_ok=True)
 doc=fitz.open(stream="".join(svg).encode(),filetype="svg");pix=doc[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5));pix.save(out/"schema.png")
 overview="# "+title+" — Schema overview\n\n![Entity relationship diagram](schema.png)\n\n[Editable draw.io diagram](schema.drawio) · [Column dictionary](data_dictionary.md) · [CSV dictionary](data_dictionary.csv)\n\n"
 overview+=docs.split("## Columns")[0].split("Generated from the executable SQLite schema and English metadata.\n\n")[1]
 overview+="\n## Relationships\n\n| Parent | Child | Child FK | Parent key | Parent-to-child count | Kind |\n|---|---|---|---|---|---|\n"
 for r in relationships:overview+="| "+r["parent"]+" | "+r["child"]+" | "+r["from_col"]+" | "+r["to_col"]+" | "+r["label"]+" | "+("logical" if r["logical"] else "declared")+" |\n"
 (out/"schema_overview.md").write_text(overview)
 readme=p/"README.md";s=re.sub(r"\n## Schema and documentation\n.*?(?=\n## |\Z)","",readme.read_text(),flags=re.S);s+="\n## Schema and documentation\n\n"+("" if "![Schema](docs/schema.png)" in s else "![Schema](docs/schema.png)\n\n")+"- [Table inventory and relationships](docs/schema_overview.md)\n- [English column dictionary](docs/data_dictionary.md)\n- [CSV dictionary](docs/data_dictionary.csv)\n- [Editable draw.io diagram](docs/schema.drawio)\n- [Object-based Gold logs and coverage](docs/object_event_logs.md)\n";readme.write_text(s)
 con.close()
build("warehouseflow",{"warehouse":(575,130),"goods":(65,130),"loader":(1085,130),"transaction_record":(575,480),"goods_transaction_detail":(65,830),"loader_transaction":(1085,830)},"WarehouseFlow · RSchema")
build("plateflow",{"slab_material":(65,130),"planned_rolling_instruction":(575,130),"rolling_instruction":(1085,130),"furnace_charge_tracking":(65,480),"as_rolled_material":(575,480),"cutting_finishing_instruction":(1085,480),"plate_material":(65,830),"material_operation_history":(575,830),"operation_code":(1085,830)},"PlateFlow · Korean manufacturer")

build("universityflow",{"student":(65,130),"course":(575,130),"instructor":(1085,130),"degree_examination_result":(65,480),"registration":(575,480),"assignment":(1085,480),"task":(65,830),"simulation_module":(575,830),"assignment_grading":(1085,830),"thesis":(65,1180),"student_simulation_experiment_result":(575,1180)},"UniversityFlow · combined RSchema examples")
format_documents(ROOT)

from timestamp_inventory import refresh
refresh()
from dictionary_standard import render
for name in ["warehouseflow","universityflow","plateflow"]:render(ROOT/"datasets"/name)
