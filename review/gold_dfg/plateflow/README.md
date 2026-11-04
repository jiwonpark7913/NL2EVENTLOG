# plateflow: questions and Gold DFGs

**EVALUATION ONLY — NEVER PROVIDE TO A MODEL.**

Source commit: `ed132438b2a634a39da997e733751ccf1aa6322c`. Open index.html for search, review notes and complete case traces.

Node counts = event occurrences. Edge counts = adjacent selected events within a case. Dashed amber edges touch timestamp ties and depend on the tie-break rule. DFGs are projections of the selected log, not causal models.

## V01 — Q1

Extract Reheating Started, Rolling Completed, Crop Shear Passed events for each as-rolled mother material.

Events: **72** · Cases with events: **30** · Activities: **3** · Edges: **2**

![V01 Gold DFG](graphs/V01.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/V01.csv)

## V02 — Q2

For each as-rolled mother material, build a timeline of the material entering the reheating furnace, rolling finishing, the mother plate passing the crop shear.

Events: **72** · Cases with events: **30** · Activities: **3** · Edges: **2**

![V02 Gold DFG](graphs/V01.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/V02.csv)

## V03 — Q1

Extract Inspection Failed, Heat Treatment Completed, Inspection Passed events for each as-rolled mother material.

Events: **75** · Cases with events: **18** · Activities: **3** · Edges: **7**

![V03 Gold DFG](graphs/V03.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/V03.csv)

## V04 — Q2

For each as-rolled mother material, build a timeline of a quality check rejecting the material, heat treatment finishing, a quality check accepting the material.

Events: **75** · Cases with events: **18** · Activities: **3** · Edges: **7**

![V04 Gold DFG](graphs/V03.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/V04.csv)

## V05 — Q3

Extract the full recorded lifecycle event log for each as-rolled mother material.

Events: **1108** · Cases with events: **36** · Activities: **39** · Edges: **63**

![V05 Gold DFG](graphs/V05.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/V05.csv)

## V06 — Q4

Show the complete recorded history associated with each as-rolled mother material.

Events: **1108** · Cases with events: **36** · Activities: **39** · Edges: **63**

![V06 Gold DFG](graphs/V05.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/V06.csv)

## V07 — Q1

Extract Cutting Instruction Released, Split Cutting Completed, Dimensional Inspection Completed events for each as-rolled mother material.

Events: **75** · Cases with events: **18** · Activities: **3** · Edges: **3**

![V07 Gold DFG](graphs/V07.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/V07.csv)

## V08 — Q1

Extract Slab Cast events for each slab.

**No Gold log:** No casting event times in this selected schema.

## OPV01 — Q3

Extract the full recorded lifecycle event log for each slab.

Events: **1108** · Cases with events: **36** · Activities: **39** · Edges: **63**

![OPV01 Gold DFG](graphs/OPV01.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV01.csv)

## OPV02 — Q3

Extract the full recorded lifecycle event log for each rolling plan.

Events: **174** · Cases with events: **36** · Activities: **5** · Edges: **5**

![OPV02 Gold DFG](graphs/OPV02.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV02.csv)

## OPV03 — Q3

Extract the full recorded lifecycle event log for each rolling instruction.

Events: **150** · Cases with events: **36** · Activities: **5** · Edges: **4**

![OPV03 Gold DFG](graphs/OPV03.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV03.csv)

## OPV04 — Q3

Extract the full recorded lifecycle event log for each mother material.

Events: **1108** · Cases with events: **36** · Activities: **39** · Edges: **63**

![OPV04 Gold DFG](graphs/V05.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV04.csv)

## OPV05 — Q3

Extract the full recorded lifecycle event log for each furnace tracking record.

Events: **133** · Cases with events: **30** · Activities: **5** · Edges: **4**

![OPV05 Gold DFG](graphs/OPV05.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV05.csv)

## OPV06 — Q3

Extract the full recorded lifecycle event log for each cutting instruction.

Events: **87** · Cases with events: **18** · Activities: **5** · Edges: **4**

![OPV06 Gold DFG](graphs/OPV06.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV06.csv)

## OPV07 — Q3

Extract the full recorded lifecycle event log for each cut plate piece.

