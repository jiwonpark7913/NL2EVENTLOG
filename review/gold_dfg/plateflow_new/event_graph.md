# plateflow_new · Event graph inventory

**EVALUATION ONLY.** [Back to question and DFG review](README.md).

This page shows the authored benchmark graph. Table bindings identify where events are recorded. Object links identify which activities are attributed to an object, including activities recorded in other tables.

Each documented object view is listed as a singleton OT for review. Tables without a documented object view have no assigned OT here.

## Tables and event sources

| Table | Event classification | Carrier column | Selected event timestamps | Physical object (table · PK) | OT group | Events produced |
|---|---|---|---|---|---|---|
| `as_rolled_material` | Non-event | — | — | `as_rolled_material` · `material_id` | Mother Material | — |
| `dimension_inspection` | Event · non-carrier | — | `inspected_at` | `dimension_inspection` · `inspection_id` | Dimension Inspection | Dimensional Inspection Completed |
| `equipment` | Non-event | — | — | `equipment` · `equipment_id` | Equipment | — |
| `finishing_operation_history` | Event · carrier | `operation_code` | `finished_at` | `finishing_operation_history` · `operation_id` | Finishing Operation Record | Heat Treatment Completed, Leveling Completed, Surface Finishing Completed |
| `furnace_operation_history` | Event · carrier | `operation_code` | `finished_at` | `furnace_operation_history` · `operation_id` | Furnace Operation Record | Furnace Charged, Furnace Discharged, Heating Completed |
| `planned_rolling_instruction` | Event · non-carrier | — | `approved_at`, `released_at`, `submitted_at` | `planned_rolling_instruction` · `plan_id` | Rolling Plan | Rolling Plan Approved, Rolling Plan Released, Rolling Plan Submitted |
| `plate_material` | Event · non-carrier | — | `identified_at`, `packed_at`, `released_at` | `plate_material` · `plate_id` | Plate Piece | Plate Identified, Plate Packed, Plate Released |
| `plate_quality_review` | Event · non-carrier | — | `finished_at` | `plate_quality_review` · `review_id` | Quality Review | Plate Quality Review Completed |
| `process_code` | Non-event | — | — | `process_code` · `process_group`, `code` | — | — |
| `rolling_instruction` | Event · non-carrier | — | `issued_at` | `rolling_instruction` · `instruction_id` | Rolling Instruction | Rolling Instruction Issued |
| `rolling_operation_history` | Event · carrier | `phase_code` | `finished_at` | `rolling_operation_history` · `operation_id` | Rolling Operation Record | Finish Rolling Completed, Rough Rolling Completed |
| `slab_material` | Event · non-carrier | — | `received_at`, `released_at`, `verified_at` | `slab_material` · `slab_id` | Slab | Slab Received, Slab Released, Slab Verified |

## Object types and attributed activities

