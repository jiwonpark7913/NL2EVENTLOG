#!/usr/bin/env python3
"""Regenerate four dataset review diagrams and final-user README pages.

Immutable: SQLite, Data Dictionary, case questions, Gold SQL and Gold CSV.
Evidence graph is a documented *projection* of table OT membership and
event-source bindings; it is not an inferred or record-level graph.
"""
from __future__ import annotations
import csv
import html
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASETS = ("hospitalflow", "plateflow", "universityflow", "warehouseflow")
DISPLAY = {"hospitalflow":"HospitalFlow","plateflow":"PlateFlow","universityflow":"UniversityFlow","warehouseflow":"WarehouseFlow"}
TICK = chr(96)
CORE = {
  "hospitalflow": {"Patient","Hospital Admission","Laboratory Order","Medication Order","Procedure Order"},
  "plateflow": {"Slab","Mother Material","Plate Piece","Rolling Plan","Rolling Instruction","Equipment"},
  "universityflow": {"Student","Course","Instructor","Assignment","Thesis","Student-course registration","Simulation module","Course-design task"},
  "warehouseflow": {"Receiving Request","Dispatch Order","Goods","Warehouse","Worker"},
}
DESCRIPTION = {
  "hospitalflow": (
    "HospitalFlow models synthetic patient encounters, clinical orders, medication administration, laboratory testing, procedures, and care-unit transfers. "
    "Its patient and admission structures and time-column vocabulary are inspired by the public MIMIC-IV hospital schema; all records are synthetic, not MIMIC-IV patient records."
  ),
  "plateflow": (
    "PlateFlow is a synthetic steel-plate production database with slab receiving, rolling preparation, furnace and rolling operations, finishing, inspection and quality review. "
    "It reflects industrial process concepts, not observed production records."
  ),
  "universityflow": (
    "UniversityFlow is a synthetic university operations database representing students, courses, registration, assignments, examinations, theses, and simulation experiments. "
    "Its domain design draws on RSchema university requirements and uses authored synthetic records."
  ),
  "warehouseflow": (
    "WarehouseFlow is a synthetic warehouse operations database covering goods, receiving requests, dispatch, stock movement, handling, worker tasks and audits. "
    "It uses authored business records rather than observed warehouse transactions."
  ),
}
def quote(s): return '"' + s.replace('"','""') + '"'
def esc(x): return html.escape(str(x),quote=True)
def readj(path): return json.loads(path.read_text())
def gitmd(label,href): return "["+label+"]("+href+")"
def markdown_clean(text,name):
    # Canonical dataset names in every Markdown, without changing SQL or question data.
    text=text.replace("plateflow_new","plateflow").replace("warehouseflow_new","warehouseflow")
    text=text.replace("PlateFlow New dataset","PlateFlow dataset").replace("WarehouseFlow New dataset","WarehouseFlow dataset")
    text=text.replace("PlateFlow New","PlateFlow").replace("WarehouseFlow New","WarehouseFlow")
    return text

def inventory(base,db,n):
    # Stable authored Gold manifest; never parse already rendered Markdown as input.
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    source=readj(base/"review/gold_dfg/gold_source_manifest.json")
    assert source["dataset"]==n
    assert set(source["tables"])==tables,(n, "Gold inventory-table mismatch")
    ot={}
    acts=defaultdict(set)
    times=defaultdict(set)
    for t,item in source["tables"].items():
        assert item["ot"]
        ot[t]=item["ot"]
        acts[t].update(item["activities"])
        times[t].update(item["timestamps"])
    if n=="hospitalflow":
        private=readj(base/"private/identity_gold.json")
        actual={m["table"]:g["object_type"] for g in private["groups"] for m in g["members"]}
        assert actual==ot,(n,"authored identity Gold diverges from source manifest")
    return ot,acts,times

