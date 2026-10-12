# Question types and paired requests

- Q1 and Q2 specify a case concept and activities. Q2 uses alternate wording for the exact same scope.
- Q3 and Q4 specify a case concept without listing activities. Their Gold scope uses the declared task catalog.
- Every Q2 is paired with Q1; every Q4 is paired with Q3. Pairs have identical ES, Gold CSV and answerability.
- Answerability is independent of type. Existing unavailable actions remain unavailable and receive Q2 pairs. No evidence is fabricated.
- `answerability` is an evaluation annotation: exclude it from model inputs. `question_type` defines the taxonomy; legacy `category` records question origin.
- These are authored English paraphrases; there is no claim of model-generated linguistic diversity.
- Existing IDs are preserved. Added E/EP IDs select explicit activity subsets; added P IDs are paired paraphrases.

| Type | Included information | Answerability | Meaning |
|---|---|---|---|
| Q1 Explicit | Process View + Activities | O / X | Case concept and exact business activity labels |
| Q2 Paraphrased | Process View + Activities | O / X | Same scope as Q1, expressed with alternate business wording |
| Q3 Full Lifecycle | Process View | O / X | Case concept only; default recorded scope from catalog |
| Q4 Full Lifecycle Paraphrased | Process View | O / X | Alternate wording of Q3 with identical default scope |

