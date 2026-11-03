"""Command line entry point.

  python -m hospital_sim run configs/mimic_like.yaml --out out/run1
  python -m hospital_sim run configs/mimic_like.yaml --seed 7 --set n_patients=200
  python -m hospital_sim validate configs/mimic_like.yaml
  python -m hospital_sim ui            # web UI on http://127.0.0.1:8765
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .engine import ConfigError
from .run import load_config, load_value, simulate


def parse_set(items: list[str]) -> dict:
    out = {}
    for it in items or []:
        k, _, v = it.partition("=")
        out[k] = load_value(v)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="hospital_sim")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("run", "validate"):  # noqa: B007
        p = sub.add_parser(name)
        p.add_argument("config")
        p.add_argument("--seed", type=int)
        p.add_argument("--set", action="append", help="override a variable, e.g. n_patients=50")
        if name == "run":
            p.add_argument("--out", default="out")
    u = sub.add_parser("ui")
    u.add_argument("--configs", default="configs")
    u.add_argument("--out", default="out")
    u.add_argument("--host", default="127.0.0.1")
    u.add_argument("--port", type=int, default=8765)
    u.add_argument("--no-browser", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "ui":
        from .server import serve
        serve(Path(a.configs), Path(a.out), a.host, a.port, not a.no_browser)
        return 0
    cfg = load_config(a.config)
    cfg.setdefault("variables", {}).update(parse_set(a.set))
    try:
        if a.cmd == "validate":
            # a full dry run (no files) exercises every flow and column spec
            summary = simulate(cfg, None, seed=a.seed)
            print("config OK:", json.dumps(summary["tables"]))
        else:
            summary = simulate(cfg, Path(a.out), seed=a.seed)
            print(json.dumps(summary, indent=2))
    except ConfigError as e:
        print("config error:", e, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
