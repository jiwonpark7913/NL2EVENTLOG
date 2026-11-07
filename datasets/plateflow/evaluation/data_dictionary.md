# PlateFlow New — data dictionary

## 1. Dictionary basic information

| Field | Value |
| --- | --- |
| dictionary_id | NL2EVENTLOG:plateflow_new |
| name | PlateFlow New |
| version | 2026-10-29 |
| language | en |
| dbms | SQLite |
| timezone | UTC |
| description | Synthetic plate-manufacturing business records with explicitly declared identifiers and relationships. |
| status | Project-maintained synthetic business-data definitions |
| standards_profile | Three-part project profile informed by public ISO/IEC 11179-3 and 11179-4 scope statements; not a certification or full conformance assessment. |
| source_policy | Schema-informed manufacturing simulation; authored additions are documented separately. |

- The three-part layout is a project choice. ISO/IEC 11179-3 concerns registry facilities and 11179-4 concerns semantic definitions; the public scope statements do not mandate this template.
- A composite primary key is one key over its full tuple. All SQL constraints below are taken from the executable schema.
- References: [ISO/IEC 11179-3](https://www.iso.org/standard/78915.html), [ISO/IEC 11179-4](https://www.iso.org/standard/35346.html).

## 2. Table definitions

| Table ID | Logical / physical name | PK | FK | Business definition |
| --- | --- | --- | --- | --- |
| plateflow_new.slab_material | Slab Material / slab_material | slab_id | None declared | Slab identity, steel grade and actual receipt, verification and release times. |
| plateflow_new.planned_rolling_instruction | Planned Rolling Instruction / planned_rolling_instruction | plan_id | (slab_id) → slab_material(slab_id) | One rolling plan per slab, its scheduled reheating time and actual submission, approval and release times. |
| plateflow_new.rolling_instruction | Rolling Instruction / rolling_instruction | instruction_id | (plan_id) → planned_rolling_instruction(plan_id) | An issued rolling instruction for an approved plan. |
| plateflow_new.as_rolled_material | As Rolled Material / as_rolled_material | material_id | (instruction_id) → rolling_instruction(instruction_id); (slab_id) → slab_material(slab_id) | Allocated mother-material identity and genealogy for a rolling instruction; created_at and updated_at describe database maintenance, not production completion. |
| plateflow_new.process_code | Process Code / process_code | process_group, code | None declared | Business code meanings within each manufacturing process group. The same code text can have a different meaning in another group. |
| plateflow_new.equipment | Equipment / equipment | equipment_id | None declared | Equipment identifiers, names and system-maintenance times. Each equipment_code identifies a machine, not a manufacturing step. |
| plateflow_new.furnace_operation_history | Furnace Operation History / furnace_operation_history | operation_id | (process_group,operation_code) → process_code(process_group,code); (equipment_id) → equipment(equipment_id); (material_id) → as_rolled_material(material_id) | Actual furnace work occurrences for mother materials, retaining repeat work and unfinished intervals. |
| plateflow_new.rolling_operation_history | Rolling Operation History / rolling_operation_history | operation_id | (process_group,phase_code) → process_code(process_group,code); (equipment_id) → equipment(equipment_id); (material_id) → as_rolled_material(material_id) | Actual rolling phase occurrences for mother materials, retaining repeat work and unfinished intervals. |
| plateflow_new.plate_material | Plate Material / plate_material | plate_id | (mother_material_id) → as_rolled_material(material_id) | Individual plate-piece identity and mother-material genealogy, with actual identification, release and packing times. |
| plateflow_new.finishing_operation_history | Finishing Operation History / finishing_operation_history | operation_id | (process_group,operation_code) → process_code(process_group,code); (equipment_id) → equipment(equipment_id); (plate_id) → plate_material(plate_id) | Actual finishing work occurrences for individual plate pieces, including repeated heat treatment after rework. |
| plateflow_new.dimension_inspection | Dimension Inspection / dimension_inspection | inspection_id | (plate_id) → plate_material(plate_id) | One dimensional inspection record per inspection occurrence. Reinspection has a new inspection_id; PASS/FAIL describes its result. |
| plateflow_new.plate_quality_review | Plate Quality Review / plate_quality_review | review_id | (plate_id) → plate_material(plate_id) | One quality review record per review round. APPROVED/REWORK describes its outcome; PENDING means the review has not finished. |

## 3. Column definitions

### slab_material

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow_new.slab_material.slab_id | slab_id | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique slab identifier; on a plan or mother record, identifies its source slab. |
| plateflow_new.slab_material.charge_id | charge_id | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Steelmaking charge identifier recorded for material genealogy; no casting time is recorded here. |
| plateflow_new.slab_material.steel_grade | steel_grade | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Synthetic steel-grade category G1 or G2. |
| plateflow_new.slab_material.received_at | received_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC time at which the slab was received. |
| plateflow_new.slab_material.verified_at | verified_at | TEXT | False |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC time at which the slab identity was verified; NULL if not yet verified. |
| plateflow_new.slab_material.released_at | released_at | TEXT | False |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC release time for the slab, rolling plan or plate piece described by this table; NULL if not yet released. |

```sql
CREATE TABLE slab_material(slab_id TEXT PRIMARY KEY NOT NULL, charge_id TEXT NOT NULL, steel_grade TEXT NOT NULL CHECK(steel_grade IN ('G1','G2')), received_at TEXT NOT NULL, verified_at TEXT, released_at TEXT, CHECK(verified_at IS NULL OR received_at<=verified_at), CHECK(released_at IS NULL OR (verified_at IS NOT NULL AND verified_at<=released_at)));
```

### planned_rolling_instruction

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow_new.planned_rolling_instruction.plan_id | plan_id | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique rolling-plan identifier; on an instruction, references its plan. |
| plateflow_new.planned_rolling_instruction.slab_id | slab_id | TEXT | True |  | slab_material.slab_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique slab identifier; on a plan or mother record, identifies its source slab. |
| plateflow_new.planned_rolling_instruction.planned_reheat_at | planned_reheat_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Scheduled UTC reheating time; a schedule does not establish that reheating occurred. |
| plateflow_new.planned_rolling_instruction.submitted_at | submitted_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC rolling-plan submission time. |
| plateflow_new.planned_rolling_instruction.approved_at | approved_at | TEXT | False |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC rolling-plan approval time; NULL if not yet approved. |
| plateflow_new.planned_rolling_instruction.released_at | released_at | TEXT | False |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC release time for the slab, rolling plan or plate piece described by this table; NULL if not yet released. |

```sql
CREATE TABLE planned_rolling_instruction(plan_id TEXT PRIMARY KEY NOT NULL, slab_id TEXT NOT NULL UNIQUE REFERENCES slab_material(slab_id), planned_reheat_at TEXT NOT NULL, submitted_at TEXT NOT NULL, approved_at TEXT, released_at TEXT, CHECK(approved_at IS NULL OR submitted_at<=approved_at), CHECK(released_at IS NULL OR (approved_at IS NOT NULL AND approved_at<=released_at)));
```

### rolling_instruction

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow_new.rolling_instruction.instruction_id | instruction_id | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique rolling-instruction identifier; on a mother record, references the instruction allocating it. |
| plateflow_new.rolling_instruction.plan_id | plan_id | TEXT | True |  | planned_rolling_instruction.plan_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique rolling-plan identifier; on an instruction, references its plan. |
| plateflow_new.rolling_instruction.issued_at | issued_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC rolling-instruction issue time. |

```sql
CREATE TABLE rolling_instruction(instruction_id TEXT PRIMARY KEY NOT NULL, plan_id TEXT NOT NULL UNIQUE REFERENCES planned_rolling_instruction(plan_id), issued_at TEXT NOT NULL);
```

### as_rolled_material

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow_new.as_rolled_material.material_id | material_id | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique mother-material identifier; on a work record, references the mother material processed. |
| plateflow_new.as_rolled_material.plate_no | plate_no | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique business plate number within this table; mother and piece numbers have separate ranges. |
| plateflow_new.as_rolled_material.slab_id | slab_id | TEXT | True |  | slab_material.slab_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique slab identifier; on a plan or mother record, identifies its source slab. |
| plateflow_new.as_rolled_material.instruction_id | instruction_id | TEXT | True |  | rolling_instruction.instruction_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique rolling-instruction identifier; on a mother record, references the instruction allocating it. |
| plateflow_new.as_rolled_material.created_at | created_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | UTC database record-creation time; this field does not document a production action. |
| plateflow_new.as_rolled_material.updated_at | updated_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | UTC database maintenance time; this field does not document a production action. |

```sql
CREATE TABLE as_rolled_material(material_id TEXT PRIMARY KEY NOT NULL, plate_no TEXT NOT NULL UNIQUE, slab_id TEXT NOT NULL UNIQUE REFERENCES slab_material(slab_id), instruction_id TEXT NOT NULL UNIQUE REFERENCES rolling_instruction(instruction_id), created_at TEXT NOT NULL, updated_at TEXT NOT NULL, CHECK(created_at<=updated_at));
```

### process_code

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow_new.process_code.process_group | process_group | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Business context FURNACE, ROLLING or FINISHING; each work-history table has one fixed group enforced by CHECK. |
| plateflow_new.process_code.code | code | TEXT | True | 2 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Business code within a process group; the pair (process_group,code) uniquely identifies its meaning. |
| plateflow_new.process_code.meaning | meaning | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | Not applicable | English business meaning of the code in the specified process group. |

```sql
CREATE TABLE process_code(process_group TEXT NOT NULL CHECK(process_group IN ('FURNACE','ROLLING','FINISHING')), code TEXT NOT NULL, meaning TEXT NOT NULL, PRIMARY KEY(process_group,code));
```

### equipment

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow_new.equipment.equipment_id | equipment_id | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique equipment-unit identifier; on a work record, references the unit that performed the work. |
| plateflow_new.equipment.equipment_code | equipment_code | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Human-readable machine code; identifies the machine, not the work performed. |
| plateflow_new.equipment.equipment_name | equipment_name | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | Not applicable | English equipment-unit name. |
| plateflow_new.equipment.created_at | created_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | UTC database record-creation time; this field does not document a production action. |
| plateflow_new.equipment.updated_at | updated_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | UTC database maintenance time; this field does not document a production action. |

```sql
CREATE TABLE equipment(equipment_id TEXT PRIMARY KEY NOT NULL, equipment_code TEXT NOT NULL UNIQUE, equipment_name TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, CHECK(created_at<=updated_at));
```

### furnace_operation_history

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow_new.furnace_operation_history.operation_id | operation_id | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique work-occurrence identifier within this table; repeat work receives a new identifier. |
| plateflow_new.furnace_operation_history.material_id | material_id | TEXT | True |  | as_rolled_material.material_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique mother-material identifier; on a work record, references the mother material processed. |
| plateflow_new.furnace_operation_history.process_group | process_group | TEXT | True |  | process_code.process_group | 'FURNACE' | Unbounded SQLite TEXT | Not applicable | Business context FURNACE, ROLLING or FINISHING; each work-history table has one fixed group enforced by CHECK. |
| plateflow_new.furnace_operation_history.operation_code | operation_code | TEXT | True |  | process_code.code | No SQL default | Unbounded SQLite TEXT | Not applicable | Kind of manufacturing work performed, as defined by the matching process_group/code entry. |
| plateflow_new.furnace_operation_history.equipment_id | equipment_id | TEXT | True |  | equipment.equipment_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique equipment-unit identifier; on a work record, references the unit that performed the work. |
| plateflow_new.furnace_operation_history.started_at | started_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC start of this manufacturing work occurrence or quality-review round. |
| plateflow_new.furnace_operation_history.finished_at | finished_at | TEXT | False |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC finish of this manufacturing work occurrence or quality-review round; NULL if unfinished. |

```sql
CREATE TABLE furnace_operation_history(operation_id TEXT PRIMARY KEY NOT NULL, material_id TEXT NOT NULL REFERENCES as_rolled_material(material_id), process_group TEXT NOT NULL DEFAULT 'FURNACE' CHECK(process_group='FURNACE'), operation_code TEXT NOT NULL, equipment_id TEXT NOT NULL REFERENCES equipment(equipment_id), started_at TEXT NOT NULL, finished_at TEXT, FOREIGN KEY(process_group,operation_code) REFERENCES process_code(process_group,code), CHECK(finished_at IS NULL OR started_at<finished_at));
```

### rolling_operation_history

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow_new.rolling_operation_history.operation_id | operation_id | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique work-occurrence identifier within this table; repeat work receives a new identifier. |
| plateflow_new.rolling_operation_history.material_id | material_id | TEXT | True |  | as_rolled_material.material_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique mother-material identifier; on a work record, references the mother material processed. |
| plateflow_new.rolling_operation_history.process_group | process_group | TEXT | True |  | process_code.process_group | 'ROLLING' | Unbounded SQLite TEXT | Not applicable | Business context FURNACE, ROLLING or FINISHING; each work-history table has one fixed group enforced by CHECK. |
| plateflow_new.rolling_operation_history.phase_code | phase_code | TEXT | True |  | process_code.code | No SQL default | Unbounded SQLite TEXT | Not applicable | Rolling phase performed, as defined by the matching process_group/code entry. |
| plateflow_new.rolling_operation_history.equipment_id | equipment_id | TEXT | True |  | equipment.equipment_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique equipment-unit identifier; on a work record, references the unit that performed the work. |
| plateflow_new.rolling_operation_history.started_at | started_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC start of this manufacturing work occurrence or quality-review round. |
| plateflow_new.rolling_operation_history.finished_at | finished_at | TEXT | False |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC finish of this manufacturing work occurrence or quality-review round; NULL if unfinished. |

```sql
CREATE TABLE rolling_operation_history(operation_id TEXT PRIMARY KEY NOT NULL, material_id TEXT NOT NULL REFERENCES as_rolled_material(material_id), process_group TEXT NOT NULL DEFAULT 'ROLLING' CHECK(process_group='ROLLING'), phase_code TEXT NOT NULL, equipment_id TEXT NOT NULL REFERENCES equipment(equipment_id), started_at TEXT NOT NULL, finished_at TEXT, FOREIGN KEY(process_group,phase_code) REFERENCES process_code(process_group,code), CHECK(finished_at IS NULL OR started_at<finished_at));
```

### plate_material

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow_new.plate_material.plate_id | plate_id | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique individual plate-piece identifier; on work, inspection or review records, references the piece concerned. |
| plateflow_new.plate_material.plate_no | plate_no | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique business plate number within this table; mother and piece numbers have separate ranges. |
| plateflow_new.plate_material.mother_material_id | mother_material_id | TEXT | True |  | as_rolled_material.material_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Mother material from which the individual plate piece was derived. |
| plateflow_new.plate_material.identified_at | identified_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC time at which the plate piece was identified after rolling. |
| plateflow_new.plate_material.released_at | released_at | TEXT | False |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC release time for the slab, rolling plan or plate piece described by this table; NULL if not yet released. |
| plateflow_new.plate_material.packed_at | packed_at | TEXT | False |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC packing-completion time; NULL if not yet packed. |

```sql
CREATE TABLE plate_material(plate_id TEXT PRIMARY KEY NOT NULL, plate_no TEXT NOT NULL UNIQUE, mother_material_id TEXT NOT NULL REFERENCES as_rolled_material(material_id), identified_at TEXT NOT NULL, released_at TEXT, packed_at TEXT, CHECK(released_at IS NULL OR identified_at<=released_at), CHECK(packed_at IS NULL OR (released_at IS NOT NULL AND released_at<=packed_at)));
```

### finishing_operation_history

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow_new.finishing_operation_history.operation_id | operation_id | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique work-occurrence identifier within this table; repeat work receives a new identifier. |
| plateflow_new.finishing_operation_history.plate_id | plate_id | TEXT | True |  | plate_material.plate_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique individual plate-piece identifier; on work, inspection or review records, references the piece concerned. |
| plateflow_new.finishing_operation_history.process_group | process_group | TEXT | True |  | process_code.process_group | 'FINISHING' | Unbounded SQLite TEXT | Not applicable | Business context FURNACE, ROLLING or FINISHING; each work-history table has one fixed group enforced by CHECK. |
| plateflow_new.finishing_operation_history.operation_code | operation_code | TEXT | True |  | process_code.code | No SQL default | Unbounded SQLite TEXT | Not applicable | Kind of manufacturing work performed, as defined by the matching process_group/code entry. |
| plateflow_new.finishing_operation_history.equipment_id | equipment_id | TEXT | True |  | equipment.equipment_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique equipment-unit identifier; on a work record, references the unit that performed the work. |
| plateflow_new.finishing_operation_history.started_at | started_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC start of this manufacturing work occurrence or quality-review round. |
| plateflow_new.finishing_operation_history.finished_at | finished_at | TEXT | False |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC finish of this manufacturing work occurrence or quality-review round; NULL if unfinished. |

```sql
CREATE TABLE finishing_operation_history(operation_id TEXT PRIMARY KEY NOT NULL, plate_id TEXT NOT NULL REFERENCES plate_material(plate_id), process_group TEXT NOT NULL DEFAULT 'FINISHING' CHECK(process_group='FINISHING'), operation_code TEXT NOT NULL, equipment_id TEXT NOT NULL REFERENCES equipment(equipment_id), started_at TEXT NOT NULL, finished_at TEXT, FOREIGN KEY(process_group,operation_code) REFERENCES process_code(process_group,code), CHECK(finished_at IS NULL OR started_at<finished_at));
```

### dimension_inspection

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow_new.dimension_inspection.inspection_id | inspection_id | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique dimensional-inspection occurrence identifier; distinct for each reinspection. |
| plateflow_new.dimension_inspection.plate_id | plate_id | TEXT | True |  | plate_material.plate_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique individual plate-piece identifier; on work, inspection or review records, references the piece concerned. |
| plateflow_new.dimension_inspection.inspected_at | inspected_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC dimensional-inspection completion time. |
| plateflow_new.dimension_inspection.result_code | result_code | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Inspection outcome PASS or FAIL; either value represents a completed dimensional inspection. |
| plateflow_new.dimension_inspection.thickness_mm | thickness_mm | REAL | True |  |  | No SQL default | Not applicable | mm | Synthetic measured thickness in millimetres. |

```sql
CREATE TABLE dimension_inspection(inspection_id TEXT PRIMARY KEY NOT NULL, plate_id TEXT NOT NULL REFERENCES plate_material(plate_id), inspected_at TEXT NOT NULL, result_code TEXT NOT NULL CHECK(result_code IN ('PASS','FAIL')), thickness_mm REAL NOT NULL CHECK(thickness_mm>0));
```

### plate_quality_review

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plateflow_new.plate_quality_review.review_id | review_id | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique quality-review round identifier; distinct for each subsequent review. |
| plateflow_new.plate_quality_review.plate_id | plate_id | TEXT | True |  | plate_material.plate_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique individual plate-piece identifier; on work, inspection or review records, references the piece concerned. |
| plateflow_new.plate_quality_review.started_at | started_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC start of this manufacturing work occurrence or quality-review round. |
| plateflow_new.plate_quality_review.finished_at | finished_at | TEXT | False |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC finish of this manufacturing work occurrence or quality-review round; NULL if unfinished. |
| plateflow_new.plate_quality_review.review_status | review_status | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | Not applicable | APPROVED or REWORK for a finished quality review, PENDING for an unfinished review. |

```sql
CREATE TABLE plate_quality_review(review_id TEXT PRIMARY KEY NOT NULL, plate_id TEXT NOT NULL REFERENCES plate_material(plate_id), started_at TEXT NOT NULL, finished_at TEXT, review_status TEXT NOT NULL CHECK(review_status IN ('APPROVED','REWORK','PENDING')), CHECK((review_status='PENDING' AND finished_at IS NULL) OR (review_status IN ('APPROVED','REWORK') AND finished_at IS NOT NULL AND started_at<finished_at)));
```

### Business codes

| Process group | Code | Business meaning |
| --- | --- | --- |
| FURNACE | CH | Furnace charging |
| FURNACE | HT | Furnace heating |
| FURNACE | DS | Furnace discharge |
| ROLLING | RR | Rough rolling |
| ROLLING | FR | Finish rolling |
| FINISHING | LEV | Leveling |
| FINISHING | HT | Heat treatment |
| FINISHING | SF | Surface finishing |

### Business rules

- Each plan concerns one slab. Each issued instruction refers to one plan. Mother and plate-piece identifiers refer to distinct physical materials.
- A mother-material identity can be allocated before work finishes. Database creation and maintenance times are not evidence of production completion.
- Every work occurrence retains its own identifier. Repeat work, reinspection and later review rounds retain separate records.
- Each work-history table is restricted to its declared process group. Code meanings are resolved within that group.
- Review outcome and inspection result describe the result of the same kind of business record; they do not change its business purpose.
- Actual start times may exist without finish times. NULL finish means unfinished work; NULL release/packing means not yet released/packed.
- Scheduled reheating time is a plan and may differ from actual heating time.
- An approved quality review is required before piece release; packing follows release.
- All business records, identifiers, times and measurements are synthetic.
