"""Persists a simulated history into relational tables (the `recording` section).

Table kinds
  object  one row per object of `object:` type      (column encoding of events)
  event   one row per event whose activity is listed (row encoding)
  static  one row per entry of a catalog            (dictionary tables, d_*)

Column sources (exactly one per column)
  id: <type>|self          persisted id of the row object or of a linked object
  attr: <path>             object attribute (dot path); `of: <type>` for a linked object
  event_time: <activity>   time of that activity on the row object (or `of: <type>`),
                           pick: first|last. One activity or a list.
  time: event              time of the row's event (event tables)
  activity: true           raw activity name; activity_map: {Activity: code}
  event_attr: <name>       attribute attached to the event
  rowid: {start, step} | {format: "{patient}-{seq}", seq_per: patient}
  seq: <type>              running number per linked object of <type> in this table
  rowid_of: {table, activity, of}   row id another table gave to an event
  field: <name>            catalog field (static tables)
  const: <value>

Modifiers
  only_for: [activities]   NULL unless the row's event is one of these
  format: date|datetime    timestamps only (date drops the clock time)
  offset: <dist>           add minutes to a timestamp (technical/store times)
  null_rate: 0.05          recording noise: blank the value with this probability
  pk: true, fk: table.column, type: INTEGER|REAL|TEXT, desc: "..."
"""
from __future__ import annotations

import random
import sqlite3
from datetime import timedelta
from pathlib import Path
from typing import Any

from .distributions import Sampler
from .engine import ConfigError, Simulation, get_path

SOURCES = ("id", "attr", "event_time", "time", "activity", "activity_map", "event_attr",
           "rowid", "seq", "rowid_of", "field", "const")


