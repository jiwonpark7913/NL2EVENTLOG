# plateflow — Question definitions and Gold review

[Interactive question / DFG / source-row review](../review/gold_dfg/index.html)

Q1: explicit; Q2: explicit paraphrase; Q3: lifecycle; Q4: lifecycle paraphrase. Pairs retain the same scope and Gold log. Revised requests and paraphrases are author edits following the 2026-11-20 audit.

| ID | Type | Pair | Case | Process focus | Answerability | Supported activities | Observed activities | Events | Question |
|---|---|---|---|---|---|---:|---:|---:|---|
| N01 | Q1 | N01P | Slab |  | answerable | 3 | 3 | 86 | For each slab, extract Slab Received, Slab Verified and Slab Released events. |
| N01P | Q2 | N01 | Slab |  | answerable | 3 | 3 | 86 | Build a timeline for each slab showing its receipt, verification and release. |
| N02 | Q1 | N02P | Rolling Plan |  | answerable | 3 | 3 | 80 | For each rolling plan, extract Rolling Plan Submitted, Rolling Plan Approved and Rolling Plan Released events. |
| N02P | Q2 | N02 | Rolling Plan |  | answerable | 3 | 3 | 80 | For every rolling plan, show when it was submitted, approved and released. |
| N03 | Q1 | N03P | Rolling Instruction |  | answerable | 3 | 3 | 68 | For each rolling instruction, extract Rolling Instruction Issued, Heating Completed and Finish Rolling Completed events. |
| N03P | Q2 | N03 | Rolling Instruction |  | answerable | 3 | 3 | 68 | For every rolling instruction, show its issue, the completion of heating and the completion of finish rolling. |
| N04 | Q1 | N04P | Mother Material |  | answerable | 5 | 5 | 110 | For each mother material, extract Furnace Charged, Heating Completed, Furnace Discharged, Rough Rolling Completed and Finish Rolling Completed events. |
| N04P | Q2 | N04 | Mother Material |  | answerable | 5 | 5 | 110 | For each mother material, show the completion of charging into the furnace, heating, discharge from the furnace, rough rolling and finish rolling. |
| N05 | Q1 | N05P | Mother Material |  | answerable | 3 | 3 | 138 | For each mother material, extract Heat Treatment Completed, Surface Finishing Completed and Dimensional Inspection Completed events, including those of its descendant plate pieces. |
| N05P | Q2 | N05 | Mother Material |  | answerable | 3 | 3 | 138 | For every mother material, show when heat treatment, surface finishing and dimensional inspection were completed, including work on all plate pieces derived from it. |
| N06 | Q1 | N06P | Plate Piece |  | answerable | 3 | 3 | 130 | For each plate piece, extract Leveling Completed, Heat Treatment Completed and Surface Finishing Completed events, retaining repeated occurrences. |
| N06P | Q2 | N06 | Plate Piece |  | answerable | 3 | 3 | 130 | For each plate piece, show every completed leveling, heat-treatment and surface-finishing operation, including repeat work. |
| N07 | Q1 | N07P | Plate Piece |  | answerable | 2 | 2 | 89 | For each plate piece, extract Dimensional Inspection Completed and Plate Quality Review Completed events. |
| N07P | Q2 | N07 | Plate Piece |  | answerable | 2 | 2 | 89 | For every plate piece, show when its dimensional inspections and quality reviews finished. |
| N08 | Q1 | N08P | Plate Piece |  | answerable | 3 | 3 | 99 | For each plate piece, extract Plate Identified, Plate Released and Plate Packed events. |
| N08P | Q2 | N08 | Plate Piece |  | answerable | 3 | 3 | 99 | For each plate piece, show when it was identified, released and packed. |
| N11 | Q1 | N11P | Equipment |  | answerable | 2 | 2 | 68 | For each equipment unit, extract Heating Completed and Heat Treatment Completed events. |
| N11P | Q2 | N11 | Equipment |  | answerable | 2 | 2 | 68 | For each equipment unit, show the completion of heating and of heat treatment. |
| N12 | Q1 | N12P | Mother Material |  | answerable | 3 | 3 | 68 | For each mother material, extract Furnace Charged, Heating Completed and Furnace Discharged events. |
| N12P | Q2 | N12 | Mother Material |  | answerable | 3 | 3 | 68 | For every mother material, show when furnace charging, heating and furnace discharge finished. |
| NF01 | Q3 | NF01P | Slab |  | answerable | 29 | 29 | 910 | Extract the full recorded lifecycle for each slab. |
| NF01P | Q4 | NF01 | Slab |  | answerable | 29 | 29 | 910 | Show the complete recorded history of each slab. |
| NF02 | Q3 | NF02P | Rolling Plan |  | answerable | 26 | 26 | 824 | Extract the full recorded lifecycle for each rolling plan. |
| NF02P | Q4 | NF02 | Rolling Plan |  | answerable | 26 | 26 | 824 | Build the entire recorded timeline for every rolling plan. |
| NF03 | Q3 | NF03P | Rolling Instruction |  | answerable | 23 | 23 | 744 | Extract the full recorded lifecycle for each rolling instruction. |
| NF03P | Q4 | NF03 | Rolling Instruction |  | answerable | 23 | 23 | 744 | Trace each rolling instruction through its full recorded history. |
| NF04 | Q3 | NF04P | Mother Material |  | answerable | 22 | 22 | 718 | Extract the full recorded lifecycle for each mother material. |
| NF04P | Q4 | NF04 | Mother Material |  | answerable | 22 | 22 | 718 | Show the whole recorded lifecycle of every mother material. |
| NF05 | Q3 | NF05P | Plate Piece |  | answerable | 12 | 12 | 494 | Extract the full recorded lifecycle for each plate piece. |
| NF05P | Q4 | NF05 | Plate Piece |  | answerable | 12 | 12 | 494 | Build a complete timeline of the recorded history of each plate piece. |
| NF07 | Q3 | NF07P | Quality Review |  | answerable | 2 | 2 | 89 | Extract the full recorded lifecycle for each quality review record. |
| NF07P | Q4 | NF07 | Quality Review |  | answerable | 2 | 2 | 89 | Trace each individual quality review record through its complete recorded history. |
| NF08 | Q3 | NF08P | Equipment |  | answerable | 16 | 16 | 484 | Extract the full recorded lifecycle for each equipment unit. |
| NF08P | Q4 | NF08 | Equipment |  | answerable | 16 | 16 | 484 | Show the full recorded history associated with every equipment unit. |
| NF09 | Q3 | NF09P | Furnace Operation Record |  | answerable | 6 | 6 | 138 | Extract the full recorded lifecycle for each furnace operation record. |
| NF09P | Q4 | NF09 | Furnace Operation Record |  | answerable | 6 | 6 | 138 | Build the complete recorded timeline of each individual furnace operation record. |
| NF10 | Q3 | NF10P | Rolling Operation Record |  | answerable | 4 | 4 | 86 | Extract the full recorded lifecycle for each rolling operation record. |
| NF10P | Q4 | NF10 | Rolling Operation Record |  | answerable | 4 | 4 | 86 | Show the whole recorded history of each individual rolling operation record. |
| NF11 | Q3 | NF11P | Finishing Operation Record |  | answerable | 6 | 6 | 260 | Extract the full recorded lifecycle for each finishing operation record. |
| NF11P | Q4 | NF11 | Finishing Operation Record |  | answerable | 6 | 6 | 260 | Trace the entire recorded history of every individual finishing operation record. |