Events: **336** · Cases with events: **39** · Activities: **10** · Edges: **12**

![OPV07 Gold DFG](graphs/OPV07.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV07.csv)

## OPV08 — Q3

Extract the full recorded lifecycle event log for each material operation record.

Events: **216** · Cases with events: **216** · Activities: **9** · Edges: **0**

![OPV08 Gold DFG](graphs/OPV08.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV08.csv)

## TS01 — Q1

Extract Plate Quality Review Started, Plate Packing Started events for each cut plate piece.

Events: **72** · Cases with events: **39** · Activities: **2** · Edges: **1**

![TS01 Gold DFG](graphs/TS01.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/TS01.csv)

## V07P — Q2

For each as-rolled mother material, build a timeline of the cutting work order being issued, the mother plate being cut into separate pieces, the dimensions of a cut piece being checked.

Events: **75** · Cases with events: **18** · Activities: **3** · Edges: **3**

![V07P Gold DFG](graphs/V07.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/V07P.csv)

## V08P — Q2

For each slab, build a timeline of the initial casting of a slab.

**No Gold log:** No casting event times in this selected schema.

## TS01P — Q2

For each cut plate piece, build a timeline of a finished plate quality review beginning, packaging of a finished plate beginning.

Events: **72** · Cases with events: **39** · Activities: **2** · Edges: **1**

![TS01P Gold DFG](graphs/TS01.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/TS01P.csv)

## OPV01P — Q4

Show the complete recorded history associated with each slab.

Events: **1108** · Cases with events: **36** · Activities: **39** · Edges: **63**

![OPV01P Gold DFG](graphs/OPV01.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV01P.csv)

## OPV01E — Q1

Extract Slab Received, Slab Quality Checked, Slab Released for Rolling events for each slab.

Events: **102** · Cases with events: **36** · Activities: **3** · Edges: **2**

![OPV01E Gold DFG](graphs/OPV01E.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV01E.csv)

## OPV01EP — Q2

For each slab, build a timeline of an incoming slab being received, the quality of a slab being checked, a slab being authorized for rolling.

Events: **102** · Cases with events: **36** · Activities: **3** · Edges: **2**

![OPV01EP Gold DFG](graphs/OPV01E.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV01EP.csv)

## OPV02P — Q4

Show the complete recorded history associated with each rolling plan.

Events: **174** · Cases with events: **36** · Activities: **5** · Edges: **5**

![OPV02P Gold DFG](graphs/OPV02.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV02P.csv)

## OPV02E — Q1

Extract Rolling Instruction Released, Rolling Plan Approved, Rolling Plan Created events for each rolling plan.

Events: **108** · Cases with events: **36** · Activities: **3** · Edges: **2**

![OPV02E Gold DFG](graphs/OPV02E.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV02E.csv)

## OPV02EP — Q2

For each rolling plan, build a timeline of the rolling work order being issued, a rolling schedule being authorized, a rolling schedule being prepared.

Events: **108** · Cases with events: **36** · Activities: **3** · Edges: **2**

![OPV02EP Gold DFG](graphs/OPV02E.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV02EP.csv)

## OPV03P — Q4

Show the complete recorded history associated with each rolling instruction.

Events: **150** · Cases with events: **36** · Activities: **5** · Edges: **4**

![OPV03P Gold DFG](graphs/OPV03.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV03P.csv)

## OPV03E — Q1

Extract Rolling Instruction Acknowledged, Rolling Instruction Closed, Rolling Instruction Released events for each rolling instruction.

Events: **92** · Cases with events: **36** · Activities: **3** · Edges: **2**

![OPV03E Gold DFG](graphs/OPV03E.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV03E.csv)

## OPV03EP — Q2

For each rolling instruction, build a timeline of the rolling team acknowledging its work order, the rolling work order being closed, the rolling work order being issued.

Events: **92** · Cases with events: **36** · Activities: **3** · Edges: **2**

![OPV03EP Gold DFG](graphs/OPV03E.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV03EP.csv)

## OPV04P — Q4

Show the complete recorded history associated with each mother material.

Events: **1108** · Cases with events: **36** · Activities: **39** · Edges: **63**

![OPV04P Gold DFG](graphs/V05.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV04P.csv)

