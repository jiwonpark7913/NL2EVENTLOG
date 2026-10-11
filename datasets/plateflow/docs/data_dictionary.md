# PlateFlow · Korean manufacturer — table and column dictionary

- Generated from the executable SQLite schema and English metadata.

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
| slab_material_activity | 138 | 5 | event_id | Authored actual-action history for slab_material |
| planned_rolling_instruction_activity | 138 | 5 | event_id | Authored actual-action history for planned_rolling_instruction |
| rolling_instruction_activity | 114 | 5 | event_id | Authored actual-action history for rolling_instruction |
| furnace_charge_tracking_activity | 103 | 5 | event_id | Authored actual-action history for furnace_charge_tracking |
| cutting_finishing_instruction_activity | 69 | 5 | event_id | Authored actual-action history for cutting_finishing_instruction |
| plate_material_activity | 150 | 5 | event_id | Authored actual-action history for plate_material |
| lifecycle_case_link | 1998 | 3 | event_id, case_table, case_id | Explicit case attribution across typed action histories; auxiliary extraction index, not a business case |

## Columns

### slab_material

- Slab material and charge genealogy; no upstream operation timestamps in this subset

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| slab_id | TEXT | yes | PK | Synthetic slab identity |
| charge_id | TEXT | yes |  | Upstream charge identity, contextual attribute |

### planned_rolling_instruction

- Scheduled rolling instruction; plan times do not prove execution

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| plan_id | TEXT | yes | PK | Plan identity |
| slab_id | TEXT | yes | FK → slab_material.slab_id | Planned input slab |
| planned_reheat_at | TEXT | yes |  | Scheduled furnace charging time |

### rolling_instruction

- Released rolling work instruction, separate from planning

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| instruction_id | TEXT | yes | PK | Synthetic row identity |
| plan_id | TEXT | yes | FK → planned_rolling_instruction.plan_id | Synthetic explicit link to plan |
| released_at | TEXT | yes |  | Actual instruction release time |

### as_rolled_material

- As-rolled mother material with milestone columns and latest-operation snapshot

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| material_id | TEXT | yes | PK | Mother material identity |
| as_rolled_plate_no | TEXT | yes |  | Mother as-rolled plate number |
| slab_id | TEXT | yes | FK → slab_material.slab_id | Source slab |
| instruction_id | TEXT | yes | FK → rolling_instruction.instruction_id | Synthetic explicit link to released instruction |
| furnace_charged_at | TEXT | no |  | Actual furnace material charging |
| crop_shear_passed_at | TEXT | no |  | Actual crop-shear passage |
| latest_operation_completed_at | TEXT | no |  | Snapshot of latest mother-material operation, not always rolling completion |
| created_at | TEXT | yes |  | Technical database creation timestamp |
| updated_at | TEXT | yes |  | Technical database update timestamp |

### furnace_charge_tracking

- Furnace charge tracking record separated from material lifecycle snapshot

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| tracking_id | TEXT | yes | PK | Tracking occurrence ID |
| material_id | TEXT | yes | FK → as_rolled_material.material_id | Tracked material |
| yard_instruction_received_at | TEXT | yes |  | Actual yard instruction receipt |
| lot_charging_started_at | TEXT | yes |  | Furnace lot charging start; different event granularity from material entry |

### cutting_finishing_instruction

- Cutting/finishing work instruction for mother material

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| instruction_id | TEXT | yes | PK | Synthetic instruction ID |
| material_id | TEXT | yes | FK → as_rolled_material.material_id | Directed mother material |
| released_at | TEXT | yes |  | Actual cutting/finishing instruction release |
| cut_method | TEXT | yes |  | Synthetic split-cut method code |

### plate_material

- Individual cut Plate material, distinct from mother as-rolled material

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| plate_material_id | TEXT | yes | PK | Finished-piece material identity |
| plate_no | TEXT | yes |  | Individual Plate number |
| parent_as_rolled_plate_no | TEXT | yes | FK → as_rolled_material.as_rolled_plate_no | Mother as-rolled plate number; synthetic FK policy |
| dimension_inspected_at | TEXT | no |  | Actual dimensional inspection timestamp |
| latest_operation_completed_at | TEXT | no |  | Latest piece operation snapshot |

