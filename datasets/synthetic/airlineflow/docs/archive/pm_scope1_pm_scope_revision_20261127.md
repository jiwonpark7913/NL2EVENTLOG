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

Q03/Q07 triples unchanged; Q04/Q05 retain all prior triples. Revised DFGs use shared styling, timestamp buckets and deterministic SVG layout; DOT included. Prior verification and compressed releases are historical. Production scorer integration and refreshed release archives pending. No model inference.

Update 2026-11-27: SQLite replay completed at `5cd9d57`. Each `gold.sql` was executed read-only on its manifest databases; all 108 conditions, including the 20 revised Pilot conditions (Q02, Q03, Q04, Q05, Q07 at L05–L20), equal `events.csv` as exact multisets. `verify.py` passes.
