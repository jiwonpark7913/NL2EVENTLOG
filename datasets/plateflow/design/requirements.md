# PlateFlow Requirements

- A fictional steelworks maintains distinct records for slab materials, planned rolling instructions, released rolling instructions, furnace-charge tracking, as-rolled mother materials, cutting/finishing instructions, individual cut Plate materials and operation history.
- Preserve milestone timestamps on material records and repeated operation occurrences with start/completion times in history.
- Separate planned, actual and technical times.
- Model one-to-many mother-to-piece relationships.
- Extract mother-material lifecycle logs including descendant-piece operations exactly once.
- Use a table that defines the synthetic process-code meanings.

- The physical separation follows selected tables in the supplied Korean manufacturer metadata.
- Relationship counts, keys, types, code values and execution rules are newly specified assumptions.

## Authored lifecycle extension

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
