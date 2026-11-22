#!/usr/bin/env python3
"""Regenerate the question-level Gold review (README, DFG SVGs, review_data.json) for the
datasets whose question sets were audited in 2026-11: hospitalflow, plateflow, warehouseflow.

Author/evaluation tooling only. It reads private Gold files and never writes below input/.
It reuses the DFG extraction and SVG layout of ``build_gold_dfg_review.py`` and the source-row
evidence panels of ``gold_source_rows.py``, but resolves files in the current repository layout
(``datasets/<group>/<name>/review/gold_dfg``) and takes event bindings from
``private/persistence_mapping.json`` for every dataset.

Usage:  python tools/rebuild_question_gold_review.py [dataset ...]
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "validation"))

DISPLAY = {"hospitalflow": "HospitalFlow", "plateflow": "PlateFlow", "warehouseflow": "WarehouseFlow"}
RICH = ("plateflow", "warehouseflow")  # README with source-row evidence panels


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def loadjl(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()]


def question_file(base):
    for rel in ("private/questions.jsonl", "evaluation/questions.jsonl"):
        if (base / rel).exists():
            return base / rel
    raise FileNotFoundError(base)


def rebuild_rich(name):
    """PlateFlow / WarehouseFlow format: overview table, DFG and matched source rows per question."""
    import validate_event_scope

    validate_event_scope.bindings = lambda p: json.loads((p / "private/persistence_mapping.json").read_text())
    dfg = load("build_gold_dfg_review", ROOT / "tools/build_gold_dfg_review.py")
    from gold_source_rows import SourceRows, render_review_evidence

    base = ROOT / "datasets/synthetic" / name
    out = base / "review/gold_dfg"
    graphs = out / "graphs"
    graphs.mkdir(parents=True, exist_ok=True)
    questions = loadjl(question_file(base))
    gold = {g["question_id"]: g for g in loadjl(base / "private/gold.jsonl")}
    md = [
        f"# {DISPLAY[name]} — Question-level Gold DFG inspection\n\n**Gold reference only. These files are not model input.**\n\n"
        "[Gold OT → Table → Activities diagram](../database/gold_evidence_graph.svg)\n\n"
        "\nNode counts = event occurrences. Edge counts = adjacent selected events within a case. Dashed amber edges touch timestamp ties "
        "and depend on the tie-break rule. DFGs are projections of the selected log, not causal models.\n"
        "\n[Event graph inventory · tables, objects, OTs and activities](event_graph.md)\n"
        "\n**Source tables** produced matched Gold events. **SQL tables** are all physical tables read by the Gold SQL, including join tables and shared CTE branches.\n"
    ]
    md.append(dfg.dataset_overview(name, questions))
    sources = SourceRows(base)
    cache, records, written = {}, [], set()
    for q in questions:
        ident, typ, text = q["question_id"], q["question_type"], q["text"]
        g = gold[ident]
        answerable = g.get("answerability") == "answerable"
        record = dict(dataset=name, id=ident, type=typ, question=text, answerable=answerable, pair_of=q.get("pair_of"), gold_sha256=None, chart=None)
        md.append(f"\n## {ident} — {typ}\n\n{text}\n")
        if not answerable:
            reason = g.get("reason", "Unsupported by design; no Gold log is present.")
            md.append("\n**No Gold log:** " + reason + "\n")
            record["reason"] = reason
            records.append(record)
            continue
        csvpath = base / "private/gold_logs" / f"{ident}.csv"
        rows = list(csv.DictReader(csvpath.open()))
        sha = hashlib.sha256(csvpath.read_bytes()).hexdigest()
        d = dfg.extract(rows)
        record["gold_sha256"] = sha
        if sha not in cache:
            svg = dfg.graph_svg(d)
            (graphs / f"{ident}.svg").write_text(svg)
            written.add(f"{ident}.svg")
            cache[sha] = f"{ident}.svg"
        filename = cache[sha]
        record["chart"] = "graphs/" + filename
        activities = sorted(d["nodes"])
        cases = len(d["traces"])
        duplicates = len(rows) - len({(r["case_id"], r["event_id"]) for r in rows})
        wanted = (g.get("process_view") or {}).get("activities", [])
        missing = sorted(set(wanted) - set(activities))
        extra = sorted(set(activities) - set(wanted)) if wanted else []
        stats = dict(events=len(rows), observed_cases=cases, activities=len(activities), dfg_edges=len(d["edges"]), duplicate_case_event_pairs=duplicates,
                     tied_timestamp_groups=d["tied_timestamp_groups"], requested_but_not_observed=missing, observed_outside_gold_scope=extra)
        record.update(stats=stats, activity_counts=dict(d["nodes"]),
                      edges=[dict(source=a, target=b, count=n, tie_affected=d["ambiguous"][(a, b)]) for (a, b), n in sorted(d["edges"].items())])
        source_tables, sql_reads, unmatched, related = sources.inspect((base / "private/gold_sql" / f"{ident}.sql").read_text(), rows)
        record["source_tables"] = {table: len(matches) for table, _, matches in source_tables}
        record["unmatched_gold_rows"] = unmatched
        evidence = render_review_evidence(source_tables, unmatched, related, dataset_path="../..", question_id=ident)
        md.append(
            f"\nEvents: **{len(rows)}** · Cases with events: **{cases}** · Activities: **{len(activities)}** "
            f"· Edges: **{len(d['edges'])}** · Source tables: **{len(source_tables)}** · SQL tables: **{len(sql_reads)}**\n\n"
            f'<table><tr><td width="42%" valign="top"><a href="graphs/{filename}">'
            f'<img src="graphs/{filename}" width="390" alt="{ident} Gold DFG"></a></td>'
            f'<td width="58%" valign="top">{evidence}</td></tr></table>\n'
        )
        records.append(record)
    sources.db.close()
    for p in graphs.glob("*.svg"):
        if p.name not in written:
            p.unlink()
    (out / "README.md").write_text("".join(md))
    (out / "review_data.json").write_text(json.dumps(records, indent=2) + "\n")
    return dict(dataset=name, questions=len(questions), gold_logs=sum(r["answerable"] for r in records), graphs=len(written))


def rebuild_hospital():
    """HospitalFlow format: one table row and one DFG per answerable question."""
    name = "hospitalflow"
    hosp = load("rebuild_hospital_gold_review", ROOT / "tools/experiments/rebuild_hospital_gold_review.py")
    from collections import Counter, defaultdict

    base = ROOT / "datasets/synthetic" / name
    out = base / "review/gold_dfg"
    graphs = out / "graphs"
    graphs.mkdir(parents=True, exist_ok=True)
    counts = []
    for g in loadjl(base / "private/gold.jsonl"):
        if g.get("answerability") != "answerable":
            continue
        qid = g["question_id"]
        with (base / "private/gold_logs" / f"{qid}.csv").open(newline="") as f:
            records = list(csv.DictReader(f))
        bycase = defaultdict(list)
        for row in records:
            bycase[row["case_id"]].append(row)
        act, edge, start, end = Counter(), Counter(), Counter(), Counter()
        for items in bycase.values():
            items.sort(key=lambda x: (x["timestamp"], x["event_id"]))
            for x in items:
                act[x["activity"]] += 1
            start[items[0]["activity"]] += 1
            end[items[-1]["activity"]] += 1
            for a, b in zip(items, items[1:]):
                edge[(a["activity"], b["activity"])] += 1
        hosp.make_svg(graphs / f"{qid}.svg", act, edge, start, end)
        counts.append((qid, len(records), len(bycase), len(act)))
    keep = {c[0] + ".svg" for c in counts}
    for p in graphs.glob("*.svg"):
        if p.name not in keep:
            p.unlink()
    rows = [
        "# HospitalFlow — Question-level Gold DFG inspection", "",
        "**Evaluation only: never provide Gold data or DFGs to NL2EventLog model inputs.**", "",
        "DFGs are calculated from each question's Gold event log, using timestamp and event ID for deterministic ordering.", "",
        "Timestamp ties are ordered using event_id only for deterministic display; this does not establish causal ordering.", "",
        "| Question | Events | Cases | Activity types | Gold DFG | Gold SQL |", "|---|---:|---:|---:|---|---|",
    ]
    for q, n, c, a in counts:
        rows.append(f"| {q} | {n} | {c} | {a} | [Graph](graphs/{q}.svg) | [SQL](../../private/gold_sql/{q}.sql) |")
    return counts, rows


def main(argv):
    names = argv or ["hospitalflow", "plateflow", "warehouseflow"]
    for name in names:
        if name in RICH:
            print(json.dumps(rebuild_rich(name)))
        elif name == "hospitalflow":
            counts, rows = rebuild_hospital()
            readme = ROOT / "datasets/synthetic/hospitalflow/review/gold_dfg/README.md"
            old = readme.read_text().splitlines()
            # keep whatever footer followed the question table in the checked-in file
            tail_start = max((i for i, line in enumerate(old) if line.startswith("| ")), default=len(old) - 1) + 1
            readme.write_text("\n".join(rows + old[tail_start:]) + "\n")
            print(json.dumps(dict(dataset=name, gold_logs=len(counts), graphs=len(counts))))
        else:
            raise SystemExit(f"unsupported dataset: {name}")


if __name__ == "__main__":
    main(sys.argv[1:])
