#!/usr/bin/env python3
"""Apply the 2026-11 question/Gold audit to HospitalFlow, PlateFlow and WarehouseFlow.

One-off, author-only migration (same role as the other ``tools/experiments/migrate_*`` scripts).

What it does
------------
1. Reduces each dataset to 40 requests (Q1/Q2/Q3/Q4 = 10 each) by removing the request pairs in
   ``DROP`` together with their Gold SQL/CSV.
2. Repairs request text that no longer matched its Gold log (HospitalFlow H11/H11P) and stale
   request metadata (activity counts, frozen seeds).
3. Repairs stale *physical code values* in author metadata (Gold event bindings and
   ``private/persistence_mapping.json``) so that they agree with the SQLite file and the stored
   Gold SQL. The Gold SQL and Gold CSV of the remaining requests are NOT changed.
4. Repairs data-dictionary statements that contradict the SQLite file (stale CHECK text, checks on
   a column that no longer exists, a rule about a removed table, duplicated rules).
5. Refreshes question documentation and validation counts.

It never writes ``input/database.sqlite``.  Afterwards run::

    python tools/rebuild_all_dataset_reviews.py      # dataset READMEs
    python tools/rebuild_question_gold_review.py     # question-level Gold SQL/DFG review

Usage: python tools/experiments/apply_question_audit_2026_11.py [--drop-file choices.json]
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "datasets/synthetic"

# Request pairs to remove (each id also removes its paraphrase "<id>P").
# Unanswerable requests and one-activity requests go first; the remaining choices are the
# author's selection (defaults below can be overridden with --drop-file).
DROP = {
    "hospitalflow": ["H08", "H10"],
    "plateflow": ["N15", "N16", "N09", "N10", "N13", "N14", "NF06"],
    "warehouseflow": ["W15", "W16", "W01", "W02", "W04", "W05", "WF07"],
}

TEXT_FIXES = {
    "hospitalflow": {
        # The patient_profile table was removed in the MIMIC migration; the Gold log already
        # contains Care Unit Transferred + Hospital Admitted, but the request still asked for
        # "Patient Profile Verified".
        "H11": "For each patient, extract Hospital Admitted and Care Unit Transferred events.",
        "H11P": "Build a timeline for every patient showing their entries into hospital and their moves to a different hospital care unit.",
    }
}
SEED_ACTIVITIES = {"hospitalflow": {"H09": ["Care Unit Transferred"], "H11": ["Hospital Admitted", "Care Unit Transferred"]}}

# logical code used by the legacy builder -> physical code stored in the SQLite file
CODE_MAP = {
    "warehouseflow": {
        ("goods_movement", "movement_code"): {"IN": "I", "OUT": "O"},
        ("request_action", "action_code"): {"CHECK": "A", "HOLD": "H", "RELEASE": "R"},
        ("warehouse_task_history", "task_code"): {"PUTAWAY": "A", "PICK": "K", "PACK": "B"},
        ("handling_history", "handling_code"): {"UNLOAD": "U", "LOAD": "L"},
    },
    "plateflow": {
        ("furnace_operation_history", "operation_code"): {"CH": "C", "HT": "A", "DS": "D"},
        ("rolling_operation_history", "phase_code"): {"RR": "R", "FR": "F"},
        ("finishing_operation_history", "operation_code"): {"LEV": "L", "HT": "A", "SF": "S"},
    },
}

QUESTION_FILES = {
    "hospitalflow": ["evaluation/questions.jsonl", "evaluation/model_questions.jsonl", "private/gold.jsonl"],
    "plateflow": ["private/questions.jsonl", "evaluation/model_questions.jsonl", "private/gold.jsonl"],
    "warehouseflow": ["private/questions.jsonl", "evaluation/model_questions.jsonl", "private/gold.jsonl"],
}
LOG = []


def note(msg):
    LOG.append(msg)
    print(msg)


def qid(rec):
    return rec.get("question_id", rec.get("id"))


def read_jsonl(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()]


def write_jsonl(path, recs, compact):
    sep = (",", ":") if compact else (", ", ": ")
    path.write_text("".join(json.dumps(r, ensure_ascii=False, separators=sep) + "\n" for r in recs))


def _pretty(o, ind=0, key=None):
    """indent=2 JSON with inline ``sample_values`` lists (layout of the checked-in data dictionaries)."""
    sp = " " * ind
    if isinstance(o, dict):
        if not o:
            return "{}"
        return "{\n" + ",\n".join(" " * (ind + 2) + json.dumps(k, ensure_ascii=False) + ": " + _pretty(v, ind + 2, k) for k, v in o.items()) + "\n" + sp + "}"
    if isinstance(o, list):
        if not o:
            return "[]"
        if key == "sample_values" and all(not isinstance(x, (dict, list)) for x in o):
            return "[" + ", ".join(json.dumps(x, ensure_ascii=False) for x in o) + "]"
        return "[\n" + ",\n".join(" " * (ind + 2) + _pretty(x, ind + 2) for x in o) + "\n" + sp + "]"
    return json.dumps(o, ensure_ascii=False)


def _candidates(obj):
    yield _pretty(obj)
    yield json.dumps(obj, indent=2, ensure_ascii=False)
    yield json.dumps(obj, indent=1, ensure_ascii=False)
    yield json.dumps(obj, ensure_ascii=False)
    yield json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    c = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))
    if isinstance(obj, list):
        yield "[\n " + ",\n ".join(c(o) for o in obj) + "\n]"
    if isinstance(obj, dict):
        yield "{\n " + ",\n ".join(c(k) + ":" + c(v) for k, v in obj.items()) + "\n}"
        parts = []
        for k, v in obj.items():
            if isinstance(v, dict):
                parts.append(c(k) + ":{\n  " + ",\n  ".join(c(a) + ":" + c(b) for a, b in v.items()) + "\n }")
            else:
                parts.append(c(k) + ":" + c(v))
        yield "{\n " + ",\n ".join(parts) + "\n}"


def dump_like(path, raw, original, new):
    """Write `new` using whichever JSON layout reproduces the file's current bytes for `original`."""
    tail = raw[len(raw.rstrip()):]
    for i, cand in enumerate(_candidates(original)):
        if cand == raw.rstrip():
            path.write_text(list(_candidates(new))[i] + tail)
            return
    note(f"   (layout of {path.relative_to(ROOT)} not reproducible; rewritten with indent=2)")
    path.write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n")


