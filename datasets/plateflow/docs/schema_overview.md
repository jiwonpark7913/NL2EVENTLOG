# PlateFlow · Korean manufacturer — Schema overview

![Entity relationship diagram](schema.png)

- [Editable draw.io diagram](schema.drawio) · [SVG](schema.svg) · [Column dictionary](data_dictionary.md) · [CSV dictionary](data_dictionary.csv)

| Table | Rows | Columns | Primary key | Role |
|---|---:|---:|---|---|
| slab_material | 36 | 2 | slab_id | Slab material and charge genealogy; no upstream operation timestamps in this subset |
| planned_rolling_instruction | 36 | 3 | plan_id | Scheduled rolling instruction; plan times do not prove execution |
| rolling_instruction | 36 | 3 | instruction_id | Released rolling work instruction, separate from planning |
| as_rolled_material | 36 | 9 | material_id | As-rolled mother material with milestone columns and latest-operation snapshot |
| furnace_charge_tracking | 30 | 4 | tracking_id | Furnace charge tracking record separated from material lifecycle snapshot |
| cutting_finishing_instruction | 18 | 4 | instruction_id | Cutting/finishing work instruction for mother material |
| plate_material | 39 | 5 | plate_material_id | Individual cut Plate material, distinct from mother as-rolled material |
| operation_code | 7 | 2 | code | Synthetic operation process-code meanings; codes are newly authored |
| material_operation_history | 153 | 6 | transaction_id | Immutable operation history for mother and piece material identities |


## Relationships

| Parent | Child | Child FK | Parent key | Parent-to-child count | Kind |
|---|---|---|---|---|---|
| slab_material | planned_rolling_instruction | slab_id | slab_id | 1 : 0..N | declared |
| planned_rolling_instruction | rolling_instruction | plan_id | plan_id | 1 : 0..1 | declared |
| rolling_instruction | as_rolled_material | instruction_id | instruction_id | 1 : 0..1 | declared |
| slab_material | as_rolled_material | slab_id | slab_id | 1 : 0..1 | declared |
| as_rolled_material | furnace_charge_tracking | material_id | material_id | 1 : 0..1 | declared |
| as_rolled_material | cutting_finishing_instruction | material_id | material_id | 1 : 0..1 | declared |
| as_rolled_material | plate_material | parent_as_rolled_plate_no | as_rolled_plate_no | 1 : 0..N | declared |
| operation_code | material_operation_history | operation_code | code | 1 : 0..N | declared |
| as_rolled_material | material_operation_history | material_id | material_id | logical 1 : 0..N | logical |
| plate_material | material_operation_history | material_id | plate_material_id | logical 1 : 0..N | logical |
