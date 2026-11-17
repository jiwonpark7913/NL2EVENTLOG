#!/usr/bin/env python3
"""Independent, fail-closed integrity audit for NL2EventLog dataset artifacts.

Does not confer human Gold approval. Reports warnings for missing coverage,
semantic ambiguities and benchmark leakage. Model input never reads review/.
"""
from __future__ import annotations
import argparse,csv,gzip,hashlib,json,sqlite3,subprocess,sys,tempfile,xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def quote(s):return '"'+s.replace('"','""')+'"'
def check(report,key,condition,detail=None,warning=False):
 report["checks"].append({"name":key,"status":"PASS" if condition else ("WARN" if warning else "FAIL"),"detail":detail})
def attach(db):
 conn=sqlite3.connect(f"file:{db}?mode=ro",uri=True)
 return conn
def structure(conn):
 return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
def audit_mimic(report,root):
 p=root/"datasets/mimic";manifest=p/"input/data_dictionary.json"
 dd=json.loads(manifest.read_text())
 db=p/"input/database.sqlite";gz=p/"input/database.sqlite.gz"
 with tempfile.TemporaryDirectory() as tmp:
  if not db.exists() and gz.exists():
   db=Path(tmp)/"database.sqlite"
   with gzip.open(gz,"rb") as a,db.open("wb") as b:
    import shutil;shutil.copyfileobj(a,b)
  check(report,"mimic.sqlite_present",db.exists())
  if not db.exists():return
  with attach(db) as c:
   check(report,"mimic.integrity",c.execute("PRAGMA integrity_check").fetchone()[0]=="ok")
   tables=structure(c)
   check(report,"mimic.table_catalog",tables==set(dd["tables"]),f"actual={len(tables)}, dictionary={len(dd['tables'])}")
   total=0
   for name,meta in dd["tables"].items():
    if name not in tables:continue
    n=c.execute("SELECT COUNT(*) FROM "+quote(name)).fetchone()[0];total+=n
    check(report,"mimic.rows."+name,n==meta["row_count"],f"actual={n},expected={meta['row_count']}")
    cols=[r[1] for r in c.execute("PRAGMA table_info("+quote(name)+")")]
    expected=[col["name"] for col in meta["columns"]]
    check(report,"mimic.columns."+name,cols==expected)
   check(report,"mimic.total_rows",total==dd["statistics"]["rows"],f"actual={total}")
   documented=sum(bool(col.get("definition")) for t in dd["tables"].values() for col in t["columns"])
   total_columns=sum(len(t["columns"]) for t in dd["tables"].values())
   check(report,"mimic.documented_columns",documented>0,
         f"with verified semantic definitions={documented}/{total_columns}")
   check(report,"mimic.documentation_sources",
         all(t.get("documentation_url") for t in dd["tables"].values()),
         "table source URLs must be attached to each MIMIC table")
   invalid=[(name,col["name"]) for name,t in dd["tables"].items()
            for col in t["columns"] if col.get("definition") and not col.get("definition_source")]
   check(report,"mimic.definition_provenance",not invalid,
         f"definitions without source URLs={invalid[:10]}")
   standardized=p/"docs/data_dictionary.standard.json"
   if standardized.exists():
    norm=json.loads(standardized.read_text())
    check(report,"mimic.standard_catalog",
          {t["table"] for t in norm["tables"]}==tables,
          "canonical projection must cover all imported tables")
   if "patients" in tables:
    check(report,"mimic.patient_count",c.execute("SELECT COUNT(*) FROM patients").fetchone()[0]==100)
   # Candidate links are checked for invalid non-null references. MIMIC CSVs
   # have no declared FKs, so the result is not a FK-constraint certification.
   for ref in dd.get("candidate_relationships",[]):
    child,parent,key=ref["source_table"],ref["target_table"],ref["column"]
    if child not in tables or parent not in tables:continue
    violations=c.execute(f"SELECT COUNT(*) FROM {quote(child)} a WHERE a.{quote(key)} IS NOT NULL "
       f"AND NOT EXISTS(SELECT 1 FROM {quote(parent)} b WHERE b.{quote(key)}=a.{quote(key)})").fetchone()[0]
    # This is a warning because itemid is context-dependent and some
    # documented relations genuinely permit missing targets.
    check(report,"mimic.candidate_link."+child+"."+key,violations==0,
          f"non_null_orphans={violations},target={parent}",warning=True)
  svg=p/"docs/schema.svg";draw=p/"docs/schema.drawio";png=p/"docs/schema.png"
  for ext,path in (("svg",svg),("drawio",draw)):
   try:tree=ET.parse(path)
   except (OSError,ET.ParseError) as e:check(report,"mimic."+ext+"_parse",False,str(e));continue
   check(report,"mimic."+ext+"_parse",True)
   if ext=="svg":
    nodes={n.get("data-table") for n in tree.getroot().iter() if n.get("data-table")}
    check(report,"mimic.svg_table_coverage",nodes==set(dd["tables"]),f"{len(nodes)} table boxes")
    labels=svg.read_text()
    check(report,"mimic.svg_colors","#bae6fd" in labels and "#fde68a" in labels,
          "blue=temporal candidate; yellow=maintenance")
   else:
    cells=[n for n in tree.getroot().iter("mxCell") if n.get("vertex")=="1"]
    check(report,"mimic.drawio_table_count",len(cells)==len(dd["tables"]),f"boxes={len(cells)}")
    check(report,"mimic.drawio_relationship_edges",any(n.get("edge")=="1" for n in tree.getroot().iter("mxCell")),
          "draw.io contains inferred table relationships",warning=True)
  check(report,"mimic.png_signature",png.exists() and png.open("rb").read(8)==b"\x89PNG\r\n\x1a\n")
  proposal=p/"review/admission_timeline.json"
  if proposal.exists():
   gold=json.loads(proposal.read_text())
   check(report,"mimic.gold_approved",gold.get("approved") is True,
        "Admission lifecycle currently requires independent human approval",warning=True)
  check(report,"mimic.model_db_uncompressed",
        (p/"input/database.sqlite").exists(),"README advertises database.sqlite but GitHub stores database.sqlite.gz",warning=True)

