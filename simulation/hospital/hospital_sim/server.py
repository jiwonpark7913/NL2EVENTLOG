"""Local web UI:  python -m hospital_sim ui  ->  http://127.0.0.1:8765

Three panels
  left    variables (edit, preview distribution, save back into the YAML file)
  middle  process model (flows rendered as blocks)
  right   recording: tables, column sources, where every activity is stored

Standard library only (plus PyYAML). Saving rewrites only the edited value
lines of the `variables:` block, so comments and layout of the file survive.
"""
from __future__ import annotations

import json
import random
import re
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml

from .distributions import Sampler, UNIT_TO_MIN
from .engine import ConfigError
from .run import load_config, load_value, simulate

UI_FILE = Path(__file__).with_name("ui.html")
LOCK = threading.Lock()


# ----------------------------------------------------------------------------- model
def _aslist(x):
    return x if isinstance(x, list) else [x]


def _vars_in(node, acc: set):
    if isinstance(node, str):
        if node.startswith("$"):
            acc.add(node[1:])
    elif isinstance(node, dict):
        for v in node.values():
            _vars_in(v, acc)
    elif isinstance(node, list):
        for v in node:
            _vars_in(v, acc)
    return acc


def _acts_in(node, acc: list):
    if isinstance(node, dict):
        if "act" in node:
            acc.append(node["act"])
        for v in node.values():
            _acts_in(v, acc)
    elif isinstance(node, list):
        for v in node:
            _acts_in(v, acc)
    return acc


def variable_groups(text: str) -> list[dict]:
    """Groups taken from '# comment' lines inside the variables block."""
    groups, cur, inside = [], None, False
    for line in text.splitlines():
        if re.match(r"^variables:\s*(#.*)?$", line):
            inside = True
            continue
        if inside and re.match(r"^\S", line) and not line.startswith("#"):
            break
        if not inside:
            continue
        m = re.match(r"^\s{2}#\s*(.+)$", line)
        if m:
            cur = {"name": m.group(1).strip(), "vars": []}
            groups.append(cur)
            continue
        m = re.match(r"^\s{2}([A-Za-z_]\w*):", line)
        if m:
            if cur is None:
                cur = {"name": "variables", "vars": []}
                groups.append(cur)
            cur["vars"].append(m.group(1))
    return groups


def describe_source(spec: dict) -> dict:
    """Human-readable summary of one recording column."""
    s = dict(spec)
    out = {"kind": "", "text": "", "activities": [], "role": None}
    if "event_time" in s:
        acts = _aslist(s["event_time"])
        out.update(kind="time", activities=acts,
                   role="date only" if s.get("format") == "date" else ("derived" if s.get("offset") else "column"))
        out["text"] = " / ".join(acts) + (f"  (of {s['of']})" if s.get("of") else "") + \
            (f"  [{s.get('pick')}]" if s.get("pick") else "")
    elif "time" in s:
        out.update(kind="time", role="derived" if s.get("offset") else "row", text="event time")
    elif "id" in s:
        out.update(kind="id", text="own id" if s["id"] == "self" else f"id of {s['id']}")
    elif "attr" in s:
        out.update(kind="attr", text=s["attr"] + (f"  (of {s['of']})" if s.get("of") else ""))
    elif "activity_map" in s or "activity" in s:
        m = s.get("activity_map") or {}
        out.update(kind="activity", activities=list(m), role="label",
                   text=", ".join(f"{k} → {v}" for k, v in m.items()) or "activity name")
    elif "event_attr" in s:
        out.update(kind="attr", text=f"event attribute {s['event_attr']}")
    elif "rowid" in s:
        r = s["rowid"]
        out.update(kind="id", text=f"row id {r.get('format', 'counter')}")
    elif "rowid_of" in s:
        r = s["rowid_of"]
        out.update(kind="id", text=f"row id of {r['table']} [{r.get('activity', '*')}]")
    elif "seq" in s:
        out.update(kind="id", text=f"sequence per {s['seq']}")
    elif "field" in s:
        out.update(kind="attr", text=f"catalog field {s['field']}")
    elif "const" in s:
        out.update(kind="const", text=f"constant {s['const']}")
    flags = []
    if s.get("pk"):
        flags.append("PK")
    if s.get("fk"):
        flags.append("FK → " + s["fk"])
    if s.get("only_for"):
        flags.append("only for " + ", ".join(_aslist(s["only_for"])))
    if s.get("offset") is not None:
        flags.append("offset " + (s["offset"] if isinstance(s["offset"], str) else "dist"))
    if s.get("null_rate"):
        flags.append(f"null {s['null_rate']}")
    out["flags"] = flags
    out["desc"] = s.get("desc", "")
    return out


