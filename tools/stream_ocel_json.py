#!/usr/bin/env python3
"""Stream OCEL 2.0 JSON from ZIP into a bounded-memory SQLite staging source.

The output intentionally contains the four tables consumed by
ocel_to_relational.py; event/object attributes are NOT yet preserved.
This is not an official OCEL2 SQLite serialization.
"""
import argparse, ijson, sqlite3, zipfile
from pathlib import Path

def convert(archive: Path, member: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    conn = sqlite3.connect(dest)
    conn.executescript("""
      CREATE TABLE event(ocel_id TEXT PRIMARY KEY, ocel_type TEXT NOT NULL, ocel_time TEXT NOT NULL);
      CREATE TABLE object(ocel_id TEXT PRIMARY KEY, ocel_type TEXT NOT NULL);
      CREATE TABLE event_object(ocel_event_id TEXT NOT NULL, ocel_object_id TEXT NOT NULL, ocel_qualifier TEXT);
      CREATE TABLE object_object(ocel_source_id TEXT NOT NULL, ocel_target_id TEXT NOT NULL, ocel_qualifier TEXT);
      CREATE INDEX event_object_event_idx ON event_object(ocel_event_id);
      CREATE INDEX event_object_object_idx ON event_object(ocel_object_id);
    """)
    counts = {"objects":0,"events":0,"e2o":0,"o2o":0}
    with zipfile.ZipFile(archive) as z:
        for collection in ("objects", "events"):
            with z.open(member) as stream:
                iterator = ijson.items(stream, collection + ".item")
                for record in iterator:
                    if collection == "objects":
                        conn.execute("INSERT INTO object VALUES (?,?)",
                                     (record["id"],record["type"]))
                        counts["objects"] += 1
                        for rel in record.get("relationships", []):
                            conn.execute("INSERT INTO object_object VALUES (?,?,?)",
                                         (record["id"],rel["objectId"],rel.get("qualifier","")))
                            counts["o2o"] += 1
                    else:
                        conn.execute("INSERT INTO event VALUES (?,?,?)",
                                     (record["id"],record["type"],record["time"]))
                        counts["events"] += 1
                        for rel in record.get("relationships", []):
                            conn.execute("INSERT INTO event_object VALUES (?,?,?)",
                                         (record["id"],rel["objectId"],rel.get("qualifier","")))
                            counts["e2o"] += 1
                    if counts[collection] % 25000 == 0 and counts[collection]:
                        conn.commit()
                        print(f"{collection}: {counts[collection]} processed",flush=True)
            conn.commit()
    if not counts["events"] or not counts["objects"]:
        raise ValueError("Empty event/object collection")
    for link_table,src_table,src_field,dst_table,dst_field in (
       ("event_object","event","ocel_event_id","object","ocel_object_id"),
       ("object_object","object","ocel_source_id","object","ocel_target_id"),
    ):
        for table,key in ((src_table,src_field),(dst_table,dst_field)):
            dangling=conn.execute(f"""SELECT COUNT(*) FROM {link_table} r
                  LEFT JOIN {table} t ON t.ocel_id = r.{key}
                  WHERE t.ocel_id IS NULL""").fetchone()[0]
            if dangling:
                raise ValueError(f"{dangling} unresolved {key} references in {link_table}")
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    conn.close()
    print(f"OCEL JSON streaming conversion completed: {counts}",flush=True)
    return counts

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--member",required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    convert(a.archive,a.member,a.output)
