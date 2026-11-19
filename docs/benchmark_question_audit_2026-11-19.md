# Question and Gold audit — HospitalFlow, PlateFlow, WarehouseFlow (2026-11-19)

Scope: the request sets, Gold SQL, Gold event logs, author metadata and data dictionaries of the three
datasets. UniversityFlow and the other databases were not touched. `input/database.sqlite` is unchanged
in every dataset.

## Method

1. **SQL ↔ CSV.** Every stored `private/gold_sql/<id>.sql` was executed on the SQLite file and compared
   with `private/gold_logs/<id>.csv` as a multiset of `(event_id, case_id, activity, timestamp)`.
2. **Independent re-derivation.** For each dataset an event catalogue (activity → table, row condition,
   timestamp column) was written by hand from the data dictionary, without reading `private/`.
   Event-to-case attribution was then derived mechanically from the foreign keys declared in SQLite
   (forward child → parent paths). For explicit requests the activity list was transcribed from the
   request text; for lifecycle requests every attributable activity was selected. The result was
   compared with the Gold CSV as a multiset of `(case, activity, timestamp)`, and the case population
   with `case_population`.
3. **Dictionary ↔ database.** Tables, columns, primary keys, foreign keys, code meanings, `sql_definition`
   and table checks in `input/data_dictionary.json` were compared with the SQLite catalogue and data.

## Result

| Check | HospitalFlow | PlateFlow | WarehouseFlow |
|---|---|---|---|
| Stored Gold SQL reproduces stored Gold CSV | 42 / 42 | 50 / 50 | 50 / 50 |
| Independent log equals Gold log (answerable requests) | 40 / 42 | 48 / 50 | 48 / 50 |
| Requests that differ | H11, H11P | NF02, NF02P | WF03, WF03P |

No Gold log extracts an event from a wrong table, wrong timestamp column or wrong code value, and no
case attribution uses a wrong key. H11 is repaired under "Errors found"; NF02 and WF03 are covered
under "Lifecycle Gold aligned with the paper's contract". The counts in this table are the state
before the audit.

### Errors found and repaired

| # | Dataset | Finding | Repair |
|---|---|---|---|
| 1 | HospitalFlow | H11/H11P asked for *Patient Profile Verified*, an activity of the removed `patient_profile` table. The Gold log contained *Care Unit Transferred* + *Hospital Admitted* instead, so request and Gold disagreed. | Request texts rewritten to ask for *Hospital Admitted* and *Care Unit Transferred*. Gold unchanged. |
| 2 | HospitalFlow | HF02/HF02P declared 19 requested/extractable activities; the Gold log has 20. | Counts set to 20. |
| 3 | HospitalFlow | `source/question_seeds.json` and `llm_paraphrases.json` still held the pre-migration H06, H09 and H11 seeds. | Aligned with the current requests. |
| 4 | WarehouseFlow | `input/data_dictionary.json` (model input): `sql_definition` of `goods_movement`, `warehouse_task_history`, `handling_history` showed `CHECK` clauses with the old codes (`IN`/`OUT`, `PUTAWAY`/`PICK`/`PACK`, `UNLOAD`/`LOAD`) while the database and the column definitions use `I`/`O`, `A`/`K`/`B`, `U`/`L`. | Replaced by the actual SQLite DDL; the copies in `evaluation/schema.sql` and the dictionary documents were replaced as well. |
| 5 | HospitalFlow | `input/data_dictionary.json` (model input): `admissions.table_checks` and `constraint_notes` described checks on `discharge_authorized_at`, a column that does not exist; one check (`edregtime<=admittime`) is not in the database either. A business rule described the removed patient-profile table. `transfers` listed its foreign keys at table level only. | Checks replaced by the three checks in the SQLite DDL, stale note and rule removed, column-level foreign keys added. |
| 6 | all three | The last business rule of each dictionary was duplicated. | Duplicate removed. |
| 7 | PlateFlow, WarehouseFlow | `es.event_bindings[].row_filter.value` in `private/gold.jsonl` used the legacy logical codes (`HT`, `PUTAWAY`, …) although `compiled_sql` and the Gold SQL use the physical codes. | 336 row filters rewritten to the physical code. |
| 8 | all three | `private/persistence_mapping.json` was stale: 15 (Warehouse), 8 (Plate) and 3 (Hospital) event queries returned no rows because of old codes, and 2 Hospital bindings referred to a removed table/column. | Codes repaired; the Hospital mapping was rebuilt from the current Gold activity sources. All bindings return rows again. |

### Request set after the audit

Each dataset now has 40 requests: Q1 10, Q2 10, Q3 10, Q4 10; all are answerable and have a Gold log.

