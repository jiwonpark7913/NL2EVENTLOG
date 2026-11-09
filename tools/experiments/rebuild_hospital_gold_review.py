#!/usr/bin/env python3
"""Regenerate accurate question-level Gold DFGs after HospitalFlow schema migration."""
import csv
import html
import json
import math
from collections import Counter,defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"datasets/hospitalflow"
OUT=P/"review/gold_dfg"
def make_svg(path,activity,edges,start,end):
    names=sorted(activity)
    n=len(names)
    r=270 if n>8 else 205
    cx=500;cy=410
    loc={}
    for i,name in enumerate(names):
        angle=(2*math.pi*i/max(n,1))-math.pi/2
        loc[name]=(cx+r*math.cos(angle),cy+r*math.sin(angle))
    lines=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 860">',
      '<rect x="0" y="0" width="1100" height="860" fill="#ffffff"/>',
      '<text x="20" y="32" font-size="20" font-weight="700" font-family="sans-serif">Gold directly-follows graph</text>',
      '<text x="20" y="56" font-size="12" fill="#64748b" font-family="sans-serif">Nodes: occurrence counts; edges: directly-follows counts; timestamp and event-ID tie break.</text>']
    for (a,b),count in sorted(edges.items()):
        x1,y1=loc[a];x2,y2=loc[b]
        if a==b:
            lines.append('<path d="M%.1f %.1f q -55 -95 30 -110 q 90 15 65 95" fill="none" stroke="#94a3b8" stroke-width="1.5"/>'%(x1,y1))
            continue
        delta=math.hypot(x2-x1,y2-y1) or 1
        dx=(x2-x1)/delta;dy=(y2-y1)/delta
        p1=(x1+dx*65,y1+dy*23);p2=(x2-dx*65,y2-dy*23)
        lines.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#94a3b8" stroke-width="1.5"/>'%(*p1,*p2))
        lines.append('<text x="%.1f" y="%.1f" font-size="12" text-anchor="middle" font-family="sans-serif" fill="#475569">%s</text>'%((p1[0]+p2[0])/2,(p1[1]+p2[1])/2,str(count)))
    for a in names:
        x,y=loc[a]
        lines.append('<rect x="%.1f" y="%.1f" width="150" height="50" rx="8" fill="#eff6ff" stroke="#64748b"/>'%(x-75,y-25))
        lines.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="sans-serif" font-size="11">%s</text>'%(x,y-4,html.escape(a[:24])))
        lines.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="sans-serif" font-size="13" font-weight="700">%s</text>'%(x,y+15,activity[a]))
    lines.append('</svg>')
    path.write_text('\n'.join(lines))

def run():
    gold=[json.loads(l) for l in (P/"private/gold.jsonl").read_text().splitlines() if l]
    out=OUT/"graphs";out.mkdir(parents=True,exist_ok=True)
    counts=[]
    for g in gold:
        if g.get("answerability")!="answerable":continue
        qid=g["question_id"]
        with (P/"private/gold_logs"/(qid+".csv")).open(newline="") as f:
            records=list(csv.DictReader(f))
        bycase=defaultdict(list)
        for row in records:bycase[row["case_id"]].append(row)
        act=Counter();edge=Counter();start=Counter();end=Counter()
        for case,items in bycase.items():
            items.sort(key=lambda x:(x["timestamp"],x["event_id"]))
            for x in items:act[x["activity"]]+=1
            if items:
                start[items[0]["activity"]]+=1
                end[items[-1]["activity"]]+=1
            for a,b in zip(items,items[1:]):
                edge[(a["activity"],b["activity"])]+=1
        make_svg(out/(qid+".svg"),act,edge,start,end)
        counts.append((qid,len(records),len(bycase),len(act)))
    # Remove obsolete graphs but preserve one graph per existing answerable question.
    keep={x[0]+".svg" for x in counts}
    for p in out.glob("*.svg"):
        if p.name not in keep:p.unlink()
    rows=["# HospitalFlow — Gold DFG visual inspection","",
      "**Evaluation only: never provide Gold data or DFGs to NL2EventLog model inputs.**","",
      "All DFGs are regenerated from current Gold CSV files, not from the previous split-profile benchmark.","",
      "Timestamp ties are ordered using event_id only for deterministic display; this does not establish causal ordering.","",
      "| Question | Events | Cases | Activity types | Gold DFG | Gold SQL |","|---|---:|---:|---:|---|---|"]
    for q,n,c,a in counts:
        rows.append("| "+q+" | "+str(n)+" | "+str(c)+" | "+str(a)+" | [Graph](graphs/"+q+".svg) | [SQL](../../private/gold_sql/"+q+".sql) |")
    rows+=["","[Current source evidence inventory](event_graph.md) · [Current database inspection](../database/README.md)"]
    (OUT/"README.md").write_text("\n".join(rows)+"\n")
    # A current summary of the dataset, not the previous identity-split design.
    report=json.loads((P/"validation_report.json").read_text())
    summary=["# HospitalFlow — MIMIC-IV-inspired synthetic hospital database","",
      "The database uses MIMIC-IV-inspired schema and timestamp names but wholly synthetic patient, admission and transfer records.",
      "No real MIMIC-IV individual-level patient data are included.","",
      "## Current benchmark summary","",
      "| Tables | Patients | Admissions | Transfer rows | Object types | Distinct events | Answerable questions |",
      "|---:|---:|---:|---:|---:|---:|---:|",
      "| "+str(len(report["table_rows"]))+" | "+str(report["table_rows"]["patients"])+" | "+str(report["table_rows"]["admissions"])+" | "+str(report["table_rows"]["transfers"])+" | "+str(report["semantic_object_types"])+" | "+str(report["events"])+" | "+str(report["answerable_questions"])+" |",
      "","## Design changes","",
      "- Patient demographics and anchor metadata now reside in patients; patient_profile and preferred_language were removed.",
      "- Original MIMIC admission timestamp names used: admittime, dischtime, deathtime, edregtime, edouttime.",
      "- transfers contains eventtype, careunit, intime and outtime and is linked to patient and hospital admission.",
      "- Only actual transfer eventtype rows create Care Unit Transferred events; admission/discharge intervals are not counted twice.",
      "- Gold SQL and event logs were regenerated, including a new Care Unit Transferred activity.",
      "","## Inspection","",
      "- [Database and first 10 rows per table](review/database/README.md)",
      "- [Gold DFGs](review/gold_dfg/README.md)",
      "- [Gold source evidence inventory](review/gold_dfg/event_graph.md)",
      "- [Editable Draw.io ERD](docs/schema.drawio)",
      "- [MIMIC-IV hospital schema documentation](https://mimic.mit.edu/docs/iv/modules/hosp/)",
      "","All files under private and review are author-only, never model inputs."
    ]
    (P/"README.md").write_text("\n".join(summary)+"\n")
    print(json.dumps({"question_graphs":len(counts),"events":report["events"],"current_tables":len(report["table_rows"])}))
if __name__=="__main__":run()