| OT group | Member physical objects | Activities linked to OT |
|---|---|---|
| Slab | `slab_material` | Dimensional Inspection Completed, Finish Rolling Completed, Furnace Charged, Furnace Discharged, Heat Treatment Completed, Heating Completed, Leveling Completed, Plate Identified, Plate Packed, Plate Quality Review Completed, Plate Released, Rolling Instruction Issued, Rolling Plan Approved, Rolling Plan Released, Rolling Plan Submitted, Rough Rolling Completed, Slab Received, Slab Released, Slab Verified, Surface Finishing Completed |
| Rolling Plan | `planned_rolling_instruction` | Rolling Instruction Issued, Rolling Plan Approved, Rolling Plan Released, Rolling Plan Submitted |
| Rolling Instruction | `rolling_instruction` | Dimensional Inspection Completed, Finish Rolling Completed, Furnace Charged, Furnace Discharged, Heat Treatment Completed, Heating Completed, Leveling Completed, Plate Identified, Plate Packed, Plate Quality Review Completed, Plate Released, Rolling Instruction Issued, Rough Rolling Completed, Surface Finishing Completed |
| Mother Material | `as_rolled_material` | Dimensional Inspection Completed, Finish Rolling Completed, Furnace Charged, Furnace Discharged, Heat Treatment Completed, Heating Completed, Leveling Completed, Plate Identified, Plate Packed, Plate Quality Review Completed, Plate Released, Rough Rolling Completed, Surface Finishing Completed |
| Plate Piece | `plate_material` | Dimensional Inspection Completed, Heat Treatment Completed, Leveling Completed, Plate Identified, Plate Packed, Plate Quality Review Completed, Plate Released, Surface Finishing Completed |
| Dimension Inspection | `dimension_inspection` | Dimensional Inspection Completed |
| Quality Review | `plate_quality_review` | Plate Quality Review Completed |
| Equipment | `equipment` | Finish Rolling Completed, Furnace Charged, Furnace Discharged, Heat Treatment Completed, Heating Completed, Leveling Completed, Rough Rolling Completed, Surface Finishing Completed |
| Furnace Operation Record | `furnace_operation_history` | Furnace Charged, Furnace Discharged, Heating Completed |
| Rolling Operation Record | `rolling_operation_history` | Finish Rolling Completed, Rough Rolling Completed |
| Finishing Operation Record | `finishing_operation_history` | Heat Treatment Completed, Leveling Completed, Surface Finishing Completed |

## Physical objects and attributed activities

| Physical object | OT group | Activities linked to this object |
|---|---|---|
| `as_rolled_material` | Mother Material | Dimensional Inspection Completed, Finish Rolling Completed, Furnace Charged, Furnace Discharged, Heat Treatment Completed, Heating Completed, Leveling Completed, Plate Identified, Plate Packed, Plate Quality Review Completed, Plate Released, Rough Rolling Completed, Surface Finishing Completed |
| `dimension_inspection` | Dimension Inspection | Dimensional Inspection Completed |
| `equipment` | Equipment | Finish Rolling Completed, Furnace Charged, Furnace Discharged, Heat Treatment Completed, Heating Completed, Leveling Completed, Rough Rolling Completed, Surface Finishing Completed |
| `finishing_operation_history` | Finishing Operation Record | Heat Treatment Completed, Leveling Completed, Surface Finishing Completed |
| `furnace_operation_history` | Furnace Operation Record | Furnace Charged, Furnace Discharged, Heating Completed |
| `planned_rolling_instruction` | Rolling Plan | Rolling Instruction Issued, Rolling Plan Approved, Rolling Plan Released, Rolling Plan Submitted |
| `plate_material` | Plate Piece | Dimensional Inspection Completed, Heat Treatment Completed, Leveling Completed, Plate Identified, Plate Packed, Plate Quality Review Completed, Plate Released, Surface Finishing Completed |
| `plate_quality_review` | Quality Review | Plate Quality Review Completed |
| `process_code` | — | No authored object view |
| `rolling_instruction` | Rolling Instruction | Dimensional Inspection Completed, Finish Rolling Completed, Furnace Charged, Furnace Discharged, Heat Treatment Completed, Heating Completed, Leveling Completed, Plate Identified, Plate Packed, Plate Quality Review Completed, Plate Released, Rolling Instruction Issued, Rough Rolling Completed, Surface Finishing Completed |
| `rolling_operation_history` | Rolling Operation Record | Finish Rolling Completed, Rough Rolling Completed |
| `slab_material` | Slab | Dimensional Inspection Completed, Finish Rolling Completed, Furnace Charged, Furnace Discharged, Heat Treatment Completed, Heating Completed, Leveling Completed, Plate Identified, Plate Packed, Plate Quality Review Completed, Plate Released, Rolling Instruction Issued, Rolling Plan Approved, Rolling Plan Released, Rolling Plan Submitted, Rough Rolling Completed, Slab Received, Slab Released, Slab Verified, Surface Finishing Completed |