## OPV04E — Q1

Extract Slab Received, Slab Quality Checked, Slab Released for Rolling events for each mother material.

Events: **102** · Cases with events: **36** · Activities: **3** · Edges: **2**

![OPV04E Gold DFG](graphs/OPV04E.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV04E.csv)

## OPV04EP — Q2

For each mother material, build a timeline of an incoming slab being received, the quality of a slab being checked, a slab being authorized for rolling.

Events: **102** · Cases with events: **36** · Activities: **3** · Edges: **2**

![OPV04EP Gold DFG](graphs/OPV04E.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV04EP.csv)

## OPV05P — Q4

Show the complete recorded history associated with each furnace tracking record.

Events: **133** · Cases with events: **30** · Activities: **5** · Edges: **4**

![OPV05P Gold DFG](graphs/OPV05.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV05P.csv)

## OPV05E — Q1

Extract Furnace Charge Assigned, Furnace Charge Confirmed, Furnace Discharge Confirmed events for each furnace tracking record.

Events: **79** · Cases with events: **30** · Activities: **3** · Edges: **2**

![OPV05E Gold DFG](graphs/OPV05E.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV05E.csv)

## OPV05EP — Q2

For each furnace tracking record, build a timeline of a furnace charge being assigned, the furnace charge being confirmed, the material leaving the furnace being confirmed.

Events: **79** · Cases with events: **30** · Activities: **3** · Edges: **2**

![OPV05EP Gold DFG](graphs/OPV05E.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV05EP.csv)

## OPV06P — Q4

Show the complete recorded history associated with each cutting instruction.

Events: **87** · Cases with events: **18** · Activities: **5** · Edges: **4**

![OPV06P Gold DFG](graphs/OPV06.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV06P.csv)

## OPV06E — Q1

Extract Cutting Instruction Acknowledged, Cutting Instruction Closed, Cutting Instruction Released events for each cutting instruction.

Events: **51** · Cases with events: **18** · Activities: **3** · Edges: **2**

![OPV06E Gold DFG](graphs/OPV06E.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV06E.csv)

## OPV06EP — Q2

For each cutting instruction, build a timeline of the cutting team acknowledging its work order, the cutting work order being closed, the cutting work order being issued.

Events: **51** · Cases with events: **18** · Activities: **3** · Edges: **2**

![OPV06EP Gold DFG](graphs/OPV06E.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV06EP.csv)

## OPV07P — Q4

Show the complete recorded history associated with each cut plate piece.

Events: **336** · Cases with events: **39** · Activities: **10** · Edges: **12**

![OPV07P Gold DFG](graphs/OPV07.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV07P.csv)

## OPV07E — Q1

Extract Dimensional Inspection Completed, Heat Treatment Completed, Inspection Failed events for each cut plate piece.

Events: **75** · Cases with events: **39** · Activities: **3** · Edges: **3**

![OPV07E Gold DFG](graphs/OPV07E.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV07E.csv)

## OPV07EP — Q2

For each cut plate piece, build a timeline of the dimensions of a cut piece being checked, heat treatment finishing, a quality check rejecting the material.

Events: **75** · Cases with events: **39** · Activities: **3** · Edges: **3**

![OPV07EP Gold DFG](graphs/OPV07E.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV07EP.csv)

## OPV08P — Q4

Show the complete recorded history associated with each material operation record.

Events: **216** · Cases with events: **216** · Activities: **9** · Edges: **0**

![OPV08P Gold DFG](graphs/OPV08.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV08P.csv)

## OPV08E — Q1

Extract Cooling Completed, Heat Treatment Completed, Heating Completed events for each material operation record.

Events: **66** · Cases with events: **66** · Activities: **3** · Edges: **0**

![OPV08E Gold DFG](graphs/OPV08E.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV08E.csv)

## OPV08EP — Q2

For each material operation record, build a timeline of cooling finishing, heat treatment finishing, furnace heating finishing.

Events: **66** · Cases with events: **66** · Activities: **3** · Edges: **0**

![OPV08EP Gold DFG](graphs/OPV08E.svg)

[Gold CSV](../../../datasets/plateflow/private/gold_logs/OPV08EP.csv)
