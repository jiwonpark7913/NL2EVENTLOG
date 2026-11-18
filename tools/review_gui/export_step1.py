"""Invoke an external genuine Step 1 runtime and export reviewer artifacts."""
from __future__ import annotations
import argparse, json, os, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
from model import adapt_native_graph, sha256_file, table_catalog

def write_json(path:Path,value:dict)->None:
    """PURPOSE: Persist auditable JSON. INPUT: Destination and mapping. OUTPUT: None; creates review parents."""
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")

def runtime_commit(root:Path)->str|None:
    """PURPOSE: Read runtime Git provenance. INPUT: Runtime root. OUTPUT: Commit or None; no mutation."""
    result=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],capture_output=True,text=True)
    return result.stdout.strip() if result.returncode==0 else None

def find_native_graph(output:Path)->Path:
    """PURPOSE: Locate the native runtime graph. INPUT: Runtime output directory. OUTPUT: Exact path or raises."""
    for name in ("evidence_graph.json","graph.json","dbu_graph.json"):
        if (output/name).is_file(): return output/name
    candidates=[p for p in output.glob("*.json") if p.name not in {"dbu_report.json","llm_calls.json","repair_cache.json"}]
    if len(candidates)==1: return candidates[0]
    raise FileNotFoundError(f"Cannot identify native graph: {[p.name for p in candidates]}")

def export_dataset(dataset_root:Path,runtime_root:Path,*,model:str)->dict:
    """PURPOSE: Run actual Step 1 using only public DB/DD. INPUT: Dataset/runtime roots. OUTPUT: Manifest; writes only review/eeg/."""
    database=dataset_root/"input/database.sqlite"; dictionary=dataset_root/"input/data_dictionary.json"; review=dataset_root/"review/eeg"
    base={"schema_version":"nl2eventlog-step1-run-v1","dataset":dataset_root.name,"started_at":datetime.now(timezone.utc).isoformat(),"runtime_root":str(runtime_root.resolve()),"runtime_commit":runtime_commit(runtime_root),"model":model,"input_policy":"database.sqlite + data_dictionary.json only","gold_used":False,"completed_stages":[],"configuration":{"repair":False,"global_ot_review":False,"semantic_signatures":False}}
    missing=[str(p) for p in (database,dictionary) if not p.is_file()]
    if missing:
        manifest={**base,"status":"BLOCKED_NO_DB","missing_inputs":missing,"finished_at":datetime.now(timezone.utc).isoformat()}; write_json(review/"run_manifest.json",manifest); return manifest
    base["source_files"]={"database.sqlite":sha256_file(database),"data_dictionary.json":sha256_file(dictionary)}
    with tempfile.TemporaryDirectory(prefix="nl2eventlog-step1-") as temporary:
        temporary_root=Path(temporary); output=temporary_root/"runtime"; env=dict(os.environ); env["PYTHONPATH"]=str(runtime_root)+os.pathsep+env.get("PYTHONPATH","")
        raw_dictionary=json.loads(dictionary.read_text(encoding="utf-8")); runtime_dictionary=dictionary.resolve()
        if isinstance(raw_dictionary.get("tables"),dict):
            # Compatibility normalization is lossless and temporary; the original input and hash remain authoritative.
            raw_dictionary["tables"]=table_catalog(raw_dictionary); runtime_dictionary=temporary_root/"data_dictionary.normalized.json"
            runtime_dictionary.write_text(json.dumps(raw_dictionary,ensure_ascii=False),encoding="utf-8"); base["dictionary_adapter"]="legacy_tables_object_to_array"
        command=[sys.executable,"-m","nl2el.dbu","build","--db",str(database.resolve()),"--dd",str(runtime_dictionary),"--out",str(output),"--no-repair","--no-global-ot-review","--no-semantic-signatures","--model",model]
        result=subprocess.run(command,cwd=runtime_root,env=env,capture_output=True,text=True); base.update(command=command,runtime_stdout=result.stdout[-4000:],runtime_stderr=result.stderr[-4000:])
        if result.returncode:
            manifest={**base,"status":"BLOCKED_RUNTIME_ERROR","returncode":result.returncode,"finished_at":datetime.now(timezone.utc).isoformat()}; write_json(review/"run_manifest.json",manifest); return manifest
        native_path=find_native_graph(output); native=json.loads(native_path.read_text(encoding="utf-8")); graph=adapt_native_graph(native); write_json(review/"actual_eeg.json",graph)
        manifest={**base,"status":"RUNNABLE","completed_stages":["1.1","1.2","1.3","1.4","review_adapter"],"native_graph_sha256":sha256_file(native_path),"actual_eeg_sha256":sha256_file(review/"actual_eeg.json"),"node_count":len(graph["nodes"]),"edge_count":len(graph["edges"]),"finished_at":datetime.now(timezone.utc).isoformat()}; write_json(review/"run_manifest.json",manifest); return manifest

def main()->None:
    """PURPOSE: Parse CLI and export datasets. INPUT: Explicit runtime root/slugs. OUTPUT: JSON status list."""
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--runtime-root",type=Path,required=True); parser.add_argument("--repo-root",type=Path,default=Path(__file__).resolve().parents[2]); parser.add_argument("--model",default="deterministic-no-model"); parser.add_argument("datasets",nargs="+",choices=("mimic","adventureworks","bpi2019_ocel","order_management_ocel")); args=parser.parse_args()
    if not (args.runtime_root/"nl2el/dbu/__main__.py").is_file(): parser.error("--runtime-root does not expose nl2el.dbu")
    print(json.dumps([export_dataset(args.repo_root/"datasets"/slug,args.runtime_root,model=args.model) for slug in args.datasets],ensure_ascii=False,indent=2))

if __name__=="__main__": main()
