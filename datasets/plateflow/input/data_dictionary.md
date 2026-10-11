# PlateFlow English Data Dictionary

- Schema-informed synthetic subset; custom metadata profile.

## slab_material

- Slab material and charge genealogy; no upstream operation timestamps in this subset

| Column | Type | Constraints | Definition |
|---|---|---|---|
| slab_id | TEXT | PRIMARY KEY | Synthetic slab identity |
| charge_id | TEXT | NOT NULL | Upstream charge identity, contextual attribute |

## planned_rolling_instruction

- Scheduled rolling instruction; plan times do not prove execution

| Column | Type | Constraints | Definition |
|---|---|---|---|
| plan_id | TEXT | PRIMARY KEY | Plan identity |
| slab_id | TEXT | NOT NULL REFERENCES slab_material(slab_id) | Planned input slab |
| planned_reheat_at | TEXT | NOT NULL | Scheduled furnace charging time |

## rolling_instruction

- Released rolling work instruction, separate from planning

| Column | Type | Constraints | Definition |
|---|---|---|---|
| instruction_id | TEXT | PRIMARY KEY | Synthetic row identity |
| plan_id | TEXT | NOT NULL UNIQUE REFERENCES planned_rolling_instruction(plan_id) | Synthetic explicit link to plan |
| released_at | TEXT | NOT NULL | Actual instruction release time |

## as_rolled_material

- As-rolled mother material with milestone columns and latest-operation snapshot

| Column | Type | Constraints | Definition |
|---|---|---|---|
| material_id | TEXT | PRIMARY KEY | Mother material identity |
| as_rolled_plate_no | TEXT | NOT NULL UNIQUE | Mother as-rolled plate number |
| slab_id | TEXT | NOT NULL UNIQUE REFERENCES slab_material(slab_id) | Source slab |
| instruction_id | TEXT | NOT NULL UNIQUE REFERENCES rolling_instruction(instruction_id) | Synthetic explicit link to released instruction |
| furnace_charged_at | TEXT |  | Actual furnace material charging |
| crop_shear_passed_at | TEXT |  | Actual crop-shear passage |
| latest_operation_completed_at | TEXT |  | Snapshot of latest mother-material operation, not always rolling completion |
| created_at | TEXT | NOT NULL | Technical database creation timestamp |
| updated_at | TEXT | NOT NULL | Technical database update timestamp |

## furnace_charge_tracking

- Furnace charge tracking record separated from material lifecycle snapshot

| Column | Type | Constraints | Definition |
|---|---|---|---|
| tracking_id | TEXT | PRIMARY KEY | Tracking occurrence ID |
| material_id | TEXT | NOT NULL UNIQUE REFERENCES as_rolled_material(material_id) | Tracked material |
| yard_instruction_received_at | TEXT | NOT NULL | Actual yard instruction receipt |
| lot_charging_started_at | TEXT | NOT NULL | Furnace lot charging start; different event granularity from material entry |

## cutting_finishing_instruction

- Cutting/finishing work instruction for mother material

| Column | Type | Constraints | Definition |
|---|---|---|---|
| instruction_id | TEXT | PRIMARY KEY | Synthetic instruction ID |
| material_id | TEXT | NOT NULL UNIQUE REFERENCES as_rolled_material(material_id) | Directed mother material |
| released_at | TEXT | NOT NULL | Actual cutting/finishing instruction release |
| cut_method | TEXT | NOT NULL CHECK(cut_method='SPLIT') | Synthetic split-cut method code |

## plate_material

- Individual cut Plate material, distinct from mother as-rolled material

| Column | Type | Constraints | Definition |
|---|---|---|---|
| plate_material_id | TEXT | PRIMARY KEY | Finished-piece material identity |
| plate_no | TEXT | NOT NULL UNIQUE | Individual Plate number |
| parent_as_rolled_plate_no | TEXT | NOT NULL REFERENCES as_rolled_material(as_rolled_plate_no) | Mother as-rolled plate number; synthetic FK policy |
| dimension_inspected_at | TEXT |  | Actual dimensional inspection timestamp |
| latest_operation_completed_at | TEXT |  | Latest piece operation snapshot |

## operation_code

- Synthetic operation process-code meanings; codes are newly authored

| Column | Type | Constraints | Definition |
|---|---|---|---|
| code | TEXT | PRIMARY KEY | Synthetic process code |
| meaning | TEXT | NOT NULL UNIQUE | English operation meaning |

## material_operation_history

- Immutable operation history for mother and piece material identities

| Column | Type | Constraints | Definition |
|---|---|---|---|
| transaction_id | TEXT | PRIMARY KEY | Operation occurrence ID |
| material_id | TEXT | NOT NULL | Mother or piece material identity; validated against both material tables |
| operation_code | TEXT | NOT NULL REFERENCES operation_code(code) | Synthetic factory/process code |
| started_at | TEXT | NOT NULL | Actual operation start time |
| completed_at | TEXT | NOT NULL CHECK(completed_at > started_at) | Actual operation completion time |
| created_at | TEXT | NOT NULL | Technical record insertion time |

## Synthetic process-code meanings

- RL: Rolling Completed
- CO: Cooling Completed
- LE: Leveling Completed
- SC: Split Cutting Completed
- HT: Heat Treatment Completed
- IF: Inspection Failed
- IP: Inspection Passed

## Business rules

- Plans, released instructions, tracking records, lifecycle snapshots, individual Plate records and operation history are separate.
- One slab supplies one mother material in this dataset. A completed mother material yields one to three individual Plate materials.
- Default mother-material lifecycle includes its own events and all recorded events of its descendant pieces; each occurrence is included once.
- Plan times, lot charging start and technical timestamps are not part of the selected default material lifecycle. Lot-level analysis is outside this dataset.
- Rolling completion is obtained from operation-history code RL, not from the latest-operation snapshot column.
- Operation history preserves repeated heat treatment and inspection. Dimensional inspection and general inspection decision are distinct activities.
- Completed route: rolling, cooling, leveling, crop-shear passage, cutting instruction, split cutting, piece-level treatment/inspection.
- Factory codes and relationship counts are synthetic assumptions. Original metadata does not declare data types, PK/FK or allowed code values.
- A mother-material identifier and a Plate-material identifier are distinct. The parent as-rolled plate number identifies the mother-to-piece relationship.
- No upstream casting or shipping timestamps are recorded.
