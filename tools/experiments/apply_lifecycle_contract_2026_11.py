#!/usr/bin/env python3
"""Align the lifecycle (Q3/Q4) Gold logs of PlateFlow and WarehouseFlow with the paper's
recorded-history contract.

Contract (paper, Sections 4.1-4.2 and 5.1): for an implicit request without a process focus the
reference contains every activity that has an executable event definition and a validated, unique
forward attribution path to the requested case notion.  An actual start time and an actual
completion time of the same work record are separate occurrence times.

Three authored conventions contradicted that contract and are changed here:

1. WarehouseFlow WF03/WF03P (worker): *Goods Received* was left out although
   ``goods_movement -> goods_receipt.receiver_id -> worker`` is a unique forward path.
2. PlateFlow NF02/NF02P (rolling plan): only plan milestones and the instruction issue were kept
   although all production work reaches the plan through
   ``... -> as_rolled_material -> rolling_instruction -> planned_rolling_instruction``.
3. PlateFlow: ``started_at`` of the three operation-history tables and of ``plate_quality_review``
   never produced an event, unlike the equally documented start times of WarehouseFlow and
   HospitalFlow.  Nine "... Started" activities are added to every lifecycle log that reaches them.

Gold attribution is NOT limited by path length: the paper lists the bounded path length as a
coverage limitation of the method, so the reference keeps events that need four hops
(NF02 finishing/inspection/review events, HospitalFlow medication administration per patient).

Explicit requests (Q1/Q2) are untouched.  ``input/`` is untouched.  The script first proves that its
SQL generator reproduces every stored lifecycle Gold SQL byte for byte, then applies the changes,
re-executes the SQL and rewrites the Gold CSV and the dependent author metadata.

Run after ``apply_question_audit_2026_11.py``; afterwards run the two review generators.
"""
from __future__ import annotations

import csv
import importlib.util
import io
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "datasets"
spec = importlib.util.spec_from_file_location("audit1", Path(__file__).with_name("apply_question_audit_2026_11.py"))
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)
note, read_jsonl, write_jsonl, is_compact, dump_like, qid = A.note, A.read_jsonl, A.write_jsonl, A.is_compact, A.dump_like, A.qid

PLATE_STARTS = [  # (table, code column, code, activity, event-id prefix, key)
    ("furnace_operation_history", "operation_code", "C", "Furnace Charging Started", "FOP", "operation_id", "FURNACE"),
    ("furnace_operation_history", "operation_code", "A", "Heating Started", "FOP", "operation_id", "FURNACE"),
    ("furnace_operation_history", "operation_code", "D", "Furnace Discharge Started", "FOP", "operation_id", "FURNACE"),
    ("rolling_operation_history", "phase_code", "R", "Rough Rolling Started", "ROP", "operation_id", "ROLLING"),
    ("rolling_operation_history", "phase_code", "F", "Finish Rolling Started", "ROP", "operation_id", "ROLLING"),
    ("finishing_operation_history", "operation_code", "L", "Leveling Started", "TOP", "operation_id", "FINISHING"),
    ("finishing_operation_history", "operation_code", "A", "Heat Treatment Started", "TOP", "operation_id", "FINISHING"),
    ("finishing_operation_history", "operation_code", "S", "Surface Finishing Started", "TOP", "operation_id", "FINISHING"),
    ("plate_quality_review", None, None, "Plate Quality Review Started", "REV", "review_id", None),
]
_TO_PLAN = " JOIN rolling_instruction i ON i.instruction_id=m.instruction_id"
PLATE_PLAN_PATHS = {
    "furnace_operation_history": " JOIN as_rolled_material m ON m.material_id=s.material_id" + _TO_PLAN,
    "rolling_operation_history": " JOIN as_rolled_material m ON m.material_id=s.material_id" + _TO_PLAN,
    "plate_material": " JOIN as_rolled_material m ON m.material_id=s.mother_material_id" + _TO_PLAN,
    "finishing_operation_history": " JOIN plate_material piece ON piece.plate_id=s.plate_id JOIN as_rolled_material m ON m.material_id=piece.mother_material_id" + _TO_PLAN,
    "dimension_inspection": " JOIN plate_material piece ON piece.plate_id=s.plate_id JOIN as_rolled_material m ON m.material_id=piece.mother_material_id" + _TO_PLAN,
    "plate_quality_review": " JOIN plate_material piece ON piece.plate_id=s.plate_id JOIN as_rolled_material m ON m.material_id=piece.mother_material_id" + _TO_PLAN,
}