def is_compact(path):
    first = path.read_text().split("\n", 1)[0]
    return '": ' not in first


def db(name):
    return sqlite3.connect(f"file:{DATA / name / 'input/database.sqlite'}?mode=ro", uri=True)


# ---------------------------------------------------------------- 1. question set
def drop_questions(name, drop):
    base = DATA / name
    gone = set(drop) | {d + "P" for d in drop}
    for rel in QUESTION_FILES[name]:
        path = base / rel
        recs = read_jsonl(path)
        kept = [r for r in recs if qid(r) not in gone]
        write_jsonl(path, kept, is_compact(path))
        note(f"{name}: {rel}: {len(recs)} -> {len(kept)} records")
    removed = 0
    for q in sorted(gone):
        for rel in (f"private/gold_sql/{q}.sql", f"private/gold_logs/{q}.csv"):
            if (base / rel).exists():
                (base / rel).unlink()
                removed += 1
    note(f"{name}: removed {removed} Gold SQL/CSV files of dropped requests")
    seeds_path = base / "source/question_seeds.json"
    raw = seeds_path.read_text()
    seeds = json.loads(raw)
    dump_like(seeds_path, raw, seeds, [s for s in seeds if s["id"] not in gone])
    par_path = base / "source/llm_paraphrases.json"
    raw = par_path.read_text()
    par = json.loads(raw)
    new = dict(par, outputs={k: v for k, v in par["outputs"].items() if k not in gone})
    dump_like(par_path, raw, par, new)
    # docs/questions.md: keep the authored layout, drop removed rows
    doc = base / "docs/questions.md"
    lines = [ln for ln in doc.read_text().splitlines() if not any(ln.startswith(f"| {q} |") for q in gone)]
    doc.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------- 2. request text / metadata
