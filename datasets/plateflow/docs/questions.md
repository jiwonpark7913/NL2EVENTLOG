# PlateFlow New questions

## Question types and pairs

| Type | Questions | Answerable | Non-answerable | Avg. requested activity types |
| --- | --- | --- | --- | --- |
| Q1 | 16 | 14 | 2 | 2.44 |
| Q2 | 16 | 14 | 2 | 2.44 |
| Q3 | 11 | 11 | 0 | 7.00 |
| Q4 | 11 | 11 | 0 | 7.00 |

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
| N09 | Q1 | N09P | answerable | 1 | 1 | For each dimension inspection record, extract Dimensional Inspection Completed events. |
| N09P | Q2 | N09 | answerable | 1 | 1 | For each individual dimensional inspection record, show when the inspection finished. |
| N10 | Q1 | N10P | answerable | 1 | 1 | For each quality review record, extract Plate Quality Review Completed events. |
| N10P | Q2 | N10 | answerable | 1 | 1 | For each individual quality review record, show when the review finished. |
| N11 | Q1 | N11P | answerable | 2 | 2 | For each equipment unit, extract Heating Completed and Heat Treatment Completed events. |
| N11P | Q2 | N11 | answerable | 2 | 2 | For each equipment unit, show the completion of heating and of heat treatment. |
| N12 | Q1 | N12P | answerable | 3 | 3 | For each furnace operation record, extract Furnace Charged, Heating Completed and Furnace Discharged events. |
| N12P | Q2 | N12 | answerable | 3 | 3 | For every furnace operation record, show the recorded completion of furnace charging, heating or furnace discharge, as applicable. |
| N13 | Q1 | N13P | answerable | 2 | 2 | For each rolling operation record, extract Rough Rolling Completed and Finish Rolling Completed events. |
| N13P | Q2 | N13 | answerable | 2 | 2 | For every rolling operation record, show the recorded completion of rough rolling or finish rolling, as applicable. |
| N14 | Q1 | N14P | answerable | 3 | 3 | For each finishing operation record, extract Leveling Completed, Heat Treatment Completed and Surface Finishing Completed events. |
| N14P | Q2 | N14 | answerable | 3 | 3 | For every finishing operation record, show the recorded completion of leveling, heat treatment or surface finishing, as applicable. |
| N15 | Q1 | N15P | non_answerable | 1 | 0 | For each slab, extract Steel Cast events. |
| N15P | Q2 | N15 | non_answerable | 1 | 0 | For each slab, show when the steel was cast. |
| N16 | Q1 | N16P | non_answerable | 1 | 0 | For each plate piece, extract Truck Dispatched events. |
| N16P | Q2 | N16 | non_answerable | 1 | 0 | For each plate piece, show when its truck was dispatched. |
| NF01 | Q3 | NF01P | answerable | 20 | 20 | Extract the full recorded lifecycle for each slab. |
| NF01P | Q4 | NF01 | answerable | 20 | 20 | Show the complete recorded history of each slab. |
| NF02 | Q3 | NF02P | answerable | 4 | 4 | Extract the full recorded lifecycle for each rolling plan. |
| NF02P | Q4 | NF02 | answerable | 4 | 4 | Build the entire recorded timeline for every rolling plan. |
| NF03 | Q3 | NF03P | answerable | 14 | 14 | Extract the full recorded lifecycle for each rolling instruction. |
| NF03P | Q4 | NF03 | answerable | 14 | 14 | Trace each rolling instruction through its full recorded history. |
| NF04 | Q3 | NF04P | answerable | 13 | 13 | Extract the full recorded lifecycle for each mother material. |
| NF04P | Q4 | NF04 | answerable | 13 | 13 | Show the whole recorded lifecycle of every mother material. |
| NF05 | Q3 | NF05P | answerable | 8 | 8 | Extract the full recorded lifecycle for each plate piece. |
| NF05P | Q4 | NF05 | answerable | 8 | 8 | Build a complete timeline of the recorded history of each plate piece. |
| NF06 | Q3 | NF06P | answerable | 1 | 1 | Extract the full recorded lifecycle for each dimension inspection record. |
| NF06P | Q4 | NF06 | answerable | 1 | 1 | Show the entire recorded history of every individual dimensional inspection record. |
| NF07 | Q3 | NF07P | answerable | 1 | 1 | Extract the full recorded lifecycle for each quality review record. |
| NF07P | Q4 | NF07 | answerable | 1 | 1 | Trace each individual quality review record through its complete recorded history. |
| NF08 | Q3 | NF08P | answerable | 8 | 8 | Extract the full recorded lifecycle for each equipment unit. |
| NF08P | Q4 | NF08 | answerable | 8 | 8 | Show the full recorded history associated with every equipment unit. |
| NF09 | Q3 | NF09P | answerable | 3 | 3 | Extract the full recorded lifecycle for each furnace operation record. |
| NF09P | Q4 | NF09 | answerable | 3 | 3 | Build the complete recorded timeline of each individual furnace operation record. |
| NF10 | Q3 | NF10P | answerable | 2 | 2 | Extract the full recorded lifecycle for each rolling operation record. |
| NF10P | Q4 | NF10 | answerable | 2 | 2 | Show the whole recorded history of each individual rolling operation record. |
| NF11 | Q3 | NF11P | answerable | 3 | 3 | Extract the full recorded lifecycle for each finishing operation record. |
| NF11P | Q4 | NF11 | answerable | 3 | 3 | Trace the entire recorded history of every individual finishing operation record. |
