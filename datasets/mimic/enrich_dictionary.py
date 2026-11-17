#!/usr/bin/env python3
"""Enrich MIMIC-IV Demo dictionary from official MIMIC-IV documentation.

Do not invent definitions. A missing source remains null. Preserve provenance.
"""
import argparse,json,re,time,urllib.request
from pathlib import Path
from bs4 import BeautifulSoup

BASE="https://mimic.mit.edu/docs/iv/"
HOSP={"admissions","d_hcpcs","d_icd_diagnoses","d_icd_procedures","d_labitems",
"diagnoses_icd","drgcodes","emar","emar_detail","hcpcsevents","labevents",
"microbiologyevents","omr","patients","pharmacy","poe","poe_detail",
"prescriptions","procedures_icd","provider","services","transfers"}
ICU={"caregiver","d_items","chartevents","datetimeevents","icustays",
"ingredientevents","inputevents","outputevents","procedureevents"}
assert len(HOSP|ICU)==31
def page_url(table):
 module="hosp" if table in HOSP else "icu"
 return f"{BASE}modules/{module}/{table if table != 'datetimeevents' else 'datetimesevents'}.html"
def fetch(url):
 request=urllib.request.Request(url,headers={"User-Agent":"NL2EventLog-metadata/1.0"})
 with urllib.request.urlopen(request,timeout=35) as response:
  return response.read().decode("utf-8","replace")
def compact(text,limit=720):
 return re.sub(r"\s+"," ",text or "").strip()[:limit]
def parse(doc,column_names):
 soup=BeautifulSoup(doc,"html.parser")
 main=soup.select_one("main") or soup.select_one("article") or soup
 for x in main.select("script,style,nav,footer"):x.decompose()
 definitions={}
 source_types={}
 valid={c.lower():c for c in column_names}
 heading_nodes=main.find_all(re.compile(r"^h[2-6]$"))
 for table in main.find_all("table"):
  headers=[compact(th.get_text(" ",strip=True)).lower() for th in table.find_all("th")][:3]
  if len(headers)<2 or "name" not in headers[0] or "type" not in headers[1]:continue
  for row in table.find_all("tr"):
   cells=row.find_all(["th","td"])
   if len(cells)<2:continue
   name=compact(cells[0].get_text(" ",strip=True)).strip("`").lower()
   if name in valid:source_types[name]=compact(cells[1].get_text(" ",strip=True),130)
 for node in heading_nodes:
  title=compact(node.get_text(" ",strip=True),250)
  matching=[n for n in re.findall(r"\b[a-z][a-z0-9_]*\b",title.lower()) if n in valid]
  if not matching:continue
  parts=[]
  for sibling in node.next_siblings:
   if getattr(sibling,"name",None) in {"h1","h2","h3","h4","h5","h6"}:break
   if getattr(sibling,"get_text",None):parts.append(sibling.get_text(" ",strip=True))
   elif isinstance(sibling,str):parts.append(sibling)
  definition=compact(" ".join(parts))
  if not definition:continue
  for key in matching:
   if key not in definitions or len(matching)==1:definitions[key]=definition
 summary=None
 for node in heading_nodes:
  title=node.get_text(" ",strip=True).lower()
  if title in ("brief summary","table purpose","detailed description"):
   chunks=[]
   for sibling in node.next_siblings:
    if getattr(sibling,"name",None) in {"h1","h2","h3","h4","h5","h6"}:break
    if hasattr(sibling,"get_text"):chunks.append(sibling.get_text(" ",strip=True))
   if chunks:summary=compact(" ".join(chunks));break
 return summary,definitions,source_types
