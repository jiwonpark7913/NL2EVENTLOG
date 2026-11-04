# warehouseflow: questions and Gold DFGs

**EVALUATION ONLY — NEVER PROVIDE TO A MODEL.**

Source commit: `ed132438b2a634a39da997e733751ccf1aa6322c`. Open index.html for search, review notes and complete case traces.

Node counts = event occurrences. Edge counts = adjacent selected events within a case. Dashed amber edges touch timestamp ties and depend on the tie-break rule. DFGs are projections of the selected log, not causal models.

## R01 — Q1

Extract Goods Received events for each warehouse.

Events: **45** · Cases with events: **4** · Activities: **1** · Edges: **1**

![R01 Gold DFG](graphs/R01.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/R01.csv)

## R02 — Q2

For each warehouse, build a timeline of goods arriving at the warehouse.

Events: **45** · Cases with events: **4** · Activities: **1** · Edges: **1**

![R02 Gold DFG](graphs/R01.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/R02.csv)

## R03 — Q1

Extract Goods Dispatched events for each warehouse.

Events: **35** · Cases with events: **4** · Activities: **1** · Edges: **1**

![R03 Gold DFG](graphs/R03.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/R03.csv)

## R04 — Q2

For each warehouse, build a timeline of goods leaving the warehouse.

Events: **35** · Cases with events: **4** · Activities: **1** · Edges: **1**

![R04 Gold DFG](graphs/R03.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/R04.csv)

## R05 — Q3

Extract the full recorded lifecycle event log for each warehouse.

Events: **394** · Cases with events: **4** · Activities: **10** · Edges: **17**

![R05 Gold DFG](graphs/R05.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/R05.csv)

## R06 — Q4

Show the complete recorded history associated with each warehouse.

Events: **394** · Cases with events: **4** · Activities: **10** · Edges: **17**

![R06 Gold DFG](graphs/R05.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/R06.csv)

## R07 — Q1

Extract Warehouse Task Started events for each warehouse.

**No Gold log:** Only one task time is stored, defined as completion. Task start times are not recorded.

## OW01 — Q3

Extract the full recorded lifecycle event log for each warehouse.

Events: **394** · Cases with events: **4** · Activities: **10** · Edges: **17**

![OW01 Gold DFG](graphs/R05.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW01.csv)

## OW02 — Q3

Extract the full recorded lifecycle event log for each goods.

Events: **679** · Cases with events: **6** · Activities: **10** · Edges: **53**

![OW02 Gold DFG](graphs/OW02.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW02.csv)

## OW03 — Q3

Extract the full recorded lifecycle event log for each worker.

Events: **823** · Cases with events: **5** · Activities: **10** · Edges: **56**

![OW03 Gold DFG](graphs/OW03.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW03.csv)

## OW04 — Q3

Extract the full recorded lifecycle event log for each warehouse transaction.

Events: **394** · Cases with events: **80** · Activities: **10** · Edges: **8**

![OW04 Gold DFG](graphs/OW04.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW04.csv)

## OW05 — Q3

Extract the full recorded lifecycle event log for each goods transaction line.

Events: **679** · Cases with events: **138** · Activities: **10** · Edges: **8**

![OW05 Gold DFG](graphs/OW05.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW05.csv)

## OW06 — Q3

Extract the full recorded lifecycle event log for each worker transaction assignment.

Events: **823** · Cases with events: **167** · Activities: **10** · Edges: **8**

![OW06 Gold DFG](graphs/OW06.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW06.csv)

## TS01 — Q1

Extract Receiving Requested, Receiving Scheduled, Dispatch Requested, Dispatch Approved events for each warehouse transaction.

Events: **160** · Cases with events: **80** · Activities: **4** · Edges: **2**

![TS01 Gold DFG](graphs/TS01.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/TS01.csv)

## R07P — Q2

For each warehouse, build a timeline of the beginning of warehouse handling jobs.

**No Gold log:** Only one task time is stored, defined as completion. Task start times are not recorded.

## TS01P — Q2

For each warehouse transaction, build a timeline of a request to take goods into storage, an inbound handling appointment being arranged, a request to send goods out, permission being granted to send goods out.

Events: **160** · Cases with events: **80** · Activities: **4** · Edges: **2**

![TS01P Gold DFG](graphs/TS01.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/TS01P.csv)

## OW01P — Q4

Show the complete recorded history associated with each warehouse.

Events: **394** · Cases with events: **4** · Activities: **10** · Edges: **17**

![OW01P Gold DFG](graphs/R05.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW01P.csv)

## OW01E — Q1

Extract Receiving Requested, Goods Received, Goods Put Away events for each warehouse.

