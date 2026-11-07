#!/usr/bin/env python3
"""Regenerate human-only database review pages. Never used by model inputs."""
from __future__ import annotations
import argparse
import html
import re
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASETS = ("hospitalflow", "universityflow", "plateflow", "warehouseflow")

def quote(name):
    return '"' + name.replace('"', '""') + '"'

def table_report(conn, table):
    cols = conn.execute("PRAGMA table_info(" + quote(table) + ")").fetchall()
    count = conn.execute("SELECT COUNT(*) FROM " + quote(table)).fetchone()[0]
    rows = conn.execute("SELECT * FROM " + quote(table) + " LIMIT 10").fetchall()
    names = [c[1] for c in cols]
    def cell(x):
        if x is None: return "NULL"
        if isinstance(x, bytes): return "[BLOB %s bytes]" % len(x)
        return str(x).replace("|", "\\|").replace("\n"," ")
    out = ["# " + table, "", f"**Rows:** {count} · **Columns:** {len(cols)}", "", "## Original records (first 10)", "",
           "| " + " | ".join(names) + " |",
           "| " + " | ".join("---" for _ in names) + " |"]
    out += ["| " + " | ".join(cell(v) for v in row) + " |" for row in rows]
    out += ["", "## Column definitions", "", "| Column | SQL type | PK | Not null |", "|---|---|---|---|"]
    out += [f"| {c[1]} | {c[2]} | {bool(c[5])} | {bool(c[3])} |" for c in cols]
    return "\n".join(out) + "\n",count,names

def update_drawio(path, names, foreign_keys):
    if not path.exists(): return
    root=ET.parse(path)
    cells={c.get("id"):c for c in root.findall(".//mxCell")}
    vertices={name:cells[name] for name in names if name in cells}
    # A semantic left-to-right ordering; related children share nearby columns.
    predefined={
        "plateflow":[["slab_material"],["planned_rolling_instruction","furnace_operation_history"],["rolling_instruction","rolling_operation_history"],["as_rolled_material"],["plate_material","finishing_operation_history"],["dimension_inspection","plate_quality_review"],["equipment","process_code"]],
        "warehouseflow":[["warehouse","goods","worker","work_code"],["receiving_request"],["goods_receipt","request_action"],["goods_movement","warehouse_task_history"],["dispatch_order","handling_history"],["warehouse_audit"]],
        "hospitalflow":[["patients","patient_detail"],["admissions","admission_detail"],["lab_order","prescriptions"],["labevents","pharmacy"],["transfers","procedures"],["diagnoses","services"]],
        "universityflow":[]
    }
    dataset=path.parents[1].name
    groups=predefined.get(dataset,[])
    ordered=[v for group in groups for v in group if v in vertices]
    remaining=[x for x in names if x not in ordered]
    if not groups or len(remaining)>4:
        # Directed dependency depth from foreign keys, capped to preserve readability.
        depth={n:0 for n in names}
        for _ in range(len(names)):
            changed=False
            for child,parent in foreign_keys:
                if child in depth and parent in depth and child!=parent and depth[child]<=depth[parent] and depth[parent]<5:
                    depth[child]=depth[parent]+1;changed=True
            if not changed:break
        groups=[[n for n in names if depth[n]==d] for d in range(max(depth.values(),default=0)+1)]
        remaining=[]
    if remaining:groups.append(remaining)
    positions={}
    for i,group in enumerate(groups):
        for j,name in enumerate(group):
            positions[name]=(80+i*660,110+j*470)
    for name,cell in vertices.items():
        geo=cell.find("mxGeometry")
        if geo is not None and name in positions:
            geo.set("x",str(positions[name][0]));geo.set("y",str(positions[name][1]))
    for cell in cells.values():
        if cell.get("edge")=="1":
            style=cell.get("style","")
            style=re.sub(r"(exitX|exitY|entryX|entryY)=[^;]*;?","",style)
            cell.set("style",style+"edgeStyle=orthogonalEdgeStyle;rounded=1;jettySize=auto;orthogonalLoop=1;")
            geo=cell.find("mxGeometry")
            if geo is not None:
                for child in list(geo):
                    if child.tag=="Array" and child.get("as")=="points":geo.remove(child)
    model=root.find(".//mxGraphModel")
    if model is not None:
        model.set("pageWidth",str(max(1800, 740*len(groups))))
        model.set("pageHeight",str(max(1100, 520*max((len(x) for x in groups),default=1))))
    root.write(path,encoding="utf-8",xml_declaration=True)