def fix_texts(name):
    base = DATA / name
    fixes = TEXT_FIXES.get(name, {})
    if not fixes:
        return
    for rel in QUESTION_FILES[name]:
        path = base / rel
        recs = read_jsonl(path)
        changed = 0
        for r in recs:
            new = fixes.get(qid(r))
            if new is None:
                continue
            for key in ("question", "text"):
                if key in r and r[key] != new:
                    r[key] = new
                    changed += 1
        write_jsonl(path, recs, is_compact(path))
        if changed:
            note(f"{name}: {rel}: rewrote {changed} text fields ({', '.join(fixes)})")
    # frozen seeds and saved paraphrases must describe the current requests
    q_now = {qid(r): r for r in read_jsonl(base / QUESTION_FILES[name][0])}
    gold_acts = {qid(g): (g.get("es") or {}).get("activities") for g in read_jsonl(base / "private/gold.jsonl")}
    seeds_path = base / "source/question_seeds.json"
    raw_seeds = seeds_path.read_text()
    seeds = json.loads(raw_seeds)
    for s in seeds:
        cur = q_now.get(s["id"])
        if cur and s["question"] != cur.get("text", cur.get("question")):
            s["question"] = cur.get("text", cur.get("question"))
            s["activities"] = SEED_ACTIVITIES.get(name, {}).get(s["id"]) or gold_acts.get(s["id"], s["activities"])
            note(f"{name}: source/question_seeds.json: {s['id']} seed aligned with the current request")
    dump_like(seeds_path, raw_seeds, json.loads(raw_seeds), seeds)
    par_path = base / "source/llm_paraphrases.json"
    raw_par = par_path.read_text()
    par = json.loads(raw_par)
    for k in list(par["outputs"]):
        cur = q_now.get(k + "P")
        if cur and par["outputs"][k] != cur.get("text", cur.get("question")):
            par["outputs"][k] = cur.get("text", cur.get("question"))
            note(f"{name}: source/llm_paraphrases.json: {k} paraphrase aligned with the current request")
    dump_like(par_path, raw_par, json.loads(raw_par), par)


def fix_activity_counts(name):
    """requested/extractable activity counts must equal the number of Gold activities."""
    base = DATA / name
    gold = {qid(g): g for g in read_jsonl(base / "private/gold.jsonl")}
    for rel in QUESTION_FILES[name]:
        path = base / rel
        recs = read_jsonl(path)
        changed = []
        for r in recs:
            g = gold.get(qid(r))
            if not g or g.get("answerability") != "answerable" or "requested_activity_count" not in r:
                continue
            n = len((g.get("es") or {}).get("activities") or [])
            if n and (r["requested_activity_count"] != n or r["extractable_activity_count"] != n):
                r["requested_activity_count"] = r["extractable_activity_count"] = n
                changed.append(qid(r))
        if changed:
            write_jsonl(path, recs, is_compact(path))
            note(f"{name}: {rel}: activity counts corrected for {changed}")


# ---------------------------------------------------------------- 3. stale physical codes in author metadata
def fix_codes(name):
    base = DATA / name
    cmap = CODE_MAP.get(name)
    if cmap:
        path = base / "private/gold.jsonl"
        recs = read_jsonl(path)
        n = 0
        for g in recs:
            for b in (g.get("es") or {}).get("event_bindings", []):
                rf = b.get("row_filter")
                if rf and rf["value"] in cmap.get((b["source_table"], rf["column"]), {}):
                    rf["value"] = cmap[(b["source_table"], rf["column"])][rf["value"]]
                    n += 1
        write_jsonl(path, recs, is_compact(path))
        note(f"{name}: private/gold.jsonl: {n} event-binding row filters now use the physical code stored in SQLite")
        path = base / "private/persistence_mapping.json"
        raw_pm = path.read_text()
        pm = json.loads(raw_pm)
        n = 0
        for b in pm:
            for (table, column), codes in cmap.items():
                if b["table"] != table:
                    continue
                for old, new in codes.items():
                    target = f"({column}='{old}')"
                    if target in b["event_sql"]:
                        b["event_sql"] = b["event_sql"].replace(target, f"({column}='{new}')")
                        n += 1
                    rf = b.get("row_filter")
                    if rf and rf.get("column") == column and rf.get("value") == old:
                        rf["value"] = new
        dump_like(path, raw_pm, json.loads(raw_pm), pm)
        note(f"{name}: private/persistence_mapping.json: {n} event queries repaired")
    if name == "hospitalflow":
        # rebuild the mapping from the current Gold activity sources (old file still listed a removed
        # table/column and pre-migration action codes, and had no transfers binding)
        seen, out = set(), []
        for g in read_jsonl(base / "private/gold.jsonl"):
            for s in (g.get("es") or {}).get("activity_sources", []):
                if s["activity"] not in seen:
                    seen.add(s["activity"])
                    out.append(dict(table=s["table"], activity=s["activity"], timestamp_column=s["timestamp_column"], encoding=s["encoding"], event_sql=s["event_sql"]))
        path = base / "private/persistence_mapping.json"
        raw_pm = path.read_text()
        old = json.loads(raw_pm)
        dump_like(path, raw_pm, old, out)
        note(f"{name}: private/persistence_mapping.json: rebuilt from current Gold activity sources ({len(old)} -> {len(out)} bindings)")
    # every binding must return rows now
    con = db(name)
    bad = [b.get("activity") for b in json.loads((base / "private/persistence_mapping.json").read_text()) if not con.execute(b["event_sql"]).fetchall()]
    if bad:
        raise SystemExit(f"{name}: bindings without rows after repair: {bad}")


