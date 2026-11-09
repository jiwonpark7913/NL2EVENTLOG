#!/usr/bin/env python3
"""Audit current HospitalFlow and produce the OT-left Gold review diagram and docs."""
from pathlib import Path
from collections import defaultdict, Counter
import sqlite3, csv, json, html, re
BASE=Path(__file__).resolve().parents[2]/"datasets/hospitalflow"
P=BASE/"private"
DOC=BASE/"docs"
REV=BASE/"review"
def q(t): return '"'+t.replace('"','""')+'"'
def load(path): return json.loads(path.read_text())
def jl(path): return [json.loads(v) for v in path.read_text().splitlines() if v.strip()]
def safe(s):return html.escape(str(s))
def main():
    db=sqlite3.connect("file:"+str(BASE/"input/database.sqlite")+"?mode=ro",uri=True)
    assert db.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
    assert not list(db.execute("PRAGMA foreign_key_check"))
    names=sorted(x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'"))
    dd=load(BASE/"input/data_dictionary.json")
    identity=load(P/"identity_gold.json")
    gold=jl(P/"gold.jsonl")
    byot={g["object_type"]:[m["table"] for m in g["members"]] for g in identity["groups"]}
    membership={}
    for ot,ts in byot.items():
        for t in ts:
            assert t not in membership,("multiple OT",t)
            membership[t]=ot
    assert set(membership)==set(names)
    assert len(names)==12 and len(byot)==11
    assert sorted(byot["Hospital Admission"])==["admission_detail","admissions"]
    assert identity["expected_decision_counts"]=={"MERGE":1,"SEPARATE":65,"UNRESOLVED":0}
    sources=defaultdict(set);timing=defaultdict(set)
    valid=0;rowtotal=0
    for g in gold:
        if g.get("answerability")!="answerable":continue
        id=g["question_id"];es=g["es"]
        sql=(P/"gold_sql"/(id+".sql")).read_text().strip()
        assert sql.rstrip(";")==es["compiled_sql"].strip().rstrip(";"),("SQL/ES",id)
        rows=[["" if x is None else str(x) for x in row] for row in db.execute(sql)]
        with (P/"gold_logs"/(id+".csv")).open(newline="") as f:
            rdr=csv.reader(f)
            assert next(rdr)==["event_id","case_id","activity","timestamp"]
            target=list(rdr)
        assert rows==target,("SQL/CSV",id,len(rows),len(target))
        assert len(rows)==g["event_count"]
        assert set(r[2] for r in rows).issubset(set(es["activities"]))
        for s in es["activity_sources"]:
            table=s["table"];col=s["timestamp_column"]
            assert table in names
            assert col in {r[1] for r in db.execute("PRAGMA table_info("+q(table)+")")}
            db.execute("SELECT * FROM ("+s["event_sql"]+") LIMIT 1").fetchall()
            sources[table].add(s["activity"]);timing[table].add(col)
        valid+=1;rowtotal+=len(rows)
    assert valid==42
    order=["Patient","Hospital Admission","Care Unit Transfer","Laboratory Order","Medication Order",
           "Procedure Order","Order History Record","Lab Measurement","Medication Administration",
           "Procedure Episode","Pharmacy Dispensing"]
    assert set(order)==set(byot)
    items=[(ot,t) for ot in order for t in byot[ot]]
    y={t:150+i*78 for i,(ot,t) in enumerate(items)}
    H=150+len(items)*78+75
    svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1830 '+str(H)+'">',
         '<rect width="100%" height="100%" fill="#fff"/>',
         '<text x="24" y="37" font-family="sans-serif" font-size="26" font-weight="700">HospitalFlow — Gold evidence structure</text>',
         '<text x="24" y="65" font-family="sans-serif" font-size="14">Exactly one object-type membership per table. Source activities are not object-attribution edges.</text>',
         '<text x="25" y="115" font-family="sans-serif" font-size="18" font-weight="700">Object types (11)</text>',
         '<text x="485" y="115" font-family="sans-serif" font-size="18" font-weight="700">Physical tables (12)</text>',
         '<text x="1000" y="115" font-family="sans-serif" font-size="18" font-weight="700">Direct Gold activities</text>']
    domains=[("Identity / encounter",order[:3]),("Clinical orders",order[3:7]),("Recorded execution",order[7:])]
    for label,ots in domains:
        ts=[t for ot in ots for t in byot[ot]]
        top=y[ts[0]]-17;bottom=y[ts[-1]]+65
        svg.append('<rect x="12" y="'+str(top)+'" width="1800" height="'+str(bottom-top)+'" rx="8" fill="#F8FAFC" stroke="#E2E8F0"/>')
        svg.append('<text x="18" y="'+str(top+12)+'" font-family="sans-serif" font-size="10" fill="#64748B">'+safe(label)+" — visual group only</text>")
    def rect(x,yy,w,h,label,color,link=None,sub=None):
        if link:svg.append('<a href="'+safe(link)+'" target="_parent">')
        svg.append('<rect x="'+str(x)+'" y="'+str(yy)+'" width="'+str(w)+'" height="'+str(h)+'" rx="6" fill="'+color+'" stroke="#94A3B8"/>')
        svg.append('<text x="'+str(x+11)+'" y="'+str(yy+27)+'" font-family="sans-serif" font-size="14" font-weight="600">'+safe(label)+'</text>')
        if sub:svg.append('<text x="'+str(x+11)+'" y="'+str(yy+45)+'" font-family="sans-serif" font-size="11">'+safe(sub)+'</text>')
        if link:svg.append("</a>")
    for ot in order:
        ys=[y[t]+27 for t in byot[ot]]
        middle=(ys[0]+ys[-1])/2
        rect(24,middle-26,385,52,ot,"#E5F5EB")
        if len(ys)>1:
            svg.append('<path d="M409 '+str(middle)+' H448 V'+str(ys[0])+' M448 '+str(ys[0])+' V'+str(ys[-1])+'" stroke="#64748B" stroke-width="2" fill="none"/>')
        for py in ys:svg.append('<path d="M448 '+str(py)+' H482" stroke="#64748B" stroke-width="2"/>')
    for ot,t in items:
        yy=y[t]
        rect(482,yy,460,54,t,"#E2EFFD","tables/"+t+".md")
        if t not in sources:
            svg.append('<text x="990" y="'+str(yy+33)+'" font-family="sans-serif" font-size="13" fill="#64748B">No directly recorded Gold activity</text>')
            continue
        svg.append('<path d="M942 '+str(yy+27)+' H983" stroke="#C5A865" stroke-width="2"/>')
        labels=sorted(sources[t]);n=len(labels);half=(n+1)//2
        parts=[" · ".join(labels[:half])," · ".join(labels[half:])] if len(" · ".join(labels))>91 else [" · ".join(labels)]
        svg.append('<rect x="983" y="'+str(yy-3)+'" width="825" height="59" rx="6" fill="#FFF2CB" stroke="#D6BE87"/>')
        for k,txt in enumerate(parts):
            if txt:svg.append('<text x="994" y="'+str(yy+21+21*k)+'" font-family="sans-serif" font-size="12">'+safe(txt)+'</text>')
    svg.append('<text x="25" y="'+str(H-38)+'" font-family="sans-serif" font-size="12">Membership edges (left) are unique. Case attribution can connect one event to multiple objects; it does not merge OTs.</text>')
    svg.append('<text x="25" y="'+str(H-20)+'" font-family="sans-serif" font-size="12">Gold author annotations; review full SQL and object_event_links.json to see record-level relations.</text>')
    svg.append("</svg>")
    (REV/"database/gold_evidence_graph.svg").write_text("\n".join(svg)+"\n")
    counts={t:db.execute("SELECT COUNT(*) FROM "+q(t)).fetchone()[0] for t in names}
    cols={t:[dict(zip(["cid","name","type","notnull","dflt_value","pk"],r)) for r in db.execute("PRAGMA table_info("+q(t)+")")] for t in names}
    ddmap={t["table"]:t for t in dd["tables"]}
    current=["# HospitalFlow — current database overview","","Generated from current SQLite + authored Gold identity annotations.","",
      "[Editable Draw.io](schema.drawio) · [DB review](../review/database/README.md) · [Gold evidence](../review/database/gold_evidence_graph.svg)","",
      "| Table | Rows | Columns | PK | Gold OT |","|---|---:|---:|---|---|"]
    for t in names:
        pks=", ".join(c["name"] for c in cols[t] if c["pk"])
        current.append("| ["+t+"](../review/database/tables/"+t+".md) | "+str(counts[t])+" | "+str(len(cols[t]))+" | "+pks+" | "+membership[t]+" |")
    current+=["","## Physical foreign keys","",
      "| Child | Key | Parent | Key |","|---|---|---|---|"]
    for t in names:
        for f in db.execute("PRAGMA foreign_key_list("+q(t)+")"):
            current.append("| "+t+" | "+f[3]+" | "+f[2]+" | "+f[4]+" |")
    current+=["","Foreign-key links are not Object Type identity equivalence.",""]
    (DOC/"schema_overview.md").write_text("\n".join(current)+"\n")
    otmd=["# HospitalFlow — object identity Gold","","A physical table belongs to exactly one OT. Do not conflate FK associations with equal business-object identity.","",
      "| Object Type | Member physical tables | Identity evidence |","|---|---|---|"]
    for ot in order:
        otmd.append("| "+ot+" | "+", ".join(byot[ot])+" | "+("Shared hadm_id, enforced shared-PK FK" if len(byot[ot])>1 else "Distinct record grain and primary key")+" |")
    otmd+=["","**Decision:** Keep 11 OTs. Merge only admissions with admission_detail. Order history, lab measurements, medication administrations, pharmacy dispensing and transfer records have independent occurrence identities.","",
      "Clinical grouping in the diagram is presentation only, not an ontology merge.",""]
    (DOC/"object_type_verification.md").write_text("\n".join(otmd)+"\n")
    tsmd=["# HospitalFlow — current timestamp inventory","","Gold event time is not interchangeable with other timestamps; storetime and outtime may record observations or interval ends.","",
      "| Table | Column | Gold event timestamp |","|---|---|---|"]
    ts_count=0
    for t in names:
        for c in ddmap[t]["columns"]:
            if c.get("representation_class")!="Date-time":continue
            ts_count+=1;column=c["name"]
            tsmd.append("| "+t+" | "+column+" | "+("Yes" if column in timing.get(t,set()) else "No")+" |")
    (DOC/"timestamp_columns.md").write_text("\n".join(tsmd)+"\n")
    (DOC/"timestamp_columns.json").write_text(json.dumps({"time_columns":{t:[c["name"] for c in ddmap[t]["columns"] if c.get("representation_class")=="Date-time"] for t in names},"gold_event_time_columns":{t:sorted(v) for t,v in timing.items()}},indent=2)+"\n")
    (DOC/"schema_summary.json").write_text(json.dumps({"table_count":len(names),"tables":{t:{"row_count":counts[t],"column_count":len(cols[t]),"primary_key":[c["name"] for c in cols[t] if c["pk"]]} for t in names}},indent=2)+"\n")
    otact=["# HospitalFlow — Gold object types and direct event sources","","Activities shown here are recorded in table rows; downstream Gold case attribution can associate them with additional business objects.","",
       "| OT | Physical source table | Direct source activities |","|---|---|---|"]
    for ot,t in items:
        otact.append("| "+ot+" | "+t+" | "+(", ".join(sorted(sources[t])) if t in sources else "—")+" |")
    (DOC/"object_activity_design.md").write_text("\n".join(otact)+"\n")
    questions=["# HospitalFlow — current evaluation Gold questions","","Generated from Gold metadata; this is an evaluation-only review file.","",
       "| ID | Type | Answerability | Gold activity scope | Event rows |","|---|---|---|---:|"]
    for g in gold:
        questions.append("| "+g["question_id"]+" | "+g.get("question_type","—")+" | "+g["answerability"]+" | "+(", ".join(g["es"]["activities"]) if g.get("es") else "—")+" | "+str(g.get("event_count",0))+" |")
    (DOC/"questions.md").write_text("\n".join(questions)+"\n")
    inv=["# HospitalFlow — authored Gold source bindings","","Evaluation only; **not a model-generated Evidence Graph**.","",
       "| Physical Table | One Gold OT | Directly recorded Gold activities | Event timestamp columns |","|---|---|---|---|"]
    for t in names:
        inv.append("| "+t+" | "+membership[t]+" | "+(", ".join(sorted(sources[t])) if t in sources else "—")+" | "+(", ".join(sorted(timing[t])) if t in timing else "—")+" |")
    inv+=["","The attribution of an event to cases or linked objects is defined by the corresponding Gold SQL; it is not equivalent to table OT membership.","",
      "[Diagram with OT on left](../database/gold_evidence_graph.svg) · [Question Gold DFG](README.md)",""]
    (REV/"gold_dfg/event_graph.md").write_text("\n".join(inv)+"\n")
    p=REV/"database/README.md";txt=p.read_text()
    if "## Gold Evidence Graph" in txt:txt=txt.split("## Gold Evidence Graph")[0]
    txt+="## Gold Evidence Graph: OT → Physical Table → Direct Activities\n\n"
    txt+="![Gold graph with unique OT membership](gold_evidence_graph.svg)\n\n"
    txt+="OT (left), physical table (middle) and directly recorded event sources (right). Each physical table has exactly one Gold OT; foreign-key/event associations to several objects are distinct from OT membership. The three domain bands are visual grouping only, not merged object types.\n\n"
    txt+="[Gold source inventory](../gold_dfg/event_graph.md) · [Question-level Gold SQL and DFG](../gold_dfg/README.md)\n"
    p.write_text(txt)
    for p in [DOC/"schema_overview.md",REV/"database/README.md",REV/"gold_dfg/event_graph.md"]:
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
            if link.startswith(("http","#")):continue
            assert (p.parent/link).resolve().exists(),(p,link)
    assert ts_count>=15
    print(json.dumps({"gold_queries_validated":valid,"gold_rows_validated":rowtotal,
      "tables":len(names),"object_types":len(byot),"unique_membership":len(membership),
      "distinct_activity_labels":len(set(v for vs in sources.values() for v in vs)),
      "timestamp_columns":ts_count},indent=2))
    db.close()
if __name__=="__main__":main()