def svg_erd(conn,tables):
    # Compact, fully click-through schema map; actual foreign keys only.
    fks=[]
    for t in tables:
        for fk in conn.execute("PRAGMA foreign_key_list("+quote(t)+")"):
            if fk[2] in tables:fks.append((t,fk[2],fk[3],fk[4]))
    depth={t:0 for t in tables}
    for _ in range(len(tables)):
        change=False
        for child,parent,_,_ in fks:
            if depth[child]<=depth[parent] and depth[parent]<5 and child!=parent:
                depth[child]=depth[parent]+1;change=True
        if not change:break
    groups={}
    for t in tables:groups.setdefault(depth[t],[]).append(t)
    coords={}
    for d,items in groups.items():
        for k,t in enumerate(sorted(items)):coords[t]=(40+d*390,65+k*330)
    w=max(x for x,y in coords.values())+350;h=max(y for x,y in coords.values())+280
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
       '<defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8" fill="none" stroke="#64748b"/></marker></defs>',
       '<rect width="100%" height="100%" fill="#ffffff"/>']
    for child,parent,fc,pc in fks:
        sx,sy=coords[child];px,py=coords[parent]
        mid=(sx+px+320)/2
        s.append(f'<path d="M{px+300} {py+45} H{mid} V{sy+45} H{sx}" fill="none" stroke="#94a3b8" stroke-width="1.4" marker-end="url(#a)"><title>{html.escape(child)}.{html.escape(fc)} → {html.escape(parent)}.{html.escape(pc)}</title></path>')
    for t in tables:
        x,y=coords[t];colnames=[r[1] for r in conn.execute("PRAGMA table_info("+quote(t)+")")]
        n=conn.execute("SELECT COUNT(*) FROM "+quote(t)).fetchone()[0]
        s.append(f'<a xlink:href="tables/{html.escape(t)}.md" href="tables/{html.escape(t)}.md" target="_parent"><rect x="{x}" y="{y}" width="300" height="255" rx="9" fill="#fff" stroke="#64748b"/><rect x="{x}" y="{y}" width="300" height="43" rx="9" fill="#e2e8f0"/>')
        s.append(f'<text x="{x+12}" y="{y+28}" font-family="sans-serif" font-weight="700" font-size="16" fill="#0f172a">{html.escape(t)}</text>')
        for i,c in enumerate(colnames[:8]):s.append(f'<text x="{x+12}" y="{y+67+i*21}" font-family="monospace" font-size="12" fill="#334155">{html.escape(c)}</text>')
        s.append(f'<text x="{x+12}" y="{y+244}" font-family="sans-serif" font-size="12" fill="#475569">{n} rows · click for 10 records</text></a>')
    s.append("</svg>")
    return "\n".join(s),fks

def build(dataset):
    base=ROOT/"datasets"/dataset
    db=base/"input"/"database.sqlite"
    if not db.exists(): raise FileNotFoundError(db)
    dest=base/"review"/"database"
    (dest/"tables").mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(f"file:{db}?mode=ro",uri=True)
    tables=[r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    output=[]
    for t in tables:
        md,count,names=table_report(conn,t)
        (dest/"tables"/(t+".md")).write_text(md,encoding="utf-8")
        output.append((t,count,len(names)))
    svg,fks=svg_erd(conn,tables)
    (dest/"schema.svg").write_text(svg,encoding="utf-8")
    update_drawio(base/"docs"/"schema.drawio",tables,[(a,b) for a,b,_,_ in fks])
    report=[f"# {dataset} — Database Inspection","",
            "Original SQLite records; **not model input**. Click a table name to inspect its actual first 10 rows.",
            "", "![Interactive table overview](schema.svg)", "",
            "| Table | Rows | Columns | Open preview |","|---|---:|---:|---|"]
    report += [f"| {t} | {n} | {c} | [First 10 rows](tables/{t}.md) |" for t,n,c in output]
    report += ["","The table links are the dependable GitHub navigation path; SVG click-through may vary by GitHub's rendering/security restrictions.",
               "FK arrows are based on declared SQLite foreign keys. Informal semantic links are not asserted as physical FKs."]
    (dest/"README.md").write_text("\n".join(report)+"\n",encoding="utf-8")
    conn.close()
    print(dataset, "tables",len(tables),"FKs",len(fks),"output",dest)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--dataset",choices=DATASETS)
    a=p.parse_args()
    for n in ([a.dataset] if a.dataset else DATASETS):build(n)