def build_model(path: Path) -> dict:
    text = path.read_text()
    cfg = load_config(path)
    flows = cfg["process"].get("flows", {})
    tables, storage = [], {}
    all_acts = []
    for f in flows.values():
        for a in _acts_in(f, []):
            if a not in all_acts:
                all_acts.append(a)
    for t in cfg["recording"]["tables"]:
        kind = t.get("kind", "object")
        cols = []
        for c, spec in t["columns"].items():
            d = describe_source(spec)
            if d["kind"] == "time" and d["role"] == "row":
                d["activities"] = _aslist(t.get("activities", []))
            if d["kind"] == "time" and d["role"] == "derived" and "time" in spec:
                d["activities"] = _aslist(t.get("activities", []))
            for a in d["activities"]:
                storage.setdefault(a, []).append({"table": t["name"], "column": c, "role": d["role"]})
            cols.append({"name": c, **d})
        tables.append({"name": t["name"], "kind": kind, "object": t.get("object"),
                       "activities": _aslist(t.get("activities", [])) if kind == "event" else [],
                       "catalog": t.get("catalog"), "desc": t.get("desc", ""), "columns": cols})
    var_use = {}
    for fname, f in flows.items():
        for v in _vars_in(f, set()):
            var_use.setdefault(v, []).append(fname)
    var_use_rec = {}
    for t in cfg["recording"]["tables"]:
        for v in _vars_in(t, set()):
            var_use_rec.setdefault(v, []).append(t["name"])
    arr = cfg["process"].get("arrivals", {})
    for v in _vars_in(arr, set()):
        var_use.setdefault(v, []).append("arrivals")
    objects = {k: {"links": (v or {}).get("links", []), "attributes": list(((v or {}).get("attributes") or {})),
                   "id": (v or {}).get("id")} for k, v in cfg["objects"].items()}
    return {
        "config": path.name,
        "seed": cfg.get("seed", 0),
        "clock": cfg.get("clock", {}),
        "variables": cfg.get("variables", {}),
        "groups": variable_groups(text),
        "var_use": var_use,
        "var_use_recording": var_use_rec,
        "objects": objects,
        "entry": cfg["process"].get("entry"),
        "arrivals": arr,
        "flows": flows,
        "flow_order": list(flows),
        "tables": tables,
        "activities": all_acts,
        "storage": storage,
    }


# ----------------------------------------------------------------------------- save
def update_text(text: str, variables: dict, seed=None) -> str:
    lines = text.splitlines(keepends=True)
    start = next((i for i, l in enumerate(lines) if re.match(r"^variables:\s*(#.*)?$", l)), None)
    if start is None:
        raise ConfigError("no top-level 'variables:' block found")
    end = next((i for i in range(start + 1, len(lines))
                if re.match(r"^\S", lines[i]) and not lines[i].startswith("#")), len(lines))
    pending = dict(variables)
    for i in range(start + 1, end):
        m = re.match(r"^(\s{2})([A-Za-z_]\w*):(\s*)(.*?)(\s+#[^\]}]*)?(\r?\n)?$", lines[i])
        if m and m.group(2) in pending:
            val = yaml.safe_dump(pending.pop(m.group(2)), default_flow_style=True, sort_keys=False,
                                 width=10_000, allow_unicode=True).strip()
            if val.endswith("\n..."):
                val = val[:-4].strip()
            if val.endswith("..."):
                val = val[:-3].strip()
            lines[i] = f"{m.group(1)}{m.group(2)}: {val}{m.group(5) or ''}{m.group(6) or chr(10)}"
    if pending:
        ins = "".join(f"  {k}: " + yaml.safe_dump(v, default_flow_style=True, sort_keys=False, width=10_000)
                      .strip().removesuffix("...").strip() + "\n" for k, v in pending.items())
        lines.insert(end, ins)
    out = "".join(lines)
    if seed is not None:
        out, n = re.subn(r"(?m)^seed:\s*\S+", f"seed: {int(seed)}", out, count=1)
        if not n:
            out = f"seed: {int(seed)}\n" + out
    return out