def con_for(name):
    return sqlite3.connect(f"file:{DATA / name / 'input/database.sqlite'}?mode=ro", uri=True)


def pk_of(con, table):
    (pk,) = [r[1] for r in con.execute(f"PRAGMA table_info({table})") if r[5] > 0]
    return pk


def branch(prefix, binding, pk, path, guard):
    sql = (f"SELECT e.event_id,'{prefix}'||{path['case_key']} case_id,e.activity,e.timestamp FROM ({binding['event_sql']}) e "
           f"JOIN {binding['table']} s ON s.{pk}=e.source_key{path['joins']}")
    return sql + (f" WHERE {path['case_key']} IS NOT NULL" if guard else "")


def compile_sql(branches):
    return "SELECT * FROM (" + " UNION ALL ".join(branches) + ") ORDER BY case_id,timestamp,event_id;"


def act_of(b):
    return b.get("activity") or b["base_activity"]


class Dataset:
    def __init__(self, name):
        self.name, self.base, self.con = name, DATA / name, con_for(name)
        self.pm_path = self.base / "private/persistence_mapping.json"
        self.cp_path = self.base / "private/case_paths.json"
        self.pm_raw, self.cp_raw = self.pm_path.read_text(), self.cp_path.read_text()
        self.pm, self.paths = json.loads(self.pm_raw), json.loads(self.cp_raw)
        self.gold_path = self.base / "private/gold.jsonl"
        self.gold = read_jsonl(self.gold_path)
        self.guard = name == "warehouseflow"

    def binding(self, activity):
        return next(b for b in self.pm if b["activity"] == activity)

    def prefix(self, g):
        return re.search(r"SELECT e\.event_id,'([^']+)'\|\|", g["es"]["compiled_sql"]).group(1)

    def build(self, g, activities):
        concept = g["es"]["case_concept"]
        return compile_sql([branch(self.prefix(g), self.binding(a), pk_of(self.con, self.binding(a)["table"]), self.paths[concept][self.binding(a)["table"]], self.guard) for a in activities])

    def stored_order(self, g):
        """Activity labels in the order of the stored SQL branches."""
        return re.findall(r"event_id,'([^']+)' activity,", g["es"]["compiled_sql"])

    def check_generator(self):
        n = 0
        for g in self.gold:
            if g["question_type"] not in ("Q3", "Q4"):
                continue
            assert self.build(g, self.stored_order(g)) == g["es"]["compiled_sql"], (self.name, qid(g))
            n += 1
        note(f"{self.name}: SQL generator reproduces all {n} stored lifecycle Gold SQL statements byte for byte")

    def attributable(self, concept, prefix):
        """Activities (persistence-mapping order) with a path to the case concept and at least one event."""
        out = []
        for b in self.pm:
            path = self.paths[concept].get(b["table"])
            if path is None:
                continue
            sql = branch(prefix, b, pk_of(self.con, b["table"]), path, True)
            if self.con.execute(f"SELECT COUNT(*) FROM ({sql})").fetchone()[0]:
                out.append(b["activity"])
        return out

    def rewrite(self, g, activities):
        """Regenerate SQL, CSV and record metadata of one lifecycle request. Returns (old, new) event counts."""
        q, concept = qid(g), g["es"]["case_concept"]
        sql = self.build(g, activities)
        rows = self.con.execute(sql.rstrip(";")).fetchall()
        assert len({(r[0], r[1]) for r in rows}) == len(rows), ("duplicate event/case", q)
        csv_path = self.base / f"private/gold_logs/{q}.csv"
        newline = "\r\n" if b"\r\n" in csv_path.read_bytes() else "\n"
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator=newline)
        w.writerow(["event_id", "case_id", "activity", "timestamp"])
        w.writerows(rows)
        csv_path.write_text(buf.getvalue(), newline="")
        (self.base / f"private/gold_sql/{q}.sql").write_text(sql + ("\n" if (self.base / f"private/gold_sql/{q}.sql").read_text().endswith("\n") else ""))
        template = {act_of(b): b for gg in self.gold for b in gg["es"]["event_bindings"]}
        bindings = []
        for a in activities:
            b, path = self.binding(a), dict(self.paths[concept][self.binding(a)["table"]])
            if self.name == "plateflow":
                bindings.append(dict(source_table=b["table"], source_pk=pk_of(self.con, b["table"]), activity=a, timestamp_column=b["timestamp_column"], row_filter=b.get("row_filter"), case_path=path))
            else:
                t = json.loads(json.dumps(next(x for gg in self.gold for x in gg["es"]["event_bindings"]
                                               if x["source_table"] == b["table"] and x["timestamp_column"] == b["timestamp_column"] and x["row_filter"] == b.get("row_filter"))))
                t["case_path"] = {k: path[k] for k in t["case_path"]}
                bindings.append(t)
        old = g["event_count"]
        g["es"].update(activities=sorted(activities), event_bindings=bindings, compiled_sql=sql)
        g["process_view"]["activities"] = sorted(activities)
        g["event_count"] = len(rows)
        g["requested_activity_count"] = g["extractable_activity_count"] = len(activities)
        if "requested_base_activity_count" in g:
            base_n = len({b["base_activity"] for b in bindings})
            g["requested_base_activity_count"] = g["extractable_base_activity_count"] = base_n
        return old, len(rows)

    def save(self):
        write_jsonl(self.gold_path, self.gold, is_compact(self.gold_path))
        dump_like(self.pm_path, self.pm_raw, json.loads(self.pm_raw), self.pm)
        dump_like(self.cp_path, self.cp_raw, json.loads(self.cp_raw), self.paths)
        # question records carry the same counts
        qpath = self.base / "private/questions.jsonl"
        qs = read_jsonl(qpath)
        by = {qid(g): g for g in self.gold}
        for q in qs:
            g = by[qid(q)]
            for k in ("requested_activity_count", "extractable_activity_count", "requested_base_activity_count", "extractable_base_activity_count"):
                if k in q:
                    q[k] = g[k]
        write_jsonl(qpath, qs, is_compact(qpath))
        # docs/questions.md count columns
        doc = self.base / "docs/questions.md"
        lines = doc.read_text().splitlines()
        for i, ln in enumerate(lines):
            cells = ln.split(" | ")
            if len(cells) > 5 and cells[0].startswith("| ") and cells[0][2:] in by and cells[3] == "answerable":
                g = by[cells[0][2:]]
                nums = [g["requested_activity_count"], g["extractable_activity_count"]]
                if "requested_base_activity_count" in g:
                    nums += [g["requested_base_activity_count"], g["extractable_base_activity_count"]]
                cells[4:4 + len(nums)] = [str(n) for n in nums]
                lines[i] = " | ".join(cells)
        doc.write_text("\n".join(lines) + "\n")


