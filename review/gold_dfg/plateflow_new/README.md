# plateflow_new: questions and Gold DFGs

**EVALUATION ONLY — NEVER PROVIDE TO A MODEL.**

Source commit: `ed132438b2a634a39da997e733751ccf1aa6322c`. Open index.html for search, review notes and complete case traces.

Node counts = event occurrences. Edge counts = adjacent selected events within a case. Dashed amber edges touch timestamp ties and depend on the tie-break rule. DFGs are projections of the selected log, not causal models.

## N01 — Q1

For each slab, extract Slab Received, Slab Verified and Slab Released events.

Events: **86** · Cases with events: **30** · Activities: **3** · Edges: **2**

![N01 Gold DFG](graphs/N01.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N01.csv)

## N01P — Q2

Build a timeline for each slab showing its receipt, verification and release.

Events: **86** · Cases with events: **30** · Activities: **3** · Edges: **2**

![N01P Gold DFG](graphs/N01.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N01P.csv)

## N02 — Q1

For each rolling plan, extract Rolling Plan Submitted, Rolling Plan Approved and Rolling Plan Released events.

Events: **80** · Cases with events: **28** · Activities: **3** · Edges: **2**

![N02 Gold DFG](graphs/N02.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N02.csv)

## N02P — Q2

For every rolling plan, show when it was submitted, approved and released.

Events: **80** · Cases with events: **28** · Activities: **3** · Edges: **2**

![N02P Gold DFG](graphs/N02.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N02P.csv)

## N03 — Q1

For each rolling instruction, extract Rolling Instruction Issued, Heating Completed and Finish Rolling Completed events.

Events: **68** · Cases with events: **26** · Activities: **3** · Edges: **2**

![N03 Gold DFG](graphs/N03.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N03.csv)

## N03P — Q2

For every rolling instruction, show its issue, the completion of heating and the completion of finish rolling.

Events: **68** · Cases with events: **26** · Activities: **3** · Edges: **2**

![N03P Gold DFG](graphs/N03.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N03P.csv)

## N04 — Q1

For each mother material, extract Furnace Charged, Heating Completed, Furnace Discharged, Rough Rolling Completed and Finish Rolling Completed events.

Events: **110** · Cases with events: **24** · Activities: **5** · Edges: **4**

![N04 Gold DFG](graphs/N04.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N04.csv)

## N04P — Q2

For each mother material, show the completion of charging into the furnace, heating, discharge from the furnace, rough rolling and finish rolling.

Events: **110** · Cases with events: **24** · Activities: **5** · Edges: **4**

![N04P Gold DFG](graphs/N04.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N04P.csv)

## N05 — Q1

For each mother material, extract Heat Treatment Completed, Surface Finishing Completed and Dimensional Inspection Completed events, including those of its descendant plate pieces.

Events: **138** · Cases with events: **20** · Activities: **3** · Edges: **3**

![N05 Gold DFG](graphs/N05.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N05.csv)

## N05P — Q2

For every mother material, show when heat treatment, surface finishing and dimensional inspection were completed, including work on all plate pieces derived from it.

Events: **138** · Cases with events: **20** · Activities: **3** · Edges: **3**

![N05P Gold DFG](graphs/N05.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N05P.csv)

## N06 — Q1

For each plate piece, extract Leveling Completed, Heat Treatment Completed and Surface Finishing Completed events, retaining repeated occurrences.

Events: **130** · Cases with events: **38** · Activities: **3** · Edges: **3**

![N06 Gold DFG](graphs/N06.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N06.csv)

## N06P — Q2

For each plate piece, show every completed leveling, heat-treatment and surface-finishing operation, including repeat work.

Events: **130** · Cases with events: **38** · Activities: **3** · Edges: **3**

![N06P Gold DFG](graphs/N06.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N06P.csv)

## N07 — Q1

For each plate piece, extract Dimensional Inspection Completed and Plate Quality Review Completed events.

Events: **89** · Cases with events: **38** · Activities: **2** · Edges: **2**

![N07 Gold DFG](graphs/N07.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N07.csv)

## N07P — Q2

For every plate piece, show when its dimensional inspections and quality reviews finished.

Events: **89** · Cases with events: **38** · Activities: **2** · Edges: **2**

![N07P Gold DFG](graphs/N07.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N07P.csv)

## N08 — Q1

For each plate piece, extract Plate Identified, Plate Released and Plate Packed events.

Events: **99** · Cases with events: **38** · Activities: **3** · Edges: **2**

![N08 Gold DFG](graphs/N08.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N08.csv)