def gold_audit(base,db,n):
    sql_dir=base/"private/gold_sql"
    csv_dir=base/"private/gold_logs"
    assert sql_dir.is_dir() and csv_dir.is_dir()
    queries=0;sum_rows=0
    for p in sorted(sql_dir.glob("*.sql")):
        c=csv_dir/(p.stem+".csv")
        if not c.exists():continue
        sql=p.read_text()
        results=[tuple("" if x is None else str(x) for x in row) for row in db.execute(sql)]
        with c.open(newline="",encoding="utf-8-sig") as f:
            rd=csv.reader(f)
            header=next(rd,None)
            assert header==["event_id","case_id","activity","timestamp"],(n,p.name,header)
            expected=[tuple(v) for v in rd]
        assert Counter(results)==Counter(expected),(n,p.name,len(results),len(expected))
        queries+=1;sum_rows+=len(results)
    assert queries>0,(n,"no executable Gold SQL files")
    source=base/"private/gold.jsonl"
    if source.exists() and source.stat().st_size:
        gold=[json.loads(x) for x in source.read_text().splitlines() if x.strip()]
        for g in gold:
            if g.get("answerability")!="answerable":continue
            p=sql_dir/(g["question_id"]+".sql")
            assert p.exists(),(n,g["question_id"])
            if g.get("es") and g["es"].get("compiled_sql"):
                assert p.read_text().strip().rstrip(";")==g["es"]["compiled_sql"].strip().rstrip(";"),(n,"ES SQL mismatch",p.name)
    return queries,sum_rows

def write_svg(base,n,tables,ot,acts,core):
    # A single OT can include multiple tables only if grounded in the Gold identity.
    groups=defaultdict(list)
    for t in tables:groups[ot[t]].append(t)
    def priority(item):
        name,ts=item
        is_core=name in core
        return (0 if is_core else 1,name)
    ordered_groups=sorted(groups.items(),key=priority)
    records=[(name,t) for name,ts in ordered_groups for t in sorted(ts)]
    y={t:156+i*74 for i,(_,t) in enumerate(records)}
    W=1850;H=156+len(records)*74+95
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Gold OT left, physical tables middle and source activities right">',
      '<rect width="100%" height="100%" fill="#fff"/>',
      f'<text x="24" y="37" font-size="25" font-weight="700" font-family="Arial,sans-serif">{esc(DISPLAY[n])} · Gold Evidence Structure</text>',
      '<text x="24" y="64" font-size="14" font-family="Arial,sans-serif" fill="#475569">Gold OT membership is unique per physical table. Activity source bindings are not multi-object attribution edges.</text>',
      '<text x="25" y="111" font-size="17" font-family="Arial,sans-serif" font-weight="700">Object Types (left)</text>',
      '<text x="475" y="111" font-size="17" font-family="Arial,sans-serif" font-weight="700">Physical Tables (middle)</text>',
      '<text x="995" y="111" font-size="17" font-family="Arial,sans-serif" font-weight="700">Gold Activity Sources (right)</text>']
    def card(x,yy,w,h,title,color,link=None,sub=None):
        if link:svg.append(f'<a href="{esc(link)}" target="_parent">')
        svg.append(f'<rect x="{x}" y="{yy}" width="{w}" height="{h}" rx="6" fill="{color}" stroke="#94A3B8"/>')
        svg.append(f'<text x="{x+12}" y="{yy+28}" font-size="14" font-weight="600" font-family="Arial,sans-serif" fill="#173047">{esc(title)}</text>')
        if sub:svg.append(f'<text x="{x+12}" y="{yy+45}" font-size="11" font-family="Arial,sans-serif" fill="#64748B">{esc(sub)}</text>')
        if link:svg.append("</a>")
    # Draw OT nodes first. Branching is a short local vertical trunk, no crossing with other OTs.
    for name,ts in ordered_groups:
        ys=[y[t]+26 for t in sorted(ts)]
        mid=(min(ys)+max(ys))/2
        card(26,mid-26,386,52,name,"#DFF5E8",sub="Core business object" if name in core else "Supporting/record object")
        if len(ys)>1:
            svg.append(f'<path d="M412 {mid} H444 V{min(ys)} M444 {min(ys)} V{max(ys)}" fill="none" stroke="#64748B" stroke-width="2"/>')
        else:svg.append(f'<path d="M412 {mid} H444" fill="none" stroke="#64748B" stroke-width="2"/>')
        for py in ys:svg.append(f'<path d="M444 {py} H474" fill="none" stroke="#64748B" stroke-width="2"/>')
    for otname,t in records:
        yy=y[t]
        card(474,yy,470,52,t,"#E4EFFC","tables/"+t+".md")
        if acts[t]:
            svg.append(f'<path d="M944 {yy+26} H989" stroke="#B59B66" stroke-width="2"/>')
            labels=sorted(acts[t])
            words=" · ".join(labels)
            lines=[words]
            if len(words)>96:
                half=(len(labels)+1)//2
                lines=[" · ".join(labels[:half])," · ".join(labels[half:])]
            svg.append(f'<rect x="989" y="{yy-4}" width="829" height="60" rx="6" fill="#FFF2CB" stroke="#D6C18D"/>')
            for ix,part in enumerate(lines):
                svg.append(f'<text x="1001" y="{yy+20+21*ix}" font-size="12" font-family="Arial,sans-serif" fill="#4E401C">{esc(part)}</text>')
        else:
            svg.append(f'<text x="1000" y="{yy+31}" font-size="13" font-family="Arial,sans-serif" fill="#64748B">No directly encoded Gold activity</text>')
    svg.append(f'<text x="24" y="{H-48}" font-family="Arial,sans-serif" font-size="12" fill="#475569">Core objects are a conceptual shortlist; record-level types remain distinct Gold identities. No cross-OT mergers are inferred from foreign keys.</text>')
    svg.append(f'<text x="24" y="{H-25}" font-family="Arial,sans-serif" font-size="12" fill="#475569">Author-annotated source projection; consult Gold SQL/object event links for attribution of each event to multiple cases or objects.</text>')
    svg.append("</svg>")
    output=base/"review/database/gold_evidence_graph.svg"
    output.write_text("\n".join(svg)+"\n")
    assert output.exists() and output.stat().st_size>2000
    return len(groups)

