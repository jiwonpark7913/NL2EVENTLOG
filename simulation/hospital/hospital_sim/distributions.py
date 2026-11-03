"""Random-variable specifications used everywhere in a simulation config.

A distribution spec is either a plain number (constant), a string reference to a
named variable ("$los"), or a mapping with a ``dist`` key. Durations are
returned in MINUTES unless ``unit`` says otherwise; counts are returned as int.

Supported specs (all accept ``unit: min|h|d`` and ``min``/``max`` clipping):

  {dist: const, value: 30}
  {dist: uniform, low: 10, high: 60}
  {dist: exponential, mean: 45}
  {dist: lognormal, median: 72, sigma: 0.6}
  {dist: normal, mean: 60, sd: 15}
  {dist: gamma, shape: 2.0, scale: 30}
  {dist: triangular, low: 5, mode: 20, high: 90}
  {dist: poisson, mean: 3}               -> int
  {dist: int_uniform, low: 1, high: 4}    -> int
  {dist: geometric, p: 0.4}               -> int >= 1
  {dist: choice, values: [a, b], weights: [3, 1]}
  {dist: empirical, values: [10, 20, 30], weights: [1, 2, 1]}
  {dist: bernoulli, p: 0.3}               -> bool
"""
from __future__ import annotations

import math
import random
from typing import Any

UNIT_TO_MIN = {"s": 1 / 60, "min": 1.0, "m": 1.0, "h": 60.0, "d": 1440.0}
INT_DISTS = {"poisson", "int_uniform", "geometric"}


class DistError(ValueError):
    pass


class Sampler:
    """Samples from distribution specs, resolving $variables."""

    def __init__(self, rng: random.Random, variables: dict[str, Any]):
        self.rng = rng
        self.variables = variables

    def resolve(self, spec: Any, _depth: int = 0) -> Any:
        if isinstance(spec, str) and spec.startswith("$"):
            name = spec[1:]
            if name not in self.variables:
                raise DistError(f"unknown variable '{spec}'")
            if _depth > 20:
                raise DistError(f"variable reference cycle at '{spec}'")
            return self.resolve(self.variables[name], _depth + 1)
        return spec

    def sample(self, spec: Any) -> Any:
        spec = self.resolve(spec)
        if spec is None:
            return None
        if isinstance(spec, bool):
            return spec
        if isinstance(spec, (int, float)):
            return spec
        if isinstance(spec, str):
            return spec  # literal value (e.g. a label)
        if isinstance(spec, list):
            return self.rng.choice(spec)
        if not isinstance(spec, dict) or "dist" not in spec:
            raise DistError(f"not a distribution spec: {spec!r}")
        d = spec["dist"]
        r = self.rng
        P = lambda k: self.resolve(spec[k])  # noqa: E731
        try:
            if d == "const":
                x = P("value")
            elif d == "uniform":
                x = r.uniform(P("low"), P("high"))
            elif d == "exponential":
                x = r.expovariate(1.0 / P("mean"))
            elif d == "lognormal":
                x = r.lognormvariate(math.log(P("median")), P("sigma"))
            elif d == "normal":
                x = r.gauss(P("mean"), P("sd"))
            elif d == "gamma":
                x = r.gammavariate(P("shape"), P("scale"))
            elif d == "triangular":
                x = r.triangular(P("low"), P("high"), P("mode"))
            elif d == "poisson":
                x = _poisson(r, P("mean"))
            elif d == "int_uniform":
                x = r.randint(int(P("low")), int(P("high")))
            elif d == "geometric":
                p = P("p")
                x = 1
                while r.random() > p:
                    x += 1
            elif d in ("choice", "empirical"):
                vals = spec["values"]
                w = spec.get("weights")
                x = r.choices(vals, weights=w, k=1)[0]
                if isinstance(x, dict) or (isinstance(x, str) and x.startswith("$")):
                    x = self.sample(x)
            elif d == "bernoulli":
                return r.random() < P("p")
            else:
                raise DistError(f"unknown dist '{d}'")
        except KeyError as e:
            raise DistError(f"dist '{d}' is missing parameter {e}") from None
        if isinstance(x, (int, float)) and not isinstance(x, bool):
            if "min" in spec:
                x = max(x, P("min"))
            if "max" in spec:
                x = min(x, P("max"))
            if d not in INT_DISTS and d not in ("choice", "empirical", "const"):
                x = x * UNIT_TO_MIN[spec.get("unit", "min")]
            elif d in ("const",) and "unit" in spec:
                x = x * UNIT_TO_MIN[spec["unit"]]
        return x

    def duration(self, spec: Any) -> float:
        """Sample a duration in minutes (never negative unless explicitly allowed)."""
        if spec is None:
            return 0.0
        x = self.sample(spec)
        if not isinstance(x, (int, float)):
            raise DistError(f"duration spec did not produce a number: {spec!r}")
        return float(x)

    def count(self, spec: Any) -> int:
        if spec is None:
            return 1
        x = self.sample(spec)
        return max(0, int(round(x)))

    def chance(self, p: Any) -> bool:
        return self.rng.random() < float(self.resolve(p))


def _poisson(r: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    if lam > 50:  # normal approximation for large means
        return max(0, int(round(r.gauss(lam, math.sqrt(lam)))))
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= r.random()
        if p <= L:
            return k
        k += 1