## N08P — Q2

For each plate piece, show when it was identified, released and packed.

Events: **99** · Cases with events: **38** · Activities: **3** · Edges: **2**

![N08P Gold DFG](graphs/N08.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N08P.csv)

## N09 — Q1

For each dimension inspection record, extract Dimensional Inspection Completed events.

Events: **46** · Cases with events: **46** · Activities: **1** · Edges: **0**

![N09 Gold DFG](graphs/N09.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N09.csv)

## N09P — Q2

For each individual dimensional inspection record, show when the inspection finished.

Events: **46** · Cases with events: **46** · Activities: **1** · Edges: **0**

![N09P Gold DFG](graphs/N09.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N09P.csv)

## N10 — Q1

For each quality review record, extract Plate Quality Review Completed events.

Events: **43** · Cases with events: **43** · Activities: **1** · Edges: **0**

![N10 Gold DFG](graphs/N10.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N10.csv)

## N10P — Q2

For each individual quality review record, show when the review finished.

Events: **43** · Cases with events: **43** · Activities: **1** · Edges: **0**

![N10P Gold DFG](graphs/N10.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N10P.csv)

## N11 — Q1

For each equipment unit, extract Heating Completed and Heat Treatment Completed events.

Events: **68** · Cases with events: **4** · Activities: **2** · Edges: **2**

![N11 Gold DFG](graphs/N11.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N11.csv)

## N11P — Q2

For each equipment unit, show the completion of heating and of heat treatment.

Events: **68** · Cases with events: **4** · Activities: **2** · Edges: **2**

![N11P Gold DFG](graphs/N11.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N11P.csv)

## N12 — Q1

For each furnace operation record, extract Furnace Charged, Heating Completed and Furnace Discharged events.

Events: **68** · Cases with events: **68** · Activities: **3** · Edges: **0**

![N12 Gold DFG](graphs/N12.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N12.csv)

## N12P — Q2

For every furnace operation record, show the recorded completion of furnace charging, heating or furnace discharge, as applicable.

Events: **68** · Cases with events: **68** · Activities: **3** · Edges: **0**

![N12P Gold DFG](graphs/N12.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N12P.csv)

## N13 — Q1

For each rolling operation record, extract Rough Rolling Completed and Finish Rolling Completed events.

Events: **42** · Cases with events: **42** · Activities: **2** · Edges: **0**

![N13 Gold DFG](graphs/N13.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N13.csv)

## N13P — Q2

For every rolling operation record, show the recorded completion of rough rolling or finish rolling, as applicable.

Events: **42** · Cases with events: **42** · Activities: **2** · Edges: **0**

![N13P Gold DFG](graphs/N13.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N13P.csv)

## N14 — Q1

For each finishing operation record, extract Leveling Completed, Heat Treatment Completed and Surface Finishing Completed events.

Events: **130** · Cases with events: **130** · Activities: **3** · Edges: **0**

![N14 Gold DFG](graphs/N14.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N14.csv)

## N14P — Q2

For every finishing operation record, show the recorded completion of leveling, heat treatment or surface finishing, as applicable.

Events: **130** · Cases with events: **130** · Activities: **3** · Edges: **0**

![N14P Gold DFG](graphs/N14.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/N14P.csv)

## N15 — Q1

For each slab, extract Steel Cast events.

**No Gold log:** No corresponding casting or dispatch records or actual times are stored.

## N15P — Q2

For each slab, show when the steel was cast.

**No Gold log:** No corresponding casting or dispatch records or actual times are stored.

## N16 — Q1

For each plate piece, extract Truck Dispatched events.

**No Gold log:** No corresponding casting or dispatch records or actual times are stored.

## N16P — Q2

For each plate piece, show when its truck was dispatched.

**No Gold log:** No corresponding casting or dispatch records or actual times are stored.

## NF01 — Q3

Extract the full recorded lifecycle for each slab.

Events: **620** · Cases with events: **30** · Activities: **20** · Edges: **23**

![NF01 Gold DFG](graphs/NF01.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/NF01.csv)

## NF01P — Q4

Show the complete recorded history of each slab.

Events: **620** · Cases with events: **30** · Activities: **20** · Edges: **23**

![NF01P Gold DFG](graphs/NF01.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/NF01P.csv)

## NF02 — Q3

Extract the full recorded lifecycle for each rolling plan.

Events: **106** · Cases with events: **28** · Activities: **4** · Edges: **3**

![NF02 Gold DFG](graphs/NF02.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/NF02.csv)

## NF02P — Q4

Build the entire recorded timeline for every rolling plan.

