# PlateFlow — data dictionary

## 1. Dictionary basic information

| Field | Value |
| --- | --- |
| dictionary_id | NL2EVENTLOG:plateflow |
| version | 2026-10-12 |
| name | PlateFlow |
| description | English synthetic relational database for query-conditioned process-view and event-log extraction. |
| language | en |
| timezone | UTC |
| dbms | SQLite |
| namespace | plateflow |
| maintainer | NL2EVENTLOG project maintainers |
| registration_status | Project-maintained draft; not ISO-registered or certified |
| source_policy | Source definitions are retained and authored lifecycle additions are identified in source/design documents. |
| standards_profile | Project profile informed by ISO/IEC 11179-3 and 11179-4 public abstracts; no full clause-by-clause conformance assessment. |
| layout | 1 Dictionary basic information; 2 Table definitions; 3 Column definitions |

- The three-part layout is a project documentation choice, not a mandated ISO/IEC template.
- ISO/IEC 11179-4 addresses semantic definitions rather than prescribing their formatting. Only public standard scope descriptions were consulted.
- SQL keys and constraints are taken from the executable DB. SQLite TEXT has no declared maximum length unless an explicit constraint says otherwise. Examples are observed synthetic values, not additional allowed-value constraints.
- [ISO/IEC 11179-3:2023](https://www.iso.org/standard/78915.html): Registry identification, administration and definition concepts.
- [ISO/IEC 11179-4:2004](https://www.iso.org/standard/35346.html): Semantic formulation of data definitions.

## 2. Table definitions

| Metadata ID | Logical name | Physical name | Rows | PK | FK | Event encoding | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow.slab_material | Slab Material | slab_material | 36 | slab_id | None declared | No event encoding | Slab material and charge genealogy; no upstream operation timestamps in this subset |
| plateflow.planned_rolling_instruction | Planned Rolling Instruction | planned_rolling_instruction | 36 | plan_id | slab_id → slab_material.slab_id | No event encoding | Scheduled rolling instruction; plan times do not prove execution |
| plateflow.rolling_instruction | Rolling Instruction | rolling_instruction | 36 | instruction_id | plan_id → planned_rolling_instruction.plan_id | Column encoding | Released rolling work instruction, separate from planning |
| plateflow.as_rolled_material | As Rolled Material | as_rolled_material | 36 | material_id | instruction_id → rolling_instruction.instruction_id; slab_id → slab_material.slab_id | Column encoding | As-rolled mother material with milestone columns and latest-operation snapshot |
| plateflow.furnace_charge_tracking | Furnace Charge Tracking | furnace_charge_tracking | 30 | tracking_id | material_id → as_rolled_material.material_id | Column encoding | Furnace charge tracking record separated from material lifecycle snapshot |
| plateflow.cutting_finishing_instruction | Cutting Finishing Instruction | cutting_finishing_instruction | 18 | instruction_id | material_id → as_rolled_material.material_id | Column encoding | Cutting/finishing work instruction for mother material |
| plateflow.plate_material | Plate Material | plate_material | 39 | plate_material_id | parent_as_rolled_plate_no → as_rolled_material.as_rolled_plate_no | Column encoding | Individual cut Plate material, distinct from mother as-rolled material |
| plateflow.operation_code | Operation Code | operation_code | 7 | code | None declared | No event encoding | Synthetic operation process-code meanings; codes are newly authored |
| plateflow.material_operation_history | Material Operation History | material_operation_history | 153 | transaction_id | operation_code → operation_code.code | Row encoding | Immutable operation history for mother and piece material identities |
| plateflow.slab_material_activity | Slab Material Activity | slab_material_activity | 138 | event_id | slab_id → slab_material.slab_id | Row encoding | Authored actual-action history for slab_material |
| plateflow.planned_rolling_instruction_activity | Planned Rolling Instruction Activity | planned_rolling_instruction_activity | 138 | event_id | plan_id → planned_rolling_instruction.plan_id | Row encoding | Authored actual-action history for planned_rolling_instruction |
| plateflow.rolling_instruction_activity | Rolling Instruction Activity | rolling_instruction_activity | 114 | event_id | instruction_id → rolling_instruction.instruction_id | Row encoding | Authored actual-action history for rolling_instruction |
| plateflow.furnace_charge_tracking_activity | Furnace Charge Tracking Activity | furnace_charge_tracking_activity | 103 | event_id | tracking_id → furnace_charge_tracking.tracking_id | Row encoding | Authored actual-action history for furnace_charge_tracking |
| plateflow.cutting_finishing_instruction_activity | Cutting Finishing Instruction Activity | cutting_finishing_instruction_activity | 69 | event_id | instruction_id → cutting_finishing_instruction.instruction_id | Row encoding | Authored actual-action history for cutting_finishing_instruction |
| plateflow.plate_material_activity | Plate Material Activity | plate_material_activity | 150 | event_id | plate_material_id → plate_material.plate_material_id | Row encoding | Authored actual-action history for plate_material |
| plateflow.lifecycle_case_link | Lifecycle Case Link | lifecycle_case_link | 1998 | event_id, case_table, case_id | None declared | No event encoding | Explicit case attribution across typed action histories; auxiliary extraction index, not a business case |

- Row encoding: an event occurrence is represented by a row.
- Column encoding: an object row stores one or more actual business milestone timestamps in dedicated columns.
- No event encoding: contextual, reference, planned or relationship/index data; this does not mean the related business object lacks an event log.
- **slab_material:** Master, plan, reference or relationship/index data; this table does not directly produce an event in the current ES. Related objects can still have logs from other tables.
- **planned_rolling_instruction:** Master, plan, reference or relationship/index data; this table does not directly produce an event in the current ES. Related objects can still have logs from other tables.
- **rolling_instruction:** Instruction object row stores its actual release milestone. Extracted event columns: released_at.
- **as_rolled_material:** One material object row contains two different extracted business milestones. Extracted event columns: furnace_charged_at, crop_shear_passed_at.
- **furnace_charge_tracking:** Only yard instruction receipt is currently extracted; lot_charging_started_at is outside the declared material-event scope. Extracted event columns: yard_instruction_received_at.
- **cutting_finishing_instruction:** Cutting instruction object row stores its actual release milestone. Extracted event columns: released_at.
- **plate_material:** One cut-piece object row stores its actual dimensional-inspection milestone. Extracted event columns: dimension_inspected_at.
- **operation_code:** Master, plan, reference or relationship/index data; this table does not directly produce an event in the current ES. Related objects can still have logs from other tables.
- **material_operation_history:** operation_code selects the action; one completed operation per history row. started_at is not currently extracted as a second event.
- **slab_material_activity:** Each action is a separate row; activity selects its meaning and occurred_at is its actual time.
- **planned_rolling_instruction_activity:** Each action is a separate row; activity selects its meaning and occurred_at is its actual time.
- **rolling_instruction_activity:** Each action is a separate row; activity selects its meaning and occurred_at is its actual time.
- **furnace_charge_tracking_activity:** Each action is a separate row; activity selects its meaning and occurred_at is its actual time.
- **cutting_finishing_instruction_activity:** Each action is a separate row; activity selects its meaning and occurred_at is its actual time.
- **plate_material_activity:** Each action is a separate row; activity selects its meaning and occurred_at is its actual time.
- **lifecycle_case_link:** Master, plan, reference or relationship/index data; this table does not directly produce an event in the current ES. Related objects can still have logs from other tables.

## 3. Column definitions

### slab_material

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow.slab_material.slab_id | Slab Id / slab_id | Synthetic slab identity | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: PRIMARY KEY | See column definition; no implicit unit | ["SL001", "SL002", "SL003"] |
| plateflow.slab_material.charge_id | Charge Id / charge_id | Upstream charge identity, contextual attribute | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["CH001", "CH002", "CH003"] |

- **Declared table constraints:** `CREATE TABLE slab_material (slab_id TEXT PRIMARY KEY, charge_id TEXT NOT NULL)`

### planned_rolling_instruction

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow.planned_rolling_instruction.plan_id | Plan Id / plan_id | Plan identity | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: PRIMARY KEY | See column definition; no implicit unit | ["PLAN001", "PLAN002", "PLAN003"] |
| plateflow.planned_rolling_instruction.slab_id | Slab Id / slab_id | Planned input slab | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / slab_material.slab_id | No SQL default | SQL type and declared constraints: NOT NULL REFERENCES slab_material(slab_id) | See column definition; no implicit unit | ["SL001", "SL002", "SL003"] |
| plateflow.planned_rolling_instruction.planned_reheat_at | Planned Reheat At / planned_reheat_at | Scheduled furnace charging time | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-02T02:00:00Z", "2026-03-03T02:00:00Z", "2026-03-04T02:00:00Z"] |

- **Declared table constraints:** `CREATE TABLE planned_rolling_instruction (plan_id TEXT PRIMARY KEY, slab_id TEXT NOT NULL REFERENCES slab_material(slab_id), planned_reheat_at TEXT NOT NULL)`

### rolling_instruction

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow.rolling_instruction.instruction_id | Instruction Id / instruction_id | Synthetic row identity | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: PRIMARY KEY | See column definition; no implicit unit | ["RI001", "RI002", "RI003"] |
| plateflow.rolling_instruction.plan_id | Plan Id / plan_id | Synthetic explicit link to plan | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / planned_rolling_instruction.plan_id | No SQL default | SQL type and declared constraints: NOT NULL UNIQUE REFERENCES planned_rolling_instruction(plan_id) | See column definition; no implicit unit | ["PLAN001", "PLAN002", "PLAN003"] |
| plateflow.rolling_instruction.released_at | Released At / released_at | Actual instruction release time | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-02T00:00:00Z", "2026-03-03T00:00:00Z", "2026-03-04T00:00:00Z"] |

- **Declared table constraints:** `CREATE TABLE rolling_instruction (instruction_id TEXT PRIMARY KEY, plan_id TEXT NOT NULL UNIQUE REFERENCES planned_rolling_instruction(plan_id), released_at TEXT NOT NULL)`

### as_rolled_material

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow.as_rolled_material.material_id | Material Id / material_id | Mother material identity | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: PRIMARY KEY | See column definition; no implicit unit | ["M001", "M002", "M003"] |
| plateflow.as_rolled_material.as_rolled_plate_no | As Rolled Plate No / as_rolled_plate_no | Mother as-rolled plate number | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL UNIQUE | See column definition; no implicit unit | ["AR001", "AR002", "AR003"] |
| plateflow.as_rolled_material.slab_id | Slab Id / slab_id | Source slab | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / slab_material.slab_id | No SQL default | SQL type and declared constraints: NOT NULL UNIQUE REFERENCES slab_material(slab_id) | See column definition; no implicit unit | ["SL001", "SL002", "SL003"] |
| plateflow.as_rolled_material.instruction_id | Instruction Id / instruction_id | Synthetic explicit link to released instruction | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / rolling_instruction.instruction_id | No SQL default | SQL type and declared constraints: NOT NULL UNIQUE REFERENCES rolling_instruction(instruction_id) | See column definition; no implicit unit | ["RI001", "RI002", "RI003"] |
| plateflow.as_rolled_material.furnace_charged_at | Furnace Charged At / furnace_charged_at | Actual furnace material charging | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-03T04:00:00Z", "2026-03-04T03:00:00Z", "2026-03-05T02:00:00Z"] |
| plateflow.as_rolled_material.crop_shear_passed_at | Crop Shear Passed At / crop_shear_passed_at | Actual crop-shear passage | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-05T09:00:00Z", "2026-03-06T09:00:00Z", "2026-03-07T09:00:00Z"] |
| plateflow.as_rolled_material.latest_operation_completed_at | Latest Operation Completed At / latest_operation_completed_at | Snapshot of latest mother-material operation, not always rolling completion | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-04T06:00:00Z", "2026-03-05T11:00:00Z", "2026-03-06T11:00:00Z"] |
| plateflow.as_rolled_material.created_at | Created At / created_at | Technical database creation timestamp | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-01T23:00:00Z", "2026-03-02T23:00:00Z", "2026-03-03T23:00:00Z"] |
| plateflow.as_rolled_material.updated_at | Updated At / updated_at | Technical database update timestamp | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-02T22:00:00Z", "2026-03-03T22:00:00Z", "2026-03-04T22:00:00Z"] |

- **Declared table constraints:** `CREATE TABLE as_rolled_material (material_id TEXT PRIMARY KEY, as_rolled_plate_no TEXT NOT NULL UNIQUE, slab_id TEXT NOT NULL UNIQUE REFERENCES slab_material(slab_id), instruction_id TEXT NOT NULL UNIQUE REFERENCES rolling_instruction(instruction_id), furnace_charged_at TEXT , crop_shear_passed_at TEXT , latest_operation_completed_at TEXT , created_at TEXT NOT NULL, updated_at TEXT NOT NULL)`

### furnace_charge_tracking

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow.furnace_charge_tracking.tracking_id | Tracking Id / tracking_id | Tracking occurrence ID | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: PRIMARY KEY | See column definition; no implicit unit | ["TRM002", "TRM003", "TRM004"] |
| plateflow.furnace_charge_tracking.material_id | Material Id / material_id | Tracked material | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / as_rolled_material.material_id | No SQL default | SQL type and declared constraints: NOT NULL UNIQUE REFERENCES as_rolled_material(material_id) | See column definition; no implicit unit | ["M002", "M003", "M004"] |
| plateflow.furnace_charge_tracking.yard_instruction_received_at | Yard Instruction Received At / yard_instruction_received_at | Actual yard instruction receipt | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-03T01:00:00Z", "2026-03-04T01:00:00Z", "2026-03-05T01:00:00Z"] |
| plateflow.furnace_charge_tracking.lot_charging_started_at | Lot Charging Started At / lot_charging_started_at | Furnace lot charging start; different event granularity from material entry | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-03T01:30:00Z", "2026-03-04T01:30:00Z", "2026-03-05T01:30:00Z"] |

- **Declared table constraints:** `CREATE TABLE furnace_charge_tracking (tracking_id TEXT PRIMARY KEY, material_id TEXT NOT NULL UNIQUE REFERENCES as_rolled_material(material_id), yard_instruction_received_at TEXT NOT NULL, lot_charging_started_at TEXT NOT NULL)`

### cutting_finishing_instruction

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow.cutting_finishing_instruction.instruction_id | Instruction Id / instruction_id | Synthetic instruction ID | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: PRIMARY KEY | See column definition; no implicit unit | ["CIM004", "CIM005", "CIM006"] |
| plateflow.cutting_finishing_instruction.material_id | Material Id / material_id | Directed mother material | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / as_rolled_material.material_id | No SQL default | SQL type and declared constraints: NOT NULL UNIQUE REFERENCES as_rolled_material(material_id) | See column definition; no implicit unit | ["M004", "M005", "M006"] |
| plateflow.cutting_finishing_instruction.released_at | Released At / released_at | Actual cutting/finishing instruction release | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-05T10:00:00Z", "2026-03-06T10:00:00Z", "2026-03-07T10:00:00Z"] |
| plateflow.cutting_finishing_instruction.cut_method | Cut Method / cut_method | Synthetic split-cut method code | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL CHECK(cut_method='SPLIT') | See column definition; no implicit unit | ["SPLIT"] |

- **Declared table constraints:** `CREATE TABLE cutting_finishing_instruction (instruction_id TEXT PRIMARY KEY, material_id TEXT NOT NULL UNIQUE REFERENCES as_rolled_material(material_id), released_at TEXT NOT NULL, cut_method TEXT NOT NULL CHECK(cut_method='SPLIT'))`

### plate_material

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow.plate_material.plate_material_id | Plate Material Id / plate_material_id | Finished-piece material identity | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: PRIMARY KEY | See column definition; no implicit unit | ["P004-1", "P004-2", "P004-3"] |
| plateflow.plate_material.plate_no | Plate No / plate_no | Individual Plate number | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL UNIQUE | See column definition; no implicit unit | ["PLP004-1", "PLP004-2", "PLP004-3"] |
| plateflow.plate_material.parent_as_rolled_plate_no | Parent As Rolled Plate No / parent_as_rolled_plate_no | Mother as-rolled plate number; synthetic FK policy | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / as_rolled_material.as_rolled_plate_no | No SQL default | SQL type and declared constraints: NOT NULL REFERENCES as_rolled_material(as_rolled_plate_no) | See column definition; no implicit unit | ["AR004", "AR005", "AR006"] |
| plateflow.plate_material.dimension_inspected_at | Dimension Inspected At / dimension_inspected_at | Actual dimensional inspection timestamp | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-05T13:36:00Z", "2026-03-05T13:42:00Z", "2026-03-05T13:48:00Z"] |
| plateflow.plate_material.latest_operation_completed_at | Latest Operation Completed At / latest_operation_completed_at | Latest piece operation snapshot | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-05T13:36:00Z", "2026-03-05T13:42:00Z", "2026-03-05T13:48:00Z"] |

- **Declared table constraints:** `CREATE TABLE plate_material (plate_material_id TEXT PRIMARY KEY, plate_no TEXT NOT NULL UNIQUE, parent_as_rolled_plate_no TEXT NOT NULL REFERENCES as_rolled_material(as_rolled_plate_no), dimension_inspected_at TEXT , latest_operation_completed_at TEXT )`

### operation_code

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow.operation_code.code | Code / code | Synthetic process code | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: PRIMARY KEY | See column definition; no implicit unit | ["CO", "HT", "IF"] |
| plateflow.operation_code.meaning | Meaning / meaning | English operation meaning | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL UNIQUE | See column definition; no implicit unit | ["Cooling Completed", "Heat Treatment Completed", "Inspection Failed"] |

- **Declared table constraints:** `CREATE TABLE operation_code (code TEXT PRIMARY KEY, meaning TEXT NOT NULL UNIQUE)`

### material_operation_history

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow.material_operation_history.transaction_id | Transaction Id / transaction_id | Operation occurrence ID | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: PRIMARY KEY | See column definition; no implicit unit | ["M003-RL", "M004-CO", "M004-LE"] |
| plateflow.material_operation_history.material_id | Material Id / material_id | Mother or piece material identity; validated against both material tables | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["M003", "M004", "P004-1"] |
| plateflow.material_operation_history.operation_code | Operation Code / operation_code | Synthetic factory/process code | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / operation_code.code | No SQL default | SQL type and declared constraints: NOT NULL REFERENCES operation_code(code) | See column definition; no implicit unit | ["RL", "CO", "LE"] |
| plateflow.material_operation_history.started_at | Started At / started_at | Actual operation start time | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-04T05:30:00Z", "2026-03-05T05:30:00Z", "2026-03-05T06:30:00Z"] |
| plateflow.material_operation_history.completed_at | Completed At / completed_at | Actual operation completion time | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL CHECK(completed_at > started_at) | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-04T06:00:00Z", "2026-03-05T06:00:00Z", "2026-03-05T07:00:00Z"] |
| plateflow.material_operation_history.created_at | Created At / created_at | Technical record insertion time | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-04T06:06:00Z", "2026-03-05T06:06:00Z", "2026-03-05T07:06:00Z"] |

- **Declared table constraints:** `CREATE TABLE material_operation_history (transaction_id TEXT PRIMARY KEY, material_id TEXT NOT NULL, operation_code TEXT NOT NULL REFERENCES operation_code(code), started_at TEXT NOT NULL, completed_at TEXT NOT NULL CHECK(completed_at > started_at), created_at TEXT NOT NULL)`

### slab_material_activity

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow.slab_material_activity.event_id | Event Id / event_id | Stable identity of this actual business action; authored extension | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: PRIMARY KEY | See column definition; no implicit unit | ["LC:slab_material:SL001:1", "LC:slab_material:SL001:2", "LC:slab_material:SL001:3"] |
| plateflow.slab_material_activity.slab_id | Slab Id / slab_id | Explicit parent object key; FK to slab_material.slab_id | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / slab_material.slab_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["SL001", "SL002", "SL003"] |
| plateflow.slab_material_activity.activity | Activity / activity | Controlled business activity label; not a technical database update | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Slab Received", "Slab Identity Verified", "Slab Quality Checked"] |
| plateflow.slab_material_activity.occurred_at | Occurred At / occurred_at | Actual occurrence time in UTC, distinct from planned dates | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-01T14:00:00Z", "2026-03-01T15:00:00Z", "2026-03-01T16:00:00Z"] |
| plateflow.slab_material_activity.outcome | Outcome / outcome | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["COMPLETED", "APPROVED"] |

- **Declared table constraints:** `CREATE TABLE slab_material_activity (event_id TEXT PRIMARY KEY, slab_id TEXT NOT NULL, activity TEXT NOT NULL, occurred_at TEXT NOT NULL, outcome TEXT NOT NULL, FOREIGN KEY (slab_id) REFERENCES slab_material(slab_id))`

### planned_rolling_instruction_activity

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow.planned_rolling_instruction_activity.event_id | Event Id / event_id | Stable identity of this actual business action; authored extension | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: PRIMARY KEY | See column definition; no implicit unit | ["LC:planned_rolling_instruction:PLAN001:1", "LC:planned_rolling_instruction:PLAN001:2", "LC:planned_rolling_instruction:PLAN001:3"] |
| plateflow.planned_rolling_instruction_activity.plan_id | Plan Id / plan_id | Explicit parent object key; FK to planned_rolling_instruction.plan_id | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / planned_rolling_instruction.plan_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["PLAN001", "PLAN002", "PLAN003"] |
| plateflow.planned_rolling_instruction_activity.activity | Activity / activity | Controlled business activity label; not a technical database update | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Rolling Plan Created", "Rolling Plan Reviewed", "Rolling Plan Approved"] |
| plateflow.planned_rolling_instruction_activity.occurred_at | Occurred At / occurred_at | Actual occurrence time in UTC, distinct from planned dates | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-01T14:00:00Z", "2026-03-01T15:00:00Z", "2026-03-01T16:00:00Z"] |
| plateflow.planned_rolling_instruction_activity.outcome | Outcome / outcome | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["COMPLETED", "APPROVED"] |

- **Declared table constraints:** `CREATE TABLE planned_rolling_instruction_activity (event_id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, activity TEXT NOT NULL, occurred_at TEXT NOT NULL, outcome TEXT NOT NULL, FOREIGN KEY (plan_id) REFERENCES planned_rolling_instruction(plan_id))`

### rolling_instruction_activity

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow.rolling_instruction_activity.event_id | Event Id / event_id | Stable identity of this actual business action; authored extension | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: PRIMARY KEY | See column definition; no implicit unit | ["LC:rolling_instruction:RI001:1", "LC:rolling_instruction:RI002:1", "LC:rolling_instruction:RI002:2"] |
| plateflow.rolling_instruction_activity.instruction_id | Instruction Id / instruction_id | Explicit parent object key; FK to rolling_instruction.instruction_id | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / rolling_instruction.instruction_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["RI001", "RI002", "RI003"] |
| plateflow.rolling_instruction_activity.activity | Activity / activity | Controlled business activity label; not a technical database update | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Rolling Instruction Acknowledged", "Rolling Setup Verified", "Rolling Work Started"] |
| plateflow.rolling_instruction_activity.occurred_at | Occurred At / occurred_at | Actual occurrence time in UTC, distinct from planned dates | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-02T00:05:00Z", "2026-03-03T00:05:00Z", "2026-03-03T00:10:00Z"] |
| plateflow.rolling_instruction_activity.outcome | Outcome / outcome | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["COMPLETED"] |

- **Declared table constraints:** `CREATE TABLE rolling_instruction_activity (event_id TEXT PRIMARY KEY, instruction_id TEXT NOT NULL, activity TEXT NOT NULL, occurred_at TEXT NOT NULL, outcome TEXT NOT NULL, FOREIGN KEY (instruction_id) REFERENCES rolling_instruction(instruction_id))`

### furnace_charge_tracking_activity

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow.furnace_charge_tracking_activity.event_id | Event Id / event_id | Stable identity of this actual business action; authored extension | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: PRIMARY KEY | See column definition; no implicit unit | ["LC:furnace_charge_tracking:TRM002:1", "LC:furnace_charge_tracking:TRM003:1", "LC:furnace_charge_tracking:TRM003:2"] |
| plateflow.furnace_charge_tracking_activity.tracking_id | Tracking Id / tracking_id | Explicit parent object key; FK to furnace_charge_tracking.tracking_id | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / furnace_charge_tracking.tracking_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["TRM002", "TRM003", "TRM004"] |
| plateflow.furnace_charge_tracking_activity.activity | Activity / activity | Controlled business activity label; not a technical database update | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Furnace Charge Assigned", "Furnace Charge Confirmed", "Heating Completed"] |
| plateflow.furnace_charge_tracking_activity.occurred_at | Occurred At / occurred_at | Actual occurrence time in UTC, distinct from planned dates | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-03T01:05:00Z", "2026-03-04T01:05:00Z", "2026-03-04T03:01:00Z"] |
| plateflow.furnace_charge_tracking_activity.outcome | Outcome / outcome | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["COMPLETED"] |

- **Declared table constraints:** `CREATE TABLE furnace_charge_tracking_activity (event_id TEXT PRIMARY KEY, tracking_id TEXT NOT NULL, activity TEXT NOT NULL, occurred_at TEXT NOT NULL, outcome TEXT NOT NULL, FOREIGN KEY (tracking_id) REFERENCES furnace_charge_tracking(tracking_id))`

### cutting_finishing_instruction_activity

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow.cutting_finishing_instruction_activity.event_id | Event Id / event_id | Stable identity of this actual business action; authored extension | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: PRIMARY KEY | See column definition; no implicit unit | ["LC:cutting_finishing_instruction:CIM004:1", "LC:cutting_finishing_instruction:CIM004:2", "LC:cutting_finishing_instruction:CIM004:3"] |
| plateflow.cutting_finishing_instruction_activity.instruction_id | Instruction Id / instruction_id | Explicit parent object key; FK to cutting_finishing_instruction.instruction_id | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / cutting_finishing_instruction.instruction_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["CIM004", "CIM005", "CIM006"] |
| plateflow.cutting_finishing_instruction_activity.activity | Activity / activity | Controlled business activity label; not a technical database update | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Cutting Instruction Acknowledged", "Cutting Setup Verified", "Cutting Work Started"] |
| plateflow.cutting_finishing_instruction_activity.occurred_at | Occurred At / occurred_at | Actual occurrence time in UTC, distinct from planned dates | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-05T10:05:00Z", "2026-03-05T10:10:00Z", "2026-03-05T10:55:00Z"] |
| plateflow.cutting_finishing_instruction_activity.outcome | Outcome / outcome | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["COMPLETED"] |

- **Declared table constraints:** `CREATE TABLE cutting_finishing_instruction_activity (event_id TEXT PRIMARY KEY, instruction_id TEXT NOT NULL, activity TEXT NOT NULL, occurred_at TEXT NOT NULL, outcome TEXT NOT NULL, FOREIGN KEY (instruction_id) REFERENCES cutting_finishing_instruction(instruction_id))`

### plate_material_activity

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow.plate_material_activity.event_id | Event Id / event_id | Stable identity of this actual business action; authored extension | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: PRIMARY KEY | See column definition; no implicit unit | ["LC:plate_material:P004-1:1", "LC:plate_material:P004-1:2", "LC:plate_material:P004-1:3"] |
| plateflow.plate_material_activity.plate_material_id | Plate Material Id / plate_material_id | Explicit parent object key; FK to plate_material.plate_material_id | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / plate_material.plate_material_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["P004-1", "P004-2", "P004-3"] |
| plateflow.plate_material_activity.activity | Activity / activity | Controlled business activity label; not a technical database update | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Plate Piece Identified", "Plate Surface Checked", "Plate Quality Released"] |
| plateflow.plate_material_activity.occurred_at | Occurred At / occurred_at | Actual occurrence time in UTC, distinct from planned dates | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-05T12:36:00Z", "2026-03-05T14:06:00Z", "2026-03-05T14:36:00Z"] |
| plateflow.plate_material_activity.outcome | Outcome / outcome | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["COMPLETED", "APPROVED"] |

- **Declared table constraints:** `CREATE TABLE plate_material_activity (event_id TEXT PRIMARY KEY, plate_material_id TEXT NOT NULL, activity TEXT NOT NULL, occurred_at TEXT NOT NULL, outcome TEXT NOT NULL, FOREIGN KEY (plate_material_id) REFERENCES plate_material(plate_material_id))`

### lifecycle_case_link

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow.lifecycle_case_link.event_id | Event Id / event_id | Validated identity in a typed activity table; polymorphic reference | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["LC:cutting_finishing_instruction:CIM004:1", "LC:cutting_finishing_instruction:CIM004:2", "LC:cutting_finishing_instruction:CIM004:3"] |
| plateflow.lifecycle_case_link.case_table | Case Table / case_table | Controlled existing business table name | Identifier / TEXT | Not bounded by declared SQLite type | yes | 2 /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["slab_material", "as_rolled_material", "planned_rolling_instruction"] |
| plateflow.lifecycle_case_link.case_id | Case Id / case_id | Serialized primary key of the declared case table; composite parts separated by colon | Identifier / TEXT | Not bounded by declared SQLite type | yes | 3 /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["SL001", "SL002", "SL003"] |

- **Declared table constraints:** `CREATE TABLE lifecycle_case_link(event_id TEXT NOT NULL,case_table TEXT NOT NULL,case_id TEXT NOT NULL,PRIMARY KEY(event_id,case_table,case_id))`

### Business meanings and extraction rules

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

### Plateflow object activities and scenarios

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