### operation_code

- Synthetic operation process-code meanings; codes are newly authored

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| code | TEXT | yes | PK | Synthetic process code |
| meaning | TEXT | yes |  | English operation meaning |

### material_operation_history

- Immutable operation history for mother and piece material identities

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| transaction_id | TEXT | yes | PK | Operation occurrence ID |
| material_id | TEXT | yes |  | Mother or piece material identity; validated against both material tables |
| operation_code | TEXT | yes | FK → operation_code.code | Synthetic factory/process code |
| started_at | TEXT | yes |  | Actual operation start time |
| completed_at | TEXT | yes |  | Actual operation completion time |
| created_at | TEXT | yes |  | Technical record insertion time |

### slab_material_activity

- Authored actual-action history for slab_material

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| event_id | TEXT | yes | PK | Stable identity of this actual business action; authored extension |
| slab_id | TEXT | yes | FK → slab_material.slab_id | Explicit parent object key; FK to slab_material.slab_id |
| activity | TEXT | yes |  | Controlled business activity label; not a technical database update |
| occurred_at | TEXT | yes |  | Actual occurrence time in UTC, distinct from planned dates |
| outcome | TEXT | yes |  | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED |

### planned_rolling_instruction_activity

- Authored actual-action history for planned_rolling_instruction

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| event_id | TEXT | yes | PK | Stable identity of this actual business action; authored extension |
| plan_id | TEXT | yes | FK → planned_rolling_instruction.plan_id | Explicit parent object key; FK to planned_rolling_instruction.plan_id |
| activity | TEXT | yes |  | Controlled business activity label; not a technical database update |
| occurred_at | TEXT | yes |  | Actual occurrence time in UTC, distinct from planned dates |
| outcome | TEXT | yes |  | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED |

### rolling_instruction_activity

- Authored actual-action history for rolling_instruction

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| event_id | TEXT | yes | PK | Stable identity of this actual business action; authored extension |
| instruction_id | TEXT | yes | FK → rolling_instruction.instruction_id | Explicit parent object key; FK to rolling_instruction.instruction_id |
| activity | TEXT | yes |  | Controlled business activity label; not a technical database update |
| occurred_at | TEXT | yes |  | Actual occurrence time in UTC, distinct from planned dates |
| outcome | TEXT | yes |  | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED |

### furnace_charge_tracking_activity

- Authored actual-action history for furnace_charge_tracking

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| event_id | TEXT | yes | PK | Stable identity of this actual business action; authored extension |
| tracking_id | TEXT | yes | FK → furnace_charge_tracking.tracking_id | Explicit parent object key; FK to furnace_charge_tracking.tracking_id |
| activity | TEXT | yes |  | Controlled business activity label; not a technical database update |
| occurred_at | TEXT | yes |  | Actual occurrence time in UTC, distinct from planned dates |
| outcome | TEXT | yes |  | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED |

### cutting_finishing_instruction_activity

- Authored actual-action history for cutting_finishing_instruction

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| event_id | TEXT | yes | PK | Stable identity of this actual business action; authored extension |
| instruction_id | TEXT | yes | FK → cutting_finishing_instruction.instruction_id | Explicit parent object key; FK to cutting_finishing_instruction.instruction_id |
| activity | TEXT | yes |  | Controlled business activity label; not a technical database update |
| occurred_at | TEXT | yes |  | Actual occurrence time in UTC, distinct from planned dates |
| outcome | TEXT | yes |  | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED |

### plate_material_activity

- Authored actual-action history for plate_material

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| event_id | TEXT | yes | PK | Stable identity of this actual business action; authored extension |
| plate_material_id | TEXT | yes | FK → plate_material.plate_material_id | Explicit parent object key; FK to plate_material.plate_material_id |
| activity | TEXT | yes |  | Controlled business activity label; not a technical database update |
| occurred_at | TEXT | yes |  | Actual occurrence time in UTC, distinct from planned dates |
| outcome | TEXT | yes |  | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED |

### lifecycle_case_link

