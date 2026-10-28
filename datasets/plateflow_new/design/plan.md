# PlateFlow New construction plan

- Agreed scope: an additional independent plate-manufacturing dataset with 12 business tables, 3 row-encoded work histories, 6 column-encoded business tables and 3 contextual/reference tables.
- Classification is based on the presence of an activity-kind carrier, not timestamp count or whether repeat work occupies separate records. Equipment, steel-grade and outcome codes do not become activity carriers.
- Discover timestamp-bearing candidates first; distinguish actual occurrence/interval times, planned reheating and technical maintenance. Model input has ordinary business definitions without event-table, encoding, carrier or extraction-selection labels.
- Gold logs use actual point milestones and completed work only. Start times remain in the DB, but do not emit additional start labels.
- Keep distinct occurrence IDs for repeated heat treatment, reinspections and quality-review rounds. Retain unfinished cases without fabricating completion events.
- Separate process groups give HT different meanings: furnace heating and piece-level heat treatment. Composite code FKs preserve the business domain.
- Simulate genealogy, PK/FKs and actual equipment links. Do not materialize a generic event index or precomputed case-event link table in the input DB.
- Freeze Q1 and Q3 seeds first, then create Q2/Q4 with the assistant LLM. Save prompts and frozen outputs; rebuild without an API call.
- Keep table classification/carrier answers in README only. Private Gold ES bindings remain evaluation material. Dictionary JSON/Markdown/CSV contains ordinary schema metadata and business definitions only.
- Validate executable SQL/CSV against independent simulation history, source keys, completion-time choice, codes versus outcome/machine distractors, genealogy, empty cases, exact pairs and dictionary leakage.
- Definitions use the project's three-part profile informed by public ISO/IEC 11179 scopes, without certification claims. Retain square-corner PNG/draw.io diagrams with large fonts and a separate PK/FK column.
