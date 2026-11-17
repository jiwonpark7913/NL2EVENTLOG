#!/usr/bin/env python3
"""Create a benchmark from OCEL 2.0 SQLite without leaking reference E2O to model input.

Input: official OCEL 2.0 SQLite file. Outputs:
  input/database.sqlite         - relational source with anonymized source tables
  input/data_dictionary.json    - physical metadata only
  review/gold_flatten/<type>.csv - reference flattened events (human/evaluation only)
  review/provenance.json         - original checksum and conversion counts
DO NOT pass review/ or the original OCEL to the model.
"""
import argparse,csv,hashlib,json,re,sqlite3
from collections import defaultdict
from pathlib import Path

def quote(s):return '"'+s.replace('"','""')+'"'
def sanitize(s):
 return re.sub(r"[^a-zA-Z0-9_]","_",str(s)).strip("_")[:90] or "unnamed"
def main(src,dest):
 dest.mkdir(parents=True,exist_ok=True)
 with src.open("rb") as f:
  h=hashlib.sha256()
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 source=sqlite3.connect(f"file:{src}?mode=ro",uri=True)
 names={r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
 required={"event","object","event_object"}
 if not required<=names:raise ValueError(f"Expected OCEL 2.0 SQLite tables {required}, found {names}")
 def columns(table):return [r[1] for r in source.execute(f"PRAGMA table_info({quote(table)})")]
 e_cols=columns("event");o_cols=columns("object");rel_cols=columns("event_object")
 def find(cols,candidates):
  return next((c for c in candidates if c in cols),None)
 eid=find(e_cols,["ocel_id","id"]);etype=find(e_cols,["ocel_type","type"])
 oid=find(o_cols,["ocel_id","id"]);otype=find(o_cols,["ocel_type","type"])
 reid=find(rel_cols,["ocel_event_id","event_id"]);roid=find(rel_cols,["ocel_object_id","object_id"])
 if not all([eid,etype,oid,otype,reid,roid]):raise ValueError("Unrecognized OCEL standard column names")
 # This is a generic normalized reconstruction; record the resulting source structure
 # explicitly and never claim it was an original operational DB.
 db=dest/"input/database.sqlite";db.parent.mkdir(parents=True,exist_ok=True)
 if db.exists():db.unlink()
 out=sqlite3.connect(db)
 out.executescript("""CREATE TABLE activity_record(record_id TEXT PRIMARY KEY,activity_class TEXT,observed_at TEXT);
 CREATE TABLE business_entity(entity_id TEXT PRIMARY KEY,entity_class TEXT);
 CREATE TABLE activity_subject(record_id TEXT,entity_id TEXT,role TEXT,
     PRIMARY KEY(record_id,entity_id,role));
 CREATE INDEX idx_activity_subject_entity ON activity_subject(entity_id);
 CREATE TABLE entity_link(source_entity_id TEXT,target_entity_id TEXT,relation_role TEXT,
 PRIMARY KEY(source_entity_id,target_entity_id,relation_role));""")
 events=[(str(a),str(b)) for a,b in source.execute(f"SELECT {quote(eid)},{quote(etype)} FROM event")]
 objects=[(str(a),str(b)) for a,b in source.execute(f"SELECT {quote(oid)},{quote(otype)} FROM object")]
 out.executemany("INSERT INTO activity_record(record_id,activity_class) VALUES (?,?)",events)
 out.executemany("INSERT INTO business_entity VALUES (?,?)",objects)
 # Preserve exact event/object ids and relation qualifier; no invented link paths.
 qualifier=find(rel_cols,["ocel_qualifier","qualifier"])
 relation_sql=f"SELECT {quote(reid)},{quote(roid)}"+(f",{quote(qualifier)}" if qualifier else ",NULL")+" FROM event_object"
 out.executemany("INSERT OR IGNORE INTO activity_subject VALUES (?,?,?)",
                 ((str(a),str(b),str(c) if c is not None else "") for a,b,c in source.execute(relation_sql)))
 # Preserve direct O2O links where the original OCEL contains them, but do not
 # propagate event attribution transitively when generating the reference log.
 if "object_object" in names:
  oo=columns("object_object")
  src_col=find(oo,["ocel_source_id","source_id"])
  dst_col=find(oo,["ocel_target_id","target_id"])
  role_col=find(oo,["ocel_qualifier","qualifier"])
  if src_col and dst_col:
   sql=f"SELECT {quote(src_col)},{quote(dst_col)}"+(f",{quote(role_col)}" if role_col else ",NULL")+" FROM object_object"
   out.executemany("INSERT OR IGNORE INTO entity_link VALUES (?,?,?)",
                    ((str(a),str(b),str(c) if c is not None else "") for a,b,c in source.execute(sql)))
 # Materialize per-activity occurrence tables from OCEL typed event tables.
 eventtypes={}
 timestamps={}
 if "event_map_type" in names:
  mapcols=columns("event_map_type")
  if "ocel_type" in mapcols and "ocel_type_map" in mapcols:
   eventtypes=dict(source.execute("SELECT ocel_type,ocel_type_map FROM event_map_type"))
 for typ,mapped in eventtypes.items():
  table="event_"+str(mapped)
  if table not in names:continue
  cols=columns(table);time=find(cols,["ocel_time","time","timestamp"])
  idc=find(cols,["ocel_id","id"])
  if not time or not idc:continue
  target="observations_"+sanitize(mapped)
  # Keep individual activity tables to create multiple physical event representations.
  out.execute(f"CREATE TABLE {quote(target)}(record_id TEXT PRIMARY KEY, observed_at TEXT)")
  typed_rows=[(str(a),str(b) if b is not None else None) for a,b in source.execute(f"SELECT {quote(idc)},{quote(time)} FROM {quote(table)}")]
  out.executemany(f"INSERT INTO {quote(target)} VALUES (?,?)",typed_rows)
  for eid_value,time_value in typed_rows:
   if eid_value in timestamps and timestamps[eid_value]!=time_value:
    raise ValueError(f"Conflicting timestamps for event {eid_value}")
   timestamps[eid_value]=time_value
 # Fallback: timestamp in event root, if present.
 if not eventtypes:
  time=find(e_cols,["ocel_time","time","timestamp"])
  if time:
   timestamps.update((str(e),str(t) if t is not None else None) for e,t in source.execute(f"SELECT {quote(eid)},{quote(time)} FROM event"))
 if not timestamps or len(timestamps)!=len(events) or any(t is None for t in timestamps.values()):
  raise ValueError(f"Incomplete event timestamps: mapped {len(timestamps)} / {len(events)}. Refuse to generate Gold.")
 out.executemany("UPDATE activity_record SET observed_at=? WHERE record_id=?",
                  ((t,e) for e,t in timestamps.items()))
 out.commit()
 # The source OCEL explicitly exposes event/object concepts. The representation is
 # deliberately a controlled reconstruction baseline, not a realistic ERP schema.
 dictionary={"provenance_note":"Normalized OCEL-derived relational benchmark, NOT an original operational database",
             "tables":{}}
 for name, in out.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
  dictionary["tables"][name]={"columns":[{"name":c[1],"type":c[2]} for c in out.execute(f"PRAGMA table_info({quote(name)})")],
                               "row_count":out.execute(f"SELECT COUNT(*) FROM {quote(name)}").fetchone()[0]}
 from add_dictionary_samples import add_samples,write_dictionary
 add_samples(dictionary,db)
 write_dictionary(dest/"input/data_dictionary.json",dictionary)
 # Independent reference: per-object type, every directly linked event. Do not infer
 # transitive propagation through O2O relations; that is a separate policy decision.
 event_by_id=dict(events);object_by_id=dict(objects)
 all_records=defaultdict(list)
 for ev,obj,role in source.execute(relation_sql):
  if str(obj) not in object_by_id or str(ev) not in event_by_id:continue
  typ=object_by_id[str(obj)]
  all_records[typ].append((str(obj),str(ev),event_by_id[str(ev)],timestamps[str(ev)],role or ""))
 gold=dest/"review/gold_flatten";gold.mkdir(parents=True,exist_ok=True)
 for typ in sorted(set(object_by_id.values())):
  with (gold/(sanitize(typ)+"_cases.csv")).open("w",newline="") as f:
   writer=csv.writer(f);writer.writerow(["case_id"])
   writer.writerows((obj,) for obj,ot in objects if ot==typ)
 for typ,records in all_records.items():
  with (gold/(sanitize(typ)+".csv")).open("w",newline="") as f:
   writer=csv.writer(f);writer.writerow(["case_id","event_id","activity","timestamp","relation_qualifier"])
   writer.writerows(sorted(records))
 counts={"source_sha256":h.hexdigest(),"source_file":src.name,"events":len(events),"objects":len(objects),
        "event_object_links":out.execute("SELECT COUNT(*) FROM activity_subject").fetchone()[0],
        "object_object_links":out.execute("SELECT COUNT(*) FROM entity_link").fetchone()[0],
        "case_populations":{typ:sum(1 for _,ot in objects if ot==typ) for typ in set(object_by_id.values())},
        "flattened_et_counts":{typ:len(v) for typ,v in all_records.items()},
        "timestamp_coverage":len(timestamps),"warning":"Timestamp-complete reference for direct E2O only. Human review and full population semantics still required."}
 (dest/"review/provenance.json").write_text(json.dumps(counts,indent=2)+"\n")
 source.close();out.close()
 print(json.dumps(counts,indent=2))
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--source",required=True,type=Path);p.add_argument("--out",required=True,type=Path)
 a=p.parse_args();main(a.source,a.out)