- Explicit case attribution across typed action histories; auxiliary extraction index, not a business case

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| event_id | TEXT | yes | PK | Validated identity in a typed activity table; polymorphic reference |
| case_table | TEXT | yes | PK | Controlled existing business table name |
| case_id | TEXT | yes | PK | Serialized primary key of the declared case table; composite parts separated by colon |

## Logical history identity reference

- material_operation_history.material_id refers to either as_rolled_material.material_id or plate_material.plate_material_id.
- This is not a single-table SQLite FK.
- The builder validates the two disjoint identity sets with an insert trigger and an orphan check.
- Dashed diagram edges show this logical reference.

## Value domains and business rules

- RL: Rolling Completed
- CO: Cooling Completed
- LE: Leveling Completed
- SC: Split Cutting Completed
- HT: Heat Treatment Completed
- IF: Inspection Failed
- IP: Inspection Passed

- Original source layer: Plans, released instructions, tracking records, lifecycle snapshots, individual Plate records and operation history are separate.
- Original source layer: One slab supplies one mother material in this dataset. A completed mother material yields one to three individual Plate materials.
- Original source layer: Default mother-material lifecycle includes its own events and all recorded events of its descendant pieces; each occurrence is included once.
- Original source layer: Plan times, lot charging start and technical timestamps are not part of the selected default material lifecycle. Lot-level analysis is outside this dataset.
- Original source layer: Rolling completion is obtained from operation-history code RL, not from the latest-operation snapshot column.
- Original source layer: Operation history preserves repeated heat treatment and inspection. Dimensional inspection and general inspection decision are distinct activities.
- Original source layer: Completed route: rolling, cooling, leveling, crop-shear passage, cutting instruction, split cutting, piece-level treatment/inspection.
- Original source layer: Factory codes and relationship counts are synthetic assumptions. Original metadata does not declare data types, PK/FK or allowed code values.
- Original source layer: A mother-material identifier and a Plate-material identifier are distinct. The parent as-rolled plate number identifies the mother-to-piece relationship.
- Original source layer: No upstream casting or shipping timestamps are recorded.
- Original source rows are preserved. Added typed activity histories are authored synthetic domain extensions, not claimed source fields.
- Only actual occurred_at times generate lifecycle events. Planned dates and technical timestamps remain excluded.
- Lifecycle case links use exact typed object identity. Related cases may share an event; uniqueness is (case_id,event_id).
- Incomplete cases and conditional revision branches are intentional; no final action is inferred for an open case.

# Plateflow object activities and scenarios

- Original source requirements, columns and keys remain preserved.
- Every action below is an explicitly authored domain extension; these stages were not present in the source schemas.
- Each added history row records an actual activity, occurrence time, outcome and a declared FK to its object.
- Conditional revision branches and incomplete cases are intentional. Atomic grading/operation records remain auxiliary logs.
- Master-object views aggregate linked work; they do not assert one chronological causal process across unrelated jobs.

| Object | Added activities | Situation | Storage |
|---|---|---|---|
| slab_material | Slab Received → Slab Identity Verified → Slab Quality Checked → Slab Released for Rolling | Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects. | slab_material_activity |
| planned_rolling_instruction | Rolling Plan Created → Rolling Plan Reviewed → Rolling Plan Approved → Rolling Plan Released | Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects. | planned_rolling_instruction_activity |
| rolling_instruction | Rolling Instruction Acknowledged → Rolling Setup Verified → Rolling Work Started → Rolling Instruction Closed | Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects. | rolling_instruction_activity |
| furnace_charge_tracking | Furnace Charge Assigned → Furnace Charge Confirmed → Heating Completed → Furnace Discharge Confirmed | Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects. | furnace_charge_tracking_activity |
| cutting_finishing_instruction | Cutting Instruction Acknowledged → Cutting Setup Verified → Cutting Work Started → Cutting Instruction Closed | Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects. | cutting_finishing_instruction_activity |
| plate_material | Plate Piece Identified → Plate Surface Checked → Plate Quality Released → Plate Packed | Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects. | plate_material_activity |

- The full ES unions the original milestone sources and the new typed activity histories, then applies explicit event-to-case links.
- Related goods/workers, students/instructors and parent materials receive an event only through a documented business relationship.
- `lifecycle_case_link` is a generated extraction index with validated object identities; it is not an additional business object.
