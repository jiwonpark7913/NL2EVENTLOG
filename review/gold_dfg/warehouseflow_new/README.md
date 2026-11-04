# warehouseflow_new: questions and Gold DFGs

**EVALUATION ONLY — NEVER PROVIDE TO A MODEL.**

Source commit: `ed132438b2a634a39da997e733751ccf1aa6322c`. Open index.html for search, review notes and complete case traces.

Node counts = event occurrences. Edge counts = adjacent selected events within a case. Dashed amber edges touch timestamp ties and depend on the tie-break rule. DFGs are projections of the selected log, not causal models.

## W01 — Q1

For each receiving request, extract Receiving Request Submitted events.

Events: **26** · Cases with events: **26** · Activities: **1** · Edges: **0**

![W01 Gold DFG](graphs/W01.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W01.csv)

## W01P — Q2

For every receiving request, show when it was submitted.

Events: **26** · Cases with events: **26** · Activities: **1** · Edges: **0**

![W01P Gold DFG](graphs/W01.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W01P.csv)

## W02 — Q1

For each receipt record, extract Receipt Registered events.

Events: **23** · Cases with events: **23** · Activities: **1** · Edges: **0**

![W02 Gold DFG](graphs/W02.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W02.csv)

## W02P — Q2

For each individual receipt record, show when the receipt was registered.

Events: **23** · Cases with events: **23** · Activities: **1** · Edges: **0**

![W02P Gold DFG](graphs/W02.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W02P.csv)

## W03 — Q1

For each dispatch order, extract Dispatch Requested and Dispatch Approved events.

Events: **38** · Cases with events: **20** · Activities: **2** · Edges: **1**

![W03 Gold DFG](graphs/W03.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W03.csv)

## W03P — Q2

For every dispatch order, show when dispatch was requested and when it was approved.

Events: **38** · Cases with events: **20** · Activities: **2** · Edges: **1**

![W03P Gold DFG](graphs/W03.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W03P.csv)

## W04 — Q1

For each stock audit, extract Stock Audit Started and Stock Audit Completed events.

Events: **17** · Cases with events: **9** · Activities: **2** · Edges: **1**

![W04 Gold DFG](graphs/W04.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W04.csv)

## W04P — Q2

Show when each stock audit began and when it finished.

Events: **17** · Cases with events: **9** · Activities: **2** · Edges: **1**

![W04P Gold DFG](graphs/W04.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W04P.csv)

## W05 — Q1

For each stock movement record, extract Goods Received and Goods Dispatched events.

Events: **39** · Cases with events: **39** · Activities: **2** · Edges: **0**

![W05 Gold DFG](graphs/W05.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W05.csv)

## W05P — Q2

For every stock movement record, show the recorded receipt into stock or dispatch from stock, as applicable.

Events: **39** · Cases with events: **39** · Activities: **2** · Edges: **0**

![W05P Gold DFG](graphs/W05.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W05P.csv)

## W06 — Q1

For each request action record, extract Request Checked, Request Held and Request Released events.

Events: **56** · Cases with events: **56** · Activities: **3** · Edges: **0**

![W06 Gold DFG](graphs/W06.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W06.csv)

## W06P — Q2

For each individual request action record, show the checking, holding or releasing action that was recorded.

Events: **56** · Cases with events: **56** · Activities: **3** · Edges: **0**

![W06P Gold DFG](graphs/W06.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W06P.csv)

## W07 — Q1

For each warehouse task, extract Putaway Started, Putaway Completed, Picking Started, Picking Completed, Packing Started and Packing Completed events.

Events: **123** · Cases with events: **63** · Activities: **6** · Edges: **3**

![W07 Gold DFG](graphs/W07.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W07.csv)

## W07P — Q2

For every warehouse task, show the recorded beginnings and completions of putaway, picking or packing, as applicable.

Events: **123** · Cases with events: **63** · Activities: **6** · Edges: **3**

![W07P Gold DFG](graphs/W07.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W07P.csv)

## W08 — Q1

For each handling record, extract Unloading Started, Unloading Completed, Loading Started and Loading Completed events.

Events: **80** · Cases with events: **41** · Activities: **4** · Edges: **2**

![W08 Gold DFG](graphs/W08.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W08.csv)

## W08P — Q2

For each handling record, show when unloading or loading began and finished, as applicable.

Events: **80** · Cases with events: **41** · Activities: **4** · Edges: **2**

![W08P Gold DFG](graphs/W08.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W08P.csv)