# ---------------------------------------------------------------- 4. data dictionary vs SQLite
def table_checks(ddl):
    """Table-level CHECK(...) clauses of a CREATE TABLE statement (column-level checks are skipped)."""
    body = ddl[ddl.index("(") + 1: ddl.rindex(")")]
    parts, depth, cur = [], 0, ""
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    parts.append(cur.strip())
    return [re.sub(r"\s+", " ", p) for p in parts if p.upper().startswith("CHECK")]


def fix_dictionary(name):
    base = DATA / name
    path = base / "input/data_dictionary.json"
    raw = path.read_text()
    dd = json.loads(raw)
    con = db(name)
    ddl = {r[0]: r[1] for r in con.execute("SELECT name,sql FROM sqlite_master WHERE type='table'")}
    norm = lambda s: re.sub(r"\s+", " ", s or "").strip()
    stale_defs = {}
    for t in dd["tables"]:
        tname = t.get("table") or t.get("name")
        if "sql_definition" in t and norm(t["sql_definition"]) != norm(ddl[tname]):
            stale_defs[t["sql_definition"]] = ddl[tname]
            t["sql_definition"] = ddl[tname]
            note(f"{name}: input/data_dictionary.json: {tname}.sql_definition replaced by the actual SQLite DDL")
        if "table_checks" in t:
            actual = table_checks(ddl[tname])
            if [norm(c) for c in t["table_checks"]] != actual:
                note(f"{name}: input/data_dictionary.json: {tname}.table_checks {t['table_checks']} -> {actual}")
                t["table_checks"] = actual
        if t.get("constraint_notes"):
            cols = {r[1] for r in con.execute(f"PRAGMA table_info({tname})")}
            keep = []
            for n in t["constraint_notes"]:
                idents = set(re.findall(r"\b[a-z]+(?:_[a-z0-9]+)+\b", n))
                missing = {i for i in idents if i not in cols and i not in ddl}
                if missing:
                    note(f"{name}: input/data_dictionary.json: removed {tname} constraint note about non-existent {sorted(missing)}")
                else:
                    keep.append(n)
            t["constraint_notes"] = keep
        # column-level foreign-key entries for declared FKs (same shape as the other tables use)
        template = next((c["foreign_keys"][0] for tt in dd["tables"] for c in tt["columns"] if c.get("foreign_keys")), None)
        for r in con.execute(f"PRAGMA foreign_key_list({tname})"):
            col = next(c for c in t["columns"] if c["name"] == r[3])
            if not col.get("foreign_keys") and template is not None and set(template) >= {"table", "column"}:
                entry = dict(template)
                entry.update(table=r[2], column=r[4])
                if "constraint_id" in entry:
                    entry["constraint_id"] = r[0]
                if "position" in entry:
                    entry["position"] = r[1]
                col["foreign_keys"] = [entry]
                note(f"{name}: input/data_dictionary.json: {tname}.{r[3]} now lists its declared foreign key to {r[2]}.{r[4]}")
    rules, seen = [], set()
    for rule in dd.get("business_rules", []):
        key = json.dumps(rule, sort_keys=True)
        if key in seen:
            note(f"{name}: input/data_dictionary.json: removed duplicated business rule")
            continue
        seen.add(key)
        if name == "hospitalflow" and isinstance(rule, str) and rule.startswith("Supplementary profile rows"):
            note(f"{name}: input/data_dictionary.json: removed business rule about the removed patient-profile table")
            continue
        rules.append(rule)
    dd["business_rules"] = rules
    dump_like(path, raw, json.loads(raw), dd)
    # the same stale CREATE TABLE text is copied into author documents; keep them consistent
    if stale_defs:
        skip = {"build.py", "validate.py"}
        for p in sorted(base.rglob("*")):
            if not p.is_file() or p.suffix not in {".md", ".sql", ".json", ".csv"} or p.name in skip or "activity_semantics" in p.parts or p == path:
                continue
            text = p.read_text()
            new = text
            for old_def, new_def in stale_defs.items():
                for a, b in ((old_def, new_def), (json.dumps(old_def)[1:-1], json.dumps(new_def)[1:-1]), (old_def.replace('"', '""'), new_def.replace('"', '""'))):
                    new = new.replace(a, b)
            if new != text:
                p.write_text(new)
                note(f"{name}: {p.relative_to(base)}: stale CREATE TABLE text replaced")


