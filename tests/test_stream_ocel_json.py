"""Streaming OCEL JSON fixture: preserve occurrence timestamps, direct E2O and O2O."""
import json,sqlite3,tempfile,zipfile
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from stream_ocel_json import convert

def main():
 with tempfile.TemporaryDirectory() as root:
  base=Path(root)
  data={
   "objectTypes":[{"name":"Order","attributes":[]}],
   "eventTypes":[{"name":"Create Order","attributes":[]}],
   "objects":[
     {"id":"o1","type":"Order","attributes":[],"relationships":[{"objectId":"o2","qualifier":"related"}]},
     {"id":"o2","type":"Order","attributes":[],"relationships":[]}],
   "events":[{"id":"e1","type":"Create Order","time":"2025-01-01T00:00:00Z",
              "attributes":[],"relationships":[{"objectId":"o1","qualifier":"subject"},{"objectId":"o2","qualifier":"subject"}]}]}
  archive=base/"source.zip"
  with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED) as z:
   z.writestr("sample.json",json.dumps(data))
  target=base/"source.sqlite"
  results=convert(archive,"sample.json",target)
  assert results=={"objects":2,"events":1,"e2o":2,"o2o":1},results
  with sqlite3.connect(target) as c:
   assert c.execute("SELECT ocel_time FROM event WHERE ocel_id='e1'").fetchone()[0]=="2025-01-01T00:00:00Z"
   assert c.execute("SELECT COUNT(*) FROM event_object").fetchone()[0]==2
   assert c.execute("SELECT COUNT(*) FROM object_object").fetchone()[0]==1
  print("Streaming OCEL2 JSON fixture: OK")

if __name__=="__main__":main()
