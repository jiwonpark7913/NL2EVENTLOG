# PlateFlow

PlateFlow is a synthetic steel-plate production database with slab receiving, rolling preparation, furnace and rolling operations, finishing, inspection and quality review. It reflects industrial process concepts, not observed production records.

[Relational schema](#relational-schema) · [Table previews](#table-inspector) · [Questions](#questions) · [Gold source projection](#gold-event-extraction-graph-eeg-source-projection)

## Entity types and identifiers

[Concepts and formal definitions](../../docs/system/ENTITY_IDENTITY_AND_STORAGE.md) · [Storage cases across datasets](../ENTITY_STORAGE_CASES.md) · [Actual PK, UNIQUE and FK inventory](docs/entity_identifiers.md)

The source projection below assigns a principal type for display. It does not mean a table can identify or reference only one ET. Entity identity is resolved from table/column/condition rules, separately from table membership.

## Dataset overview

| Physical ERs | Entity Type candidates | Core business concepts | Gold SQL/CSV pairs verified |
|---:|---:|---:|---:|
| 12 | 12 | 6 | 50 |

[SQLite database](input/database.sqlite) · [Business Data Dictionary](input/data_dictionary.json) · [Readable dictionary](docs/data_dictionary.md) · [Detailed database review](review/database/README.md)

## Relational schema

![Relational database schema with highlighted timestamp columns](review/database/schema.svg)

**Yellow:** Gold event-time source, where established. **Blue:** other temporal columns. A temporal column is not automatically an event timestamp.

[Open full-size ERD](review/database/schema.svg) · [Editable Draw.io diagram](docs/schema.drawio) · [Timestamp inventory and roles](docs/timestamp_columns.md)

## Table inspector

| Physical table | Rows | Columns | ET candidate | First ten records |
|---|---:|---:|---|---|
| as_rolled_material | 26 | 6 | Mother Material | [Preview](review/database/tables/as_rolled_material.md) |
| dimension_inspection | 46 | 5 | Dimension Inspection | [Preview](review/database/tables/dimension_inspection.md) |
| equipment | 7 | 5 | Equipment | [Preview](review/database/tables/equipment.md) |
| finishing_operation_history | 130 | 7 | Finishing Operation Record | [Preview](review/database/tables/finishing_operation_history.md) |
| furnace_operation_history | 70 | 7 | Furnace Operation Record | [Preview](review/database/tables/furnace_operation_history.md) |
| planned_rolling_instruction | 28 | 6 | Rolling Plan | [Preview](review/database/tables/planned_rolling_instruction.md) |
| plate_material | 38 | 6 | Plate Piece | [Preview](review/database/tables/plate_material.md) |
| plate_quality_review | 46 | 5 | Quality Review | [Preview](review/database/tables/plate_quality_review.md) |
| process_code | 8 | 3 | process_code | [Preview](review/database/tables/process_code.md) |
| rolling_instruction | 26 | 3 | Rolling Instruction | [Preview](review/database/tables/rolling_instruction.md) |
| rolling_operation_history | 44 | 7 | Rolling Operation Record | [Preview](review/database/tables/rolling_operation_history.md) |
| slab_material | 30 | 6 | Slab | [Preview](review/database/tables/slab_material.md) |

## Questions

[**Full question list, types and answerability**](docs/questions.md) · [Question texts (JSONL)](evaluation/model_questions.jsonl) · [Question-level Gold DFGs and source records](review/gold_dfg/README.md)

The checked-in question-text file contains **54 requests**. Explicit requests enumerate activities; implicit requests ask for a recorded lifecycle. Paired paraphrases, where present, are listed in the full question documentation.

<details>
<summary>Browse all 54 question texts</summary>

| ID | Request |
|---|---|
| N01 | For each slab, extract Slab Received, Slab Verified and Slab Released events. |
| N01P | Build a timeline for each slab showing its receipt, verification and release. |
| N02 | For each rolling plan, extract Rolling Plan Submitted, Rolling Plan Approved and Rolling Plan Released events. |
| N02P | For every rolling plan, show when it was submitted, approved and released. |
| N03 | For each rolling instruction, extract Rolling Instruction Issued, Heating Completed and Finish Rolling Completed events. |
| N03P | For every rolling instruction, show its issue, the completion of heating and the completion of finish rolling. |
| N04 | For each mother material, extract Furnace Charged, Heating Completed, Furnace Discharged, Rough Rolling Completed and Finish Rolling Completed events. |
| N04P | For each mother material, show the completion of charging into the furnace, heating, discharge from the furnace, rough rolling and finish rolling. |
| N05 | For each mother material, extract Heat Treatment Completed, Surface Finishing Completed and Dimensional Inspection Completed events, including those of its descendant plate pieces. |
| N05P | For every mother material, show when heat treatment, surface finishing and dimensional inspection were completed, including work on all plate pieces derived from it. |
| N06 | For each plate piece, extract Leveling Completed, Heat Treatment Completed and Surface Finishing Completed events, retaining repeated occurrences. |
| N06P | For each plate piece, show every completed leveling, heat-treatment and surface-finishing operation, including repeat work. |
| N07 | For each plate piece, extract Dimensional Inspection Completed and Plate Quality Review Completed events. |
| N07P | For every plate piece, show when its dimensional inspections and quality reviews finished. |
| N08 | For each plate piece, extract Plate Identified, Plate Released and Plate Packed events. |
| N08P | For each plate piece, show when it was identified, released and packed. |
| N09 | For each dimension inspection record, extract Dimensional Inspection Completed events. |
| N09P | For each individual dimensional inspection record, show when the inspection finished. |
| N10 | For each quality review record, extract Plate Quality Review Completed events. |
| N10P | For each individual quality review record, show when the review finished. |
| N11 | For each equipment unit, extract Heating Completed and Heat Treatment Completed events. |
| N11P | For each equipment unit, show the completion of heating and of heat treatment. |
| N12 | For each furnace operation record, extract Furnace Charged, Heating Completed and Furnace Discharged events. |
| N12P | For every furnace operation record, show the recorded completion of furnace charging, heating or furnace discharge, as applicable. |
| N13 | For each rolling operation record, extract Rough Rolling Completed and Finish Rolling Completed events. |
| N13P | For every rolling operation record, show the recorded completion of rough rolling or finish rolling, as applicable. |
| N14 | For each finishing operation record, extract Leveling Completed, Heat Treatment Completed and Surface Finishing Completed events. |
| N14P | For every finishing operation record, show the recorded completion of leveling, heat treatment or surface finishing, as applicable. |
| N15 | For each slab, extract Steel Cast events. |
| N15P | For each slab, show when the steel was cast. |
| N16 | For each plate piece, extract Truck Dispatched events. |
| N16P | For each plate piece, show when its truck was dispatched. |
| NF01 | Extract the full recorded lifecycle for each slab. |
| NF01P | Show the complete recorded history of each slab. |
| NF02 | Extract the full recorded lifecycle for each rolling plan. |
| NF02P | Build the entire recorded timeline for every rolling plan. |
| NF03 | Extract the full recorded lifecycle for each rolling instruction. |
| NF03P | Trace each rolling instruction through its full recorded history. |
| NF04 | Extract the full recorded lifecycle for each mother material. |
| NF04P | Show the whole recorded lifecycle of every mother material. |
| NF05 | Extract the full recorded lifecycle for each plate piece. |
| NF05P | Build a complete timeline of the recorded history of each plate piece. |
| NF06 | Extract the full recorded lifecycle for each dimension inspection record. |
| NF06P | Show the entire recorded history of every individual dimensional inspection record. |
| NF07 | Extract the full recorded lifecycle for each quality review record. |
| NF07P | Trace each individual quality review record through its complete recorded history. |
| NF08 | Extract the full recorded lifecycle for each equipment unit. |
| NF08P | Show the full recorded history associated with every equipment unit. |
| NF09 | Extract the full recorded lifecycle for each furnace operation record. |
| NF09P | Build the complete recorded timeline of each individual furnace operation record. |
| NF10 | Extract the full recorded lifecycle for each rolling operation record. |
| NF10P | Show the whole recorded history of each individual rolling operation record. |
| NF11 | Extract the full recorded lifecycle for each finishing operation record. |
| NF11P | Trace the entire recorded history of every individual finishing operation record. |

</details>

## Gold Event Extraction Graph (EEG) Source Projection

![Entity Type candidates → Entity Representations → Activities](review/database/gold_evidence_graph.svg)

The diagram distinguishes core business entity concepts from supporting entity and event-record types. 
Each physical ER has exactly one currently annotated Entity Type candidate. Event-to-entity case attribution is separate from the source ER's provisional ET annotation; FK paths alone do not establish lifecycle membership.

**This is a source-level author-annotated projection, not an inferred EEG or a validated namespace-aware ET Gold.**
Gold SQL and record-level evidence are available in the linked inspection materials; their internal consistency does not validate the target namespace model. The current membership labels originate from the pre-namespace Gold; an independently validated ET/Identity Namespace Gold is a separate evaluation task.



**Entity-model status:** A physical table is one **Entity Representation (ER)**. Its displayed **Entity Type (ET) candidate** comes from legacy Gold annotations. ET semantic grouping and cross-ER instance identity resolution must be validated independently. FK reachability alone does not establish Case Attribution or Lifecycle Membership. [Terminology and namespace contract](../../docs/system/EEG_ENTITY_MODEL.md).

## Entity Type candidates vs. core business objects

Legacy identity groups (ET candidates): **12**; principal business object concepts in this domain: **6**. 
The core set is a candidate semantic grouping, not a rule for merging unrelated instances or Identity Namespaces.

**Core business concepts:** Equipment, Mother Material, Plate Piece, Rolling Instruction, Rolling Plan, Slab.

Supporting Gold types: Dimension Inspection, Finishing Operation Record, Furnace Operation Record, Quality Review, Rolling Operation Record, process_code.

## Evaluation evidence

- Gold SQL/CSV pairs executable and consistent: 50; compared event rows across questions: 7384.
- [Gold source inventory](review/gold_dfg/event_graph.md)
- [Question-level Gold DFGs](review/gold_dfg/README.md)
- [Editable Draw.io schema](docs/schema.drawio)

## Model input boundary

This README, diagrams, table previews and Gold evidence are reader/reviewer material. Use the [model-input manifest](evaluation/model_input_manifest.json) to identify evaluation inputs; do not supply Gold annotations or review materials to the model.
