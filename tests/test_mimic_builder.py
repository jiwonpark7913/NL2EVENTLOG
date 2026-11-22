"""Small deterministic MIMIC-IV Demo builder smoke test (does not require network)."""
import csv,json,sqlite3,subprocess,sys,tempfile
from pathlib import Path
BUILDER=Path(__file__).resolve().parents[1]/"datasets/source_relational/mimic/build.py"
def main():
 with tempfile.TemporaryDirectory() as folder:
  root=Path(folder);src=root/"source"
  (src/"hosp").mkdir(parents=True)
  (src/"icu").mkdir(parents=True)
  for filename,header,values in [
    ("hosp/patients.csv",["subject_id","gender"],[["1","F"]]),
    ("hosp/admissions.csv",["subject_id","hadm_id","admittime","dischtime"],[["1","2","2025-01-01","2025-01-03"]]),
    ("icu/chartevents.csv",["subject_id","charttime","storetime"],[["1","2025-01-02","2025-01-02"]])]:
   with (src/filename).open("w",newline="") as f:
    w=csv.writer(f);w.writerow(header);w.writerows(values)
  # Builder writes to its module directory, so smoke test imports only the pure source-discovery
  # and temporal-classification functions to avoid modifying tracked dataset artifacts.
  import importlib.util
  spec=importlib.util.spec_from_file_location("mimic_builder",BUILDER)
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  files=module.find_sources(src)
  assert set(files)=={"patients","admissions","chartevents"}
  assert module.temporal("charttime")=="temporal"
  assert module.temporal("storetime")=="maintenance"
  assert module.temporal("modifieddate")=="maintenance"
  assert module.temporal("admittime")=="temporal"
  assert module.temporal("subject_id")=="other"
  svg,coords,size=module.render(files,{"patients":["subject_id","gender"],
       "admissions":["subject_id","hadm_id","admittime","dischtime"],
       "chartevents":["subject_id","charttime","storetime"]},
       [("admissions","patients","subject_id")])
  assert "#bae6fd" in svg and "#fde68a" in svg
  assert "admissions" in coords
  print("MIMIC builder smoke tests: OK")
if __name__=="__main__":main()