def readme_update(base,n,db,ot,acts,times,core,goldqueries,goldrows):
    review=base/"review/database"
    tables=sorted(ot)
    counts={t:db.execute("SELECT COUNT(*) FROM "+quote(t)).fetchone()[0] for t in tables}
    cols={t:[row[1] for row in db.execute("PRAGMA table_info("+quote(t)+")")] for t in tables}
    readme=["# "+DISPLAY[n]+" — Database and Gold Evidence Review","",
      DESCRIPTION[n],"",
      "## Gold Evidence Graph","",
      "![Gold Object Types → Physical Tables → Activities](gold_evidence_graph.svg)","",
      "The diagram distinguishes core business object concepts from supporting entities and activity-record types. ",
      "Each physical table belongs to exactly one Gold Object Type. An event can be associated with several business objects through foreign keys without its source table belonging to multiple OTs.","",
      "**This is an author-annotated Gold source projection, not an inferred Evidence Graph or a full provenance graph.**",
      "Gold SQL and record-level evidence are available in the linked inspection materials.","",
      "## Relational Schema (SQL foreign keys)","",
      "![Relational database schema](schema.svg)","",
      "## Table inspector","",
      "| Physical table | Rows | Columns | Gold OT | First ten records |",
      "|---|---:|---:|---|---|"]
    for t in tables:
        readme.append("| "+t+" | "+str(counts[t])+" | "+str(len(cols[t]))+" | "+ot[t]+" | "+gitmd("Preview","tables/"+t+".md")+" |")
    readme+=["","## Gold object types vs. core business objects","",
      "Gold identity types: **"+str(len(set(ot.values())))+"**; principal business object concepts in this domain: **"+str(len(core & set(ot.values())))+"**. ",
      "The core set is a conceptual layer for interpreting process scope, not a rule that forces unrelated PK domains to merge.","",
      "**Core business concepts:** "+", ".join(sorted(core & set(ot.values())))+".","",
      "Supporting Gold types: "+", ".join(sorted(set(ot.values())-core))+".","",
      "## Evaluation evidence","",
      "- Gold SQL/CSV pairs executable and consistent: "+str(goldqueries)+"; compared event rows across questions: "+str(goldrows)+".",
      "- "+gitmd("Gold source inventory","../gold_dfg/event_graph.md"),
      "- "+gitmd("Question-level Gold DFGs","../gold_dfg/README.md"),
      "- "+gitmd("Editable Draw.io schema","../../docs/schema.drawio"),
      ""]
    if n=="hospitalflow":
        readme+=["","## MIMIC-IV provenance","",
          "HospitalFlow is a synthetic database informed by the [MIMIC-IV hospital schema](https://mimic.mit.edu/docs/iv/modules/hosp/).",
          "The patient master contains gender, anchor_age, anchor_year, anchor_year_group and dod. The admissions record uses admittime, dischtime, deathtime, edregtime and edouttime. Transfer intervals use eventtype, careunit, intime and outtime.",
          "All individual records are synthetic."]
    (review/"README.md").write_text("\n".join(readme)+"\n")
    top=["# "+DISPLAY[n],"",DESCRIPTION[n],"",
      "## Dataset overview","",
      "| Physical tables | Gold object types | Core business concepts | Gold SQL/CSV pairs verified |",
      "|---:|---:|---:|---:|",
      "| "+str(len(tables))+" | "+str(len(set(ot.values())))+" | "+str(len(core & set(ot.values())))+" | "+str(goldqueries)+" |",
      "","## Explore the dataset","",
      "- "+gitmd("Gold Evidence Graph and real table records","review/database/README.md"),
      "- "+gitmd("Editable Draw.io relational diagram","docs/schema.drawio"),
      "- "+gitmd("Per-question Gold DFGs","review/gold_dfg/README.md"),
      "- "+gitmd("Business Data Dictionary","input/data_dictionary.json"),
      "- "+gitmd("Gold object membership and source bindings","review/gold_dfg/event_graph.md"),
      "","## Schema and process semantics","",
      "Object types identify business entities or independent occurrence records. The conceptual shortlist of core nouns is not a physical schema transformation.",
      "Event timestamps and activity codes are interpreted using the Data Dictionary and their source-table context. The Gold event-log oracle is stored separately from normal model inputs.",""]
    (base/"README.md").write_text("\n".join(top))
    # The README describes only the final public dataset.
    assert all(w not in (base/"README.md").read_text().lower() for w in ["_new","was removed","previous version","formerly","new dataset"])
    # Brief review inventory grounded in Gold membership, generated from the original inventory.
    inv=["# "+DISPLAY[n]+" — Gold source inventory","","**Author annotations.** One identity OT per physical table; event-to-object attribution is a separate relation.","",
      "| Physical table | Gold Object Type | Gold activity source labels |","|---|---|---|"]
    for t in tables:inv.append("| "+t+" | "+ot[t]+" | "+(", ".join(sorted(acts[t])) if acts[t] else "—")+" |")
    inv+=["","This is a source-binding projection. The model is not given this file.","",
       gitmd("Gold diagram","../database/gold_evidence_graph.svg")+" · "+gitmd("Gold DFGs","README.md")]
    (base/"review/gold_dfg/event_graph.md").write_text("\n".join(inv)+"\n")
    # Huge question review pages: preserve case-level SQL and trace displays, change only header/history copy.
    q=base/"review/gold_dfg/README.md"
    if q.exists():
        body=q.read_text()
        body=markdown_clean(body,n)
        body=re.sub(r'^# [^\n]+', "# "+DISPLAY[n]+" — Question-level Gold DFG inspection",body,count=1)
        body=re.sub(r"^Source commit:.*\n","",body,flags=re.M)
        body=body.replace("**EVALUATION ONLY — NEVER PROVIDE TO A MODEL.**",
            "**Gold reference only. These files are not model input.**\n\n[Gold OT → Table → Activities diagram](../database/gold_evidence_graph.svg)")
        q.write_text(body)
    return counts

def run():
    report=[]
    for n in DATASETS:
        b=ROOT/"datasets"/n
        con=sqlite3.connect("file:"+str(b/"input/database.sqlite")+"?mode=ro",uri=True)
        assert con.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
        assert not list(con.execute("PRAGMA foreign_key_check"))
        tables=sorted(r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
        ot,activities,timestamps=inventory(b,con,n)
        assert len(tables)==len(ot)
        gold_count,rows=gold_audit(b,con,n)
        groups=write_svg(b,n,tables,ot,activities,CORE[n])
        counts=readme_update(b,n,con,ot,activities,timestamps,CORE[n],gold_count,rows)
        report.append({"dataset":n,"tables":len(tables),"gold_ots":groups,
            "core_concepts":len(CORE[n] & set(ot.values())),"gold_sql_checked":gold_count,"event_rows_checked":rows,
            "direct_activity_source_labels":len(set(a for v in activities.values() for a in v))})
        con.close()
    print(json.dumps(report,indent=2))
if __name__=="__main__": run()