def enrich(path,strict=False):
 data=json.loads(path.read_text(encoding="utf-8"))
 tables=data["tables"]
 stats={"tables":len(tables),"documented_tables":0,"documented_columns":0,
        "total_columns":0,"missing_pages":[],"unmatched_columns":{}}
 data["dictionary_schema_version"]="2.0"
 data.setdefault("name","MIMIC-IV Clinical Database Demo 2.2")
 data.setdefault("language","en")
 data.setdefault("dbms","SQLite")
 data["documentation_sources"]={"overview":BASE,
  "dataset":"https://physionet.org/content/mimic-iv-demo/2.2/",
  "publisher":"MIT Laboratory for Computational Physiology"}
 for table,record in sorted(tables.items()):
  url=page_url(table)
  record["documentation_url"]=url
  record["definition_source"]=url
  record["source_module"]="hosp" if table in HOSP else "icu"
  record.setdefault("definition",None)
  record.setdefault("foreign_keys",[])
  cols=record["columns"];stats["total_columns"]+=len(cols)
  try:
   summary,definitions,source_types=parse(fetch(url),[c["name"] for c in cols])
   if summary:record["definition"]=summary;stats["documented_tables"]+=1
   for col in cols:
    name=col["name"].lower()
    col["definition"]=definitions.get(name) or col.get("definition") or None
    col["definition_source"]=url if definitions.get(name) else col.get("definition_source")
    col["metadata_id"]="mimic."+table+"."+col["name"]
    col["source_type"]=source_types.get(name) or col.get("source_type")
    col["source_type_source"]=url if source_types.get(name) else col.get("source_type_source")
    if definitions.get(name):stats["documented_columns"]+=1
   missing=[c["name"] for c in cols if not c["definition"]]
   if missing:stats["unmatched_columns"][table]=missing
  except Exception as exc:
   stats["missing_pages"].append({"table":table,"url":url,"reason":str(exc)})
   for col in cols:
    col["definition"]=col.get("definition") or None
    col["definition_source"]=col.get("definition_source")
    col["metadata_id"]="mimic."+table+"."+col["name"]
    col["source_type"]=col.get("source_type")
  time.sleep(0.15)
 data["metadata_coverage"]={"documented_columns":stats["documented_columns"],
   "total_columns":stats["total_columns"],
   "source":"official MIMIC-IV table documentation",
   "notes":"Null means the official description could not be reliably mapped."}
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 # Keep human-readable dictionary consistent with the actual model-input JSON.
 md=["# MIMIC-IV Demo 2.2 — Data Dictionary", "",
     "Source: [MIMIC-IV official documentation]("+BASE+") · "
     "[MIMIC-IV Demo 2.2](https://physionet.org/content/mimic-iv-demo/2.2/)", "",
     "Column descriptions and native types come from the linked official table pages. "
     "Unknown descriptions are left blank; inferred links are not declared FKs.", ""]
 for name,meta in sorted(tables.items()):
  md.extend(["## "+name, "",
   "Official table documentation: ["+meta["documentation_url"]+"]("+meta["documentation_url"]+")", "",
   (meta.get("definition") or "*No verified table summary*"), "",
   "| Column | Native type | SQLite type | Description |",
   "|---|---|---|---|"])
  for col in meta["columns"]:
   desc=(col.get("definition") or "*Not documented / not reliably matched*").replace("|","\\|").replace("\n"," ")
   native=col.get("source_type") or "Unverified"
   md.append("| `"+col["name"]+"` | "+native+" | "+col.get("sql_type","")+" | "+desc+" |")
  md.append("")
 destination=path.parent.parent/"docs/data_dictionary.md"
 destination.parent.mkdir(parents=True,exist_ok=True)
 destination.write_text("\n".join(md)+"\n",encoding="utf-8")
 print(json.dumps(stats,ensure_ascii=False,indent=2),flush=True)
 if strict and (stats["missing_pages"] or stats["documented_columns"]<stats["total_columns"]//2):
  raise SystemExit("Official documentation coverage insufficient; review extraction.")
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--dictionary",type=Path,required=True)
 p.add_argument("--strict",action="store_true")
 a=p.parse_args();enrich(a.dictionary,a.strict)
