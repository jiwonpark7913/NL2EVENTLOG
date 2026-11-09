# PlateFlow — Database and Gold Evidence Review

PlateFlow is a synthetic steel-plate production database with slab receiving, rolling preparation, furnace and rolling operations, finishing, inspection and quality review. It reflects industrial process concepts, not observed production records.

## Gold Evidence Graph

![Gold Object Types → Physical Tables → Activities](gold_evidence_graph.svg)

The diagram distinguishes core business object concepts from supporting entities and activity-record types. 
Each physical table belongs to exactly one Gold Object Type. An event can be associated with several business objects through foreign keys without its source table belonging to multiple OTs.

**This is an author-annotated Gold source projection, not an inferred Evidence Graph or a full provenance graph.**
Gold SQL and record-level evidence are available in the linked inspection materials.

## Relational Schema (SQL foreign keys)

![Relational database schema](schema.svg)

## Table inspector

| Physical table | Rows | Columns | Gold OT | First ten records |
|---|---:|---:|---|---|
| as_rolled_material | 26 | 6 | Mother Material | [Preview](tables/as_rolled_material.md) |
| dimension_inspection | 46 | 5 | Dimension Inspection | [Preview](tables/dimension_inspection.md) |
| equipment | 7 | 5 | Equipment | [Preview](tables/equipment.md) |
| finishing_operation_history | 130 | 7 | Finishing Operation Record | [Preview](tables/finishing_operation_history.md) |
| furnace_operation_history | 70 | 7 | Furnace Operation Record | [Preview](tables/furnace_operation_history.md) |
| planned_rolling_instruction | 28 | 6 | Rolling Plan | [Preview](tables/planned_rolling_instruction.md) |
| plate_material | 38 | 6 | Plate Piece | [Preview](tables/plate_material.md) |
| plate_quality_review | 46 | 5 | Quality Review | [Preview](tables/plate_quality_review.md) |
| process_code | 8 | 3 | process_code | [Preview](tables/process_code.md) |
| rolling_instruction | 26 | 3 | Rolling Instruction | [Preview](tables/rolling_instruction.md) |
| rolling_operation_history | 44 | 7 | Rolling Operation Record | [Preview](tables/rolling_operation_history.md) |
| slab_material | 30 | 6 | Slab | [Preview](tables/slab_material.md) |

## Gold object types vs. core business objects

Gold identity types: **12**; principal business object concepts in this domain: **6**. 
The core set is a conceptual layer for interpreting process scope, not a rule that forces unrelated PK domains to merge.

**Core business concepts:** Equipment, Mother Material, Plate Piece, Rolling Instruction, Rolling Plan, Slab.

Supporting Gold types: Dimension Inspection, Finishing Operation Record, Furnace Operation Record, Quality Review, Rolling Operation Record, process_code.

## Evaluation evidence

- Gold SQL/CSV pairs executable and consistent: 50; compared event rows across questions: 7384.
- [Gold source inventory](../gold_dfg/event_graph.md)
- [Question-level Gold DFGs](../gold_dfg/README.md)
- [Editable Draw.io schema](../../docs/schema.drawio)

