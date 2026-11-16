"""Smoke tests for OCEL 2.0 relational reconstruction (no external download)."""
import csv,sqlite3,subprocess,sys,tempfile
from pathlib import Path

SCRIPT=Path(__file__).resolve().parents[1]/"tools/ocel_to_relational.py"
def fixture(path,missing_timestamp=False):
 con=sqlite3.connect(path)
 con.executescript("""
 CREATE TABLE event(ocel_id TEXT,ocel_type TEXT);
 CREATE TABLE object(ocel_id TEXT,ocel_type TEXT);
 CREATE TABLE event_object(ocel_event_id TEXT,ocel_object_id TEXT,ocel_qualifier TEXT);
 CREATE TABLE event_map_type(ocel_type TEXT,ocel_type_map TEXT);
 CREATE TABLE object_object(ocel_source_id TEXT,ocel_target_id TEXT,ocel_qualifier TEXT);
 CREATE TABLE event_PlaceOrder(ocel_id TEXT,ocel_time TEXT);
 INSERT INTO event VALUES('e1','Place Order');
 INSERT INTO object VALUES('o1','Order');
 INSERT INTO object VALUES('o2','Order');
 INSERT INTO object VALUES('o3','Order');
 INSERT INTO object_object VALUES('o1','o3','related');
 INSERT INTO event_object VALUES('e1','o1','subject');
 INSERT INTO event_object VALUES('e1','o2','subject');
 INSERT INTO event_map_type VALUES('Place Order','PlaceOrder');
 """)
 if not missing_timestamp:con.execute("INSERT INTO event_PlaceOrder VALUES('e1','2026-01-01 12:00:00')")
 con.commit();con.close()
def run(tmp,missing=False):
 input=tmp/"source.sqlite";fixture(input,missing)
 output=tmp/"output"
 process=subprocess.run([sys.executable,str(SCRIPT),"--source",str(input),"--out",str(output)],
                        capture_output=True,text=True)
 return process,output
def test_event_to_multiple_cases():
 with tempfile.TemporaryDirectory() as t:
  result,out=run(Path(t))
  assert result.returncode==0,result.stderr
  with (out/"review/gold_flatten/Order.csv").open() as f:rows=list(csv.DictReader(f))
  assert len(rows)==2
  assert {r["case_id"] for r in rows}=={"o1","o2"}
  assert set(r["timestamp"] for r in rows)=={"2026-01-01 12:00:00"}
  with sqlite3.connect(out/"input/database.sqlite") as c:
   assert c.execute("SELECT COUNT(*) FROM activity_subject").fetchone()[0]==2
   assert c.execute("SELECT COUNT(*) FROM entity_link").fetchone()[0]==1
  with (out/"review/gold_flatten/Order_cases.csv").open() as f:
   cases=list(csv.DictReader(f))
  assert {c["case_id"] for c in cases}=={"o1","o2","o3"}
def test_missing_timestamp_fails_closed():
 with tempfile.TemporaryDirectory() as t:
  result,out=run(Path(t),True)
  assert result.returncode!=0
  assert "Incomplete event timestamps" in result.stderr

if __name__=="__main__":
 test_event_to_multiple_cases();test_missing_timestamp_fails_closed()
 print("OCEL reconstruction smoke tests: OK")