Events: **129** · Cases with events: **4** · Activities: **3** · Edges: **7**

![OW01E Gold DFG](graphs/OW01E.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW01E.csv)

## OW01EP — Q2

For each warehouse, build a timeline of a request to take goods into storage, goods arriving at the warehouse, goods being placed into their storage locations.

Events: **129** · Cases with events: **4** · Activities: **3** · Edges: **7**

![OW01EP Gold DFG](graphs/OW01E.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW01EP.csv)

## OW02P — Q4

Show the complete recorded history associated with each goods.

Events: **679** · Cases with events: **6** · Activities: **10** · Edges: **53**

![OW02P Gold DFG](graphs/OW02.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW02P.csv)

## OW02E — Q1

Extract Receiving Requested, Goods Received, Goods Put Away events for each goods.

Events: **226** · Cases with events: **6** · Activities: **3** · Edges: **7**

![OW02E Gold DFG](graphs/OW02E.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW02E.csv)

## OW02EP — Q2

For each goods, build a timeline of a request to take goods into storage, goods arriving at the warehouse, goods being placed into their storage locations.

Events: **226** · Cases with events: **6** · Activities: **3** · Edges: **7**

![OW02EP Gold DFG](graphs/OW02E.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW02EP.csv)

## OW03P — Q4

Show the complete recorded history associated with each worker.

Events: **823** · Cases with events: **5** · Activities: **10** · Edges: **56**

![OW03P Gold DFG](graphs/OW03.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW03P.csv)

## OW03E — Q1

Extract Receiving Requested, Goods Received, Goods Put Away events for each worker.

Events: **276** · Cases with events: **5** · Activities: **3** · Edges: **7**

![OW03E Gold DFG](graphs/OW03E.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW03E.csv)

## OW03EP — Q2

For each worker, build a timeline of a request to take goods into storage, goods arriving at the warehouse, goods being placed into their storage locations.

Events: **276** · Cases with events: **5** · Activities: **3** · Edges: **7**

![OW03EP Gold DFG](graphs/OW03E.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW03EP.csv)

## OW04P — Q4

Show the complete recorded history associated with each warehouse transaction.

Events: **394** · Cases with events: **80** · Activities: **10** · Edges: **8**

![OW04P Gold DFG](graphs/OW04.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW04P.csv)

## OW04E — Q1

Extract Receiving Requested, Goods Received, Goods Put Away events for each warehouse transaction.

Events: **129** · Cases with events: **45** · Activities: **3** · Edges: **2**

![OW04E Gold DFG](graphs/OW04E.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW04E.csv)

## OW04EP — Q2

For each warehouse transaction, build a timeline of a request to take goods into storage, goods arriving at the warehouse, goods being placed into their storage locations.

Events: **129** · Cases with events: **45** · Activities: **3** · Edges: **2**

![OW04EP Gold DFG](graphs/OW04E.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW04EP.csv)

## OW05P — Q4

Show the complete recorded history associated with each goods transaction line.

Events: **679** · Cases with events: **138** · Activities: **10** · Edges: **8**

![OW05P Gold DFG](graphs/OW05.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW05P.csv)

## OW05E — Q1

Extract Receiving Requested, Goods Received, Goods Put Away events for each goods transaction line.

Events: **226** · Cases with events: **79** · Activities: **3** · Edges: **2**

![OW05E Gold DFG](graphs/OW05E.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW05E.csv)

## OW05EP — Q2

For each goods transaction line, build a timeline of a request to take goods into storage, goods arriving at the warehouse, goods being placed into their storage locations.

Events: **226** · Cases with events: **79** · Activities: **3** · Edges: **2**

![OW05EP Gold DFG](graphs/OW05E.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW05EP.csv)

## OW06P — Q4

Show the complete recorded history associated with each worker transaction assignment.

Events: **823** · Cases with events: **167** · Activities: **10** · Edges: **8**

![OW06P Gold DFG](graphs/OW06.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW06P.csv)

## OW06E — Q1

Extract Receiving Requested, Goods Received, Goods Put Away events for each worker transaction assignment.

Events: **276** · Cases with events: **96** · Activities: **3** · Edges: **2**

![OW06E Gold DFG](graphs/OW06E.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW06E.csv)

## OW06EP — Q2

For each worker transaction assignment, build a timeline of a request to take goods into storage, goods arriving at the warehouse, goods being placed into their storage locations.

Events: **276** · Cases with events: **96** · Activities: **3** · Edges: **2**

![OW06EP Gold DFG](graphs/OW06E.svg)

[Gold CSV](../../../datasets/warehouseflow/private/gold_logs/OW06EP.csv)
