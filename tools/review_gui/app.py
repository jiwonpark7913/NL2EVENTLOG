"""Read-only dataset and EEG evidence review UI.

Run: streamlit run tools/review_gui/app.py
Review output is separate from model inputs; importing an EEG does not
validate its semantics. This GUI never fabricates EEG nodes.
"""
from __future__ import annotations
import csv
import os
import sys
import gzip
import io
import json
import sqlite3
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_eeg import dataset_path, execute as execute_eeg, validate_graph as validate_actual_graph

ROOT = Path(__file__).resolve().parents[2]
DATASETS = {
    "MIMIC-IV Demo": "mimic",
    "AdventureWorks": "adventureworks",
    "BPI 2019 OCEL": "bpi2019_ocel",
    "Order Management OCEL": "order_management_ocel",
}
st.set_page_config(page_title="NL2EventLog | Evidence Review", layout="wide")
st.title("NL2EventLog — Dataset & EEG Review")
st.caption("Physical DB → Data Dictionary → actual EEG evidence → request-specific Event Log. Review-only: never edits model input.")
with st.sidebar:
    dataset = st.selectbox("Dataset", list(DATASETS))
    slug = DATASETS[dataset]
    root = dataset_path(ROOT, slug)
    st.markdown("**Data source**")
    st.code(str(root), language=None)
    st.info("The OCEL relational databases are generated as GitHub Actions artifacts and may need to be downloaded into datasets/.")
    st.markdown("**Evidence state**")
    st.caption("No graph is displayed as an actual EEG unless an EEG export is supplied.")
    st.markdown("[EEG terminology contract](https://github.com/jiwonpark7913/NL2EVENTLOG/blob/main/docs/system/EEG_ENTITY_MODEL.md)")

def read_json(path):
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return None

def read_db(path):
    if path.exists():
        return sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    return None

def valid_identifier(value):
    return '"' + value.replace('"', '""') + '"'

def table_catalog(dd):
    raw = dd.get("tables", [])
    if isinstance(raw, dict):
        return [{"table": name, **meta} for name, meta in raw.items()]
    return raw

def metadata(cols):
    return [{
        "name": c.get("name"),
        "type": c.get("data_type") or c.get("source_type") or c.get("type"),
        "storage": c.get("storage_type") or c.get("sql_type"),
        "definition": c.get("definition") or c.get("description"),
        "sample_values": c.get("sample_values", []),
    } for c in cols]

def validate_graph(graph):
    if not isinstance(graph, dict):
        return "EEG JSON must be an object."
    nodes, edges = graph.get("nodes"), graph.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return "EEG requires nodes[] and edges[]. Export an adapter JSON from the actual Step 1 EEG."
    ids = [n.get("id") for n in nodes if isinstance(n, dict)]
    if len(ids) != len(nodes) or any(not isinstance(i, str) or not i for i in ids):
        return "Every EEG node must have a unique nonempty string id."
    if len(set(ids)) != len(ids):
        return "Duplicated EEG node ids."
    for edge in edges:
        if not isinstance(edge, dict) or edge.get("source") not in ids or edge.get("target") not in ids:
            return "Every EEG edge must connect existing node IDs."
    return None

def graphviz_source(graph, selected, show_unresolved):
    palette = {"table": "#dbeafe", "entity_type": "#dcfce7", "event_definition": "#fef3c7",
               "identification_rule": "#d1fae5", "attribution_rule": "#fce7f3"}
    escaped = lambda s: str(s).replace("\\", "\\\\").replace('"', r'\"').replace("\n", " ")
    nodes = graph["nodes"]
    selected_ids = set(selected)
    visible = {n["id"] for n in nodes if (not selected_ids or n["id"] in selected_ids) and (
        show_unresolved or n.get("status") not in {"unresolved", "rejected"})}
    lines = ['digraph EEG {', 'rankdir=LR; bgcolor="white"; graph [pad="0.3",nodesep="0.4",ranksep="0.75"];',
             'node [shape=box,style="rounded,filled",fontname="Arial",fontsize=11];']
    for node in nodes:
        if node["id"] not in visible:
            continue
        typ = node.get("type", "unknown")
        label = node.get("label") or node["id"]
        detail = node.get("status") or ""
        lines.append(f'"{escaped(node["id"])}" [label="{escaped(label)}\\n{escaped(typ)} | {escaped(detail)}",fillcolor="{palette.get(typ, "#f1f5f9")}"];')
    for edge in graph["edges"]:
        if edge["source"] not in visible or edge["target"] not in visible:
            continue
        lines.append(f'"{escaped(edge["source"])}" -> "{escaped(edge["target"])}" [label="{escaped(edge.get("type", ""))}",fontsize=9];')
    lines.append("}")
    return "\n".join(lines)

