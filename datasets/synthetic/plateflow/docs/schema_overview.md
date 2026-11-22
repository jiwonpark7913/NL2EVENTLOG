# PlateFlow New — schema overview

- [Editable draw.io diagram](schema.drawio) · [Data dictionary](data_dictionary.md)

| Table | Rows | Columns | Business role |
| --- | --- | --- | --- |
| slab_material | 30 | 6 | Slab identity, steel grade and actual receipt, verification and release times. |
| planned_rolling_instruction | 28 | 6 | One rolling plan per slab, its scheduled reheating time and actual submission, approval and release times. |
| rolling_instruction | 26 | 3 | An issued rolling instruction for an approved plan. |
| as_rolled_material | 26 | 6 | Allocated mother-material identity and genealogy for a rolling instruction; created_at and updated_at describe database maintenance, not production completion. |
| process_code | 8 | 3 | Business code meanings within each manufacturing process group. The same code text can have a different meaning in another group. |
| equipment | 7 | 5 | Equipment identifiers, names and system-maintenance times. Each equipment_code identifies a machine, not a manufacturing step. |
| furnace_operation_history | 70 | 7 | Actual furnace work occurrences for mother materials, retaining repeat work and unfinished intervals. |
| rolling_operation_history | 44 | 7 | Actual rolling phase occurrences for mother materials, retaining repeat work and unfinished intervals. |
| plate_material | 38 | 6 | Individual plate-piece identity and mother-material genealogy, with actual identification, release and packing times. |
| finishing_operation_history | 130 | 7 | Actual finishing work occurrences for individual plate pieces, including repeated heat treatment after rework. |
| dimension_inspection | 46 | 5 | One dimensional inspection record per inspection occurrence. Reinspection has a new inspection_id; PASS/FAIL describes its result. |
| plate_quality_review | 46 | 5 | One quality review record per review round. APPROVED/REWORK describes its outcome; PENDING means the review has not finished. |

| Parent | Child | FK columns | Referenced columns | Cardinality |
| --- | --- | --- | --- | --- |
| slab_material | planned_rolling_instruction | slab_id | slab_id | 1 : 0..1 |
| planned_rolling_instruction | rolling_instruction | plan_id | plan_id | 1 : 0..1 |
| rolling_instruction | as_rolled_material | instruction_id | instruction_id | 1 : 0..1 |
| slab_material | as_rolled_material | slab_id | slab_id | 1 : 0..1 |
| process_code | furnace_operation_history | process_group, operation_code | process_group, code | 1 : 0..N |
| equipment | furnace_operation_history | equipment_id | equipment_id | 1 : 0..N |
| as_rolled_material | furnace_operation_history | material_id | material_id | 1 : 0..N |
| process_code | rolling_operation_history | process_group, phase_code | process_group, code | 1 : 0..N |
| equipment | rolling_operation_history | equipment_id | equipment_id | 1 : 0..N |
| as_rolled_material | rolling_operation_history | material_id | material_id | 1 : 0..N |
| as_rolled_material | plate_material | mother_material_id | material_id | 1 : 0..N |
| process_code | finishing_operation_history | process_group, operation_code | process_group, code | 1 : 0..N |
| equipment | finishing_operation_history | equipment_id | equipment_id | 1 : 0..N |
| plate_material | finishing_operation_history | plate_id | plate_id | 1 : 0..N |
| plate_material | dimension_inspection | plate_id | plate_id | 1 : 0..N |
| plate_material | plate_quality_review | plate_id | plate_id | 1 : 0..N |
