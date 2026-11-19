# PlateFlow New questions

## Question types and pairs

| Type | Questions | Answerable | Non-answerable | Avg. requested activity types |
| --- | --- | --- | --- | --- |
| Q1 | 10 | 10 | 0 | 3.00 |
| Q2 | 10 | 10 | 0 | 3.00 |
| Q3 | 10 | 10 | 0 | 14.60 |
| Q4 | 10 | 10 | 0 | 14.60 |

- Requested activity averages include unavailable requests. Process View includes its activity scope.
- Seeds are frozen before assistant-LLM paraphrasing; exact paired scopes and Gold are checked.

| ID | Type | Paired with | Answerability | Requested activities | Extractable activities | Question |
| --- | --- | --- | --- | --- | --- | --- |
| N01 | Q1 | N01P | answerable | 3 | 3 | For each slab, extract Slab Received, Slab Verified and Slab Released events. |
| N01P | Q2 | N01 | answerable | 3 | 3 | Build a timeline for each slab showing its receipt, verification and release. |
| N02 | Q1 | N02P | answerable | 3 | 3 | For each rolling plan, extract Rolling Plan Submitted, Rolling Plan Approved and Rolling Plan Released events. |
| N02P | Q2 | N02 | answerable | 3 | 3 | For every rolling plan, show when it was submitted, approved and released. |
| N03 | Q1 | N03P | answerable | 3 | 3 | For each rolling instruction, extract Rolling Instruction Issued, Heating Completed and Finish Rolling Completed events. |
| N03P | Q2 | N03 | answerable | 3 | 3 | For every rolling instruction, show its issue, the completion of heating and the completion of finish rolling. |
| N04 | Q1 | N04P | answerable | 5 | 5 | For each mother material, extract Furnace Charged, Heating Completed, Furnace Discharged, Rough Rolling Completed and Finish Rolling Completed events. |
| N04P | Q2 | N04 | answerable | 5 | 5 | For each mother material, show the completion of charging into the furnace, heating, discharge from the furnace, rough rolling and finish rolling. |
| N05 | Q1 | N05P | answerable | 3 | 3 | For each mother material, extract Heat Treatment Completed, Surface Finishing Completed and Dimensional Inspection Completed events, including those of its descendant plate pieces. |
| N05P | Q2 | N05 | answerable | 3 | 3 | For every mother material, show when heat treatment, surface finishing and dimensional inspection were completed, including work on all plate pieces derived from it. |
| N06 | Q1 | N06P | answerable | 3 | 3 | For each plate piece, extract Leveling Completed, Heat Treatment Completed and Surface Finishing Completed events, retaining repeated occurrences. |
| N06P | Q2 | N06 | answerable | 3 | 3 | For each plate piece, show every completed leveling, heat-treatment and surface-finishing operation, including repeat work. |
| N07 | Q1 | N07P | answerable | 2 | 2 | For each plate piece, extract Dimensional Inspection Completed and Plate Quality Review Completed events. |
| N07P | Q2 | N07 | answerable | 2 | 2 | For every plate piece, show when its dimensional inspections and quality reviews finished. |
| N08 | Q1 | N08P | answerable | 3 | 3 | For each plate piece, extract Plate Identified, Plate Released and Plate Packed events. |
| N08P | Q2 | N08 | answerable | 3 | 3 | For each plate piece, show when it was identified, released and packed. |
| N11 | Q1 | N11P | answerable | 2 | 2 | For each equipment unit, extract Heating Completed and Heat Treatment Completed events. |
| N11P | Q2 | N11 | answerable | 2 | 2 | For each equipment unit, show the completion of heating and of heat treatment. |
| N12 | Q1 | N12P | answerable | 3 | 3 | For each furnace operation record, extract Furnace Charged, Heating Completed and Furnace Discharged events. |
| N12P | Q2 | N12 | answerable | 3 | 3 | For every furnace operation record, show the recorded completion of furnace charging, heating or furnace discharge, as applicable. |
| NF01 | Q3 | NF01P | answerable | 29 | 29 | Extract the full recorded lifecycle for each slab. |
| NF01P | Q4 | NF01 | answerable | 29 | 29 | Show the complete recorded history of each slab. |
| NF02 | Q3 | NF02P | answerable | 26 | 26 | Extract the full recorded lifecycle for each rolling plan. |
| NF02P | Q4 | NF02 | answerable | 26 | 26 | Build the entire recorded timeline for every rolling plan. |
| NF03 | Q3 | NF03P | answerable | 23 | 23 | Extract the full recorded lifecycle for each rolling instruction. |
| NF03P | Q4 | NF03 | answerable | 23 | 23 | Trace each rolling instruction through its full recorded history. |
| NF04 | Q3 | NF04P | answerable | 22 | 22 | Extract the full recorded lifecycle for each mother material. |
| NF04P | Q4 | NF04 | answerable | 22 | 22 | Show the whole recorded lifecycle of every mother material. |
| NF05 | Q3 | NF05P | answerable | 12 | 12 | Extract the full recorded lifecycle for each plate piece. |
| NF05P | Q4 | NF05 | answerable | 12 | 12 | Build a complete timeline of the recorded history of each plate piece. |
| NF07 | Q3 | NF07P | answerable | 2 | 2 | Extract the full recorded lifecycle for each quality review record. |
| NF07P | Q4 | NF07 | answerable | 2 | 2 | Trace each individual quality review record through its complete recorded history. |
| NF08 | Q3 | NF08P | answerable | 16 | 16 | Extract the full recorded lifecycle for each equipment unit. |
| NF08P | Q4 | NF08 | answerable | 16 | 16 | Show the full recorded history associated with every equipment unit. |
| NF09 | Q3 | NF09P | answerable | 6 | 6 | Extract the full recorded lifecycle for each furnace operation record. |
| NF09P | Q4 | NF09 | answerable | 6 | 6 | Build the complete recorded timeline of each individual furnace operation record. |
| NF10 | Q3 | NF10P | answerable | 4 | 4 | Extract the full recorded lifecycle for each rolling operation record. |
| NF10P | Q4 | NF10 | answerable | 4 | 4 | Show the whole recorded history of each individual rolling operation record. |
| NF11 | Q3 | NF11P | answerable | 6 | 6 | Extract the full recorded lifecycle for each finishing operation record. |
| NF11P | Q4 | NF11 | answerable | 6 | 6 | Trace the entire recorded history of every individual finishing operation record. |
