# Codex implementation request — real Step 1 EEG exports and evidence-based review

Repository: `jiwonpark7913/NL2EVENTLOG`
Goal: make the human review GUI at `tools/review_gui/app.py` fully usable for **MIMIC-IV Demo, AdventureWorks, BPI 2019 OCEL, and Order Management OCEL**; generate **actual EEGs from the implemented Step 1 pipeline** and allow evidence-based review. Never substitute authored Gold, synthetic placeholder, ERD, or DFG for an actual EEG. The dataset repository primarily contains builders, dictionaries and review artifacts; discover the genuine NL2EventLog runtime implementation if available in another checkout/linked repository. If absent, implement a clear export integration contract and report an explicit block instead of claiming a working EEG.

## Non-negotiable scope and constraints

1. **Inspect first.** Read `docs/system/EEG_ENTITY_MODEL.md`, current dataset builders, `tools/review_gui/app.py`, all four dataset READMEs, workflow outputs, and the actual Step 1 API/code if present. Give a concise inventory of the code that *actually* generates the EEG versus review-only source artifacts.
2. **Model input isolation.** Run Step 1 using exclusively each dataset's `input/database.sqlite` and `input/data_dictionary.json` (or the documented user input). No `review/`, `private/`, `evaluation/`, authored process questions or reference event logs in the model-facing context. Do not reveal any Gold labels as DD content.
3. **Actual EEG export, not reconstruction from Gold.** Capture the original Step 1 graph and all evidence/status metadata using a lossless or auditable adapter. Export an additive reviewer-only JSON at `datasets/<slug>/review/eeg/actual_eeg.json` and run manifest with source file SHA256, pipeline version/commit, config, model name/version if applicable, completed stages, and failure/unresolved statuses. Do NOT put it in `input/`.
4. **Use the exact conceptual contract.** Physical tables and DB relations, Entity Types and Entity identification rules (instance meaning/granularity), Event definitions (schema-level rules: carrier/non-carrier, activity value mapping, predicate, occurrence ID, timestamp expression and time role), event-to-entity attribution rules, supported directed key paths and validation statuses. Events are occurrences at extraction time, not EEGraph nodes. A case ET is not the same as a table. Documented descriptions are evidence, not Gold.
5. **No fabricated success.** When a pipeline cannot run (API error, missing credentials, missing data, missing implemented Step 1), show a clear blocked/incomplete status and still provide DB/DD inspection. No illustrative node may be labeled "actual". Preserve rejected/unresolved candidates for review.
6. **No automatic Gold approval.** Reviewer acceptance/rejection/comments must be separate `review/eeg/*.json` files and are not automatically injected into future Step 1 runs. Avoid leakage even when displaying prior reference logs.
7. **Clinical privacy and data isolation.** Use the public MIMIC Demo distribution only. Never send patient rows or free-text samples to external services without an explicit data-sharing policy. Reviewer GUI should bind only to localhost. Enforce read-only SQLite operations and safe identifier quoting.

## GUI UX

One integrated, searchable and filterable Streamlit dashboard:

**Dataset selector:** MIMIC-IV, AdventureWorks, BPI 2019, Order Management. Show state: input ready / DB missing / EEG generated / EEG blocked / reference draft / reference validated. The two OCEL databases are produced as Actions artifacts, not guaranteed checked into Git. Make downloading/extracting the expected artifacts straightforward, document the exact paths and checksums, and don't claim they exist when absent. Support `database.sqlite.gz` for MIMIC safely.

**A. Database evidence:** expandable table catalog with names, all columns, data_type/source_type and storage_type/sql_type fallback, definitions and sample_values, PK/FK and inferred relationships separately; live first N original SQLite rows (no writes). Display the ERD where available, but clearly label it **physical schema**, not EEG. Table filters, timestamp candidates, zero-row tables.

**B. Actual EEG interactive graph:** render a real graph from Step 1, not the physical ERD. Types visually distinct: Table, Entity Type, Event Definition, Entity Identification Rule, Event–Entity Attribution Rule, physical key/reference, and uncertainty. Group or filter by ET, activity, source table, status and time role. Clicking a node opens a **source-evidence inspector**: exact source table/column/key/row predicate, carrier vs non-carrier mapping, temporal role (actual vs planned vs recording vs validity), original column description, sample DB values, conditions, unique event occurrence ID mapping, candidate path direction, join uniqueness and validation status. Use a genuine graph library or Graphviz; for >150 nodes provide focus/neighbor/subgraph mode, zoom/pan and full-screen. Show unresolved alternatives and semantic conflicts; do not auto-elide failures.