# ---------------------------------------------------------------- 5. documentation and counts
def refresh_docs(name):
    base = DATA / name
    qs = read_jsonl(base / QUESTION_FILES[name][0])
    counts = Counter(q["question_type"] for q in qs)
    answerable = sum(q["answerability"] == "answerable" for q in qs)
    doc = base / "docs/questions.md"
    lines = doc.read_text().splitlines()
    for i, ln in enumerate(lines):
        m = re.match(r"\| (Q[1-4]) \| \d+ \| \d+ \| \d+ \| [\d.]+ \|", ln)
        if m:
            t = [q for q in qs if q["question_type"] == m.group(1)]
            ans = sum(q["answerability"] == "answerable" for q in t)
            avg = sum(q["requested_activity_count"] for q in t) / len(t)
            lines[i] = f"| {m.group(1)} | {len(t)} | {ans} | {len(t) - ans} | {avg:.2f} |"
    doc.write_text("\n".join(lines) + "\n")
    rep_path = base / "validation_report.json"
    raw = rep_path.read_text()
    rep = json.loads(raw)
    rep["total_questions"], rep["answerable_questions"] = len(qs), answerable
    dump_like(rep_path, raw, json.loads(raw), rep)
    # dataset README: question count, browsable question table and Gold pair count
    readme = base / "README.md"
    text = readme.read_text()
    text = re.sub(r"contains \*\*\d+ requests\*\*", f"contains **{len(qs)} requests**", text)
    text = re.sub(r"Browse all \d+ question texts", f"Browse all {len(qs)} question texts", text)
    head = "| ID | Request |\n|---|---|\n"
    start = text.index(head) + len(head)
    end = text.index("\n\n", start)
    table = "\n".join(f"| {qid(q)} | {q.get('text', q.get('question'))} |" for q in qs)
    text = text[:start] + table + text[end:]
    import csv
    rows = sum(len(list(csv.DictReader((base / f"private/gold_logs/{qid(q)}.csv").open()))) for q in qs if q["answerability"] == "answerable")
    text = re.sub(r"Gold SQL/CSV pairs executable and consistent: \d+; compared event rows across questions: \d+\.",
                  f"Gold SQL/CSV pairs executable and consistent: {answerable}; compared event rows across questions: {rows}.", text)
    if name == "hospitalflow":
        old = "H09/H09P and H11/H11P test patient profile events; H10/H10P tests admission detail events."
        if old in text:
            text = text.replace(old, "H09/H09P and H11/H11P test care-unit transfer events from transfers.")
            note(f"{name}: README.md: stale description of H09/H11 corrected")
    readme.write_text(text)
    note(f"{name}: {len(qs)} requests {dict(sorted(counts.items()))}, answerable {answerable}")
    if dict(counts) != {"Q1": 10, "Q2": 10, "Q3": 10, "Q4": 10}:
        raise SystemExit(f"{name}: question-type distribution is not 10/10/10/10")


def verify(name):
    """Stored Gold SQL must reproduce the stored Gold CSV for every remaining request."""
    import csv

    base = DATA / name
    con = db(name)
    n = 0
    for g in read_jsonl(base / "private/gold.jsonl"):
        q = qid(g)
        rows = [tuple(r[k] for k in ("event_id", "case_id", "activity", "timestamp")) for r in csv.DictReader((base / f"private/gold_logs/{q}.csv").open())]
        cur = con.execute((base / f"private/gold_sql/{q}.sql").read_text().strip().rstrip(";"))
        cols = [c[0] for c in cur.description]
        got = [tuple(str(dict(zip(cols, r))[k]) for k in ("event_id", "case_id", "activity", "timestamp")) for r in cur.fetchall()]
        assert Counter(got) == Counter(rows), (name, q)
        n += 1
    stray = {p.stem for p in (base / "private/gold_sql").glob("*.sql")} ^ {qid(g) for g in read_jsonl(base / "private/gold.jsonl")}
    assert not stray, (name, stray)
    note(f"{name}: {n} Gold SQL files re-executed; all equal their Gold CSV")


def main(argv):
    drop = dict(DROP)
    if "--drop-file" in argv:
        drop.update(json.loads(Path(argv[argv.index("--drop-file") + 1]).read_text()))
    for name in ("hospitalflow", "plateflow", "warehouseflow"):
        drop_questions(name, drop[name])
        fix_texts(name)
        fix_activity_counts(name)
        fix_codes(name)
        fix_dictionary(name)
        refresh_docs(name)
        verify(name)


if __name__ == "__main__":
    main(sys.argv[1:])
