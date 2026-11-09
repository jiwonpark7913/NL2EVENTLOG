# Plateflow — Gold source inventory

**Author annotations.** One identity OT per physical table; event-to-object attribution is a separate relation.

| Physical table | Gold Object Type | Gold activity source labels |
|---|---|---|
| as_rolled_material | Mother Material | — |
| dimension_inspection | Dimension Inspection | Dimensional Inspection Completed |
| equipment | Equipment | — |
| finishing_operation_history | Finishing Operation Record | Heat Treatment Completed, Leveling Completed, Surface Finishing Completed |
| furnace_operation_history | Furnace Operation Record | Furnace Charged, Furnace Discharged, Heating Completed |
| planned_rolling_instruction | Rolling Plan | Rolling Plan Approved, Rolling Plan Released, Rolling Plan Submitted |
| plate_material | Plate Piece | Plate Identified, Plate Packed, Plate Released |
| plate_quality_review | Quality Review | Plate Quality Review Completed |
| process_code | process_code | — |
| rolling_instruction | Rolling Instruction | Rolling Instruction Issued |
| rolling_operation_history | Rolling Operation Record | Finish Rolling Completed, Rough Rolling Completed |
| slab_material | Slab | Slab Received, Slab Released, Slab Verified |

This is a source-binding projection. The model is not given this file.

[Gold diagram](../database/gold_evidence_graph.svg) · [Gold DFGs](README.md)