**C. Human EEG semantic review:** per-node and per-edge decisions `pass | fail | uncertain`, edit reviewer notes, cite source table, key, row ID, counterexamples. Track suggested missing/mislabeled ET, missed event definitions, false-positive events, wrong timestamp role, invalid linking, duplication, identity collision. Export structured review patches with node IDs, graph SHA/hash, reviewer/date; never silently change the evidence graph in place.

**D. Natural-language requests and Gold:** separately curate *realistic process-analysis requests* (not a reviewer checklist) with target case notion, explicit/implicit mode and requested activities/process focus. Show case population, source rows, reference SQL, event occurrences, per-case traces and derived DFG only when independently created/verified. Ensure one source record may map to multiple cases without accidental deduplication; preserve zero-event cases. Compare model log with reference by event identity/attribution and micro P/R/F1 and exact match, with explicit unapproved status. Review SQL and logs are reviewer-only.

**E. Result exports:** `review/eeg/actual_eeg.json`, `review/eeg/run_manifest.json`, `review/eeg/reviewer_decisions.json`, optionally screenshots/SVG of actual EEG. No generated results are written under `input/`.

## Engineering work

- Find and adapt the true EEG runtime. If located elsewhere, implement an adapter invoked explicitly with its path/environment, not hard-coded Python imports that fail in this repository. If impossible to locate it, deliver the dashboard and a prominent blocker plus a defined JSON API that Codex can finish once the user supplies the runtime. Report this honestly.
- Refactor GUI data/model logic into pure tested functions separated from Streamlit rendering. Don't load multi-GB source files into RAM. Use read-only, paginated SQL previews; BPI 2019 may be large.
- Normalize DD *when reading* across legacy `tables{}` and `tables[]`, `definition`, `source_type`/`data_type`, `sql_type`/`storage_type`. Don't mutate all dictionaries as a side effect of GUI work.
- Type detection uses a robust SQL type parser: TIMESTAMP, TIMESTAMPTZ, DATETIME, DATETIME2, DATE, TIME; prevent the recent `test_temporal_candidates.py` failure and add tests for modifiers, brackets and NULL. `source_type` missing must be unknown/fallback, not an automatic rejection.
- Avoid hiding implementation/execution errors by writing plausible-looking placeholder JSON.
- Update reviewer README and dataset README links so GUI can be launched and inputs found.
- Tests: unit tests for graph adapter and consistency, integration tests with a small SQLite fixture and real fake *runtime export* fixture (clearly a test fixture), read-only guarantees, missing artifacts, OCEL many-to-many attribution, planned/recording time labeling, empty case population, no Gold leakage, reviewer patch persistence. Include `python -m py_compile`, `pytest`, and Streamlit smoke test in CI.
- Test each dataset for available inputs and record results as `RUNNABLE`, `BLOCKED_NO_DB`, `BLOCKED_NO_RUNTIME`, `BLOCKED_MODEL_ACCESS`, etc. Never claim all four EEGs were generated unless their manifest and corresponding complete runtime outputs exist.

## Acceptance criteria / final report

1. `streamlit run tools/review_gui/app.py` launches without syntax/import/runtime errors.
2. All four dataset selectors work, with explicit availability state and no silent fallbacks.
3. Physical ERD visually separate from actual EEG.
4. Loaded real EEG JSON draws full multi-type graph and offers evidence drill-down; graph adapter validates all edges and stable IDs.
5. Per-node/edge review decisions export without mutating DB/DD.
6. At least one end-to-end actual Step 1 run with provenance and independent check, **if and only if the runtime is accessible**. If not accessible, list the missing dependency and do not fabricate.
7. README gives exact local commands and expected file paths.
8. All tests pass; report outcomes and known failures, not assumptions.

Please implement changes in a PR rather than overwriting stable main, attach screenshots of the UI if possible, and explain which portions represent actual Step 1 output versus separate reviewer reference artifacts.
