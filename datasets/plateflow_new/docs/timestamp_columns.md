# Timestamp inventory

- This is author evaluation material; it is excluded from the model-input manifest.

| Table | Column | Role | Selected as Gold time | Non-null rows |
| --- | --- | --- | --- | --- |
| slab_material | received_at | Completed work or actual milestone | True | 30 |
| slab_material | verified_at | Completed work or actual milestone | True | 28 |
| slab_material | released_at | Completed work or actual milestone | True | 28 |
| planned_rolling_instruction | planned_reheat_at | Scheduled instant | False | 28 |
| planned_rolling_instruction | submitted_at | Completed work or actual milestone | True | 28 |
| planned_rolling_instruction | approved_at | Completed work or actual milestone | True | 26 |
| planned_rolling_instruction | released_at | Completed work or actual milestone | True | 26 |
| rolling_instruction | issued_at | Completed work or actual milestone | True | 26 |
| as_rolled_material | created_at | Technical maintenance instant | False | 26 |
| as_rolled_material | updated_at | Technical maintenance instant | False | 26 |
| equipment | created_at | Technical maintenance instant | False | 7 |
| equipment | updated_at | Technical maintenance instant | False | 7 |
| furnace_operation_history | started_at | Actual interval start; not separately emitted | False | 70 |
| furnace_operation_history | finished_at | Completed work or actual milestone | True | 68 |
| rolling_operation_history | started_at | Actual interval start; not separately emitted | False | 44 |
| rolling_operation_history | finished_at | Completed work or actual milestone | True | 42 |
| plate_material | identified_at | Completed work or actual milestone | True | 38 |
| plate_material | released_at | Completed work or actual milestone | True | 35 |
| plate_material | packed_at | Completed work or actual milestone | True | 26 |
| finishing_operation_history | started_at | Actual interval start; not separately emitted | False | 130 |
| finishing_operation_history | finished_at | Completed work or actual milestone | True | 130 |
| dimension_inspection | inspected_at | Completed work or actual milestone | True | 46 |
| plate_quality_review | started_at | Actual interval start; not separately emitted | False | 46 |
| plate_quality_review | finished_at | Completed work or actual milestone | True | 43 |
