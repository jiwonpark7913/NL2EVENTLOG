# Gold event logs

[All 72 requests and references](../docs/queries.md) · [Gold summary](../evaluation/gold_summary.csv)

Each Qxx directory contains the event log CSV, executable reference SQL, process interpretation (PI), extraction specification (ESpec), and directly-follows graph (DFG). The latter retains equal timestamp buckets. The canonical columns are case_id, activity, timestamp; event multiplicity matters. All files are evaluator-only, never model inputs.

## Enriched reference logs

Every Qxx also contains `events_enriched.csv`, a deterministic display/analysis extension of the canonical log. The first three columns remain `case_id, activity, timestamp`; extra fields depend on the case entity. `flight_no` and `operating_date` are separate columns; turnaround inbound/outbound flight context is separate from occurrence-specific flight context. Blank values mean not applicable, not an invented association. Only `events.csv` is used for Exact Match and F1. Both files are evaluator-only.

Compact ID revision: internal entity keys now use entity-specific management numbers (F001, J001, PL0001, etc.). Canonical and enriched logs retain the same event population; only identifier strings change. Data Dictionary in the review is the exact model-facing dictionary of the selected DB variant.