def view_stats(ds, concept, table):
    """Activities / rows / empty cases of the full lifecycle view of one case concept."""
    g = next((g for g in ds.gold if g["question_type"] == "Q3" and g["es"]["case_concept"] == concept), None)
    if g is None:
        return None
    rows = list(csv.DictReader((ds.base / f"private/gold_logs/{qid(g)}.csv").open()))
    cases = ds.con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    return dict(activities=sorted({r["activity"] for r in rows}), event_rows=len(rows), cases_without_events=cases - len({r["case_id"] for r in rows}))


def refresh_views(ds):
    """task_scope_catalog.json and validation_report.json describe the lifecycle views."""
    for path, key in ((ds.base / "private/task_scope_catalog.json", "views"), (ds.base / "validation_report.json", "object_view_coverage")):
        raw = path.read_text()
        obj = json.loads(raw)
        for v in obj[key]:
            st = view_stats(ds, v["case_concept"], v["case_table"])
            if st is None:
                continue
            v["activities"], v["activity_count"] = st["activities"], len(st["activities"])
            if "base_activity_count" in v:
                v["base_activity_count"] = len({re.sub(r" (Started|Completed)$", "", a) for a in st["activities"]})
            v["event_rows"], v["cases_without_events"] = st["event_rows"], st["cases_without_events"]
        if path.name == "task_scope_catalog.json" and "completion_policy" in obj:
            obj["completion_policy"] = "Use actual starts, completed occurrences and actual point milestones; an unfinished occurrence supplies its start only."
        if path.name == "validation_report.json":
            counts = Counter()
            for b in ds.pm:
                counts[b["activity"]] = ds.con.execute(f"SELECT COUNT(*) FROM ({b['event_sql']})").fetchone()[0]
            obj["activity_counts"] = {b["activity"]: counts[b["activity"]] for b in ds.pm}
            obj["events"] = sum(counts.values())
            if "checks" in obj:
                obj["checks"]["gold_csvs_verified"] = len(ds.gold)
                if "completion_only" in obj["checks"]:
                    obj["checks"]["completion_only"] = False
            if ds.name == "plateflow":
                obj["timestamp_summary"]["event_timestamp_columns"] = len({(b["table"], b["timestamp_column"]) for b in ds.pm})
                obj["timestamp_summary"]["other_timestamp_columns"] = obj["timestamp_summary"]["timestamp_columns"] - obj["timestamp_summary"]["event_timestamp_columns"]
        dump_like(path, raw, json.loads(raw), obj)