# ----------------------------------------------------------------------------- sampling
def sample_preview(variables: dict, spec, n: int = 3000) -> dict:
    S = Sampler(random.Random(0), variables)
    resolved = S.resolve(spec)
    unit = resolved.get("unit", "min") if isinstance(resolved, dict) else "min"
    is_dur = isinstance(resolved, dict) and resolved.get("dist") not in (
        "poisson", "int_uniform", "geometric", "choice", "empirical", "bernoulli", None)
    xs = [S.sample(spec) for _ in range(n)]
    if all(isinstance(x, bool) for x in xs):
        return {"type": "bool", "p_true": sum(xs) / n}
    nums = [x for x in xs if isinstance(x, (int, float)) and not isinstance(x, bool)]
    if len(nums) < n:
        from collections import Counter
        c = Counter(str(x) for x in xs)
        return {"type": "categorical", "counts": c.most_common(12), "n": n}
    scale = UNIT_TO_MIN.get(unit, 1.0) if is_dur else 1.0
    vals = sorted(x / scale for x in nums)
    q = lambda p: vals[min(len(vals) - 1, int(p * len(vals)))]  # noqa: E731
    lo, hi = vals[0], q(0.99)
    integer = all(float(v).is_integer() for v in vals[:200])
    bins = min(30, int(hi - lo) + 1) if integer and hi - lo < 30 else 30
    width = (hi - lo) / bins or 1
    hist = [0] * bins
    for v in vals:
        if v <= hi:
            hist[min(bins - 1, int((v - lo) / width))] += 1
    return {"type": "numeric", "unit": unit if is_dur else "", "hist": hist, "lo": lo, "hi": hi,
            "mean": sum(vals) / len(vals), "p10": q(0.1), "p50": q(0.5), "p90": q(0.9)}


# ----------------------------------------------------------------------------- http
class Handler(BaseHTTPRequestHandler):
    configs_dir: Path
    out_dir: Path

    def log_message(self, fmt, *args):  # quiet
        pass

    def _send(self, code: int, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _cfg_path(self, name: str) -> Path:
        p = (self.configs_dir / Path(name).name)
        if p.suffix not in (".yaml", ".yml"):
            raise ConfigError("config must be a .yaml file")
        return p

    def do_GET(self):
        u = urlparse(self.path)
        try:
            if u.path in ("/", "/index.html"):
                return self._send(200, UI_FILE.read_bytes(), "text/html")
            if u.path == "/api/configs":
                return self._send(200, sorted(p.name for p in self.configs_dir.glob("*.y*ml")))
            if u.path == "/api/model":
                name = parse_qs(u.query).get("config", [""])[0]
                return self._send(200, build_model(self._cfg_path(name)))
            return self._send(404, {"error": "not found"})
        except Exception as e:  # noqa: BLE001
            return self._send(400, {"error": str(e), "trace": traceback.format_exc(limit=3)})

    def do_POST(self):
        u = urlparse(self.path)
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if u.path == "/api/sample":
                return self._send(200, sample_preview(body.get("variables", {}), body["spec"]))
            if u.path == "/api/save":
                src = self._cfg_path(body["config"])
                dst = self._cfg_path(body.get("save_as") or body["config"])
                new = update_text(src.read_text(), body.get("variables", {}), body.get("seed"))
                cfg = load_value(new)  # the file must still parse, and every variable must sample
                chk = Sampler(random.Random(0), cfg.get("variables", {}))
                for k, v in cfg.get("variables", {}).items():
                    try:
                        chk.sample(v)
                    except Exception as e:  # noqa: BLE001
                        raise ConfigError(f"variable '{k}': {e}") from None
                dst.write_text(new)
                return self._send(200, {"saved": dst.name})
            if u.path == "/api/run":
                path = self._cfg_path(body["config"])
                cfg = load_config(path)
                cfg.setdefault("variables", {}).update(body.get("variables", {}))
                if body.get("seed") is not None:
                    cfg["seed"] = int(body["seed"])
                out = self.out_dir / path.stem
                with LOCK:
                    summary = simulate(cfg, out)
                summary["out"] = str(out)
                return self._send(200, summary)
            if u.path == "/api/parse":
                return self._send(200, {"value": load_value(body["text"])})
            return self._send(404, {"error": "not found"})
        except ConfigError as e:
            return self._send(400, {"error": f"config error: {e}"})
        except Exception as e:  # noqa: BLE001
            return self._send(400, {"error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc(limit=4)})


def serve(configs: Path, out: Path, host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True):
    Handler.configs_dir = configs.resolve()
    Handler.out_dir = out.resolve()
    srv = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}/"
    print(f"HospitalFlow simulator UI: {url}   (configs: {Handler.configs_dir}, outputs: {Handler.out_dir})")
    if open_browser:
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:  # noqa: BLE001
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