class Recorder:
    def __init__(self, sim: Simulation, ids: dict, lazy_ids: dict, seed: int):
        self.sim = sim
        self.ids = ids
        self.lazy = lazy_ids
        self.rec = sim.cfg["recording"]
        self.rng = random.Random(seed * 7919 + 1)  # recording noise independent of the process
        self.S = Sampler(self.rng, sim.cfg.get("variables", {}))
        self.tfmt = self.rec.get("time_format", "%Y-%m-%d %H:%M:%S")
        self.dfmt = self.rec.get("date_format", "%Y-%m-%d")
        self.precision = self.rec.get("time_precision", "s")
        self.tables: list[dict] = []
        self.rowreg: dict[tuple, Any] = {}
        self.provenance: list[dict] = []
        self.counters: dict[tuple, int] = {}

    # ------------------------------------------------------------------ ids
    def obj_id(self, uid: int | None) -> Any:
        if uid is None:
            return None
        if uid in self.ids and self.ids[uid] is not None:
            return self.ids[uid]
        o = self.sim.objects[uid]
        if o.type in self.lazy:
            spec = self.lazy[o.type]
            v = self.rowreg.get((spec["table"], spec["activity"], uid))
            if v is not None:
                self.ids[uid] = v
            return v
        return None

    def gold_id(self, uid: int) -> str:
        o = self.sim.objects[uid]
        v = self.obj_id(uid)
        return f"{o.type}:{v if v is not None else 'u' + str(uid)}"

    # ------------------------------------------------------------------ build
    def build(self) -> None:
        names = set()
        for t in self.rec["tables"]:
            if t["name"] in names:
                raise ConfigError(f"duplicate table '{t['name']}'")
            names.add(t["name"])
            self.build_table(t)

    def contexts(self, t: dict):
        kind = t.get("kind", "object")
        sim = self.sim
        if kind == "object":
            otype = t["object"]
            objs = sorted((o for o in sim.objects if o.type == otype), key=lambda o: (o.created, o.uid))
            for o in objs:
                if not self._where(o, t.get("where")):
                    continue
                req = t.get("require_event")
                if req and not any(e.activity in _aslist(req) for e in sim.events_by_obj.get(o.uid, [])):
                    continue
                yield {"start": [o.uid], "obj": o.uid, "event": None}
        elif kind == "event":
            acts = set(_aslist(t["activities"]))
            for e in sim.events:
                if e.activity in acts:
                    row_obj = sim.find_any(t["object"], e.objects) if t.get("object") else None
                    yield {"start": list(e.objects), "obj": row_obj, "event": e}
        elif kind == "static":
            for r in sim.catalogs.get(t["catalog"], []):
                yield {"start": [], "obj": None, "event": None, "row": r}
        else:
            raise ConfigError(f"table {t['name']}: unknown kind '{kind}'")

    def _where(self, o, where) -> bool:
        if not where:
            return True
        for k, allowed in where.items():
            if get_path(o.attrs, k) not in _aslist(allowed):
                return False
        return True

    def build_table(self, t: dict) -> None:
        cols = t["columns"]
        pk = [c for c, s in cols.items() if s.get("pk")]
        if len(pk) > 1:
            raise ConfigError(f"table {t['name']}: only one pk column supported")
        rows, provs = [], []
        for ctx in self.contexts(t):
            row, prov = {}, []
            for c, spec in cols.items():
                row[c] = self.value(t, c, spec, ctx, prov)
            rows.append(row)
            pkv = row[pk[0]] if pk else len(rows)
            for p in prov:
                p["row_key"] = pkv
                p["key_column"] = pk[0] if pk else "(rownum)"
            provs.extend(prov)
            e = ctx["event"]
            if e is not None:
                for u in set(e.objects) | ({ctx["obj"]} if ctx["obj"] is not None else set()):
                    self.rowreg.setdefault((t["name"], e.activity, u), pkv)
            elif ctx["obj"] is not None:
                self.rowreg.setdefault((t["name"], "*", ctx["obj"]), pkv)
        self.provenance.extend(provs)
        self.tables.append({"spec": t, "rows": rows})

    # ------------------------------------------------------------------ values
    def value(self, t, c, spec, ctx, prov) -> Any:
        if not isinstance(spec, dict):
            raise ConfigError(f"{t['name']}.{c}: column spec must be a mapping")
        src = [k for k in SOURCES if k in spec]
        if len(src) != 1 and not (set(src) == {"activity", "activity_map"}):
            raise ConfigError(f"{t['name']}.{c}: need exactly one source of {SOURCES}, got {src}")
        e = ctx["event"]
        if spec.get("only_for") and (e is None or e.activity not in _aslist(spec["only_for"])):
            return None
        sim, start = self.sim, ctx["start"]
        v: Any = None
        k = src[0]
        if k == "id":
            uid = ctx["obj"] if spec["id"] == "self" else sim.find_any(spec["id"], start)
            v = self.obj_id(uid)
        elif k == "attr":
            uid = sim.find_any(spec["of"], start) if spec.get("of") else ctx["obj"]
            v = get_path(sim.objects[uid].attrs, spec["attr"]) if uid is not None else None
        elif k == "event_time":
            uid = sim.find_any(spec["of"], start) if spec.get("of") else ctx["obj"]
            evs = [x for x in sim.events_by_obj.get(uid, []) if x.activity in _aslist(spec["event_time"])]
            if evs:
                ev = evs[0] if spec.get("pick", "first") == "first" else evs[-1]
                v = self.fmt_time(ev.time, spec)
                prov.append({"event_id": ev.eid, "table": t["name"], "column": c,
                             "role": "derived" if spec.get("offset") else "exact"})
        elif k == "time":
            if e is None:
                raise ConfigError(f"{t['name']}.{c}: 'time' needs an event table")
            v = self.fmt_time(e.time, spec)
            prov.append({"event_id": e.eid, "table": t["name"], "column": c,
                         "role": "derived" if spec.get("offset") else "exact"})
        elif k in ("activity", "activity_map"):
            if e is None:
                raise ConfigError(f"{t['name']}.{c}: activity columns need an event table")
            v = spec["activity_map"].get(e.activity, e.activity) if "activity_map" in spec else e.activity
        elif k == "event_attr":
            v = e.attrs.get(spec["event_attr"]) if e else None
        elif k == "rowid":
            v = self.rowid(t, c, spec["rowid"], ctx)
        elif k == "seq":
            key = (t["name"], c, sim.find_any(spec["seq"], start))
            self.counters[key] = self.counters.get(key, 0) + 1
            v = self.counters[key]
        elif k == "rowid_of":
            r = spec["rowid_of"]
            uid = sim.find_any(r["of"], start) if r.get("of") else ctx["obj"]
            v = self.rowreg.get((r["table"], r.get("activity", "*"), uid))
        elif k == "field":
            v = ctx["row"].get(spec["field"])
        elif k == "const":
            v = spec["const"]
        if v is not None and spec.get("null_rate") and self.rng.random() < float(spec["null_rate"]):
            if prov and prov[-1]["column"] == c:
                prov.pop()  # the value is lost, so is the evidence
            return None
        return v

    def rowid(self, t, c, spec, ctx) -> Any:
        if "format" in spec:
            per = spec.get("seq_per")
            anchor = self.sim.find_any(per, ctx["start"]) if per else None
            key = (t["name"], c, anchor)
            self.counters[key] = self.counters.get(key, 0) + 1
            vals = {"seq": self.counters[key]}
            import string
            for _, f, _, _ in string.Formatter().parse(spec["format"]):
                if f and f.split(":")[0] != "seq":
                    vals[f.split(":")[0]] = self.obj_id(self.sim.find_any(f.split(":")[0], ctx["start"]))
            return spec["format"].format(**vals)
        key = (t["name"], c, "counter")
        if key not in self.counters:
            self.counters[key] = int(spec.get("start", 1))
        v = self.counters[key]
        self.counters[key] += max(1, self.S.count(spec.get("step", 1)))
        return v

    def fmt_time(self, minutes: float, spec: dict) -> str:
        if spec.get("offset") is not None:
            minutes += self.S.duration(spec["offset"])
        dt = self.sim.to_datetime(minutes)
        prec = spec.get("precision", self.precision)
        if prec == "s":
            dt = dt.replace(microsecond=0)
        elif prec == "min":
            dt = (dt + timedelta(seconds=30)).replace(second=0, microsecond=0)
        elif prec == "h":
            dt = (dt + timedelta(minutes=30)).replace(minute=0, second=0, microsecond=0)
        return dt.strftime(self.dfmt if spec.get("format") == "date" else self.tfmt)

    # ------------------------------------------------------------------ output
    def write_sqlite(self, path: Path) -> tuple[str, list]:
        path.unlink(missing_ok=True)
        ddl = []
        for tb in self.tables:
            t, rows = tb["spec"], tb["rows"]
            parts = []
            for c, s in t["columns"].items():
                typ = s.get("type") or _infer([r[c] for r in rows])
                d = f"{c} {typ}"
                if s.get("pk"):
                    d += " PRIMARY KEY"
                if s.get("not_null"):
                    d += " NOT NULL"
                if s.get("fk"):
                    rt, rc = s["fk"].split(".")
                    d += f" REFERENCES {rt}({rc})"
                parts.append(d)
            ddl.append(f"CREATE TABLE {t['name']} (\n  " + ",\n  ".join(parts) + "\n);")
        schema = "\n\n".join(ddl) + "\n"
        con = sqlite3.connect(path)
        con.executescript(schema)
        for tb in self.tables:
            t, rows = tb["spec"], tb["rows"]
            cols = list(t["columns"])
            con.executemany(
                f"INSERT INTO {t['name']} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                [[r[c] for c in cols] for r in rows])
        con.commit()
        fk_issues = con.execute("PRAGMA foreign_key_check").fetchall()
        con.close()
        return schema, fk_issues


def _aslist(x) -> list:
    return x if isinstance(x, list) else [x]


def _infer(vals: list) -> str:
    vals = [v for v in vals if v is not None]
    if vals and all(isinstance(v, bool) or isinstance(v, int) for v in vals):
        return "INTEGER"
    if vals and all(isinstance(v, (int, float)) for v in vals):
        return "REAL"
    return "TEXT"