def audit_adventure(report,root):
 p=root/"datasets/adventureworks"
 script=p/"validate.py"
 if script.exists():
  result=subprocess.run([sys.executable,str(script)],cwd=p,capture_output=True,text=True)
  check(report,"adventure.full_validator",result.returncode==0,
        (result.stdout+result.stderr)[-1600:])
 else:check(report,"adventure.full_validator",False,"Missing validate.py")
 # This repository has no independent Gold event occurrence specification.
 found=[x for x in (p/"review").rglob("*") if x.is_file() and ("gold" in x.name.lower() or "gold" in str(x.parent).lower())] if (p/"review").exists() else []
 check(report,"adventure.gold_reference",bool(found),
       "No approved case-specific Reference Event Log/Gold SQL is included",warning=True)

def audit_ocel(report,root,dataset,source):
 p=root/"datasets"/(dataset+"_ocel")
 db=p/"input/database.sqlite";reference=p/"review/gold_flatten"
 check(report,dataset+".database_exists",db.exists())
 check(report,dataset+".source_exists",source is not None and source.exists(),
       "Supply official OCEL 2.0 SQLite (or staging output) with --source",warning=True)
 if not db.exists():return
 with attach(db) as c:
  check(report,dataset+".sqlite_integrity",c.execute("PRAGMA integrity_check").fetchone()[0]=="ok")
  tables=structure(c)
  for t in ("activity_record","business_entity","activity_subject","entity_link"):
   check(report,dataset+".required_table."+t,t in tables)
  total_events=c.execute("SELECT COUNT(*) FROM activity_record").fetchone()[0]
  total_objects=c.execute("SELECT COUNT(*) FROM business_entity").fetchone()[0]
  check(report,dataset+".timestamp_nonnull",
        c.execute("SELECT COUNT(*) FROM activity_record WHERE observed_at IS NULL").fetchone()[0]==0)
  check(report,dataset+".event_link_orphans",
        c.execute("SELECT COUNT(*) FROM activity_subject a LEFT JOIN activity_record e "
                  "ON a.record_id=e.record_id WHERE e.record_id IS NULL").fetchone()[0]==0)
  check(report,dataset+".object_link_orphans",
        c.execute("SELECT COUNT(*) FROM activity_subject a LEFT JOIN business_entity o "
                  "ON a.entity_id=o.entity_id WHERE o.entity_id IS NULL").fetchone()[0]==0)
  catalog=json.loads((p/"input/data_dictionary.json").read_text())
  check(report,dataset+".dictionary_tables",set(catalog["tables"])==tables)
  # Count all object instances, including those with no events.
  for typ,n in c.execute("SELECT entity_class,COUNT(*) FROM business_entity GROUP BY entity_class"):
   path=reference/(slug(typ)+"_cases.csv")
   if path.exists():
    with path.open(newline="") as f:rows=list(csv.DictReader(f))
    check(report,dataset+".case_population."+slug(typ),len(rows)==n,
          f"expected={n},exported={len(rows)}")
   else:check(report,dataset+".case_population."+slug(typ),False,"Missing case population CSV")
  # Detect missing/extra event rows using the database's actual E2O join.
  for typ, in c.execute("SELECT DISTINCT entity_class FROM business_entity"):
   path=reference/(slug(typ)+".csv")
   expected=c.execute("""
      SELECT COUNT(*) FROM activity_subject s
      JOIN business_entity o ON o.entity_id=s.entity_id
      JOIN activity_record e ON e.record_id=s.record_id
      WHERE o.entity_class=?""",(typ,)).fetchone()[0]
   if not path.exists():
    check(report,dataset+".flatten."+slug(typ),expected==0,
          f"missing CSV, expected {expected} rows")
    continue
   # Compare every CSV occurrence against the corresponding relational join,
   # including multiplicity, case, activity, time and qualifier.
   # Sorted streaming avoids holding millions of reference records in Python.
   from itertools import zip_longest
   query="""SELECT o.entity_id,s.record_id,e.activity_class,e.observed_at,COALESCE(s.role,'')
       FROM activity_subject s
       JOIN business_entity o ON o.entity_id=s.entity_id
       JOIN activity_record e ON e.record_id=s.record_id
       WHERE o.entity_class=?
       ORDER BY o.entity_id,s.record_id,e.activity_class,e.observed_at,s.role"""
   mismatches=0;actual=0;missing_timestamp=0;first_mismatch=None
   with path.open(newline="") as f:
    reader=csv.DictReader(f)
    csv_rows=((r.get("case_id"),r.get("event_id"),r.get("activity"),r.get("timestamp"),
               r.get("relation_qualifier") or "") for r in reader)
    for a,b in zip_longest(csv_rows,c.execute(query,(typ,))):
     if a is not None:
      actual+=1
      if not a[3]:missing_timestamp+=1
     if a!=b:
      mismatches+=1
      if first_mismatch is None:first_mismatch={"csv":a,"db":b}
   check(report,dataset+".flatten_count."+slug(typ),actual==expected,
         f"expected={expected},csv={actual}")
   check(report,dataset+".flatten_timestamp."+slug(typ),missing_timestamp==0,
         f"missing timestamps={missing_timestamp}")
   check(report,dataset+".flatten_exact."+slug(typ),mismatches==0,
         f"mismatched occurrences={mismatches}, first={first_mismatch}")
  if source is not None and source.exists():
   with attach(source) as src:
    names=structure(src)
    if {"event","object","event_object"}<=names:
     n_event=src.execute("SELECT COUNT(*) FROM event").fetchone()[0]
     n_obj=src.execute("SELECT COUNT(*) FROM object").fetchone()[0]
     n_e2o=src.execute("SELECT COUNT(*) FROM event_object").fetchone()[0]
     check(report,dataset+".source_events",n_event==total_events,
           f"source={n_event},database={total_events}")
     check(report,dataset+".source_objects",n_obj==total_objects,
           f"source={n_obj},database={total_objects}")
     check(report,dataset+".source_E2O",n_e2o==c.execute("SELECT COUNT(*) FROM activity_subject").fetchone()[0],
           f"source={n_e2o}")
     scols={r[1] for r in src.execute("PRAGMA table_info(event)")}
     if "ocel_time" in scols:
      missing=src.execute("SELECT COUNT(*) FROM event WHERE ocel_time IS NULL").fetchone()[0]
      check(report,dataset+".source_timestamps_complete",missing==0)
     # Direct reference event IDs and types must match source; robust against
     # independent count equality hiding partial identity mismatch.
     c.execute("ATTACH DATABASE ? AS upstream",(str(source),))
     for name,condition,detail in (
       ("event_identity","SELECT COUNT(*) FROM (SELECT record_id AS id, activity_class AS typ FROM activity_record EXCEPT SELECT ocel_id,ocel_type FROM upstream.event)","event identifiers / types"),
       ("object_identity","SELECT COUNT(*) FROM (SELECT entity_id AS id, entity_class AS typ FROM business_entity EXCEPT SELECT ocel_id,ocel_type FROM upstream.object)","object identifiers / types")):
      bad=c.execute(condition).fetchone()[0]
      check(report,dataset+".source_"+name,bad==0,f"extra/mismatched {detail}={bad}")
     source_cols={r[1] for r in c.execute("PRAGMA upstream.table_info(event_object)")}
     ekey="ocel_event_id" if "ocel_event_id" in source_cols else "event_id"
     okey="ocel_object_id" if "ocel_object_id" in source_cols else "object_id"
     role="ocel_qualifier" if "ocel_qualifier" in source_cols else ("qualifier" if "qualifier" in source_cols else None)
     role_expr=f"COALESCE({quote(role)},'')" if role else "''"
     src_rel=f"SELECT {quote(ekey)},{quote(okey)},{role_expr} FROM upstream.event_object"
     dst_rel="SELECT record_id,entity_id,role FROM activity_subject"
     for direction,left,right in (("missing",src_rel,dst_rel),("extra",dst_rel,src_rel)):
      bad=c.execute(f"SELECT COUNT(*) FROM ({left} EXCEPT {right})").fetchone()[0]
      check(report,dataset+".source_E2O_"+direction,bad==0,
            f"unique direct E2O/qualifier tuples={bad}")
     if "ocel_time" in scols:
      count=c.execute("""SELECT COUNT(*) FROM activity_record a
          JOIN upstream.event e ON e.ocel_id=a.record_id
          WHERE a.observed_at IS NOT e.ocel_time""").fetchone()[0]
      check(report,dataset+".source_timestamp_values",count==0,
            f"event timestamps different from source={count}")
     c.execute("DETACH DATABASE upstream")
  check(report,dataset+".human_gold_approval",False,
        "Automated direct E2O flattening is not independently approved Gold",warning=True)
  check(report,dataset+".erd_present",(p/"docs/schema.drawio").exists() and (p/"docs/schema.svg").exists(),
        "OCEL-derived datasets currently have no linked ERD artifacts",warning=True)
  check(report,dataset+".attributes_preserved",False,
        "OCEL-derived relational schema drops original event/object attributes",warning=True)
def slug(s):
 import re
 return re.sub(r"[^a-zA-Z0-9_]","_",str(s)).strip("_")[:90] or "unnamed"
def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--dataset",choices=["adventureworks","mimic","bpi2019","order_management"],required=True)
 parser.add_argument("--root",type=Path,default=ROOT)
 parser.add_argument("--source",type=Path)
 parser.add_argument("--report",type=Path)
 a=parser.parse_args()
 report={"dataset":a.dataset,"checks":[],"scope":"Automated physical/evidence audit; does not certify semantic Gold."}
 try:
  if a.dataset=="adventureworks":audit_adventure(report,a.root)
  elif a.dataset=="mimic":audit_mimic(report,a.root)
  else:audit_ocel(report,a.root,a.dataset,a.source)
 except Exception as exc:
  check(report,"audit_exception",False,f"{type(exc).__name__}: {exc}")
 if a.report:
  a.report.parent.mkdir(parents=True,exist_ok=True)
  a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
 totals=Counter(c["status"] for c in report["checks"])
 print(json.dumps({"dataset":a.dataset,"summary":dict(totals),"checks":report["checks"]},indent=2,ensure_ascii=False))
 raise SystemExit(1 if totals["FAIL"] else 0)
if __name__=="__main__":main()
