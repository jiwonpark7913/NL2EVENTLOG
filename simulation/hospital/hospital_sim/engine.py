"""Process engine: turns the `objects`, `variables` and `process` sections of a
config into a ground-truth object-centric event history.

The engine knows nothing about tables. It produces
  * objects  (type, attributes, links to parent objects, creation time)
  * events   (activity, time, related objects, event attributes)
which are later persisted by recorder.py according to the `recording` section.

Process nodes (YAML). A list is a sequence. A string is a call to a named flow.

  - act: Hospital Admitted          # emit an event
    on: [adm, patient]              # objects related to the event (aliases)
    delay: $door_to_admit           # wait before the event (minutes)
    attrs: {priority: {dist: choice, values: [STAT, ROUTINE]}}
    clip: true                      # if the deadline is hit, emit AT the deadline
  - create: admission               # create an object, bind it to an alias
    as: adm
    attrs: {...}                    # overrides / extra attributes
    link_to: [ed]                   # extra parent links (aliases) besides `links:`
  - wait: $something                # advance the clock
  - xor:                            # exclusive choice
      - {p: 0.3, do: icu_path}
      - {else: true, do: ward_path}
  - and: [branch_a, branch_b]       # parallel, continue after the latest one
  - repeat: lab_draw                # sequential repetitions
    count: $n_draws
    gap: $draw_gap
    isolate: true                   # each repetition starts from a fresh scope
  - spawn: medication_order_flow    # concurrent child instances
    count: $n_med_orders
    start: $first_order_offset      # offset of the first child
    gap: $order_gap                 # offset between successive children
    wait: false                     # parent does not wait for children
  - during:                         # background work bounded by a main path
      main: inpatient_path
      background: [order_activity]
  - set: {adm: {discharge_location: HOME}}
  - link: {ed: [adm]}               # add parent links after creation
  - call: some_flow
  - spawn: lab_result_flow          # one child per list element
    foreach: spec.panel.items       # inside: attrs {item: true} / {lookup: cat, key: k}

Durations anywhere may also be {from_attr: rx.med.interval_h, unit: h}
(a number or a dist stored on a bound object).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from .distributions import Sampler

NODE_KEYS = ("act", "create", "wait", "xor", "and", "repeat", "spawn", "during", "call", "set", "link")


class ConfigError(ValueError):
    pass


@dataclass
class Obj:
    uid: int
    type: str
    created: float
    attrs: dict[str, Any] = field(default_factory=dict)
    links: dict[str, int] = field(default_factory=dict)  # parent type -> uid


@dataclass
class Event:
    uid: int
    activity: str
    time: float
    objects: list[int]
    attrs: dict[str, Any] = field(default_factory=dict)
    eid: str = ""


class Simulation:
    def __init__(self, cfg: dict, seed: int | None = None):
        self.cfg = cfg
        self.seed = cfg.get("seed", 0) if seed is None else seed
        self.rng = random.Random(self.seed)
        self.S = Sampler(self.rng, cfg.get("variables", {}))
        self.otypes: dict[str, dict] = cfg["objects"]
        proc = cfg["process"]
        self.flows: dict[str, Any] = proc.get("flows", {})
        self.catalogs: dict[str, list] = cfg.get("catalogs", {})
        clock = cfg.get("clock", {})
        self.t0 = datetime.fromisoformat(str(clock.get("start", "2150-01-01T00:00:00")))
        self.horizon = float(self.S.resolve(clock.get("observation_end_days", 400))) * 1440.0
        self.objects: list[Obj] = []
        self.events: list[Event] = []
        self._depth = 0

    # ------------------------------------------------------------------ objects
    def new_object(self, otype: str, scope: dict[str, int], t: float, extra: dict | None) -> Obj:
        if otype not in self.otypes:
            raise ConfigError(f"create: unknown object type '{otype}'")
        spec = self.otypes[otype] or {}
        o = Obj(uid=len(self.objects), type=otype, created=t)
        for lt in spec.get("links", []):
            if lt in scope:
                o.links[lt] = scope[lt]
        self.objects.append(o)
        gens = dict(spec.get("attributes", {}) or {})
        gens.update(extra or {})
        for k, g in gens.items():
            o.attrs[k] = self.gen_attr(g, o, scope)
        return o

    def gen_attr(self, g: Any, o: Obj, scope: dict | None = None) -> Any:
        if isinstance(g, dict) and g.get("item") is True and "lookup" not in g:
            return (scope or {}).get("__item__")
        if isinstance(g, dict) and "lookup" in g:
            rows = self.catalogs.get(g["lookup"], [])
            key = (scope or {}).get("__item__") if g.get("item", True) else g.get("value")
            for r in rows:
                if r.get(g["key"]) == key:
                    return dict(r)
            raise ConfigError(f"lookup: no row with {g['key']}={key!r} in catalog '{g['lookup']}'")
        if isinstance(g, dict) and "pick" in g:
            rows = self.catalogs.get(g["pick"])
            if not rows:
                raise ConfigError(f"attribute pick: unknown or empty catalog '{g['pick']}'")
            w = [float(r.get("weight", 1)) for r in rows]
            return dict(self.rng.choices(rows, weights=w, k=1)[0])
        if isinstance(g, dict) and "sample" in g:  # sample a dist stored in another attribute
            v = get_path(o.attrs, g["sample"])
            x = self.S.sample(v)
            if "round" in g and isinstance(x, (int, float)):
                x = round(x, int(g["round"]))
            return x
        x = self.S.sample(g)
        if isinstance(g, dict) and "round" in g and isinstance(x, (int, float)):
            x = round(x, int(g["round"]))
        return x

    def dur(self, spec: Any, scope: dict) -> float:
        if isinstance(spec, dict) and "from_attr" in spec:
            alias, _, path = spec["from_attr"].partition(".")
            if alias not in scope:
                raise ConfigError(f"from_attr: alias '{alias}' not bound")
            v = get_path(self.objects[scope[alias]].attrs, path)
            x = self.S.duration(v)
            from .distributions import UNIT_TO_MIN
            return x * UNIT_TO_MIN[spec.get("unit", "min")]
        return self.S.duration(spec)

    # ------------------------------------------------------------------ running
    def run_all(self) -> None:
        proc = self.cfg["process"]
        arr = proc["arrivals"]
        root = proc.get("root_object", "patient")
        entry = proc["entry"]
        n = self.S.count(arr.get("patients", 10))
        window = float(self.S.resolve(arr.get("window_days", 365))) * 1440.0
        prof = arr.get("hour_profile") or [1] * 24
        if len(prof) != 24:
            raise ConfigError("arrivals.hour_profile must have 24 weights")
        wprof = arr.get("weekday_profile") or [1] * 7
        times = []
        for _ in range(n):
            day = self.rng.randrange(max(1, int(window // 1440)))
            # weekday re-weighting by rejection
            while self.rng.random() > wprof[(self.t0 + timedelta(days=day)).weekday()] / max(wprof):
                day = self.rng.randrange(max(1, int(window // 1440)))
            hour = self.rng.choices(range(24), weights=prof, k=1)[0]
            times.append(day * 1440.0 + hour * 60.0 + self.rng.uniform(0, 60))
        times.sort()
        for t in times:
            p = self.new_object(root, {}, t, None)
            self.run(entry, t, {root: p.uid}, self.horizon)
        self.finalize()

    def run(self, node: Any, t: float, scope: dict[str, int], deadline: float) -> tuple[float, bool]:
        """Execute a node. Returns (end time, alive). alive=False stops the enclosing sequence."""
        if node is None:
            return t, True
        if isinstance(node, list):
            for n in node:
                t, alive = self.run(n, t, scope, deadline)
                if not alive:
                    return t, False
            return t, True
        if isinstance(node, str):
            return self.call(node, t, scope, deadline)
        if not isinstance(node, dict):
            raise ConfigError(f"invalid process node: {node!r}")
        kind = [k for k in NODE_KEYS if k in node]
        if len(kind) != 1:
            raise ConfigError(f"process node must have exactly one of {NODE_KEYS}: {node!r}")
        handler = "n_and_" if kind[0] == "and" else "n_" + kind[0]
        return getattr(self, handler)(node, t, scope, deadline)

    def call(self, name: str, t, scope, deadline):
        if name not in self.flows:
            raise ConfigError(f"unknown flow '{name}'")
        self._depth += 1
        if self._depth > 200:
            raise ConfigError(f"flow recursion too deep at '{name}'")
        try:
            return self.run(self.flows[name], t, scope, deadline)
        finally:
            self._depth -= 1

    def n_call(self, node, t, scope, deadline):
        return self.call(node["call"], t, scope, deadline)

    def n_act(self, node, t, scope, deadline):
        t2 = t + self.dur(node.get("delay"), scope)
        if t2 > deadline:
            if node.get("clip") and deadline < self.horizon:
                t2 = deadline
            else:
                return deadline, False
        on = node.get("on", [])
        on = [on] if isinstance(on, str) else on
        uids = []
        for a in on:
            opt = a.endswith("?")
            a = a.rstrip("?")
            if a in scope:
                uids.append(scope[a])
            elif not opt:
                raise ConfigError(f"act '{node['act']}': alias '{a}' is not bound here (bound: {sorted(scope)})")
        ev = Event(uid=len(self.events), activity=node["act"], time=t2, objects=uids)
        for k, g in (node.get("attrs") or {}).items():
            ev.attrs[k] = self.S.sample(g)
        self.events.append(ev)
        return t2, True

    def n_create(self, node, t, scope, deadline):
        o = self.new_object(node["create"], scope, t, node.get("attrs"))
        for a in node.get("link_to", []):          # extra parents, by alias
            if a not in scope:
                raise ConfigError(f"create {node['create']}: link_to alias '{a}' is not bound")
            o.links[self.objects[scope[a]].type] = scope[a]
        scope[node["create"]] = o.uid
        if node.get("as"):
            scope[node["as"]] = o.uid
        return t, True

    def n_wait(self, node, t, scope, deadline):
        t2 = t + self.dur(node["wait"], scope)
        if t2 > deadline:
            return deadline, False
        return t2, True

    def n_set(self, node, t, scope, deadline):
        for alias, kv in node["set"].items():
            o = self.objects[scope[alias]]
            for k, g in kv.items():
                o.attrs[k] = self.gen_attr(g, o, scope)
        return t, True

    def n_link(self, node, t, scope, deadline):
        for alias, parents in node["link"].items():
            o = self.objects[scope[alias]]
            for p in parents if isinstance(parents, list) else [parents]:
                po = self.objects[scope[p]]
                o.links[po.type] = po.uid
        return t, True

    def n_xor(self, node, t, scope, deadline):
        u = self.rng.random()
        acc = 0.0
        for opt in node["xor"]:
            if opt.get("else"):
                return self.run(opt.get("do"), t, scope, deadline)
            acc += float(self.S.resolve(opt["p"]))
            if u < acc:
                return self.run(opt.get("do"), t, scope, deadline)
        return t, True

    def n_and_(self, node, t, scope, deadline):
        ends, alive = [], True
        merged = dict(scope)
        for br in node["and"]:
            sc = dict(scope)
            e, a = self.run(br, t, sc, deadline)
            ends.append(e)
            alive &= a
            merged.update({k: v for k, v in sc.items() if scope.get(k) != v})
        scope.update(merged)
        return max(ends + [t]), alive

    def n_repeat(self, node, t, scope, deadline):
        n = self.S.count(node.get("count", 1))
        for i in range(n):
            if i:
                t += self.dur(node.get("gap"), scope)
                if t > deadline:
                    return deadline, False
            sc = dict(scope) if node.get("isolate") else scope
            t, alive = self.run(node["repeat"], t, sc, deadline)
            if not alive:
                return t, False
        return t, True

    def n_spawn(self, node, t, scope, deadline):
        items = None
        if node.get("foreach"):
            alias, _, path = node["foreach"].partition(".")
            if alias not in scope:
                raise ConfigError(f"spawn foreach: alias '{alias}' is not bound")
            items = get_path(self.objects[scope[alias]].attrs, path) or []
            n = len(items)
        else:
            n = self.S.count(node.get("count", 1))
        start = t + self.dur(node.get("start"), scope)
        ends = []
        for i in range(n):
            if i:
                start += self.dur(node.get("gap"), scope)
            if start > deadline:
                break
            sc = dict(scope)
            if items is not None:
                sc["__item__"] = items[i]
            e, _ = self.run(node["spawn"], start, sc, deadline)
            ends.append(e)
        if node.get("wait"):
            return max(ends + [t]), True
        return t, True

    def n_during(self, node, t, scope, deadline):
        spec = node["during"]
        snapshot = dict(scope)
        t_end, alive = self.run(spec["main"], t, scope, deadline)
        bg_deadline = t_end if alive else deadline
        bgs = spec.get("background", [])
        for br in bgs if isinstance(bgs, list) else [bgs]:
            self.run(br, t, dict(snapshot), bg_deadline)
        return t_end, alive

    # ------------------------------------------------------------------ helpers
    def finalize(self) -> None:
        self.events.sort(key=lambda e: (e.time, e.uid))
        for i, e in enumerate(self.events, 1):
            e.eid = f"e{i}"
        self.events_by_obj: dict[int, list[Event]] = {}
        for e in self.events:
            for u in e.objects:
                self.events_by_obj.setdefault(u, []).append(e)
        self.children: dict[int, list[int]] = {}
        for o in self.objects:
            for p in o.links.values():
                self.children.setdefault(p, []).append(o.uid)

    def find(self, otype: str, start: list[int]) -> int | None:
        """Nearest object of `otype` among `start` or their ancestors (BFS over links)."""
        seen, frontier = set(), list(start)
        while frontier:
            nxt = []
            for u in frontier:
                if u in seen:
                    continue
                seen.add(u)
                o = self.objects[u]
                if o.type == otype:
                    return u
                nxt.extend(o.links.values())
            frontier = nxt
        return None

    def find_any(self, otype: str, start: list[int]) -> int | None:
        """Ancestor of `otype` if any, else the earliest-created descendant of `otype`."""
        u = self.find(otype, start)
        if u is not None:
            return u
        seen, frontier, hits = set(), list(start), []
        while frontier and not hits:
            nxt = []
            for v in frontier:
                if v in seen:
                    continue
                seen.add(v)
                for c in self.children.get(v, []):
                    (hits if self.objects[c].type == otype else nxt).append(c)
            frontier = nxt
        return min(hits, key=lambda c: (self.objects[c].created, c)) if hits else None

    def to_datetime(self, minutes: float) -> datetime:
        return self.t0 + timedelta(minutes=minutes)


def get_path(d: Any, path: str) -> Any:
    for part in path.split("."):
        if d is None:
            return None
        d = d.get(part) if isinstance(d, dict) else None
    return d
