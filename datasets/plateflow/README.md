# PlateFlow

- **Situation:** Slabs are checked and released, rolling plans and instructions progress through approval and execution, furnace tracking records heating stages, and cut pieces progress through inspection, quality release and packing.
- **Source:** Selected metadata from a Korean manufacturing company. Original source columns and keys are preserved.
- **Extension:** New activity histories, timestamps and cross-object attribution rules are authored synthetic domain design. They are not copied from the source or observed production data.
- **Database:** 16 tables; 37 activity types; 8 object / case types; 1036 distinct recorded business events.
- **Gold:** 15 answerable question-specific CSV logs out of 16 questions. Paraphrase pairs can share the same expected content.
- **Execution:** Run `python datasets/plateflow/build.py` from the repository root, then `python make_docs.py`. Only the Python standard library is needed for DB/log generation; diagrams use PyMuPDF.

## Dataset counts

| Dataset | Tables | Object / case types | Activity types | Distinct events | Questions | Gold CSVs |
|---|---:|---:|---:|---:|---:|---:|
| PlateFlow | 16 | 8 | 37 | 1036 | 16 | 15 |

- **Activity types:** distinct business labels across all recorded events in this database, counted once even when shared by several objects.
- **Object / case types:** distinct keyed tables with an answerable object-specific event log, including auxiliary event/association-record cases. This is a type count, not a count of individual object instances.
- Activity-history tables, the case-link index and code reference tables do not add object types.
- Individual cases may contain fewer activities because of incomplete work or conditional branches.

## Objects, activities and situations

| Object / case | Activity types in its log | Situation / scope | Gold CSV |
|---|---|---|---|
| slab_material | Cooling Completed; Crop Shear Passed; Cutting Instruction Acknowledged; Cutting Instruction Closed; Cutting Instruction Released; Cutting Setup Verified; Cutting Work Started; Dimensional Inspection Completed; Furnace Charge Assigned; Furnace Charge Confirmed; Furnace Discharge Confirmed; Heat Treatment Completed; Heating Completed; Inspection Failed; Inspection Passed; Leveling Completed; Plate Packed; Plate Piece Identified; Plate Quality Released; Plate Surface Checked; Reheating Started; Rolling Completed; Rolling Instruction Acknowledged; Rolling Instruction Closed; Rolling Instruction Released; Rolling Plan Approved; Rolling Plan Created; Rolling Plan Released; Rolling Plan Reviewed; Rolling Setup Verified; Rolling Work Started; Slab Identity Verified; Slab Quality Checked; Slab Received; Slab Released for Rolling; Split Cutting Completed; Yard Instruction Received | Original recorded actions and authored lifecycle actions explicitly linked to this slab. | [CSV](private/gold_logs/OPV01.csv) |
| planned_rolling_instruction | Rolling Instruction Released; Rolling Plan Approved; Rolling Plan Created; Rolling Plan Released; Rolling Plan Reviewed | Original recorded actions and authored lifecycle actions explicitly linked to this rolling plan. | [CSV](private/gold_logs/OPV02.csv) |
| rolling_instruction | Rolling Instruction Acknowledged; Rolling Instruction Closed; Rolling Instruction Released; Rolling Setup Verified; Rolling Work Started | Original recorded actions and authored lifecycle actions explicitly linked to this rolling instruction. | [CSV](private/gold_logs/OPV03.csv) |
| as_rolled_material | Cooling Completed; Crop Shear Passed; Cutting Instruction Acknowledged; Cutting Instruction Closed; Cutting Instruction Released; Cutting Setup Verified; Cutting Work Started; Dimensional Inspection Completed; Furnace Charge Assigned; Furnace Charge Confirmed; Furnace Discharge Confirmed; Heat Treatment Completed; Heating Completed; Inspection Failed; Inspection Passed; Leveling Completed; Plate Packed; Plate Piece Identified; Plate Quality Released; Plate Surface Checked; Reheating Started; Rolling Completed; Rolling Instruction Acknowledged; Rolling Instruction Closed; Rolling Instruction Released; Rolling Plan Approved; Rolling Plan Created; Rolling Plan Released; Rolling Plan Reviewed; Rolling Setup Verified; Rolling Work Started; Slab Identity Verified; Slab Quality Checked; Slab Received; Slab Released for Rolling; Split Cutting Completed; Yard Instruction Received | Original recorded actions and authored lifecycle actions explicitly linked to this mother material. | [CSV](private/gold_logs/OPV04.csv) |
| furnace_charge_tracking | Furnace Charge Assigned; Furnace Charge Confirmed; Furnace Discharge Confirmed; Heating Completed; Yard Instruction Received | Original recorded actions and authored lifecycle actions explicitly linked to this furnace tracking record. | [CSV](private/gold_logs/OPV05.csv) |
| cutting_finishing_instruction | Cutting Instruction Acknowledged; Cutting Instruction Closed; Cutting Instruction Released; Cutting Setup Verified; Cutting Work Started | Original recorded actions and authored lifecycle actions explicitly linked to this cutting instruction. | [CSV](private/gold_logs/OPV06.csv) |
| plate_material | Dimensional Inspection Completed; Heat Treatment Completed; Inspection Failed; Inspection Passed; Plate Packed; Plate Piece Identified; Plate Quality Released; Plate Surface Checked | Original recorded actions and authored lifecycle actions explicitly linked to this cut plate piece. | [CSV](private/gold_logs/OPV07.csv) |
| material_operation_history | Cooling Completed; Heat Treatment Completed; Inspection Failed; Inspection Passed; Leveling Completed; Rolling Completed; Split Cutting Completed | The operation-completion event represented by this transaction ID, preserving its process-code meaning. | [CSV](private/gold_logs/OPV08.csv) |

- Atomic grading and operation records are auxiliary cases; a single occurrence is not expanded into an invented lifecycle.
- Master cases can aggregate unrelated jobs. Multiple activity types do not imply one causal process across all rows.
- Conditional revision branches and incomplete histories are intentional. Repeated activity occurrences keep distinct event IDs.
- Actual activity times are separate from plans, schedules and technical creation/update times.
- Case population includes objects with no selected events; those cases have no CSV rows.
- These are case-based CSV logs, not OCEL.

## Database, extraction and validation

- Typed `<object>_activity` tables store `event_id`, parent PK/FK, `activity`, actual `occurred_at` and `outcome`.
- `lifecycle_case_link` is an explicitly validated auxiliary index relating a recorded event to each permitted case. It is not a business object.
- Full ES queries union original milestone sources and new action histories. Object-specific ES queries apply explicit case links and sort by case, time and event ID.
- Gold logs are generated from simulated history and compared against executable SQL on the populated DB. This checks internal consistency, not model accuracy.
- [Detailed activity design](docs/object_activity_design.md)
- [Event-log case scopes and counts](docs/object_event_logs.md)
- [Data dictionary](docs/data_dictionary.md)
- [Schema overview](docs/schema_overview.md)
- [Editable draw.io](docs/schema.drawio)
- [Validation report](validation_report.json)

![Schema](docs/schema.png)

## Schema and documentation

- [Table inventory and relationships](docs/schema_overview.md)
- [English column dictionary](docs/data_dictionary.md)
- [CSV dictionary](docs/data_dictionary.csv)
- [Editable draw.io diagram](docs/schema.drawio)
- [Object-based Gold logs and coverage](docs/object_event_logs.md)
