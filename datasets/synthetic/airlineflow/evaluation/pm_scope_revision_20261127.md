# PM-Scope1

Researcher-approved scope: Q02 Turnaround with coordination and readiness, Q04 all execution phases, Q05 cleaning/refuelling phases. Q03/Q07 milestone-only wording. No source DB or independent Test Gold changes.

Canonical source reconstruction:

```json
{
  "Q02": {
    "cases": 48,
    "activities": 14,
    "events": 672,
    "variants": 40,
    "tie_cases": 1,
    "duplicate_rows": 0,
    "source_reconstruction": "PASS"
  },
  "Q03": {
    "cases": 48,
    "activities": 5,
    "events": 240,
    "variants": 2,
    "tie_cases": 0,
    "duplicate_rows": 0,
    "source_reconstruction": "PASS"
  },
  "Q04": {
    "cases": 48,
    "activities": 20,
    "events": 960,
    "variants": 44,
    "tie_cases": 1,
    "duplicate_rows": 0,
    "source_reconstruction": "PASS"
  },
  "Q05": {
    "cases": 48,
    "activities": 6,
    "events": 288,
    "variants": 4,
    "tie_cases": 0,
    "duplicate_rows": 0,
    "source_reconstruction": "PASS"
  },
  "Q07": {
    "cases": 48,
    "activities": 5,
    "events": 240,
    "variants": 6,
    "tie_cases": 0,
    "duplicate_rows": 0,
    "source_reconstruction": "PASS"
  }
}
```

Q03/Q07 triples unchanged; Q04/Q05 retain all prior triples. Revised DFGs use shared styling, timestamp buckets and deterministic SVG layout; DOT included. Prior verification and compressed releases are historical. SQLite replay, production scorer integration and refreshed release archives pending. No model inference.
