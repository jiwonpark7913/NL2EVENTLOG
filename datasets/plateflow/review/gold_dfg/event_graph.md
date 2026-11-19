# PlateFlow — Gold source inventory

**Legacy author annotations.** Physical storage is described as Tables and Keys. A table may identify or reference several Entity Types through different keys; a single Entity can appear in several tables. The displayed type labels are legacy author annotations, not validated semantic ET truth. Type classification, Entity identity resolution, and event attribution are separate decisions.

| Physical table | Entity Type candidate | Gold activity source labels |
|---|---|---|
| as_rolled_material | Mother Material | — |
| dimension_inspection | Dimension Inspection | Dimensional Inspection Completed |
| equipment | Equipment | — |
| finishing_operation_history | Finishing Operation Record | Heat Treatment Completed, Heat Treatment Started, Leveling Completed, Leveling Started, Surface Finishing Completed, Surface Finishing Started |
| furnace_operation_history | Furnace Operation Record | Furnace Charged, Furnace Charging Started, Furnace Discharge Started, Furnace Discharged, Heating Completed, Heating Started |
| planned_rolling_instruction | Rolling Plan | Rolling Plan Approved, Rolling Plan Released, Rolling Plan Submitted |
| plate_material | Plate Piece | Plate Identified, Plate Packed, Plate Released |
| plate_quality_review | Quality Review | Plate Quality Review Completed, Plate Quality Review Started |
| process_code | process_code | — |
| rolling_instruction | Rolling Instruction | Rolling Instruction Issued |
| rolling_operation_history | Rolling Operation Record | Finish Rolling Completed, Finish Rolling Started, Rough Rolling Completed, Rough Rolling Started |
| slab_material | Slab | Slab Received, Slab Released, Slab Verified |

This is a source-binding projection. The model is not given this file.

[Gold diagram](../database/gold_evidence_graph.svg) · [Gold DFGs](README.md)

[Table/key review inventory](entity_model_candidates.json) — reviewer-only, not model input.
