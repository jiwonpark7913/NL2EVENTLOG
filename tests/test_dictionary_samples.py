import json,sqlite3,tempfile
from pathlib import Path
from sys import path as spath
spath.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from add_dictionary_samples import add_samples,write_dictionary

def main():
 with tempfile.TemporaryDirectory() as tmp:
  p=Path(tmp)
  con=sqlite3.connect(p/"d.sqlite")
  con.execute("CREATE TABLE logs(id TEXT, status TEXT, event_time TEXT, notes TEXT)")
  con.executemany("INSERT INTO logs VALUES(?,?,?,?)",[
   ("1","A","2026-01-01","internal sensitive notes"),
   ("2","B","2026-01-02","more sensitive content"),
   ("3","B","2026-01-03","never show notes"),
   ("4","C","2026-01-04","restricted"),
   ("5","D","2026-01-05","restricted")])
  con.commit();con.close()
  d={"tables":[{"table":"logs","columns":[{"name":n,"definition":""} for n in ["id","status","event_time","notes"]]}]}
  n=add_samples(d,p/"d.sqlite")
  assert n["columns"]==4
  cols={c["name"]:c["sample_values"] for c in d["tables"][0]["columns"]}
  assert cols["status"]==["A","B","C"],cols
  assert cols["event_time"]==["2026-01-01","2026-01-02","2026-01-03"]
  assert cols["notes"]==[]
  dest=p/"data_dictionary.json";write_dictionary(dest,d)
  assert json.loads(dest.read_text())==d
  assert '"sample_values": ["A", "B", "C"]' in dest.read_text()
  assert '"sample_values": []' in dest.read_text()
  print("PASS real SQLite samples + privacy + single-line arrays")
if __name__=="__main__":main()