def read_log(path):
    if path is None: return []
    content = path.read().decode("utf-8-sig") if hasattr(path, "read") else Path(path).read_text(encoding="utf-8-sig")
    return list(csv.DictReader(io.StringIO(content)))

dd = read_json(root / "input/data_dictionary.json")
if dd is None:
    st.warning("Data Dictionary가 로컬에 없습니다. 특히 OCEL은 Actions artifact를 먼저 다운로드해 datasets/<group>/<name>/input/에 배치하세요.")
    uploaded_dd = st.file_uploader("Load data_dictionary.json", type="json")
    if uploaded_dd:
        dd = json.load(uploaded_dd)

tabs = st.tabs(["1 · DB & Dictionary", "2 · Actual EEG", "3 · Question & Gold", "4 · Review export"])
with tabs[0]:
    st.subheader("Physical evidence")
    if dd:
        tables = table_catalog(dd)
        names = [t["table"] for t in tables]
        st.metric("Tables", len(tables))
        filter_text = st.text_input("Search table", "")
        filtered = [n for n in names if filter_text.lower() in n.lower()]
        if not filtered:
            st.info("No matching tables.")
        else:
            name = st.selectbox("Table", filtered)
            table = next(t for t in tables if t["table"] == name)
            st.write("**Definition:**", table.get("definition") or "Not documented")
            st.dataframe(metadata(table.get("columns", [])), use_container_width=True, hide_index=True)
            st.write("**Declared primary key:**", table.get("primary_key"))
            st.write("**Declared foreign keys:**", table.get("foreign_keys") or table.get("foreign_keys_declared") or [])
            with st.expander("Candidate relationships (not declared FKs)"):
                links = [x for x in dd.get("candidate_relationships", [])
                         if name in (x.get("source_table"), x.get("target_table"))]
                st.json(links)
            dbpath = root / "input/database.sqlite"
            if not dbpath.exists() and (root / "input/database.sqlite.gz").exists():
                st.warning("Compressed SQLite exists, but the DB must be decompressed locally before preview.")
            con = read_db(dbpath)
            if con is not None:
                try:
                    actual = {x[0] for x in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    if name in actual:
                        st.markdown("**Actual source rows (read-only, LIMIT 10)**")
                        cursor = con.execute("SELECT * FROM " + valid_identifier(name) + " LIMIT 10")
                        st.dataframe([dict(zip([c[0] for c in cursor.description], row)) for row in cursor.fetchall()],
                                     use_container_width=True)
                    else: st.warning("Table not found in physical DB.")
                finally: con.close()
            else: st.info("SQLite snapshot not found. Dictionary-only mode.")
    else: st.info("No database dictionary loaded.")

with tabs[1]:
    st.subheader("Actual Event Extraction Graph")
    runner = os.environ.get("NL2EVENTLOG_EEG_RUNNER", "").strip()
    if runner:
        st.success("External Step 1 runner configured. The EEG can be generated from the current dataset inputs.")
        if st.button("Run actual Step 1 and load EEG", key="run_actual_step1"):
            with st.spinner("Executing real Step 1 using database and dictionary only"):
                try:
                    output, manifest = execute_eeg(slug, runner=runner)
                    st.success(f"Actual EEG saved: {output}")
                    st.json(manifest)
                except Exception as exc:
                    st.error(str(exc))
    else:
        st.warning("BLOCKED_NO_RUNTIME: The full Step 1 implementation is not in this dataset repository. Configure NL2EVENTLOG_EEG_RUNNER to its executable; no fake EEG is generated.")
        st.code('export NL2EVENTLOG_EEG_RUNNER="python /absolute/path/to/step1_export.py"', language="bash")
    manifest_path = root / "review/eeg/run_manifest.json"
    manifest = read_json(manifest_path)
    if manifest:
        st.caption(f"EEG generation provenance: {manifest.get('status', 'unknown')} · {manifest.get('generator_version', '?')}")

    st.warning("ERD and authored Gold evidence graphs are **not** the EEG produced by Step 1. Only an exported Step 1 EEG is accepted here.")
    eeg_paths = [
        root / "review/eeg/actual_eeg.json",
        root / "review/eeg/eeg_export.json",
    ]
    existing = next((p for p in eeg_paths if p.exists()), None)
    upload = st.file_uploader("Upload actual EEG export (JSON)", type="json", key="eeg")
    graph = json.load(upload) if upload is not None else read_json(existing) if existing else None
    if graph is None:
        st.info("No actual EEG export was found. Use Codex to run the Step 1 implementation and export the graph to review/eeg/actual_eeg.json.")
    else:
        error = validate_graph(graph)
        if not error:
            try:
                validate_actual_graph(graph, slug)
            except ValueError as exc:
                error = str(exc)
        if error:
            st.error(error)
        else:
            nodes = graph["nodes"]; edges = graph["edges"]
            a,b,c = st.columns(3)
            a.metric("Graph nodes", len(nodes)); b.metric("Graph edges", len(edges))
            c.metric("Unresolved nodes", sum(n.get("status") in ("unresolved", "rejected") for n in nodes))
            types = sorted({n.get("type", "unknown") for n in nodes})
            chosen_types = st.multiselect("Node types", types, default=types)
            chosen_nodes = [n["id"] for n in nodes if n.get("type", "unknown") in chosen_types]
            include_unresolved = st.checkbox("Show unresolved/rejected evidence", value=True)
            try:
                st.graphviz_chart(graphviz_source(graph, chosen_nodes, include_unresolved), use_container_width=True)
            except Exception as exc:
                st.error(f"Graphviz render failed: {exc}")
            st.dataframe([{"id":n["id"],"type":n.get("type"),"label":n.get("label"),
                          "status":n.get("status"),"evidence":str(n.get("evidence", ""))[:400]} for n in nodes],
                         use_container_width=True, hide_index=True)
            st.caption("Inspect each Event definition's source table, predicate, time role, occurrence identity and applicable Entity Type attribution.")
            node_id = st.selectbox("Inspect specific node", [n["id"] for n in nodes])
            st.json(next(n for n in nodes if n["id"]==node_id))
            attached = [e for e in edges if node_id in (e["source"], e["target"])]
            st.json({"related_edges":attached})
with tabs[2]:
    st.subheader("Natural-language request → reviewed extraction")
    proposal = read_json(root / "review/admission_timeline.json") if slug == "mimic" else None
    req = st.text_area("Natural-language analysis request",value=(proposal or {}).get("request", ""),key="request")
    st.caption("The question must describe a process analysis objective, not an evaluator's Gold verification checklist.")
    case_et = st.text_input("Case ET (reviewer interpretation)",value=(proposal or {}).get("case_et",""),key="case_et")
    if proposal:
        st.info("MIMIC admission example is a draft. Its proposed event candidates are not approved Gold.")
        st.dataframe(proposal.get("event_candidates",[]), use_container_width=True)
    gold_file = st.file_uploader("Upload reviewed/reference Event Log CSV", type="csv")
    if gold_file is not None:
        log = read_log(gold_file)
        st.metric("Rows",len(log))
        st.dataframe(log[:200],use_container_width=True)
        fields = list(log[0]) if log else []
        needed = {"case_id","event_id","activity","timestamp"}
        missing = sorted(needed-set(fields))
        if missing:st.warning(f"Missing canonical fields: {missing}; reconcile column mappings before auditing.")
        else:
            distinct = len({row["event_id"] for row in log})
            st.metric("Distinct event IDs",distinct)
            st.write("Case count in event rows:",len({row["case_id"] for row in log}))
            st.caption("Event-row case count does not include empty cases. A separate case-population file is required.")
    st.warning("Passing structural checks is not independent semantic approval of Gold or EEG.")
with tabs[3]:
    st.subheader("Independent reviewer decision")
    st.caption("Review output is never written under model input/. Download it into review/eeg/ manually.")
    checklist = {
        "Physical schema and DD match": "Compare actual SQLite tables/columns and dictionary.",
        "Entity Type meaning and granularity": "Confirm ET identity rules and same-instance mapping.",
        "Event definition provenance": "Verify source, carrier/value, predicate, timestamp, and occurrence ID.",
        "Temporal semantics": "Distinguish occurrence, recording and planned/valid time.",
        "Event-to-Entity attribution": "Validate join direction, key uniqueness and applicable rows.",
        "Case population": "Include eligible cases with zero selected events.",
        "No evaluation leakage": "Only DB/DD are model-visible; Gold and reviewer notes stay private.",
        "Reference event rows": "Compare selected source records to event occurrences independently.",
    }
    st.write("Select checks only after independently inspecting evidence.")
    decisions = {}
    for label, help_text in checklist.items():
        decisions[label] = st.selectbox(label, ["pending","pass","fail","not_applicable"],help=help_text)
    notes = st.text_area("Evidence, record IDs, counterexamples, unresolved issues")
    reviewer = st.text_input("Reviewer ID")
    result = {
        "dataset":slug, "request":st.session_state.get("request",""),
        "case_et":st.session_state.get("case_et",""),
        "reviewer":reviewer,"checks":decisions,"notes":notes,
        "approval":"needs_review", "method":"manual_evidence_review"}
    st.download_button("Export review JSON",data=json.dumps(result,indent=2,ensure_ascii=False),
                       file_name=f"{slug}_review.json",mime="application/json")
    st.caption("Downloading a review never converts a draft into approved Gold.")
