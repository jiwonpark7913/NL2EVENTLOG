"""simulate(cfg, out_dir) — the whole pipeline in one call."""
from __future__ import annotations

import json
import random
from pathlib import Path

import yaml

from .engine import ConfigError, Simulation
from .exporters import summarize, write_dictionary, write_gold
from .ids import assign_ids
from .recorder import Recorder

REQUIRED = ("objects", "process", "recording")


class _Loader(yaml.SafeLoader):
    """YAML 1.1 turns on/off/yes/no into booleans; here only true/false are booleans."""


_Loader.yaml_implicit_resolvers = {
    k: [(tag, rx) for tag, rx in v if tag != "tag:yaml.org,2002:bool"]
    for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
import re as _re  # noqa: E402

_Loader.add_implicit_resolver("tag:yaml.org,2002:bool", _re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
                              list("tTfF"))


def load_config(path) -> dict:
    return yaml.load(Path(path).read_text(), Loader=_Loader)


def load_value(text: str):
    return yaml.load(text, Loader=_Loader)


def simulate(cfg: dict, out: Path | None, seed: int | None = None) -> dict:
    for k in REQUIRED:
        if k not in cfg:
            raise ConfigError(f"config is missing the '{k}' section")
    sim = Simulation(cfg, seed=seed)
    sim.run_all()
    ids, lazy = assign_ids(sim, random.Random(sim.seed * 31 + 5))
    rec = Recorder(sim, ids, lazy, sim.seed)
    rec.build()
    if out is None:
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            _, fk = rec.write_sqlite(Path(d) / "db.sqlite")
        return summarize(rec, fk)
    out.mkdir(parents=True, exist_ok=True)
    schema, fk = rec.write_sqlite(out / "database.sqlite")
    (out / "schema.sql").write_text(schema)
    write_dictionary(rec, out / "data_dictionary.md")
    write_gold(rec, out / "gold")
    (out / "config.used.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    summary = summarize(rec, fk)
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary
