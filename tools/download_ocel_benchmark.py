#!/usr/bin/env python3
"""Download pinned OCEL benchmarks from Zenodo API and convert to OCEL 2.0 SQLite.

BPI 2019 release: https://zenodo.org/records/22663565
Order Management: https://zenodo.org/records/8428112
Never treat the transformed relational schema as a recovered original enterprise DB.
"""
import argparse,hashlib,json,urllib.request,zipfile,shutil,tempfile,time
from pathlib import Path

RECORDS={"bpi2019":("22663565","BPIC19_ocel2.zip","06d7911d54db9a9f1ca33ad991488676"),
         "order_management":("8428112","order-management.sqlite","4635d8689ce03687866210afa41457b2")}
def digest(p,kind):
 h=hashlib.new(kind)
 with p.open("rb") as f:
  for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
 return h.hexdigest()
def download(url,out):
 # Large Zenodo archives can intermittently exceed a 90-second read timeout.
 # Resume partial downloads with HTTP Range where supported and validate MD5
 # before accepting the file. If Range is ignored, restart from byte zero.
 for attempt in range(4):
  existing=out.stat().st_size if out.exists() else 0
  headers={"User-Agent":"NL2EventLog-benchmark/1.0"}
  if existing:headers["Range"]=f"bytes={existing}-"
  req=urllib.request.Request(url,headers=headers)
  try:
   with urllib.request.urlopen(req,timeout=240) as response:
    status=getattr(response,"status",200)
    mode="ab" if existing and status==206 else "wb"
    with out.open(mode) as f:shutil.copyfileobj(response,f,length=1024*1024)
   print(f"Downloaded {out.name}: {out.stat().st_size} bytes",flush=True)
   return
  except Exception as exc:
   print(f"Download attempt {attempt+1}/4 failed: {type(exc).__name__}: {exc}",flush=True)
   if attempt==3:raise
   time.sleep(min(2**attempt,8))
def acquire(name,outdir):
 record_id,filename,md5=RECORDS[name]
 outdir.mkdir(parents=True,exist_ok=True)
 meta_url=f"https://zenodo.org/api/records/{record_id}"
 with urllib.request.urlopen(meta_url,timeout=90) as f:metadata=json.load(f)
 entries=metadata.get("files",[])
 file=next((x for x in entries if x.get("key")==filename),None)
 if file is None:raise ValueError(f"Cannot find pinned {filename} in Zenodo record {record_id}")
 print(f"Zenodo record {record_id}, source {filename}, metadata checksum={file.get('checksum','missing')}",flush=True)
 url=file["links"].get("self") or file["links"].get("content")
 if not url:raise ValueError("No download link")
 target=outdir/filename
 if not target.exists() or digest(target,"md5")!=md5:download(url,target)
 if digest(target,"md5")!=md5:raise ValueError("Downloaded source hash differs from pinned Zenodo release")
 print(f"Checksum OK: {target.name} ({target.stat().st_size} bytes)",flush=True)
 if target.suffix==".sqlite":return target
 print(f"Opening ZIP archive: {target}",flush=True)
 with zipfile.ZipFile(target) as z:
  members=[m for m in z.infolist() if not m.is_dir() and m.filename.lower().endswith((".sqlite",".sqlite3",".jsonocel",".json",".xmlocel",".xml"))]
  # Prefer the native SQLite format, then OCEL2 XML, then JSON.
  priority={".sqlite":0,".sqlite3":0,".xmlocel":1,".xml":2,".jsonocel":3,".json":4}
  members=[m for m in members if not m.filename.startswith("__MACOSX/") and not Path(m.filename).name.startswith("._")]
  members.sort(key=lambda m:(priority.get(Path(m.filename).suffix.lower(),9),len(m.filename)))
  if not members:raise ValueError(f"No supported OCEL 2.0 file in zip. Members: {z.namelist()[:40]}")
  print(f"Archive members: {[m.filename for m in members[:10]]}",flush=True)
  member=members[0]
  if member.file_size>2_000_000_000:raise ValueError("Oversized decompressed OCEL")
  extracted=outdir/Path(member.filename).name
  with z.open(member) as a, extracted.open("wb") as b:shutil.copyfileobj(a,b)
 print(f"Extracted OCEL source: {extracted.name} ({extracted.stat().st_size} bytes)",flush=True)
 if extracted.suffix.lower() in (".sqlite",".sqlite3"):return extracted
 try:import pm4py
 except ImportError as e:raise RuntimeError("Install pm4py to convert JSON/XML OCEL 2.0") from e
 ext=extracted.suffix.lower()
 print(f"Converting OCEL file using pm4py, format={ext}",flush=True)
 if ext in (".json",".jsonocel"):ocel=pm4py.read_ocel2_json(str(extracted))
 elif ext in (".xml",".xmlocel"):ocel=pm4py.read_ocel2_xml(str(extracted))
 else:raise ValueError("Unknown OCEL format")
 output=outdir/(name+".sqlite")
 print(f"Imported OCEL: {len(ocel.events)} events, {len(ocel.objects)} objects",flush=True)
 pm4py.write_ocel2_sqlite(ocel,str(output))
 return output
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("dataset",choices=RECORDS)
 p.add_argument("--dest",type=Path,required=True)
 args=p.parse_args()
 source=acquire(args.dataset,args.dest)
 print(json.dumps({"source":str(source),"sha256":digest(source,"sha256")},indent=2))
