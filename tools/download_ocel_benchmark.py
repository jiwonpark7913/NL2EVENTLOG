#!/usr/bin/env python3
"""Download pinned OCEL benchmarks from Zenodo API and convert to OCEL 2.0 SQLite.

BPI 2019 release: https://zenodo.org/records/22663565
Order Management: https://zenodo.org/records/8428112
Never treat the transformed relational schema as a recovered original enterprise DB.
"""
import argparse,hashlib,json,urllib.request,zipfile,shutil,tempfile
from pathlib import Path

RECORDS={"bpi2019":("22663565","BPIC19_ocel2.zip","06d7911d54db9a9f1ca33ad991488676"),
         "order_management":("8428112","order-management.sqlite","4635d8689ce03687866210afa41457b2")}
def digest(p,kind):
 h=hashlib.new(kind)
 with p.open("rb") as f:
  for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
 return h.hexdigest()
def download(url,out):
 req=urllib.request.Request(url,headers={"User-Agent":"NL2EventLog-benchmark/1.0"})
 with urllib.request.urlopen(req,timeout=90) as response, out.open("wb") as f:shutil.copyfileobj(response,f)
def acquire(name,outdir):
 record_id,filename,md5=RECORDS[name]
 outdir.mkdir(parents=True,exist_ok=True)
 meta_url=f"https://zenodo.org/api/records/{record_id}"
 with urllib.request.urlopen(meta_url,timeout=90) as f:metadata=json.load(f)
 entries=metadata.get("files",[])
 file=next((x for x in entries if x.get("key")==filename),None)
 if file is None:raise ValueError(f"Cannot find pinned {filename} in Zenodo record {record_id}")
 url=file["links"].get("self") or file["links"].get("content")
 if not url:raise ValueError("No download link")
 target=outdir/filename
 if not target.exists() or digest(target,"md5")!=md5:download(url,target)
 if digest(target,"md5")!=md5:raise ValueError("Downloaded source hash differs from pinned Zenodo release")
 if target.suffix==".sqlite":return target
 with zipfile.ZipFile(target) as z:
  members=[m for m in z.infolist() if not m.is_dir() and m.filename.lower().endswith((".sqlite",".sqlite3",".jsonocel",".json",".xml"))]
  if len(members)!=1:raise ValueError(f"Expected one OCEL file in zip, got: {[m.filename for m in members]}")
  member=members[0]
  if member.file_size>2_000_000_000:raise ValueError("Oversized decompressed OCEL")
  extracted=outdir/Path(member.filename).name
  with z.open(member) as a, extracted.open("wb") as b:shutil.copyfileobj(a,b)
 if extracted.suffix.lower() in (".sqlite",".sqlite3"):return extracted
 try:import pm4py
 except ImportError as e:raise RuntimeError("Install pm4py to convert JSON/XML OCEL 2.0") from e
 ext=extracted.suffix.lower()
 if ext in (".json",".jsonocel"):ocel=pm4py.read_ocel2_json(str(extracted))
 elif ext==".xml":ocel=pm4py.read_ocel2_xml(str(extracted))
 else:raise ValueError("Unknown OCEL format")
 output=outdir/(name+".sqlite")
 pm4py.write_ocel2_sqlite(ocel,str(output))
 return output
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("dataset",choices=RECORDS)
 p.add_argument("--dest",type=Path,required=True)
 args=p.parse_args()
 source=acquire(args.dataset,args.dest)
 print(json.dumps({"source":str(source),"sha256":digest(source,"sha256")},indent=2))
