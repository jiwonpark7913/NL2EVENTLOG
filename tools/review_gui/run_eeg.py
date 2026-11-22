"""Explicit bridge to an external, actual Step-1 EEG implementation.

The dataset repository contains no actual EEG builder. Configure an executable
using NL2EVENTLOG_EEG_RUNNER; the runner MUST accept --database --dictionary
--output --dataset and generate genuine Step-1 nodes/edges. Never use Gold.
"""
from __future__ import annotations
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from dataset_paths import dataset_path

ALLOWED={"mimic","adventureworks","bpi2019_ocel","order_management_ocel"}

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
    return h.hexdigest()

def validate_graph(graph,slug):
    if not isinstance(graph,dict) or not isinstance(graph.get("nodes"),list) or not isinstance(graph.get("edges"),list):
        raise ValueError("Real Step 1 output must be an object with nodes[] and edges[].")
    if graph.get("source")!="actual_step1_eeg" or graph.get("dataset")!=slug:
        raise ValueError("Missing actual_step1_eeg provenance; reject placeholders and mismatched datasets.")
    if not graph.get("generator_version"):
        raise ValueError("EEG generator_version must identify real runtime/version.")
    ids=[n.get("id") for n in graph["nodes"] if isinstance(n,dict)]
    if len(ids)!=len(graph["nodes"]) or not all(isinstance(x,str) and x for x in ids) or len(ids)!=len(set(ids)):
        raise ValueError("Invalid or duplicated EEG node IDs.")
    if any(not isinstance(e,dict) or e.get("source") not in ids or e.get("target") not in ids for e in graph["edges"]):
        raise ValueError("Dangling EEG edges.")
    return graph

def execute(slug, runner=None, timeout=3600):
    if slug not in ALLOWED:raise ValueError("Unsupported dataset")
    runner=runner or os.environ.get("NL2EVENTLOG_EEG_RUNNER","").strip()
    if not runner:
        raise RuntimeError("BLOCKED_NO_RUNTIME: Set NL2EVENTLOG_EEG_RUNNER to the real Step 1 executable. Dataset repository does not implement Step 1.")
    cmd=shlex.split(runner)
    if not cmd:raise RuntimeError("BLOCKED_NO_RUNTIME: empty runner")
    folder=dataset_path(ROOT, slug)
    db=folder/"input/database.sqlite"
    dd=folder/"input/data_dictionary.json"
    if not db.is_file() or not dd.is_file():
        raise FileNotFoundError("BLOCKED_NO_DB_OR_DD: " + str(folder/"input"))
    review=folder/"review/eeg"
    review.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="step1-eeg-") as tmp:
        output=Path(tmp)/"runtime_eeg.json"
        args=cmd+["--database",str(db),"--dictionary",str(dd),
                  "--dataset",slug,"--output",str(output)]
        result=subprocess.run(args,cwd=str(ROOT),stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,text=True,timeout=timeout,check=False)
        if result.returncode!=0:
            raise RuntimeError("BLOCKED_RUNTIME_ERROR ("+str(result.returncode)+"): "+result.stderr[-1500:])
        if not output.is_file():raise RuntimeError("BLOCKED_NO_OUTPUT: runner did not produce an EEG JSON")
        graph=validate_graph(json.loads(output.read_text(encoding="utf-8")),slug)
        # Only after validation, persist reviewer-only output and immutable evidence fingerprint.
        final=review/"actual_eeg.json"
        final.write_text(json.dumps(graph,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        manifest={"dataset":slug,"graph_sha256":sha256(final),"database_sha256":sha256(db),
                  "dictionary_sha256":sha256(dd),"generator_version":graph["generator_version"],
                  "runner_executable":cmd[0],"status":"completed"}
        (review/"run_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
        return final,manifest

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--dataset",choices=sorted(ALLOWED),required=True)
    a=p.parse_args()
    try:
        final,manifest=execute(a.dataset)
        print(json.dumps({"path":str(final),**manifest},ensure_ascii=False))
    except (RuntimeError,FileNotFoundError,ValueError,subprocess.TimeoutExpired) as error:
        print(str(error),file=sys.stderr)
        raise SystemExit(2)