def refresh_object_design(ds):
    """docs/object_activity_design.md lists the same lifecycle views as the scope catalogue."""
    views = {v["case_concept"]: v for v in json.loads((ds.base / "private/task_scope_catalog.json").read_text())["views"]}
    doc = ds.base / "docs/object_activity_design.md"
    lines = doc.read_text().splitlines()
    for i, ln in enumerate(lines):
        cells = ln.split(" | ")
        v = views.get(cells[0][2:]) if cells[0].startswith("| ") else None
        if v is None or len(cells) < 5:
            continue
        nums = [v["case_count"]] + ([v["base_activity_count"]] if "base_activity_count" in v else []) + [v["activity_count"], v["cases_without_events"]]
        if len(cells) != len(nums) + 2:
            continue
        lines[i] = " | ".join([cells[0]] + [str(n) for n in nums] + [", ".join(v["activities"]) + " |"])
    text = "\n".join(lines) + "\n"
    text = text.replace("Worker views include only directly recorded work/receipt/audit/action participation.",
                        "Worker views include directly recorded work/receipt/audit/action participation and the inbound stock posting of each receipt the worker registered.")
    doc.write_text(text)


def plateflow():
    ds = Dataset("plateflow")
    ds.check_generator()
    # (3) start events
    for table, col, code, activity, pre, key, group in PLATE_STARTS:
        cond = f"({col}='{code}')" if col else "(1=1)"
        b = dict(table=table, activity=activity, timestamp_column="started_at",
                 event_sql=f"SELECT '{pre}:'||{key}||':start' event_id,'{activity}' activity,started_at timestamp,{key} source_key FROM {table} WHERE started_at IS NOT NULL AND {cond}")
        if col:
            b["row_filter"] = dict(column=col, value=code, process_group=group)
        # place the start binding directly before its completion binding
        idx = next(i for i, x in enumerate(ds.pm) if x["table"] == table and x["timestamp_column"] == "finished_at" and (x.get("row_filter") or {}).get("value") == code)
        ds.pm.insert(idx, b)
    note("plateflow: 9 start-event bindings added (started_at of furnace/rolling/finishing operations and quality reviews)")
    # (2) rolling-plan paths to all downstream work
    for table, joins in PLATE_PLAN_PATHS.items():
        ds.paths["Rolling Plan"][table] = dict(case_key="i.plan_id", joins=joins, distinct=False)
    note("plateflow: Rolling Plan case paths added for furnace, rolling, plate, finishing, inspection and review records")
    for g in ds.gold:
        if g["question_type"] in ("Q3", "Q4"):
            acts = ds.attributable(g["es"]["case_concept"], ds.prefix(g))
            before = len(g["es"]["activities"])
            old, new = ds.rewrite(g, acts)
            if (old, before) != (new, len(acts)):
                note(f"plateflow: {qid(g)}: activities {before} -> {len(acts)}, events {old} -> {new}")
    ds.save()
    refresh_views(ds)
    # timestamp inventory and scope convention
    used = {(b["table"], b["timestamp_column"]) for b in ds.pm}
    path = ds.base / "docs/timestamp_columns.json"
    raw = path.read_text()
    inv = json.loads(raw)
    for c in inv["columns"]:
        if c["column"] == "started_at" and (c["table"], "started_at") in used:
            c["role"], c["used_as_event_time"] = "Actual interval start", True
    inv["event_timestamp_columns"] = sum(c["used_as_event_time"] for c in inv["columns"])
    inv["other_timestamp_columns"] = len(inv["columns"]) - inv["event_timestamp_columns"]
    dump_like(path, raw, json.loads(raw), inv)
    md = ds.base / "docs/timestamp_columns.md"
    md.write_text(md.read_text().replace("| started_at | Actual interval start; not separately emitted | False |", "| started_at | Actual interval start | True |"))
    ctx = ds.base / "evaluation/task_context.md"
    text = ctx.read_text()
    text = text.replace(
        "- Requests concern actual completed work and actual point milestones. An actual start without a finish does not establish completion. Scheduled or database-maintenance times do not establish completed manufacturing work.",
        "- Requests can select actual recorded starts, completions and point milestones. The full recorded lifecycle includes both actual starts and completions when present; an unfinished occurrence supplies its start only. Scheduled or database-maintenance times do not establish manufacturing work.")
    text = text.replace(
        "- A rolling-plan view includes its own submission/approval/release history and the issue of its related instruction.",
        "- A rolling-plan view includes its own submission/approval/release history, the issue of its related instruction, and the actual work and piece history performed under that instruction.")
    text = text.replace("- An equipment view includes actual completed work performed by that unit.", "- An equipment view includes actual work performed by that unit.")
    text = text.replace("includes the actual completion documented by that particular record", "includes the actual start and completion documented by that particular record")
    ctx.write_text(text)
    # source manifest used by the README / evidence-graph generator
    man_path = ds.base / "review/gold_dfg/gold_source_manifest.json"
    raw = man_path.read_text()
    man = json.loads(raw)
    for table, entry in man["tables"].items():
        acts = sorted(b["activity"] for b in ds.pm if b["table"] == table)
        if acts:
            entry["activities"], entry["timestamps"] = acts, sorted({b["timestamp_column"] for b in ds.pm if b["table"] == table})
    dump_like(man_path, raw, json.loads(raw), man)
    return ds


