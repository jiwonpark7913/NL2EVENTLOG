# PlateFlow activity storage in existing business tables

- Nine original table roles are retained. Generic activity tables and the persisted case-link index are removed.
- Actual one-time milestones use nullable timestamp columns on their existing business objects.
- Repeatable heating completions and surface checks use HF/SF rows in material_operation_history, with meanings in operation_code.
- Technical timestamps, planned times and latest-operation snapshots remain excluded as separate events.
- Milestone additions and code meanings are authored assumptions, not claimed original source fields.
- Existing FK and material-genealogy paths derive event-to-case links directly in SQL.

| Object | Activities | Storage |
|---|---|---|
| slab_material | Slab Received; Slab Identity Verified; Slab Quality Checked; Slab Released for Rolling | Existing slab_material milestone columns; repeatable checks/heating use material_operation_history where applicable |
| planned_rolling_instruction | Rolling Plan Created; Rolling Plan Reviewed; Rolling Plan Approved; Rolling Plan Released | Existing planned_rolling_instruction milestone columns; repeatable checks/heating use material_operation_history where applicable |
| rolling_instruction | Rolling Instruction Acknowledged; Rolling Setup Verified; Rolling Work Started; Rolling Instruction Closed | Existing rolling_instruction milestone columns; repeatable checks/heating use material_operation_history where applicable |
| furnace_charge_tracking | Furnace Charge Assigned; Furnace Charge Confirmed; Heating Completed; Furnace Discharge Confirmed | Existing furnace_charge_tracking milestone columns; repeatable checks/heating use material_operation_history where applicable |
| cutting_finishing_instruction | Cutting Instruction Acknowledged; Cutting Setup Verified; Cutting Work Started; Cutting Instruction Closed | Existing cutting_finishing_instruction milestone columns; repeatable checks/heating use material_operation_history where applicable |
| plate_material | Plate Piece Identified; Plate Surface Checked; Plate Quality Released; Plate Packed; Plate Quality Review Started; Plate Packing Started | Existing plate_material milestone columns; repeatable checks/heating use material_operation_history where applicable |
