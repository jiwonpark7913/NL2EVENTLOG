# WarehouseFlow New questions

## Question types and pairs

| Type | Questions | Answerable | Non-answerable | Avg. requested activity labels |
| --- | --- | --- | --- | --- |
| Q1 | 16 | 14 | 2 | 3.12 |
| Q2 | 16 | 14 | 2 | 3.12 |
| Q3 | 11 | 11 | 0 | 8.55 |
| Q4 | 11 | 11 | 0 | 8.55 |

- Start/completion labels are counted separately here; base work identity is preserved separately in private event metadata. Averages include unsupported requests.
- Q1/Q3 seeds are frozen before the assistant LLM creates Q2/Q4. Each pair has the same scope, phase selection, ES and CSV.

| ID | Type | Paired with | Answerability | Requested labels | Extractable labels | Requested base activities | Extractable base activities | Question |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| W01 | Q1 | W01P | answerable | 1 | 1 | 1 | 1 | For each receiving request, extract Receiving Request Submitted events. |
| W01P | Q2 | W01 | answerable | 1 | 1 | 1 | 1 | For every receiving request, show when it was submitted. |
| W02 | Q1 | W02P | answerable | 1 | 1 | 1 | 1 | For each receipt record, extract Receipt Registered events. |
| W02P | Q2 | W02 | answerable | 1 | 1 | 1 | 1 | For each individual receipt record, show when the receipt was registered. |
| W03 | Q1 | W03P | answerable | 2 | 2 | 2 | 2 | For each dispatch order, extract Dispatch Requested and Dispatch Approved events. |
| W03P | Q2 | W03 | answerable | 2 | 2 | 2 | 2 | For every dispatch order, show when dispatch was requested and when it was approved. |
| W04 | Q1 | W04P | answerable | 2 | 2 | 1 | 1 | For each stock audit, extract Stock Audit Started and Stock Audit Completed events. |
| W04P | Q2 | W04 | answerable | 2 | 2 | 1 | 1 | Show when each stock audit began and when it finished. |
| W05 | Q1 | W05P | answerable | 2 | 2 | 2 | 2 | For each stock movement record, extract Goods Received and Goods Dispatched events. |
| W05P | Q2 | W05 | answerable | 2 | 2 | 2 | 2 | For every stock movement record, show the recorded receipt into stock or dispatch from stock, as applicable. |
| W06 | Q1 | W06P | answerable | 3 | 3 | 3 | 3 | For each request action record, extract Request Checked, Request Held and Request Released events. |
| W06P | Q2 | W06 | answerable | 3 | 3 | 3 | 3 | For each individual request action record, show the checking, holding or releasing action that was recorded. |
| W07 | Q1 | W07P | answerable | 6 | 6 | 3 | 3 | For each warehouse task, extract Putaway Started, Putaway Completed, Picking Started, Picking Completed, Packing Started and Packing Completed events. |
| W07P | Q2 | W07 | answerable | 6 | 6 | 3 | 3 | For every warehouse task, show the recorded beginnings and completions of putaway, picking or packing, as applicable. |
| W08 | Q1 | W08P | answerable | 4 | 4 | 2 | 2 | For each handling record, extract Unloading Started, Unloading Completed, Loading Started and Loading Completed events. |
| W08P | Q2 | W08 | answerable | 4 | 4 | 2 | 2 | For each handling record, show when unloading or loading began and finished, as applicable. |
| W09 | Q1 | W09P | answerable | 6 | 6 | 3 | 3 | For each warehouse, extract Stock Audit Started, Stock Audit Completed, Putaway Started, Putaway Completed, Loading Started and Loading Completed events. |
| W09P | Q2 | W09 | answerable | 6 | 6 | 3 | 3 | For each warehouse, show the beginnings and completions of its stock audits, putaway work and loading work. |
| W10 | Q1 | W10P | answerable | 6 | 6 | 4 | 4 | For each receiving request, extract Unloading Started, Unloading Completed, Receipt Registered, Goods Received, Putaway Started and Putaway Completed events. |
| W10P | Q2 | W10 | answerable | 6 | 6 | 4 | 4 | For every receiving request, show the start and completion of unloading, registration of the receipt, receipt into warehouse stock, and the start and completion of putaway. |
| W11 | Q1 | W11P | answerable | 7 | 7 | 4 | 4 | For each dispatch order, extract Picking Started, Picking Completed, Packing Started, Packing Completed, Loading Started, Loading Completed and Goods Dispatched events. |
| W11P | Q2 | W11 | answerable | 7 | 7 | 4 | 4 | For each dispatch order, show when picking, packing and loading began and finished, together with the dispatch of goods from stock. |
| W12 | Q1 | W12P | answerable | 4 | 4 | 2 | 2 | For each worker, extract Stock Audit Started, Stock Audit Completed, Picking Started and Picking Completed events. |
| W12P | Q2 | W12 | answerable | 4 | 4 | 2 | 2 | For every worker, show when their stock audits and picking work began and finished. |
| W13 | Q1 | W13P | answerable | 2 | 2 | 2 | 2 | For each goods type, extract Goods Received and Goods Dispatched events. |
| W13P | Q2 | W13 | answerable | 2 | 2 | 2 | 2 | For each goods type, show its recorded receipts into warehouse stock and dispatches from stock. |
| W14 | Q1 | W14P | answerable | 2 | 2 | 2 | 2 | For each receipt record, extract Receipt Registered and Goods Received events. |
| W14P | Q2 | W14 | answerable | 2 | 2 | 2 | 2 | For every individual receipt record, show its registration and the corresponding receipt of goods into stock. |
| W15 | Q1 | W15P | non_answerable | 1 | 0 | 1 | 0 | For each warehouse, extract Invoice Paid events. |
| W15P | Q2 | W15 | non_answerable | 1 | 0 | 1 | 0 | For every warehouse, show when its invoices were paid. |
| W16 | Q1 | W16P | non_answerable | 1 | 0 | 1 | 0 | For each dispatch order, extract Customer Delivery Completed events. |
| W16P | Q2 | W16 | non_answerable | 1 | 0 | 1 | 0 | For each dispatch order, show when delivery to the customer was completed. |
| WF01 | Q3 | WF01P | answerable | 21 | 21 | 15 | 15 | Extract the full recorded lifecycle for each warehouse. |
| WF01P | Q4 | WF01 | answerable | 21 | 21 | 15 | 15 | Show the complete recorded history of each warehouse. |
| WF02 | Q3 | WF02P | answerable | 19 | 19 | 14 | 14 | Extract the full recorded lifecycle for each goods type. |
| WF02P | Q4 | WF02 | answerable | 19 | 19 | 14 | 14 | Build the entire recorded timeline associated with every goods type. |
| WF03 | Q3 | WF03P | answerable | 16 | 16 | 10 | 10 | Extract the full recorded lifecycle for each worker. |
| WF03P | Q4 | WF03 | answerable | 16 | 16 | 10 | 10 | Show every worker's full recorded history. |
| WF04 | Q3 | WF04P | answerable | 10 | 10 | 8 | 8 | Extract the full recorded lifecycle for each receiving request. |
| WF04P | Q4 | WF04 | answerable | 10 | 10 | 8 | 8 | Trace each receiving request through its complete recorded lifecycle. |
| WF05 | Q3 | WF05P | answerable | 2 | 2 | 2 | 2 | Extract the full recorded lifecycle for each receipt record. |
| WF05P | Q4 | WF05 | answerable | 2 | 2 | 2 | 2 | Show the entire recorded history associated with each individual receipt record. |
| WF06 | Q3 | WF06P | answerable | 9 | 9 | 6 | 6 | Extract the full recorded lifecycle for each dispatch order. |
| WF06P | Q4 | WF06 | answerable | 9 | 9 | 6 | 6 | Build a complete recorded timeline for every dispatch order. |
| WF07 | Q3 | WF07P | answerable | 2 | 2 | 1 | 1 | Extract the full recorded lifecycle for each stock audit. |
| WF07P | Q4 | WF07 | answerable | 2 | 2 | 1 | 1 | Show the full recorded history of each stock audit. |
| WF08 | Q3 | WF08P | answerable | 2 | 2 | 2 | 2 | Extract the full recorded lifecycle for each stock movement record. |
| WF08P | Q4 | WF08 | answerable | 2 | 2 | 2 | 2 | Trace each individual stock movement record through its entire recorded history. |
| WF09 | Q3 | WF09P | answerable | 3 | 3 | 3 | 3 | Extract the full recorded lifecycle for each request action record. |
| WF09P | Q4 | WF09 | answerable | 3 | 3 | 3 | 3 | Show the complete recorded history of every individual request action record. |
| WF10 | Q3 | WF10P | answerable | 6 | 6 | 3 | 3 | Extract the full recorded lifecycle for each warehouse task. |
| WF10P | Q4 | WF10 | answerable | 6 | 6 | 3 | 3 | Build the full recorded lifecycle of each warehouse task. |
| WF11 | Q3 | WF11P | answerable | 4 | 4 | 2 | 2 | Extract the full recorded lifecycle for each handling record. |
| WF11P | Q4 | WF11 | answerable | 4 | 4 | 2 | 2 | Trace every individual handling record through its complete recorded history. |
