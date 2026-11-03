"""Gold outputs (true history) and documentation for a simulated database."""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from .recorder import Recorder


def _flat(attrs: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in attrs.items():
        if isinstance(v, dict):
            out.update(_flat({kk: vv for kk, vv in v.items() if not isinstance(vv, dict)}, f"{prefix}{k}."))
        else:
            out[prefix + k] = v
    return out


def _iso(sim, minutes: float) -> str:
    return sim.to_datetime(minutes).replace(microsecond=0).isoformat()


def write_gold(rec: Recorder, out: Path) -> None:
    sim = rec.sim
    out.mkdir(parents=True, exist_ok=True)
    gid = rec.gold_id

    with open(out / "events.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["event_id", "activity", "timestamp", "objects", "attributes"])
        for e in sim.events:
            w.writerow([e.eid, e.activity, _iso(sim, e.time), ";".join(gid(u) for u in e.objects),
                        json.dumps(e.attrs) if e.attrs else ""])
    with open(out / "event_objects.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["event_id", "object_id", "object_type"])
        for e in sim.events:
            for u in e.objects:
                w.writerow([e.eid, gid(u), sim.objects[u].type])
    with open(out / "objects.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["object_id", "object_type", "created", "links", "attributes"])
        for o in sim.objects:
            w.writerow([gid(o.uid), o.type, _iso(sim, o.created),
                        ";".join(gid(p) for p in o.links.values()), json.dumps(_flat(o.attrs), default=str)])
    with open(out / "provenance.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["event_id", "table", "key_column", "row_key", "column", "role"])
        for p in rec.provenance:
            w.writerow([p["event_id"], p["table"], p["key_column"], p["row_key"], p["column"], p["role"]])

    # OCEL 2.0 (JSON)
    otypes, etypes = defaultdict(set), defaultdict(set)
    for o in sim.objects:
        otypes[o.type] |= set(_flat(o.attrs))
    for e in sim.events:
        etypes[e.activity] |= set(e.attrs)
    ocel = {
        "objectTypes": [{"name": k, "attributes": [{"name": a, "type": "string"} for a in sorted(v)]}
                        for k, v in otypes.items()],
        "eventTypes": [{"name": k, "attributes": [{"name": a, "type": "string"} for a in sorted(v)]}
                       for k, v in etypes.items()],
        "objects": [{"id": gid(o.uid), "type": o.type,
                     "attributes": [{"name": k, "time": _iso(sim, o.created), "value": str(v)}
                                    for k, v in _flat(o.attrs).items()],
                     "relationships": [{"objectId": gid(p), "qualifier": t} for t, p in o.links.items()]}
                    for o in sim.objects],
        "events": [{"id": e.eid, "type": e.activity, "time": _iso(sim, e.time),
                    "attributes": [{"name": k, "value": str(v)} for k, v in e.attrs.items()],
                    "relationships": [{"objectId": gid(u), "qualifier": sim.objects[u].type} for u in e.objects]}
                   for e in sim.events],
    }
    (out / "ocel.json").write_text(json.dumps(ocel, indent=1))


def summarize(rec: Recorder, fk_issues: list) -> dict:
    sim = rec.sim
    exact = {p["event_id"] for p in rec.provenance if p["role"] == "exact"}
    per_act = Counter(e.activity for e in sim.events)
    rec_act = Counter(e.activity for e in sim.events if e.eid in exact)
    return {
        "seed": sim.seed,
        "objects": dict(Counter(o.type for o in sim.objects)),
        "events": len(sim.events),
        "activities": {a: {"events": n, "timestamp_in_db": rec_act[a],
                           "not_recoverable": n - rec_act[a]} for a, n in sorted(per_act.items())},
        "tables": {tb["spec"]["name"]: len(tb["rows"]) for tb in rec.tables},
        "foreign_key_violations": len(fk_issues),
    }


def write_dictionary(rec: Recorder, path: Path) -> None:
    lines = ["# Data dictionary (generated)", ""]
    for tb in rec.tables:
        t = tb["spec"]
        lines += [f"## {t['name']}", "", t.get("desc", ""), ""]
        lines += ["| Column | Description |", "| --- | --- |"]
        for c, s in t["columns"].items():
            d = s.get("desc", "")
            if s.get("pk"):
                d = "Primary key. " + d
            if s.get("fk"):
                d += f" References {s['fk']}."
            lines.append(f"| {c} | {d.strip()} |")
        lines.append("")
    path.write_text("\n".join(lines))