| Dataset | Removed pairs | Reason |
|---|---|---|
| HospitalFlow | H08, H10 | H08 unanswerable; H10 single activity |
| PlateFlow | N15, N16, N09, N10, N13, N14, NF06 | N15/N16 unanswerable; N09/N10/NF06 single activity; N13/N14 have the same Gold log as NF10/NF11 |
| WarehouseFlow | W15, W16, W01, W02, W04, W05, WF07 | W15/W16 unanswerable; W01/W02 single activity; W04/W05 have the same Gold log as WF07/WF08; WF07 has two activities |

The pairs beyond the unanswerable and single-activity ones are defaults and can be changed in
`tools/experiments/apply_question_audit_2026_11.py` (`DROP`, or `--drop-file`).
H09 remains as a single-activity request because removing it would leave nine pairs; NF07 has two activities after the lifecycle alignment below.

## Lifecycle Gold aligned with the paper's contract

For an implicit request without a process focus, the paper defines the reference as every activity
with an executable event definition and a validated, unique forward attribution path to the case
notion, and treats an actual start and an actual completion of one work record as separate
occurrence times. Three authored conventions contradicted this and were changed
(`tools/experiments/apply_lifecycle_contract_2026_11.py`). Explicit requests (Q1/Q2) are unchanged.

| Change | Requests | Effect |
|---|---|---|
| Worker lifecycle now includes *Goods Received* through `goods_movement → goods_receipt.receiver_id → worker` | WF03, WF03P | 16 → 17 activities, 299 → 322 events |
| Rolling-plan lifecycle now includes all production work performed under the plan's instruction | NF02, NF02P | 4 → 26 activities, 106 → 824 events |
| PlateFlow `started_at` of furnace, rolling and finishing operations and of quality reviews now yields nine *… Started* activities | NF01, NF03, NF04, NF05, NF07–NF11 and paraphrases (also NF02) | +290 distinct events; e.g. NF01 620 → 910, NF07 43 → 89 |

New PlateFlow activities: Furnace Charging Started, Heating Started, Furnace Discharge Started,
Rough Rolling Started, Finish Rolling Started, Leveling Started, Heat Treatment Started,
Surface Finishing Started, Plate Quality Review Started. Their event ids are the completion id with
the suffix `:start`.

**Path length.** Gold attribution is not limited to three hops. The paper lists the bounded path length
as a coverage limitation of the method, so the reference keeps events that need four hops: the
finishing, inspection and review events of NF02 (`… → plate_material → as_rolled_material →
rolling_instruction → planned_rolling_instruction`) and medication administration per patient in
HospitalFlow H07 and HF01 (`emar → pharmacy → medication_order → admissions → patients`). With a strict
three-hop reference NF02 would lose its finishing, inspection and review events, and H07/HF01 would
lose 49 and 67 events.

After these changes the independently re-derived log equals the Gold log for all 120 requests
(forward-key closure; activity lists of explicit requests transcribed from the request text).

Dependent author metadata was regenerated: `private/persistence_mapping.json`, `private/case_paths.json`,
`private/task_scope_catalog.json`, `validation_report.json`, `docs/questions.md`,
`docs/object_activity_design.md`, `docs/timestamp_columns.*`, `evaluation/task_context.md` and the
review pages.

## Remaining observations

- **Model-input manifests.** `evaluation/model_input_manifest.json` of PlateFlow and WarehouseFlow lists
  `input/schema.sql`, `input/task_context.md` and `input/model_questions.jsonl`, which do not exist
  under `input/`. The README states that only the database and the dictionary are model-visible.
- **Simulation history.** `private/canonical_history.jsonl` and `private/object_event_links.json` still
  describe the events and links emitted by the legacy builders; they do not contain the PlateFlow start
  events or the new worker and rolling-plan links.

## Not repaired

- `build.py` / `validate.py` of WarehouseFlow and PlateFlow still generate the legacy codes; rebuilding
  the databases from them would undo the code migration.
- `docs/system/EVENT_TABLE_SCOPE.md` and `event_scope_audit.json` describe the pre-migration HospitalFlow
  (`patient_profile`, `discharge_authorized_at`, no `transfers`).
- `tools/build_gold_dfg_review.py` targets the old repository layout; use
  `tools/rebuild_question_gold_review.py` for these three datasets.

## Reproduce

```bash
python tools/experiments/apply_question_audit_2026_11.py     # from the pre-audit commit
python tools/experiments/apply_lifecycle_contract_2026_11.py
python tools/rebuild_all_dataset_reviews.py
python tools/rebuild_question_gold_review.py
```