def warehouseflow():
    ds = Dataset("warehouseflow")
    ds.check_generator()
    # (1) stock movements of a receipt belong to the worker who registered that receipt
    ds.paths["Worker"]["goods_movement"] = dict(case_key="r.receiver_id", joins=" JOIN goods_receipt r ON r.receipt_id=s.receipt_id")
    note("warehouseflow: Worker case path added: goods_movement -> goods_receipt.receiver_id")
    for g in ds.gold:
        if g["question_type"] in ("Q3", "Q4"):
            acts = ds.attributable(g["es"]["case_concept"], ds.prefix(g))
            if sorted(acts) != sorted(g["es"]["activities"]):
                before = len(g["es"]["activities"])
                # keep the stored branch order and append the new activities
                order = ds.stored_order(g) + [a for a in acts if a not in ds.stored_order(g)]
                old, new = ds.rewrite(g, order)
                note(f"warehouseflow: {qid(g)}: activities {before} -> {len(acts)}, events {old} -> {new}")
    ds.save()
    refresh_views(ds)
    ctx = ds.base / "evaluation/task_context.md"
    ctx.write_text(ctx.read_text().replace(
        "- A worker view contains actual recorded actions, receipts, audits and work performed by that worker.",
        "- A worker view contains actual recorded actions, receipts, audits and work performed by that worker, and the inbound stock posting of each receipt that worker registered."))
    return ds


def main():
    for build in (plateflow, warehouseflow):
        ds = build()
        refresh_object_design(ds)
        A.refresh_docs(ds.name)
        A.verify(ds.name)


if __name__ == "__main__":
    main()