Events: **106** · Cases with events: **28** · Activities: **4** · Edges: **3**

![NF02P Gold DFG](graphs/NF02.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/NF02P.csv)

## NF03 — Q3

Extract the full recorded lifecycle for each rolling instruction.

Events: **454** · Cases with events: **26** · Activities: **14** · Edges: **17**

![NF03 Gold DFG](graphs/NF03.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/NF03.csv)

## NF03P — Q4

Trace each rolling instruction through its full recorded history.

Events: **454** · Cases with events: **26** · Activities: **14** · Edges: **17**

![NF03P Gold DFG](graphs/NF03.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/NF03P.csv)

## NF04 — Q3

Extract the full recorded lifecycle for each mother material.

Events: **428** · Cases with events: **24** · Activities: **13** · Edges: **16**

![NF04 Gold DFG](graphs/NF04.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/NF04.csv)

## NF04P — Q4

Show the whole recorded lifecycle of every mother material.

Events: **428** · Cases with events: **24** · Activities: **13** · Edges: **16**

![NF04P Gold DFG](graphs/NF04.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/NF04P.csv)

## NF05 — Q3

Extract the full recorded lifecycle for each plate piece.

Events: **318** · Cases with events: **38** · Activities: **8** · Edges: **8**

![NF05 Gold DFG](graphs/NF05.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/NF05.csv)

## NF05P — Q4

Build a complete timeline of the recorded history of each plate piece.

Events: **318** · Cases with events: **38** · Activities: **8** · Edges: **8**

![NF05P Gold DFG](graphs/NF05.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/NF05P.csv)

## NF06 — Q3

Extract the full recorded lifecycle for each dimension inspection record.

Events: **46** · Cases with events: **46** · Activities: **1** · Edges: **0**

![NF06 Gold DFG](graphs/N09.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/NF06.csv)

## NF06P — Q4

Show the entire recorded history of every individual dimensional inspection record.

Events: **46** · Cases with events: **46** · Activities: **1** · Edges: **0**

![NF06P Gold DFG](graphs/N09.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/NF06P.csv)

## NF07 — Q3

Extract the full recorded lifecycle for each quality review record.

Events: **43** · Cases with events: **43** · Activities: **1** · Edges: **0**

![NF07 Gold DFG](graphs/N10.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/NF07.csv)

## NF07P — Q4

Trace each individual quality review record through its complete recorded history.

Events: **43** · Cases with events: **43** · Activities: **1** · Edges: **0**

![NF07P Gold DFG](graphs/N10.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/NF07P.csv)

## NF08 — Q3

Extract the full recorded lifecycle for each equipment unit.

Events: **240** · Cases with events: **6** · Activities: **8** · Edges: **11**

![NF08 Gold DFG](graphs/NF08.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/NF08.csv)

## NF08P — Q4

Show the full recorded history associated with every equipment unit.

Events: **240** · Cases with events: **6** · Activities: **8** · Edges: **11**

![NF08P Gold DFG](graphs/NF08.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/NF08P.csv)

## NF09 — Q3

Extract the full recorded lifecycle for each furnace operation record.

Events: **68** · Cases with events: **68** · Activities: **3** · Edges: **0**

![NF09 Gold DFG](graphs/N12.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/NF09.csv)

## NF09P — Q4

Build the complete recorded timeline of each individual furnace operation record.

Events: **68** · Cases with events: **68** · Activities: **3** · Edges: **0**

![NF09P Gold DFG](graphs/N12.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/NF09P.csv)

## NF10 — Q3

Extract the full recorded lifecycle for each rolling operation record.

Events: **42** · Cases with events: **42** · Activities: **2** · Edges: **0**

![NF10 Gold DFG](graphs/N13.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/NF10.csv)

## NF10P — Q4

Show the whole recorded history of each individual rolling operation record.

Events: **42** · Cases with events: **42** · Activities: **2** · Edges: **0**

![NF10P Gold DFG](graphs/N13.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/NF10P.csv)

## NF11 — Q3

Extract the full recorded lifecycle for each finishing operation record.

Events: **130** · Cases with events: **130** · Activities: **3** · Edges: **0**

![NF11 Gold DFG](graphs/N14.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/NF11.csv)

## NF11P — Q4

Trace the entire recorded history of every individual finishing operation record.

Events: **130** · Cases with events: **130** · Activities: **3** · Edges: **0**

![NF11P Gold DFG](graphs/N14.svg)

[Gold CSV](../../../datasets/plateflow_new/private/gold_logs/NF11P.csv)