## W09 — Q1

For each warehouse, extract Stock Audit Started, Stock Audit Completed, Putaway Started, Putaway Completed, Loading Started and Loading Completed events.

Events: **94** · Cases with events: **3** · Activities: **6** · Edges: **10**

![W09 Gold DFG](graphs/W09.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W09.csv)

## W09P — Q2

For each warehouse, show the beginnings and completions of its stock audits, putaway work and loading work.

Events: **94** · Cases with events: **3** · Activities: **6** · Edges: **10**

![W09P Gold DFG](graphs/W09.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W09P.csv)

## W10 — Q1

For each receiving request, extract Unloading Started, Unloading Completed, Receipt Registered, Goods Received, Putaway Started and Putaway Completed events.

Events: **137** · Cases with events: **24** · Activities: **6** · Edges: **5**

![W10 Gold DFG](graphs/W10.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W10.csv)

## W10P — Q2

For every receiving request, show the start and completion of unloading, registration of the receipt, receipt into warehouse stock, and the start and completion of putaway.

Events: **137** · Cases with events: **24** · Activities: **6** · Edges: **5**

![W10P Gold DFG](graphs/W10.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W10P.csv)

## W11 — Q1

For each dispatch order, extract Picking Started, Picking Completed, Packing Started, Packing Completed, Loading Started, Loading Completed and Goods Dispatched events.

Events: **128** · Cases with events: **18** · Activities: **7** · Edges: **7**

![W11 Gold DFG](graphs/W11.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W11.csv)

## W11P — Q2

For each dispatch order, show when picking, packing and loading began and finished, together with the dispatch of goods from stock.

Events: **128** · Cases with events: **18** · Activities: **7** · Edges: **7**

![W11P Gold DFG](graphs/W11.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W11P.csv)

## W12 — Q1

For each worker, extract Stock Audit Started, Stock Audit Completed, Picking Started and Picking Completed events.

Events: **61** · Cases with events: **6** · Activities: **4** · Edges: **5**

![W12 Gold DFG](graphs/W12.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W12.csv)

## W12P — Q2

For every worker, show when their stock audits and picking work began and finished.

Events: **61** · Cases with events: **6** · Activities: **4** · Edges: **5**

![W12P Gold DFG](graphs/W12.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W12P.csv)

## W13 — Q1

For each goods type, extract Goods Received and Goods Dispatched events.

Events: **39** · Cases with events: **6** · Activities: **2** · Edges: **3**

![W13 Gold DFG](graphs/W13.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W13.csv)

## W13P — Q2

For each goods type, show its recorded receipts into warehouse stock and dispatches from stock.

Events: **39** · Cases with events: **6** · Activities: **2** · Edges: **3**

![W13P Gold DFG](graphs/W13.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W13P.csv)

## W14 — Q1

For each receipt record, extract Receipt Registered and Goods Received events.

Events: **46** · Cases with events: **23** · Activities: **2** · Edges: **1**

![W14 Gold DFG](graphs/W14.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W14.csv)

## W14P — Q2

For every individual receipt record, show its registration and the corresponding receipt of goods into stock.

Events: **46** · Cases with events: **23** · Activities: **2** · Edges: **1**

![W14P Gold DFG](graphs/W14.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W14P.csv)

## W15 — Q1

For each warehouse, extract Invoice Paid events.

**No Gold log:** No corresponding invoicing or carrier delivery records exist in this DB.

## W15P — Q2

For every warehouse, show when its invoices were paid.

**No Gold log:** No corresponding invoicing or carrier delivery records exist in this DB.

## W16 — Q1

For each dispatch order, extract Customer Delivery Completed events.

**No Gold log:** No corresponding invoicing or carrier delivery records exist in this DB.

## W16P — Q2

For each dispatch order, show when delivery to the customer was completed.

**No Gold log:** No corresponding invoicing or carrier delivery records exist in this DB.

## WF01 — Q3

Extract the full recorded lifecycle for each warehouse.

Events: **402** · Cases with events: **3** · Activities: **21** · Edges: **29**

![WF01 Gold DFG](graphs/WF01.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF01.csv)

## WF01P — Q4

Show the complete recorded history of each warehouse.

Events: **402** · Cases with events: **3** · Activities: **21** · Edges: **29**

![WF01P Gold DFG](graphs/WF01.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF01P.csv)

## WF02 — Q3

Extract the full recorded lifecycle for each goods type.

Events: **385** · Cases with events: **6** · Activities: **19** · Edges: **25**

