# PlateFlow · Korean manufacturer — Schema overview

![Entity relationship diagram](schema.png)

- [Editable draw.io diagram](schema.drawio) · [Column dictionary](data_dictionary.md) · [CSV dictionary](data_dictionary.csv)

| Table | Rows | Columns | Event encoding | Primary key | Role |
|---|---:|---:|---|---|---|
| slab_material | 36 | 2 | No event encoding | slab_id | Slab material and charge genealogy; no upstream operation timestamps in this subset |
| planned_rolling_instruction | 36 | 3 | No event encoding | plan_id | Scheduled rolling instruction; plan times do not prove execution |
| rolling_instruction | 36 | 3 | Column encoding | instruction_id | Released rolling work instruction, separate from planning |
| as_rolled_material | 36 | 9 | Column encoding | material_id | As-rolled mother material with milestone columns and latest-operation snapshot |
| furnace_charge_tracking | 30 | 4 | Column encoding | tracking_id | Furnace charge tracking record separated from material lifecycle snapshot |
| cutting_finishing_instruction | 18 | 4 | Column encoding | instruction_id | Cutting/finishing work instruction for mother material |
| plate_material | 39 | 5 | Column encoding | plate_material_id | Individual cut Plate material, distinct from mother as-rolled material |
| operation_code | 7 | 2 | No event encoding | code | Synthetic operation process-code meanings; codes are newly authored |
| material_operation_history | 153 | 6 | Row encoding | transaction_id | Immutable operation history for mother and piece material identities |
| slab_material_activity | 138 | 5 | Row encoding | event_id | Authored actual-action history for slab_material |
| planned_rolling_instruction_activity | 138 | 5 | Row encoding | event_id | Authored actual-action history for planned_rolling_instruction |
| rolling_instruction_activity | 114 | 5 | Row encoding | event_id | Authored actual-action history for rolling_instruction |
| furnace_charge_tracking_activity | 103 | 5 | Row encoding | event_id | Authored actual-action history for furnace_charge_tracking |
| cutting_finishing_instruction_activity | 69 | 5 | Row encoding | event_id | Authored actual-action history for cutting_finishing_instruction |
| plate_material_activity | 150 | 5 | Row encoding | event_id | Authored actual-action history for plate_material |
| lifecycle_case_link | 1998 | 3 | No event encoding | event_id, case_table, case_id | Explicit case attribution across typed action histories; auxiliary extraction index, not a business case |

- Row encoding: each occurrence is a separate row; its activity comes from a code, label or the table meaning.
- Column encoding: an object row stores actual milestone times in dedicated columns. It can contain one or several milestones.
- No event encoding: the table supplies context, plans, identities or links rather than direct events.
- Planned dates, snapshots and technical timestamps do not automatically become events.


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
| slab_material | slab_material_activity | slab_id | slab_id | 1 : 0..N | declared |
| planned_rolling_instruction | planned_rolling_instruction_activity | plan_id | plan_id | 1 : 0..N | declared |
| rolling_instruction | rolling_instruction_activity | instruction_id | instruction_id | 1 : 0..N | declared |
| furnace_charge_tracking | furnace_charge_tracking_activity | tracking_id | tracking_id | 1 : 0..N | declared |
| cutting_finishing_instruction | cutting_finishing_instruction_activity | instruction_id | instruction_id | 1 : 0..N | declared |
| plate_material | plate_material_activity | plate_material_id | plate_material_id | 1 : 0..N | declared |
| as_rolled_material | material_operation_history | material_id | material_id | logical 1 : 0..N | logical |
| plate_material | material_operation_history | material_id | plate_material_id | logical 1 : 0..N | logical |
