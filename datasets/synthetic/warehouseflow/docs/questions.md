# warehouseflow — Question definitions and Gold review

[Interactive question / DFG / source-row review](../review/gold_dfg/index.html)

Q1: explicit; Q2: explicit paraphrase; Q3: lifecycle; Q4: lifecycle paraphrase. Pairs retain the same scope and Gold log. Revised requests and paraphrases are author edits following the 2026-11-20 audit.

| ID | Type | Pair | Case | Process focus | Answerability | Supported activities | Observed activities | Events | Question |
|---|---|---|---|---|---|---:|---:|---:|---|
| W03 | Q1 | W03P | Dispatch Order |  | answerable | 2 | 2 | 38 | For each dispatch order, extract Dispatch Requested and Dispatch Approved events. |
| W03P | Q2 | W03 | Dispatch Order |  | answerable | 2 | 2 | 38 | For every dispatch order, show when dispatch was requested and when it was approved. |
| W06 | Q1 | W06P | Receiving Request |  | answerable | 3 | 3 | 56 | For each receiving request, extract Request Checked, Request Held and Request Released events. |
| W06P | Q2 | W06 | Receiving Request |  | answerable | 3 | 3 | 56 | For every receiving request, show when it was checked, put on hold and released from hold. |
| W07 | Q1 | W07P | Warehouse Task |  | answerable | 6 | 6 | 123 | For each warehouse task, extract Putaway Started, Putaway Completed, Picking Started, Picking Completed, Packing Started and Packing Completed events. |
| W07P | Q2 | W07 | Warehouse Task |  | answerable | 6 | 6 | 123 | For every warehouse task, show the recorded beginnings and completions of putaway, picking or packing, as applicable. |
| W08 | Q1 | W08P | Handling Record |  | answerable | 4 | 4 | 80 | For each handling record, extract Unloading Started, Unloading Completed, Loading Started and Loading Completed events. |
| W08P | Q2 | W08 | Handling Record |  | answerable | 4 | 4 | 80 | For each handling record, show when unloading or loading began and finished, as applicable. |
| W09 | Q1 | W09P | Warehouse |  | answerable | 6 | 6 | 94 | For each warehouse, extract Stock Audit Started, Stock Audit Completed, Putaway Started, Putaway Completed, Loading Started and Loading Completed events. |
| W09P | Q2 | W09 | Warehouse |  | answerable | 6 | 6 | 94 | For each warehouse, show the beginnings and completions of its stock audits, putaway work and loading work. |
| W10 | Q1 | W10P | Receiving Request |  | answerable | 6 | 6 | 137 | For each receiving request, extract Unloading Started, Unloading Completed, Receipt Registered, Goods Received, Putaway Started and Putaway Completed events. |
| W10P | Q2 | W10 | Receiving Request |  | answerable | 6 | 6 | 137 | For every receiving request, show the start and completion of unloading, registration of the receipt, receipt into warehouse stock, and the start and completion of putaway. |
| W11 | Q1 | W11P | Dispatch Order |  | answerable | 7 | 7 | 128 | For each dispatch order, extract Picking Started, Picking Completed, Packing Started, Packing Completed, Loading Started, Loading Completed and Goods Dispatched events. |
| W11P | Q2 | W11 | Dispatch Order |  | answerable | 7 | 7 | 128 | For each dispatch order, show when picking, packing and loading began and finished, together with the dispatch of goods from stock. |
| W12 | Q1 | W12P | Worker |  | answerable | 4 | 4 | 61 | For each worker, extract Stock Audit Started, Stock Audit Completed, Picking Started and Picking Completed events. |
| W12P | Q2 | W12 | Worker |  | answerable | 4 | 4 | 61 | For every worker, show when their stock audits and picking work began and finished. |
| W13 | Q1 | W13P | Goods |  | answerable | 2 | 2 | 39 | For each goods type, extract Goods Received and Goods Dispatched events. |
| W13P | Q2 | W13 | Goods |  | answerable | 2 | 2 | 39 | For each goods type, show its recorded receipts into warehouse stock and dispatches from stock. |
| W14 | Q1 | W14P | Receipt |  | answerable | 2 | 2 | 46 | For each receipt record, extract Receipt Registered and Goods Received events. |
| W14P | Q2 | W14 | Receipt |  | answerable | 2 | 2 | 46 | For every individual receipt record, show its registration and the corresponding receipt of goods into stock. |
| WF01 | Q3 | WF01P | Warehouse |  | answerable | 21 | 21 | 402 | Extract the full recorded lifecycle for each warehouse. |
| WF01P | Q4 | WF01 | Warehouse |  | answerable | 21 | 21 | 402 | Show the complete recorded history of each warehouse. |
| WF02 | Q3 | WF02P | Goods |  | answerable | 19 | 19 | 385 | Extract the full recorded lifecycle for each goods type. |
| WF02P | Q4 | WF02 | Goods |  | answerable | 19 | 19 | 385 | Build the entire recorded timeline associated with every goods type. |
| WF03 | Q3 | WF03P | Worker |  | answerable | 17 | 17 | 322 | Extract the full recorded lifecycle for each worker. |
| WF03P | Q4 | WF03 | Worker |  | answerable | 17 | 17 | 322 | Show every worker's full recorded history. |
| WF04 | Q3 | WF04P | Receiving Request |  | answerable | 10 | 10 | 219 | Extract the full recorded lifecycle for each receiving request. |
| WF04P | Q4 | WF04 | Receiving Request |  | answerable | 10 | 10 | 219 | Trace each receiving request through its complete recorded lifecycle. |
| WF05 | Q3 | WF05P | Receipt |  | answerable | 2 | 2 | 46 | Extract the full recorded lifecycle for each receipt record. |
| WF05P | Q4 | WF05 | Receipt |  | answerable | 2 | 2 | 46 | Show the entire recorded history associated with each individual receipt record. |
| WF06 | Q3 | WF06P | Dispatch Order |  | answerable | 9 | 9 | 166 | Extract the full recorded lifecycle for each dispatch order. |
| WF06P | Q4 | WF06 | Dispatch Order |  | answerable | 9 | 9 | 166 | Build a complete recorded timeline for every dispatch order. |
| WF08 | Q3 | WF08P | Goods | inbound receiving | answerable | 10 | 10 | 219 | Extract the full recorded inbound-receiving lifecycle for each goods type. |
| WF08P | Q4 | WF08 | Goods | inbound receiving | answerable | 10 | 10 | 219 | For every goods type, reconstruct the complete recorded history of its inbound receiving process. |
| WF09 | Q3 | WF09P | Worker | outbound fulfillment work | answerable | 6 | 6 | 112 | Extract the full recorded outbound-fulfillment work lifecycle for each worker. |
| WF09P | Q4 | WF09 | Worker | outbound fulfillment work | answerable | 6 | 6 | 112 | For every worker, reconstruct the complete recorded history of their work on outbound fulfillment. |
| WF10 | Q3 | WF10P | Warehouse Task |  | answerable | 6 | 6 | 123 | Extract the full recorded lifecycle for each warehouse task. |
| WF10P | Q4 | WF10 | Warehouse Task |  | answerable | 6 | 6 | 123 | Build the full recorded lifecycle of each warehouse task. |
| WF11 | Q3 | WF11P | Handling Record |  | answerable | 4 | 4 | 80 | Extract the full recorded lifecycle for each handling record. |
| WF11P | Q4 | WF11 | Handling Record |  | answerable | 4 | 4 | 80 | Trace every individual handling record through its complete recorded history. |
