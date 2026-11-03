"""Assigns the identifiers that objects carry in the database.

`objects.<type>.id` options:

  {start: 20000000, step: {dist: int_uniform, low: 1, high: 60}, order: random}
      integer counter. order=random (default) breaks the link between id order
      and time order, as MIMIC's random cipher does; order=creation keeps it.
      namespace: <name> lets several types draw from ONE counter (values never
      collide, e.g. ICU and ED stays drawing from the transfer counter).
  {format: "{patient}-{seq}", seq_per: patient}
      text id built from linked object ids and a per-parent sequence number,
      like MIMIC poe_id / emar_id.
  {same_as: transfer, pick: first}
      reuse the id of the first (or last) linked child of another type, like
      MIMIC stay_id = first transfer_id of the stay.
  {from_row: {table: poe, activity: Order Entered}}
      the id is whatever row id the given table assigned to the event in which
      this object took part (resolved while recording).
  (absent)
      the object has no persisted identifier of its own.
"""
from __future__ import annotations

import random
import string

from .engine import ConfigError, Simulation


def assign_ids(sim: Simulation, rng: random.Random) -> tuple[dict[int, object], dict[str, dict]]:
    ids: dict[int, object] = {}
    lazy: dict[str, dict] = {}
    counters: dict[str, float] = {}
    by_type: dict[str, list] = {}
    for o in sim.objects:
        by_type.setdefault(o.type, []).append(o)

    fmt_types, same_types = [], []
    for otype, spec in sim.otypes.items():
        idspec = (spec or {}).get("id")
        if not idspec:
            continue
        objs = sorted(by_type.get(otype, []), key=lambda o: (o.created, o.uid))
        if "start" in idspec:
            if idspec.get("order", "random") == "random":
                rng.shuffle(objs)
            ns = idspec.get("namespace", otype)
            counters.setdefault(ns, int(idspec["start"]))
            for o in objs:
                ids[o.uid] = int(counters[ns])
                counters[ns] += max(1, sim.S.count(idspec.get("step", 1)))
        elif "format" in idspec:
            fmt_types.append((otype, idspec, objs))
        elif "same_as" in idspec:
            same_types.append((otype, idspec, objs))
        elif "from_row" in idspec:
            lazy[otype] = idspec["from_row"]
        else:
            raise ConfigError(f"objects.{otype}.id: need one of start/format/same_as/from_row")

    for otype, idspec, objs in fmt_types:
        fields = [f for _, f, _, _ in string.Formatter().parse(idspec["format"]) if f]
        per = idspec.get("seq_per")
        seq: dict[object, int] = {}
        for o in objs:
            key = sim.find(per, [o.uid]) if per else None
            seq[key] = seq.get(key, 0) + 1
            vals = {"seq": seq[key]}
            for f in fields:
                base = f.split(":")[0]
                if base != "seq":
                    u = sim.find(base, [o.uid])
                    if u is None or u not in ids:
                        raise ConfigError(f"objects.{otype}.id format needs '{base}' id, not available")
                    vals[base] = ids[u]
            ids[o.uid] = idspec["format"].format(**vals)

    for otype, idspec, objs in same_types:
        src = idspec["same_as"]
        for o in objs:
            kids = [sim.objects[c] for c in sim.children.get(o.uid, []) if sim.objects[c].type == src]
            kids.sort(key=lambda k: (k.created, k.uid))
            if kids:
                pick = kids[0] if idspec.get("pick", "first") == "first" else kids[-1]
                ids[o.uid] = ids.get(pick.uid)
    return ids, lazy