| ID | Type | Paired with | Answerability | Question |
|---|---|---|---|---|
| V01 | Q1 Explicit | — | O | Extract Reheating Started, Rolling Completed, Crop Shear Passed events for each as-rolled mother material. |
| V02 | Q2 Paraphrased | V01 | O | For each as-rolled mother material, build a timeline of the material entering the reheating furnace, rolling finishing, the mother plate passing the crop shear. |
| V03 | Q1 Explicit | — | O | Extract Inspection Failed, Heat Treatment Completed, Inspection Passed events for each as-rolled mother material. |
| V04 | Q2 Paraphrased | V03 | O | For each as-rolled mother material, build a timeline of a quality check rejecting the material, heat treatment finishing, a quality check accepting the material. |
| V05 | Q3 Full Lifecycle | — | O | Extract the full recorded lifecycle event log for each as-rolled mother material. |
| V06 | Q4 Full Lifecycle Paraphrased | V05 | O | Show the complete recorded history associated with each as-rolled mother material. |
| V07 | Q1 Explicit | — | O | Extract Cutting Instruction Released, Split Cutting Completed, Dimensional Inspection Completed events for each as-rolled mother material. |
| V08 | Q1 Explicit | — | X | Extract Slab Cast events for each slab. |
| OPV01 | Q3 Full Lifecycle | — | O | Extract the full recorded lifecycle event log for each slab. |
| OPV02 | Q3 Full Lifecycle | — | O | Extract the full recorded lifecycle event log for each rolling plan. |
| OPV03 | Q3 Full Lifecycle | — | O | Extract the full recorded lifecycle event log for each rolling instruction. |
| OPV04 | Q3 Full Lifecycle | — | O | Extract the full recorded lifecycle event log for each mother material. |
| OPV05 | Q3 Full Lifecycle | — | O | Extract the full recorded lifecycle event log for each furnace tracking record. |
| OPV06 | Q3 Full Lifecycle | — | O | Extract the full recorded lifecycle event log for each cutting instruction. |
| OPV07 | Q3 Full Lifecycle | — | O | Extract the full recorded lifecycle event log for each cut plate piece. |
| OPV08 | Q3 Full Lifecycle | — | O | Extract the full recorded lifecycle event log for each material operation record. |
| V07P | Q2 Paraphrased | V07 | O | For each as-rolled mother material, build a timeline of the cutting work order being issued, the mother plate being cut into separate pieces, the dimensions of a cut piece being checked. |
| V08P | Q2 Paraphrased | V08 | X | For each slab, build a timeline of the initial casting of a slab. |
| OPV01P | Q4 Full Lifecycle Paraphrased | OPV01 | O | Show the complete recorded history associated with each slab. |
| OPV01E | Q1 Explicit | — | O | Extract Slab Received, Slab Quality Checked, Slab Released for Rolling events for each slab. |
| OPV01EP | Q2 Paraphrased | OPV01E | O | For each slab, build a timeline of an incoming slab being received, the quality of a slab being checked, a slab being authorized for rolling. |
| OPV02P | Q4 Full Lifecycle Paraphrased | OPV02 | O | Show the complete recorded history associated with each rolling plan. |
| OPV02E | Q1 Explicit | — | O | Extract Rolling Instruction Released, Rolling Plan Approved, Rolling Plan Created events for each rolling plan. |
| OPV02EP | Q2 Paraphrased | OPV02E | O | For each rolling plan, build a timeline of the rolling work order being issued, a rolling schedule being authorized, a rolling schedule being prepared. |
| OPV03P | Q4 Full Lifecycle Paraphrased | OPV03 | O | Show the complete recorded history associated with each rolling instruction. |
| OPV03E | Q1 Explicit | — | O | Extract Rolling Instruction Acknowledged, Rolling Instruction Closed, Rolling Instruction Released events for each rolling instruction. |
| OPV03EP | Q2 Paraphrased | OPV03E | O | For each rolling instruction, build a timeline of the rolling team acknowledging its work order, the rolling work order being closed, the rolling work order being issued. |
| OPV04P | Q4 Full Lifecycle Paraphrased | OPV04 | O | Show the complete recorded history associated with each mother material. |
| OPV04E | Q1 Explicit | — | O | Extract Slab Received, Slab Quality Checked, Slab Released for Rolling events for each mother material. |
| OPV04EP | Q2 Paraphrased | OPV04E | O | For each mother material, build a timeline of an incoming slab being received, the quality of a slab being checked, a slab being authorized for rolling. |
| OPV05P | Q4 Full Lifecycle Paraphrased | OPV05 | O | Show the complete recorded history associated with each furnace tracking record. |
| OPV05E | Q1 Explicit | — | O | Extract Furnace Charge Assigned, Furnace Charge Confirmed, Furnace Discharge Confirmed events for each furnace tracking record. |
| OPV05EP | Q2 Paraphrased | OPV05E | O | For each furnace tracking record, build a timeline of a furnace charge being assigned, the furnace charge being confirmed, the material leaving the furnace being confirmed. |
| OPV06P | Q4 Full Lifecycle Paraphrased | OPV06 | O | Show the complete recorded history associated with each cutting instruction. |
| OPV06E | Q1 Explicit | — | O | Extract Cutting Instruction Acknowledged, Cutting Instruction Closed, Cutting Instruction Released events for each cutting instruction. |
| OPV06EP | Q2 Paraphrased | OPV06E | O | For each cutting instruction, build a timeline of the cutting team acknowledging its work order, the cutting work order being closed, the cutting work order being issued. |
| OPV07P | Q4 Full Lifecycle Paraphrased | OPV07 | O | Show the complete recorded history associated with each cut plate piece. |
| OPV07E | Q1 Explicit | — | O | Extract Dimensional Inspection Completed, Heat Treatment Completed, Inspection Failed events for each cut plate piece. |
| OPV07EP | Q2 Paraphrased | OPV07E | O | For each cut plate piece, build a timeline of the dimensions of a cut piece being checked, heat treatment finishing, a quality check rejecting the material. |
| OPV08P | Q4 Full Lifecycle Paraphrased | OPV08 | O | Show the complete recorded history associated with each material operation record. |
| OPV08E | Q1 Explicit | — | O | Extract Cooling Completed, Heat Treatment Completed, Inspection Failed events for each material operation record. |
| OPV08EP | Q2 Paraphrased | OPV08E | O | For each material operation record, build a timeline of cooling finishing, heat treatment finishing, a quality check rejecting the material. |
