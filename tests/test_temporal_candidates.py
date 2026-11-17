"""Temporal candidate screening must not equate a timestamp type with an event."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from temporal_candidates import temporal_type,detect
def main():
 assert temporal_type("TIMESTAMP NOT NULL") is True
 assert temporal_type("[datetime] NOT NULL") is True
 assert temporal_type("[datetime2](7)") is True
 assert temporal_type("timestamp with time zone") is True
 assert temporal_type("  [TIMESTAMP](0) NOT NULL") is True
 assert temporal_type("[datetime] NOT NULL") is True
 assert temporal_type("[datetime2](7)") is True
 assert temporal_type("TIME WITHOUT TIME ZONE") is True
 assert temporal_type("VARCHAR(50)") is False
 assert temporal_type("TIMESTAMP(0)") is True
 assert temporal_type("timestamp without time zone") is True
 assert temporal_type("DATE") is True
 assert temporal_type("DATETIME2") is True
 assert temporal_type("INTEGER NOT NULL") is False
 assert temporal_type(None) is None
 dd={"tables":{"admissions":{"columns":[
  {"name":"admittime","sql_type":"TEXT","source_type":"TIMESTAMP","definition":"Admitted at"},
  {"name":"subject_id","sql_type":"TEXT","source_type":"INTEGER","definition":"Patient identity"},
  {"name":"unknown_time","sql_type":"TEXT","source_type":None,"definition":"Unknown type"}]}}}
 result=detect(dd)
 assert [r["status"] for r in result]==["candidate","not_native_temporal","unknown"]
 assert result[0]["definition"]=="Admitted at"
 print("source_type temporal screening: OK")
if __name__=="__main__":main()
