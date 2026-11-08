# Activity semantics benchmark (four relational datasets)

This benchmark tests whether a model separates **physical code values** from **semantic activity names**, and whether it preserves uncertainty when the available evidence is contradictory or insufficient.

## Baseline DB migration
- All four SQLite databases were updated: code-bearing event rows, code lookup tables, SQL CHECK/default constraints where applicable, and input Data Dictionaries.
- Existing `event_id`, `case_id`, activity labels and timestamps remain unchanged. Gold `compiled_sql`, per-question SQL files and selector predicates now use the new stored codes.
- The migration job re-executes the Gold SQL files and compares them to all existing Gold CSV rows. No new events are inferred from current-state columns.

## Dataset-specific examples
| Dataset | Physical code | Business meaning / control |
|---|---|---|
| WarehouseFlow | `request_action.action_code='A'` | Check receiving request |
| WarehouseFlow | `warehouse_task_history.task_code='A'` | Putaway work |
| PlateFlow | `furnace_operation_history.operation_code='A'` | Furnace heating |
| PlateFlow | `finishing_operation_history.operation_code='A'` | Heat treatment |
| HospitalFlow | `order_history.action='E'` | Order Entered |
| UniversityFlow | `assignment_grading.grading_kind='A'` | Assignment Graded (original) |
| UniversityFlow | `registration.status` | Current-state snapshot; no new transition event inferred |

## Counterfactual diagnostic inputs (NOT baseline)
- `datasets/warehouseflow/evaluation/activity_semantics/conflicting_dictionary.json`: intentionally makes a DD explanation contradict the `work_code` reference table. Expected result is `conflicting` without ungrounded resolution.
- `datasets/hospitalflow/evaluation/activity_semantics/insufficient_dictionary.json`: withholds the action-code explanation. Expected result is `unresolved` unless other reliable evidence is independently available.

These overlays do **not** alter the physical SQLite database or the Gold logs and are **not** normal model input. They are separate semantic-status diagnostics, not additional end-to-end F1 samples. See `docs/system/activity_semantics_evaluation_cases.json` for machine-readable expectations.

## Gold verification
```bash
python tools/validation/validate_activity_semantics_benchmark.py
```
The original event-log labels and events are preserved; only physical predicates change. This tests Gold consistency, not LLM semantics-resolution accuracy.