![WF02 Gold DFG](graphs/WF02.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF02.csv)

## WF02P — Q4

Build the entire recorded timeline associated with every goods type.

Events: **385** · Cases with events: **6** · Activities: **19** · Edges: **25**

![WF02P Gold DFG](graphs/WF02.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF02P.csv)

## WF03 — Q3

Extract the full recorded lifecycle for each worker.

Events: **299** · Cases with events: **6** · Activities: **16** · Edges: **24**

![WF03 Gold DFG](graphs/WF03.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF03.csv)

## WF03P — Q4

Show every worker's full recorded history.

Events: **299** · Cases with events: **6** · Activities: **16** · Edges: **24**

![WF03P Gold DFG](graphs/WF03.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF03P.csv)

## WF04 — Q3

Extract the full recorded lifecycle for each receiving request.

Events: **219** · Cases with events: **26** · Activities: **10** · Edges: **10**

![WF04 Gold DFG](graphs/WF04.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF04.csv)

## WF04P — Q4

Trace each receiving request through its complete recorded lifecycle.

Events: **219** · Cases with events: **26** · Activities: **10** · Edges: **10**

![WF04P Gold DFG](graphs/WF04.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF04P.csv)

## WF05 — Q3

Extract the full recorded lifecycle for each receipt record.

Events: **46** · Cases with events: **23** · Activities: **2** · Edges: **1**

![WF05 Gold DFG](graphs/W14.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF05.csv)

## WF05P — Q4

Show the entire recorded history associated with each individual receipt record.

Events: **46** · Cases with events: **23** · Activities: **2** · Edges: **1**

![WF05P Gold DFG](graphs/W14.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF05P.csv)

## WF06 — Q3

Extract the full recorded lifecycle for each dispatch order.

Events: **166** · Cases with events: **20** · Activities: **9** · Edges: **9**

![WF06 Gold DFG](graphs/WF06.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF06.csv)

## WF06P — Q4

Build a complete recorded timeline for every dispatch order.

Events: **166** · Cases with events: **20** · Activities: **9** · Edges: **9**

![WF06P Gold DFG](graphs/WF06.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF06P.csv)

## WF07 — Q3

Extract the full recorded lifecycle for each stock audit.

Events: **17** · Cases with events: **9** · Activities: **2** · Edges: **1**

![WF07 Gold DFG](graphs/W04.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF07.csv)

## WF07P — Q4

Show the full recorded history of each stock audit.

Events: **17** · Cases with events: **9** · Activities: **2** · Edges: **1**

![WF07P Gold DFG](graphs/W04.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF07P.csv)

## WF08 — Q3

Extract the full recorded lifecycle for each stock movement record.

Events: **39** · Cases with events: **39** · Activities: **2** · Edges: **0**

![WF08 Gold DFG](graphs/W05.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF08.csv)

## WF08P — Q4

Trace each individual stock movement record through its entire recorded history.

Events: **39** · Cases with events: **39** · Activities: **2** · Edges: **0**

![WF08P Gold DFG](graphs/W05.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF08P.csv)

## WF09 — Q3

Extract the full recorded lifecycle for each request action record.

Events: **56** · Cases with events: **56** · Activities: **3** · Edges: **0**

![WF09 Gold DFG](graphs/W06.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF09.csv)

## WF09P — Q4

Show the complete recorded history of every individual request action record.

Events: **56** · Cases with events: **56** · Activities: **3** · Edges: **0**

![WF09P Gold DFG](graphs/W06.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF09P.csv)

## WF10 — Q3

Extract the full recorded lifecycle for each warehouse task.

Events: **123** · Cases with events: **63** · Activities: **6** · Edges: **3**

![WF10 Gold DFG](graphs/W07.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF10.csv)

## WF10P — Q4

Build the full recorded lifecycle of each warehouse task.

Events: **123** · Cases with events: **63** · Activities: **6** · Edges: **3**

![WF10P Gold DFG](graphs/W07.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF10P.csv)

## WF11 — Q3

Extract the full recorded lifecycle for each handling record.

Events: **80** · Cases with events: **41** · Activities: **4** · Edges: **2**

![WF11 Gold DFG](graphs/W08.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF11.csv)

## WF11P — Q4

Trace every individual handling record through its complete recorded history.

Events: **80** · Cases with events: **41** · Activities: **4** · Edges: **2**

![WF11P Gold DFG](graphs/W08.svg)

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF11P.csv)
