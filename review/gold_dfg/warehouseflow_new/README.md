# warehouseflow_new: questions and Gold DFGs

**EVALUATION ONLY — NEVER PROVIDE TO A MODEL.**

Source commit: `a0ba4c9631d12730d60bf7720d783a3a827b88dc`. Open index.html for search, review notes and complete case traces.

Node counts = event occurrences. Edge counts = adjacent selected events within a case. Dashed amber edges touch timestamp ties and depend on the tie-break rule. DFGs are projections of the selected log, not causal models.

[Event graph inventory · tables, objects, OTs and activities](event_graph.md)

**Source tables** produced matched Gold events. **SQL tables** are all physical tables read by the Gold SQL, including join tables and shared CTE branches.

## Dataset overview

[Full DB schema](../../../datasets/warehouseflow_new/docs/schema_overview.md) · [Full-size ER diagram](../../../datasets/warehouseflow_new/docs/schema.png) · [SQL DDL](../../../datasets/warehouseflow_new/input/schema.sql)

<details><summary>Show all 54 questions and the schema preview</summary>

<table><tr><td width="50%" valign="top"><h3>All questions (54)</h3><table><thead><tr><th>ID</th><th>Type</th><th>Question</th></tr></thead><tbody><tr><td><a href="#w01--q1">W01</a></td><td>Q1</td><td>For each receiving request, extract Receiving Request Submitted events.</td></tr><tr><td><a href="#w01p--q2">W01P</a></td><td>Q2</td><td>For every receiving request, show when it was submitted.</td></tr><tr><td><a href="#w02--q1">W02</a></td><td>Q1</td><td>For each receipt record, extract Receipt Registered events.</td></tr><tr><td><a href="#w02p--q2">W02P</a></td><td>Q2</td><td>For each individual receipt record, show when the receipt was registered.</td></tr><tr><td><a href="#w03--q1">W03</a></td><td>Q1</td><td>For each dispatch order, extract Dispatch Requested and Dispatch Approved events.</td></tr><tr><td><a href="#w03p--q2">W03P</a></td><td>Q2</td><td>For every dispatch order, show when dispatch was requested and when it was approved.</td></tr><tr><td><a href="#w04--q1">W04</a></td><td>Q1</td><td>For each stock audit, extract Stock Audit Started and Stock Audit Completed events.</td></tr><tr><td><a href="#w04p--q2">W04P</a></td><td>Q2</td><td>Show when each stock audit began and when it finished.</td></tr><tr><td><a href="#w05--q1">W05</a></td><td>Q1</td><td>For each stock movement record, extract Goods Received and Goods Dispatched events.</td></tr><tr><td><a href="#w05p--q2">W05P</a></td><td>Q2</td><td>For every stock movement record, show the recorded receipt into stock or dispatch from stock, as applicable.</td></tr><tr><td><a href="#w06--q1">W06</a></td><td>Q1</td><td>For each request action record, extract Request Checked, Request Held and Request Released events.</td></tr><tr><td><a href="#w06p--q2">W06P</a></td><td>Q2</td><td>For each individual request action record, show the checking, holding or releasing action that was recorded.</td></tr><tr><td><a href="#w07--q1">W07</a></td><td>Q1</td><td>For each warehouse task, extract Putaway Started, Putaway Completed, Picking Started, Picking Completed, Packing Started and Packing Completed events.</td></tr><tr><td><a href="#w07p--q2">W07P</a></td><td>Q2</td><td>For every warehouse task, show the recorded beginnings and completions of putaway, picking or packing, as applicable.</td></tr><tr><td><a href="#w08--q1">W08</a></td><td>Q1</td><td>For each handling record, extract Unloading Started, Unloading Completed, Loading Started and Loading Completed events.</td></tr><tr><td><a href="#w08p--q2">W08P</a></td><td>Q2</td><td>For each handling record, show when unloading or loading began and finished, as applicable.</td></tr><tr><td><a href="#w09--q1">W09</a></td><td>Q1</td><td>For each warehouse, extract Stock Audit Started, Stock Audit Completed, Putaway Started, Putaway Completed, Loading Started and Loading Completed events.</td></tr><tr><td><a href="#w09p--q2">W09P</a></td><td>Q2</td><td>For each warehouse, show the beginnings and completions of its stock audits, putaway work and loading work.</td></tr><tr><td><a href="#w10--q1">W10</a></td><td>Q1</td><td>For each receiving request, extract Unloading Started, Unloading Completed, Receipt Registered, Goods Received, Putaway Started and Putaway Completed events.</td></tr><tr><td><a href="#w10p--q2">W10P</a></td><td>Q2</td><td>For every receiving request, show the start and completion of unloading, registration of the receipt, receipt into warehouse stock, and the start and completion of putaway.</td></tr><tr><td><a href="#w11--q1">W11</a></td><td>Q1</td><td>For each dispatch order, extract Picking Started, Picking Completed, Packing Started, Packing Completed, Loading Started, Loading Completed and Goods Dispatched events.</td></tr><tr><td><a href="#w11p--q2">W11P</a></td><td>Q2</td><td>For each dispatch order, show when picking, packing and loading began and finished, together with the dispatch of goods from stock.</td></tr><tr><td><a href="#w12--q1">W12</a></td><td>Q1</td><td>For each worker, extract Stock Audit Started, Stock Audit Completed, Picking Started and Picking Completed events.</td></tr><tr><td><a href="#w12p--q2">W12P</a></td><td>Q2</td><td>For every worker, show when their stock audits and picking work began and finished.</td></tr><tr><td><a href="#w13--q1">W13</a></td><td>Q1</td><td>For each goods type, extract Goods Received and Goods Dispatched events.</td></tr><tr><td><a href="#w13p--q2">W13P</a></td><td>Q2</td><td>For each goods type, show its recorded receipts into warehouse stock and dispatches from stock.</td></tr><tr><td><a href="#w14--q1">W14</a></td><td>Q1</td><td>For each receipt record, extract Receipt Registered and Goods Received events.</td></tr><tr><td><a href="#w14p--q2">W14P</a></td><td>Q2</td><td>For every individual receipt record, show its registration and the corresponding receipt of goods into stock.</td></tr><tr><td><a href="#w15--q1">W15</a></td><td>Q1</td><td>For each warehouse, extract Invoice Paid events.</td></tr><tr><td><a href="#w15p--q2">W15P</a></td><td>Q2</td><td>For every warehouse, show when its invoices were paid.</td></tr><tr><td><a href="#w16--q1">W16</a></td><td>Q1</td><td>For each dispatch order, extract Customer Delivery Completed events.</td></tr><tr><td><a href="#w16p--q2">W16P</a></td><td>Q2</td><td>For each dispatch order, show when delivery to the customer was completed.</td></tr><tr><td><a href="#wf01--q3">WF01</a></td><td>Q3</td><td>Extract the full recorded lifecycle for each warehouse.</td></tr><tr><td><a href="#wf01p--q4">WF01P</a></td><td>Q4</td><td>Show the complete recorded history of each warehouse.</td></tr><tr><td><a href="#wf02--q3">WF02</a></td><td>Q3</td><td>Extract the full recorded lifecycle for each goods type.</td></tr><tr><td><a href="#wf02p--q4">WF02P</a></td><td>Q4</td><td>Build the entire recorded timeline associated with every goods type.</td></tr><tr><td><a href="#wf03--q3">WF03</a></td><td>Q3</td><td>Extract the full recorded lifecycle for each worker.</td></tr><tr><td><a href="#wf03p--q4">WF03P</a></td><td>Q4</td><td>Show every worker&#x27;s full recorded history.</td></tr><tr><td><a href="#wf04--q3">WF04</a></td><td>Q3</td><td>Extract the full recorded lifecycle for each receiving request.</td></tr><tr><td><a href="#wf04p--q4">WF04P</a></td><td>Q4</td><td>Trace each receiving request through its complete recorded lifecycle.</td></tr><tr><td><a href="#wf05--q3">WF05</a></td><td>Q3</td><td>Extract the full recorded lifecycle for each receipt record.</td></tr><tr><td><a href="#wf05p--q4">WF05P</a></td><td>Q4</td><td>Show the entire recorded history associated with each individual receipt record.</td></tr><tr><td><a href="#wf06--q3">WF06</a></td><td>Q3</td><td>Extract the full recorded lifecycle for each dispatch order.</td></tr><tr><td><a href="#wf06p--q4">WF06P</a></td><td>Q4</td><td>Build a complete recorded timeline for every dispatch order.</td></tr><tr><td><a href="#wf07--q3">WF07</a></td><td>Q3</td><td>Extract the full recorded lifecycle for each stock audit.</td></tr><tr><td><a href="#wf07p--q4">WF07P</a></td><td>Q4</td><td>Show the full recorded history of each stock audit.</td></tr><tr><td><a href="#wf08--q3">WF08</a></td><td>Q3</td><td>Extract the full recorded lifecycle for each stock movement record.</td></tr><tr><td><a href="#wf08p--q4">WF08P</a></td><td>Q4</td><td>Trace each individual stock movement record through its entire recorded history.</td></tr><tr><td><a href="#wf09--q3">WF09</a></td><td>Q3</td><td>Extract the full recorded lifecycle for each request action record.</td></tr><tr><td><a href="#wf09p--q4">WF09P</a></td><td>Q4</td><td>Show the complete recorded history of every individual request action record.</td></tr><tr><td><a href="#wf10--q3">WF10</a></td><td>Q3</td><td>Extract the full recorded lifecycle for each warehouse task.</td></tr><tr><td><a href="#wf10p--q4">WF10P</a></td><td>Q4</td><td>Build the full recorded lifecycle of each warehouse task.</td></tr><tr><td><a href="#wf11--q3">WF11</a></td><td>Q3</td><td>Extract the full recorded lifecycle for each handling record.</td></tr><tr><td><a href="#wf11p--q4">WF11P</a></td><td>Q4</td><td>Trace every individual handling record through its complete recorded history.</td></tr></tbody></table></td><td width="50%" valign="top"><h3>Database schema</h3><p><a href="../../../datasets/warehouseflow_new/docs/schema.png"><img src="../../../datasets/warehouseflow_new/docs/schema.png" alt="warehouseflow_new database schema"></a></p><p><a href="../../../datasets/warehouseflow_new/docs/schema.png">Full-size diagram</a> · <a href="../../../datasets/warehouseflow_new/input/schema.sql">Full SQL schema</a></p></td></tr></table>

</details>

## W01 — Q1

For each receiving request, extract Receiving Request Submitted events.

Events: **26** · Cases with events: **26** · Activities: **1** · Edges: **0** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W01.svg"><img src="graphs/W01.svg" width="460" alt="W01 Gold DFG"></a><br><a href="graphs/W01.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>receiving_request</strong> · 26 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>request_id = 001<br>submitted_at = 2026-02-01T05:00:00Z</td></tr><tr><td>2</td><td>request_id = 002<br>submitted_at = 2026-02-01T10:00:00Z</td></tr><tr><td>3</td><td>request_id = 003<br>submitted_at = 2026-02-01T15:00:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W01.csv)

## W01P — Q2

For every receiving request, show when it was submitted.

Events: **26** · Cases with events: **26** · Activities: **1** · Edges: **0** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W01.svg"><img src="graphs/W01.svg" width="460" alt="W01P Gold DFG"></a><br><a href="graphs/W01.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>receiving_request</strong> · 26 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>request_id = 001<br>submitted_at = 2026-02-01T05:00:00Z</td></tr><tr><td>2</td><td>request_id = 002<br>submitted_at = 2026-02-01T10:00:00Z</td></tr><tr><td>3</td><td>request_id = 003<br>submitted_at = 2026-02-01T15:00:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W01P.csv)

## W02 — Q1

For each receipt record, extract Receipt Registered events.

Events: **23** · Cases with events: **23** · Activities: **1** · Edges: **0** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W02.svg"><img src="graphs/W02.svg" width="460" alt="W02 Gold DFG"></a><br><a href="graphs/W02.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>goods_receipt</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>receipt_id = 001<br>received_at = 2026-02-01T05:32:00Z</td></tr><tr><td>2</td><td>receipt_id = 002<br>received_at = 2026-02-01T10:32:00Z</td></tr><tr><td>3</td><td>receipt_id = 003<br>received_at = 2026-02-01T15:32:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W02.csv)

## W02P — Q2

For each individual receipt record, show when the receipt was registered.

Events: **23** · Cases with events: **23** · Activities: **1** · Edges: **0** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W02.svg"><img src="graphs/W02.svg" width="460" alt="W02P Gold DFG"></a><br><a href="graphs/W02.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>goods_receipt</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>receipt_id = 001<br>received_at = 2026-02-01T05:32:00Z</td></tr><tr><td>2</td><td>receipt_id = 002<br>received_at = 2026-02-01T10:32:00Z</td></tr><tr><td>3</td><td>receipt_id = 003<br>received_at = 2026-02-01T15:32:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W02P.csv)

## W03 — Q1

For each dispatch order, extract Dispatch Requested and Dispatch Approved events.

Events: **38** · Cases with events: **20** · Activities: **2** · Edges: **1** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W03.svg"><img src="graphs/W03.svg" width="460" alt="W03 Gold DFG"></a><br><a href="graphs/W03.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>dispatch_order</strong> · 20 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>dispatch_id = 001<br>requested_at = 2026-04-11T15:40:00Z<br>approved_at = 2026-04-11T15:50:00Z</td></tr><tr><td>2</td><td>dispatch_id = 002<br>requested_at = 2026-04-11T20:40:00Z<br>approved_at = 2026-04-11T20:50:00Z</td></tr><tr><td>3</td><td>dispatch_id = 003<br>requested_at = 2026-04-12T01:40:00Z<br>approved_at = 2026-04-12T01:50:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W03.csv)

## W03P — Q2

For every dispatch order, show when dispatch was requested and when it was approved.

Events: **38** · Cases with events: **20** · Activities: **2** · Edges: **1** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W03.svg"><img src="graphs/W03.svg" width="460" alt="W03P Gold DFG"></a><br><a href="graphs/W03.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>dispatch_order</strong> · 20 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>dispatch_id = 001<br>requested_at = 2026-04-11T15:40:00Z<br>approved_at = 2026-04-11T15:50:00Z</td></tr><tr><td>2</td><td>dispatch_id = 002<br>requested_at = 2026-04-11T20:40:00Z<br>approved_at = 2026-04-11T20:50:00Z</td></tr><tr><td>3</td><td>dispatch_id = 003<br>requested_at = 2026-04-12T01:40:00Z<br>approved_at = 2026-04-12T01:50:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W03P.csv)

## W04 — Q1

For each stock audit, extract Stock Audit Started and Stock Audit Completed events.

Events: **17** · Cases with events: **9** · Activities: **2** · Edges: **1** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W04.svg"><img src="graphs/W04.svg" width="460" alt="W04 Gold DFG"></a><br><a href="graphs/W04.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>warehouse_audit</strong> · 9 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>audit_id = 001<br>started_at = 2026-05-16T05:40:00Z<br>completed_at = 2026-05-16T06:20:00Z</td></tr><tr><td>2</td><td>audit_id = 002<br>started_at = 2026-05-16T07:20:00Z<br>completed_at = 2026-05-16T08:00:00Z</td></tr><tr><td>3</td><td>audit_id = 003<br>started_at = 2026-05-16T09:00:00Z<br>completed_at = 2026-05-16T09:40:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W04.csv)

## W04P — Q2

Show when each stock audit began and when it finished.

Events: **17** · Cases with events: **9** · Activities: **2** · Edges: **1** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W04.svg"><img src="graphs/W04.svg" width="460" alt="W04P Gold DFG"></a><br><a href="graphs/W04.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>warehouse_audit</strong> · 9 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>audit_id = 001<br>started_at = 2026-05-16T05:40:00Z<br>completed_at = 2026-05-16T06:20:00Z</td></tr><tr><td>2</td><td>audit_id = 002<br>started_at = 2026-05-16T07:20:00Z<br>completed_at = 2026-05-16T08:00:00Z</td></tr><tr><td>3</td><td>audit_id = 003<br>started_at = 2026-05-16T09:00:00Z<br>completed_at = 2026-05-16T09:40:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W04P.csv)

## W05 — Q1

For each stock movement record, extract Goods Received and Goods Dispatched events.

Events: **39** · Cases with events: **39** · Activities: **2** · Edges: **0** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W05.svg"><img src="graphs/W05.svg" width="460" alt="W05 Gold DFG"></a><br><a href="graphs/W05.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>goods_movement</strong> · 39 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>movement_id = 0001<br>movement_code = IN<br>occurred_at = 2026-02-01T05:35:00Z</td></tr><tr><td>2</td><td>movement_id = 0002<br>movement_code = IN<br>occurred_at = 2026-02-01T10:35:00Z</td></tr><tr><td>3</td><td>movement_id = 0003<br>movement_code = IN<br>occurred_at = 2026-02-01T15:35:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W05.csv)

## W05P — Q2

For every stock movement record, show the recorded receipt into stock or dispatch from stock, as applicable.

Events: **39** · Cases with events: **39** · Activities: **2** · Edges: **0** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W05.svg"><img src="graphs/W05.svg" width="460" alt="W05P Gold DFG"></a><br><a href="graphs/W05.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>goods_movement</strong> · 39 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>movement_id = 0001<br>movement_code = IN<br>occurred_at = 2026-02-01T05:35:00Z</td></tr><tr><td>2</td><td>movement_id = 0002<br>movement_code = IN<br>occurred_at = 2026-02-01T10:35:00Z</td></tr><tr><td>3</td><td>movement_id = 0003<br>movement_code = IN<br>occurred_at = 2026-02-01T15:35:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W05P.csv)

## W06 — Q1

For each request action record, extract Request Checked, Request Held and Request Released events.

Events: **56** · Cases with events: **56** · Activities: **3** · Edges: **0** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W06.svg"><img src="graphs/W06.svg" width="460" alt="W06 Gold DFG"></a><br><a href="graphs/W06.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>request_action</strong> · 56 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>action_id = 0001<br>action_code = CHECK<br>occurred_at = 2026-02-01T05:05:00Z</td></tr><tr><td>2</td><td>action_id = 0002<br>action_code = RELEASE<br>occurred_at = 2026-02-01T05:12:00Z</td></tr><tr><td>3</td><td>action_id = 0003<br>action_code = CHECK<br>occurred_at = 2026-02-01T10:05:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W06.csv)

## W06P — Q2

For each individual request action record, show the checking, holding or releasing action that was recorded.

Events: **56** · Cases with events: **56** · Activities: **3** · Edges: **0** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W06.svg"><img src="graphs/W06.svg" width="460" alt="W06P Gold DFG"></a><br><a href="graphs/W06.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>request_action</strong> · 56 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>action_id = 0001<br>action_code = CHECK<br>occurred_at = 2026-02-01T05:05:00Z</td></tr><tr><td>2</td><td>action_id = 0002<br>action_code = RELEASE<br>occurred_at = 2026-02-01T05:12:00Z</td></tr><tr><td>3</td><td>action_id = 0003<br>action_code = CHECK<br>occurred_at = 2026-02-01T10:05:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W06P.csv)

## W07 — Q1

For each warehouse task, extract Putaway Started, Putaway Completed, Picking Started, Picking Completed, Packing Started and Packing Completed events.

Events: **123** · Cases with events: **63** · Activities: **6** · Edges: **3** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W07.svg"><img src="graphs/W07.svg" width="460" alt="W07 Gold DFG"></a><br><a href="graphs/W07.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>warehouse_task_history</strong> · 63 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>task_id = 0001<br>task_code = PUTAWAY<br>started_at = 2026-02-01T05:40:00Z<br>completed_at = 2026-02-01T05:50:00Z</td></tr><tr><td>2</td><td>task_id = 0002<br>task_code = PUTAWAY<br>started_at = 2026-02-01T10:40:00Z<br>completed_at = 2026-02-01T10:50:00Z</td></tr><tr><td>3</td><td>task_id = 0003<br>task_code = PUTAWAY<br>started_at = 2026-02-01T15:40:00Z<br>completed_at = 2026-02-01T15:50:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W07.csv)

## W07P — Q2

For every warehouse task, show the recorded beginnings and completions of putaway, picking or packing, as applicable.

Events: **123** · Cases with events: **63** · Activities: **6** · Edges: **3** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W07.svg"><img src="graphs/W07.svg" width="460" alt="W07P Gold DFG"></a><br><a href="graphs/W07.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>warehouse_task_history</strong> · 63 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>task_id = 0001<br>task_code = PUTAWAY<br>started_at = 2026-02-01T05:40:00Z<br>completed_at = 2026-02-01T05:50:00Z</td></tr><tr><td>2</td><td>task_id = 0002<br>task_code = PUTAWAY<br>started_at = 2026-02-01T10:40:00Z<br>completed_at = 2026-02-01T10:50:00Z</td></tr><tr><td>3</td><td>task_id = 0003<br>task_code = PUTAWAY<br>started_at = 2026-02-01T15:40:00Z<br>completed_at = 2026-02-01T15:50:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W07P.csv)

## W08 — Q1

For each handling record, extract Unloading Started, Unloading Completed, Loading Started and Loading Completed events.

Events: **80** · Cases with events: **41** · Activities: **4** · Edges: **2** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W08.svg"><img src="graphs/W08.svg" width="460" alt="W08 Gold DFG"></a><br><a href="graphs/W08.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>handling_history</strong> · 41 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>handling_id = 0001<br>handling_code = UNLOAD<br>started_at = 2026-02-01T05:20:00Z<br>completed_at = 2026-02-01T05:30:00Z</td></tr><tr><td>2</td><td>handling_id = 0002<br>handling_code = UNLOAD<br>started_at = 2026-02-01T10:20:00Z<br>completed_at = 2026-02-01T10:30:00Z</td></tr><tr><td>3</td><td>handling_id = 0003<br>handling_code = UNLOAD<br>started_at = 2026-02-01T15:20:00Z<br>completed_at = 2026-02-01T15:30:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W08.csv)

## W08P — Q2

For each handling record, show when unloading or loading began and finished, as applicable.

Events: **80** · Cases with events: **41** · Activities: **4** · Edges: **2** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W08.svg"><img src="graphs/W08.svg" width="460" alt="W08P Gold DFG"></a><br><a href="graphs/W08.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>handling_history</strong> · 41 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>handling_id = 0001<br>handling_code = UNLOAD<br>started_at = 2026-02-01T05:20:00Z<br>completed_at = 2026-02-01T05:30:00Z</td></tr><tr><td>2</td><td>handling_id = 0002<br>handling_code = UNLOAD<br>started_at = 2026-02-01T10:20:00Z<br>completed_at = 2026-02-01T10:30:00Z</td></tr><tr><td>3</td><td>handling_id = 0003<br>handling_code = UNLOAD<br>started_at = 2026-02-01T15:20:00Z<br>completed_at = 2026-02-01T15:30:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W08P.csv)

## W09 — Q1

For each warehouse, extract Stock Audit Started, Stock Audit Completed, Putaway Started, Putaway Completed, Loading Started and Loading Completed events.

Events: **94** · Cases with events: **3** · Activities: **6** · Edges: **10** · Source tables: **3** · SQL tables: **5**

<table><tr><td width="65%" valign="top"><a href="graphs/W09.svg"><img src="graphs/W09.svg" width="460" alt="W09 Gold DFG"></a><br><a href="graphs/W09.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>handling_history</strong> · 17 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>handling_id = 0025<br>handling_code = LOAD<br>started_at = 2026-04-11T16:30:00Z<br>completed_at = 2026-04-11T16:40:00Z</td></tr><tr><td>2</td><td>handling_id = 0028<br>handling_code = LOAD<br>started_at = 2026-04-12T07:30:00Z<br>completed_at = 2026-04-12T07:40:00Z</td></tr><tr><td>3</td><td>handling_id = 0031<br>handling_code = LOAD<br>started_at = 2026-04-12T22:30:00Z<br>completed_at = 2026-04-12T22:40:00Z</td></tr></table><p><strong>warehouse_audit</strong> · 9 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>audit_id = 001<br>started_at = 2026-05-16T05:40:00Z<br>completed_at = 2026-05-16T06:20:00Z</td></tr><tr><td>2</td><td>audit_id = 004<br>started_at = 2026-05-16T10:40:00Z<br>completed_at = 2026-05-16T11:20:00Z</td></tr><tr><td>3</td><td>audit_id = 007<br>started_at = 2026-05-16T15:40:00Z<br>completed_at = 2026-05-16T16:20:00Z</td></tr></table><p><strong>warehouse_task_history</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>task_id = 0001<br>task_code = PUTAWAY<br>started_at = 2026-02-01T05:40:00Z<br>completed_at = 2026-02-01T05:50:00Z</td></tr><tr><td>2</td><td>task_id = 0004<br>task_code = PUTAWAY<br>started_at = 2026-02-01T20:40:00Z<br>completed_at = 2026-02-01T20:50:00Z</td></tr><tr><td>3</td><td>task_id = 0007<br>task_code = PUTAWAY<br>started_at = 2026-02-02T11:40:00Z<br>completed_at = 2026-02-02T11:50:00Z</td></tr></table><details><summary>Other SQL tables</summary><p>dispatch_order, receiving_request</p></details></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W09.csv)

## W09P — Q2

For each warehouse, show the beginnings and completions of its stock audits, putaway work and loading work.

Events: **94** · Cases with events: **3** · Activities: **6** · Edges: **10** · Source tables: **3** · SQL tables: **5**

<table><tr><td width="65%" valign="top"><a href="graphs/W09.svg"><img src="graphs/W09.svg" width="460" alt="W09P Gold DFG"></a><br><a href="graphs/W09.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>handling_history</strong> · 17 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>handling_id = 0025<br>handling_code = LOAD<br>started_at = 2026-04-11T16:30:00Z<br>completed_at = 2026-04-11T16:40:00Z</td></tr><tr><td>2</td><td>handling_id = 0028<br>handling_code = LOAD<br>started_at = 2026-04-12T07:30:00Z<br>completed_at = 2026-04-12T07:40:00Z</td></tr><tr><td>3</td><td>handling_id = 0031<br>handling_code = LOAD<br>started_at = 2026-04-12T22:30:00Z<br>completed_at = 2026-04-12T22:40:00Z</td></tr></table><p><strong>warehouse_audit</strong> · 9 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>audit_id = 001<br>started_at = 2026-05-16T05:40:00Z<br>completed_at = 2026-05-16T06:20:00Z</td></tr><tr><td>2</td><td>audit_id = 004<br>started_at = 2026-05-16T10:40:00Z<br>completed_at = 2026-05-16T11:20:00Z</td></tr><tr><td>3</td><td>audit_id = 007<br>started_at = 2026-05-16T15:40:00Z<br>completed_at = 2026-05-16T16:20:00Z</td></tr></table><p><strong>warehouse_task_history</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>task_id = 0001<br>task_code = PUTAWAY<br>started_at = 2026-02-01T05:40:00Z<br>completed_at = 2026-02-01T05:50:00Z</td></tr><tr><td>2</td><td>task_id = 0004<br>task_code = PUTAWAY<br>started_at = 2026-02-01T20:40:00Z<br>completed_at = 2026-02-01T20:50:00Z</td></tr><tr><td>3</td><td>task_id = 0007<br>task_code = PUTAWAY<br>started_at = 2026-02-02T11:40:00Z<br>completed_at = 2026-02-02T11:50:00Z</td></tr></table><details><summary>Other SQL tables</summary><p>dispatch_order, receiving_request</p></details></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W09P.csv)

## W10 — Q1

For each receiving request, extract Unloading Started, Unloading Completed, Receipt Registered, Goods Received, Putaway Started and Putaway Completed events.

Events: **137** · Cases with events: **24** · Activities: **6** · Edges: **5** · Source tables: **4** · SQL tables: **4**

<table><tr><td width="65%" valign="top"><a href="graphs/W10.svg"><img src="graphs/W10.svg" width="460" alt="W10 Gold DFG"></a><br><a href="graphs/W10.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>goods_movement</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>movement_id = 0001<br>movement_code = IN<br>occurred_at = 2026-02-01T05:35:00Z</td></tr><tr><td>2</td><td>movement_id = 0002<br>movement_code = IN<br>occurred_at = 2026-02-01T10:35:00Z</td></tr><tr><td>3</td><td>movement_id = 0003<br>movement_code = IN<br>occurred_at = 2026-02-01T15:35:00Z</td></tr></table><p><strong>goods_receipt</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>receipt_id = 001<br>received_at = 2026-02-01T05:32:00Z</td></tr><tr><td>2</td><td>receipt_id = 002<br>received_at = 2026-02-01T10:32:00Z</td></tr><tr><td>3</td><td>receipt_id = 003<br>received_at = 2026-02-01T15:32:00Z</td></tr></table><p><strong>handling_history</strong> · 24 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>handling_id = 0001<br>handling_code = UNLOAD<br>started_at = 2026-02-01T05:20:00Z<br>completed_at = 2026-02-01T05:30:00Z</td></tr><tr><td>2</td><td>handling_id = 0002<br>handling_code = UNLOAD<br>started_at = 2026-02-01T10:20:00Z<br>completed_at = 2026-02-01T10:30:00Z</td></tr><tr><td>3</td><td>handling_id = 0003<br>handling_code = UNLOAD<br>started_at = 2026-02-01T15:20:00Z<br>completed_at = 2026-02-01T15:30:00Z</td></tr></table><p><strong>warehouse_task_history</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>task_id = 0001<br>task_code = PUTAWAY<br>started_at = 2026-02-01T05:40:00Z<br>completed_at = 2026-02-01T05:50:00Z</td></tr><tr><td>2</td><td>task_id = 0002<br>task_code = PUTAWAY<br>started_at = 2026-02-01T10:40:00Z<br>completed_at = 2026-02-01T10:50:00Z</td></tr><tr><td>3</td><td>task_id = 0003<br>task_code = PUTAWAY<br>started_at = 2026-02-01T15:40:00Z<br>completed_at = 2026-02-01T15:50:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W10.csv)

## W10P — Q2

For every receiving request, show the start and completion of unloading, registration of the receipt, receipt into warehouse stock, and the start and completion of putaway.

Events: **137** · Cases with events: **24** · Activities: **6** · Edges: **5** · Source tables: **4** · SQL tables: **4**

<table><tr><td width="65%" valign="top"><a href="graphs/W10.svg"><img src="graphs/W10.svg" width="460" alt="W10P Gold DFG"></a><br><a href="graphs/W10.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>goods_movement</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>movement_id = 0001<br>movement_code = IN<br>occurred_at = 2026-02-01T05:35:00Z</td></tr><tr><td>2</td><td>movement_id = 0002<br>movement_code = IN<br>occurred_at = 2026-02-01T10:35:00Z</td></tr><tr><td>3</td><td>movement_id = 0003<br>movement_code = IN<br>occurred_at = 2026-02-01T15:35:00Z</td></tr></table><p><strong>goods_receipt</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>receipt_id = 001<br>received_at = 2026-02-01T05:32:00Z</td></tr><tr><td>2</td><td>receipt_id = 002<br>received_at = 2026-02-01T10:32:00Z</td></tr><tr><td>3</td><td>receipt_id = 003<br>received_at = 2026-02-01T15:32:00Z</td></tr></table><p><strong>handling_history</strong> · 24 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>handling_id = 0001<br>handling_code = UNLOAD<br>started_at = 2026-02-01T05:20:00Z<br>completed_at = 2026-02-01T05:30:00Z</td></tr><tr><td>2</td><td>handling_id = 0002<br>handling_code = UNLOAD<br>started_at = 2026-02-01T10:20:00Z<br>completed_at = 2026-02-01T10:30:00Z</td></tr><tr><td>3</td><td>handling_id = 0003<br>handling_code = UNLOAD<br>started_at = 2026-02-01T15:20:00Z<br>completed_at = 2026-02-01T15:30:00Z</td></tr></table><p><strong>warehouse_task_history</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>task_id = 0001<br>task_code = PUTAWAY<br>started_at = 2026-02-01T05:40:00Z<br>completed_at = 2026-02-01T05:50:00Z</td></tr><tr><td>2</td><td>task_id = 0002<br>task_code = PUTAWAY<br>started_at = 2026-02-01T10:40:00Z<br>completed_at = 2026-02-01T10:50:00Z</td></tr><tr><td>3</td><td>task_id = 0003<br>task_code = PUTAWAY<br>started_at = 2026-02-01T15:40:00Z<br>completed_at = 2026-02-01T15:50:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W10P.csv)

## W11 — Q1

For each dispatch order, extract Picking Started, Picking Completed, Packing Started, Packing Completed, Loading Started, Loading Completed and Goods Dispatched events.

Events: **128** · Cases with events: **18** · Activities: **7** · Edges: **7** · Source tables: **3** · SQL tables: **3**

<table><tr><td width="65%" valign="top"><a href="graphs/W11.svg"><img src="graphs/W11.svg" width="460" alt="W11 Gold DFG"></a><br><a href="graphs/W11.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>goods_movement</strong> · 16 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>movement_id = 0024<br>movement_code = OUT<br>occurred_at = 2026-04-11T16:45:00Z</td></tr><tr><td>2</td><td>movement_id = 0025<br>movement_code = OUT<br>occurred_at = 2026-04-11T21:45:00Z</td></tr><tr><td>3</td><td>movement_id = 0026<br>movement_code = OUT<br>occurred_at = 2026-04-12T02:45:00Z</td></tr></table><p><strong>handling_history</strong> · 17 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>handling_id = 0025<br>handling_code = LOAD<br>started_at = 2026-04-11T16:30:00Z<br>completed_at = 2026-04-11T16:40:00Z</td></tr><tr><td>2</td><td>handling_id = 0026<br>handling_code = LOAD<br>started_at = 2026-04-11T21:30:00Z<br>completed_at = 2026-04-11T21:40:00Z</td></tr><tr><td>3</td><td>handling_id = 0027<br>handling_code = LOAD<br>started_at = 2026-04-12T02:30:00Z<br>completed_at = 2026-04-12T02:40:00Z</td></tr></table><p><strong>warehouse_task_history</strong> · 40 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>task_id = 0024<br>task_code = PICK<br>started_at = 2026-04-11T16:00:00Z<br>completed_at = 2026-04-11T16:10:00Z</td></tr><tr><td>2</td><td>task_id = 0025<br>task_code = PACK<br>started_at = 2026-04-11T16:15:00Z<br>completed_at = 2026-04-11T16:25:00Z</td></tr><tr><td>3</td><td>task_id = 0026<br>task_code = PICK<br>started_at = 2026-04-11T21:00:00Z<br>completed_at = 2026-04-11T21:10:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W11.csv)

## W11P — Q2

For each dispatch order, show when picking, packing and loading began and finished, together with the dispatch of goods from stock.

Events: **128** · Cases with events: **18** · Activities: **7** · Edges: **7** · Source tables: **3** · SQL tables: **3**

<table><tr><td width="65%" valign="top"><a href="graphs/W11.svg"><img src="graphs/W11.svg" width="460" alt="W11P Gold DFG"></a><br><a href="graphs/W11.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>goods_movement</strong> · 16 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>movement_id = 0024<br>movement_code = OUT<br>occurred_at = 2026-04-11T16:45:00Z</td></tr><tr><td>2</td><td>movement_id = 0025<br>movement_code = OUT<br>occurred_at = 2026-04-11T21:45:00Z</td></tr><tr><td>3</td><td>movement_id = 0026<br>movement_code = OUT<br>occurred_at = 2026-04-12T02:45:00Z</td></tr></table><p><strong>handling_history</strong> · 17 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>handling_id = 0025<br>handling_code = LOAD<br>started_at = 2026-04-11T16:30:00Z<br>completed_at = 2026-04-11T16:40:00Z</td></tr><tr><td>2</td><td>handling_id = 0026<br>handling_code = LOAD<br>started_at = 2026-04-11T21:30:00Z<br>completed_at = 2026-04-11T21:40:00Z</td></tr><tr><td>3</td><td>handling_id = 0027<br>handling_code = LOAD<br>started_at = 2026-04-12T02:30:00Z<br>completed_at = 2026-04-12T02:40:00Z</td></tr></table><p><strong>warehouse_task_history</strong> · 40 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>task_id = 0024<br>task_code = PICK<br>started_at = 2026-04-11T16:00:00Z<br>completed_at = 2026-04-11T16:10:00Z</td></tr><tr><td>2</td><td>task_id = 0025<br>task_code = PACK<br>started_at = 2026-04-11T16:15:00Z<br>completed_at = 2026-04-11T16:25:00Z</td></tr><tr><td>3</td><td>task_id = 0026<br>task_code = PICK<br>started_at = 2026-04-11T21:00:00Z<br>completed_at = 2026-04-11T21:10:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W11P.csv)

## W12 — Q1

For each worker, extract Stock Audit Started, Stock Audit Completed, Picking Started and Picking Completed events.

Events: **61** · Cases with events: **6** · Activities: **4** · Edges: **5** · Source tables: **2** · SQL tables: **2**

<table><tr><td width="65%" valign="top"><a href="graphs/W12.svg"><img src="graphs/W12.svg" width="460" alt="W12 Gold DFG"></a><br><a href="graphs/W12.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>warehouse_audit</strong> · 9 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>audit_id = 001<br>started_at = 2026-05-16T05:40:00Z<br>completed_at = 2026-05-16T06:20:00Z</td></tr><tr><td>2</td><td>audit_id = 007<br>started_at = 2026-05-16T15:40:00Z<br>completed_at = 2026-05-16T16:20:00Z</td></tr><tr><td>3</td><td>audit_id = 002<br>started_at = 2026-05-16T07:20:00Z<br>completed_at = 2026-05-16T08:00:00Z</td></tr></table><p><strong>warehouse_task_history</strong> · 22 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>task_id = 0035<br>task_code = PICK<br>started_at = 2026-04-12T17:00:00Z<br>completed_at = 2026-04-12T17:10:00Z</td></tr><tr><td>2</td><td>task_id = 0048<br>task_code = PICK<br>started_at = 2026-04-13T23:00:00Z<br>completed_at = 2026-04-13T23:10:00Z</td></tr><tr><td>3</td><td>task_id = 0049<br>task_code = PICK<br>started_at = 2026-04-13T23:11:00Z<br>completed_at = 2026-04-13T23:13:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W12.csv)

## W12P — Q2

For every worker, show when their stock audits and picking work began and finished.

Events: **61** · Cases with events: **6** · Activities: **4** · Edges: **5** · Source tables: **2** · SQL tables: **2**

<table><tr><td width="65%" valign="top"><a href="graphs/W12.svg"><img src="graphs/W12.svg" width="460" alt="W12P Gold DFG"></a><br><a href="graphs/W12.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>warehouse_audit</strong> · 9 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>audit_id = 001<br>started_at = 2026-05-16T05:40:00Z<br>completed_at = 2026-05-16T06:20:00Z</td></tr><tr><td>2</td><td>audit_id = 007<br>started_at = 2026-05-16T15:40:00Z<br>completed_at = 2026-05-16T16:20:00Z</td></tr><tr><td>3</td><td>audit_id = 002<br>started_at = 2026-05-16T07:20:00Z<br>completed_at = 2026-05-16T08:00:00Z</td></tr></table><p><strong>warehouse_task_history</strong> · 22 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>task_id = 0035<br>task_code = PICK<br>started_at = 2026-04-12T17:00:00Z<br>completed_at = 2026-04-12T17:10:00Z</td></tr><tr><td>2</td><td>task_id = 0048<br>task_code = PICK<br>started_at = 2026-04-13T23:00:00Z<br>completed_at = 2026-04-13T23:10:00Z</td></tr><tr><td>3</td><td>task_id = 0049<br>task_code = PICK<br>started_at = 2026-04-13T23:11:00Z<br>completed_at = 2026-04-13T23:13:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W12P.csv)

## W13 — Q1

For each goods type, extract Goods Received and Goods Dispatched events.

Events: **39** · Cases with events: **6** · Activities: **2** · Edges: **3** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W13.svg"><img src="graphs/W13.svg" width="460" alt="W13 Gold DFG"></a><br><a href="graphs/W13.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>goods_movement</strong> · 39 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>movement_id = 0001<br>movement_code = IN<br>occurred_at = 2026-02-01T05:35:00Z</td></tr><tr><td>2</td><td>movement_id = 0007<br>movement_code = IN<br>occurred_at = 2026-02-02T11:35:00Z</td></tr><tr><td>3</td><td>movement_id = 0013<br>movement_code = IN<br>occurred_at = 2026-02-03T17:35:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W13.csv)

## W13P — Q2

For each goods type, show its recorded receipts into warehouse stock and dispatches from stock.

Events: **39** · Cases with events: **6** · Activities: **2** · Edges: **3** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W13.svg"><img src="graphs/W13.svg" width="460" alt="W13P Gold DFG"></a><br><a href="graphs/W13.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>goods_movement</strong> · 39 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>movement_id = 0001<br>movement_code = IN<br>occurred_at = 2026-02-01T05:35:00Z</td></tr><tr><td>2</td><td>movement_id = 0007<br>movement_code = IN<br>occurred_at = 2026-02-02T11:35:00Z</td></tr><tr><td>3</td><td>movement_id = 0013<br>movement_code = IN<br>occurred_at = 2026-02-03T17:35:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W13P.csv)

## W14 — Q1

For each receipt record, extract Receipt Registered and Goods Received events.

Events: **46** · Cases with events: **23** · Activities: **2** · Edges: **1** · Source tables: **2** · SQL tables: **2**

<table><tr><td width="65%" valign="top"><a href="graphs/W14.svg"><img src="graphs/W14.svg" width="460" alt="W14 Gold DFG"></a><br><a href="graphs/W14.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>goods_movement</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>movement_id = 0001<br>movement_code = IN<br>occurred_at = 2026-02-01T05:35:00Z</td></tr><tr><td>2</td><td>movement_id = 0002<br>movement_code = IN<br>occurred_at = 2026-02-01T10:35:00Z</td></tr><tr><td>3</td><td>movement_id = 0003<br>movement_code = IN<br>occurred_at = 2026-02-01T15:35:00Z</td></tr></table><p><strong>goods_receipt</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>receipt_id = 001<br>received_at = 2026-02-01T05:32:00Z</td></tr><tr><td>2</td><td>receipt_id = 002<br>received_at = 2026-02-01T10:32:00Z</td></tr><tr><td>3</td><td>receipt_id = 003<br>received_at = 2026-02-01T15:32:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/W14.csv)

## W14P — Q2

For every individual receipt record, show its registration and the corresponding receipt of goods into stock.

Events: **46** · Cases with events: **23** · Activities: **2** · Edges: **1** · Source tables: **2** · SQL tables: **2**

<table><tr><td width="65%" valign="top"><a href="graphs/W14.svg"><img src="graphs/W14.svg" width="460" alt="W14P Gold DFG"></a><br><a href="graphs/W14.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>goods_movement</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>movement_id = 0001<br>movement_code = IN<br>occurred_at = 2026-02-01T05:35:00Z</td></tr><tr><td>2</td><td>movement_id = 0002<br>movement_code = IN<br>occurred_at = 2026-02-01T10:35:00Z</td></tr><tr><td>3</td><td>movement_id = 0003<br>movement_code = IN<br>occurred_at = 2026-02-01T15:35:00Z</td></tr></table><p><strong>goods_receipt</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>receipt_id = 001<br>received_at = 2026-02-01T05:32:00Z</td></tr><tr><td>2</td><td>receipt_id = 002<br>received_at = 2026-02-01T10:32:00Z</td></tr><tr><td>3</td><td>receipt_id = 003<br>received_at = 2026-02-01T15:32:00Z</td></tr></table></td></tr></table>

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

Events: **402** · Cases with events: **3** · Activities: **21** · Edges: **29** · Source tables: **8** · SQL tables: **8**

<table><tr><td width="65%" valign="top"><a href="graphs/WF01.svg"><img src="graphs/WF01.svg" width="460" alt="WF01 Gold DFG"></a><br><a href="graphs/WF01.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>dispatch_order</strong> · 20 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>dispatch_id = 001<br>requested_at = 2026-04-11T15:40:00Z<br>approved_at = 2026-04-11T15:50:00Z</td></tr><tr><td>2</td><td>dispatch_id = 004<br>requested_at = 2026-04-12T06:40:00Z<br>approved_at = 2026-04-12T06:50:00Z</td></tr><tr><td>3</td><td>dispatch_id = 007<br>requested_at = 2026-04-12T21:40:00Z<br>approved_at = 2026-04-12T21:50:00Z</td></tr></table><p><strong>goods_movement</strong> · 39 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>movement_id = 0001<br>movement_code = IN<br>occurred_at = 2026-02-01T05:35:00Z</td></tr><tr><td>2</td><td>movement_id = 0004<br>movement_code = IN<br>occurred_at = 2026-02-01T20:35:00Z</td></tr><tr><td>3</td><td>movement_id = 0007<br>movement_code = IN<br>occurred_at = 2026-02-02T11:35:00Z</td></tr></table><p><strong>goods_receipt</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>receipt_id = 001<br>received_at = 2026-02-01T05:32:00Z</td></tr><tr><td>2</td><td>receipt_id = 004<br>received_at = 2026-02-01T20:32:00Z</td></tr><tr><td>3</td><td>receipt_id = 007<br>received_at = 2026-02-02T11:32:00Z</td></tr></table><p><strong>handling_history</strong> · 41 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>handling_id = 0001<br>handling_code = UNLOAD<br>started_at = 2026-02-01T05:20:00Z<br>completed_at = 2026-02-01T05:30:00Z</td></tr><tr><td>2</td><td>handling_id = 0004<br>handling_code = UNLOAD<br>started_at = 2026-02-01T20:20:00Z<br>completed_at = 2026-02-01T20:30:00Z</td></tr><tr><td>3</td><td>handling_id = 0007<br>handling_code = UNLOAD<br>started_at = 2026-02-02T11:20:00Z<br>completed_at = 2026-02-02T11:30:00Z</td></tr></table><p><strong>receiving_request</strong> · 26 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>request_id = 001<br>submitted_at = 2026-02-01T05:00:00Z</td></tr><tr><td>2</td><td>request_id = 004<br>submitted_at = 2026-02-01T20:00:00Z</td></tr><tr><td>3</td><td>request_id = 007<br>submitted_at = 2026-02-02T11:00:00Z</td></tr></table><p><strong>request_action</strong> · 56 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>action_id = 0001<br>action_code = CHECK<br>occurred_at = 2026-02-01T05:05:00Z</td></tr><tr><td>2</td><td>action_id = 0002<br>action_code = RELEASE<br>occurred_at = 2026-02-01T05:12:00Z</td></tr><tr><td>3</td><td>action_id = 0007<br>action_code = CHECK<br>occurred_at = 2026-02-01T20:05:00Z</td></tr></table><p><strong>warehouse_audit</strong> · 9 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>audit_id = 001<br>started_at = 2026-05-16T05:40:00Z<br>completed_at = 2026-05-16T06:20:00Z</td></tr><tr><td>2</td><td>audit_id = 004<br>started_at = 2026-05-16T10:40:00Z<br>completed_at = 2026-05-16T11:20:00Z</td></tr><tr><td>3</td><td>audit_id = 007<br>started_at = 2026-05-16T15:40:00Z<br>completed_at = 2026-05-16T16:20:00Z</td></tr></table><p><strong>warehouse_task_history</strong> · 63 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>task_id = 0001<br>task_code = PUTAWAY<br>started_at = 2026-02-01T05:40:00Z<br>completed_at = 2026-02-01T05:50:00Z</td></tr><tr><td>2</td><td>task_id = 0004<br>task_code = PUTAWAY<br>started_at = 2026-02-01T20:40:00Z<br>completed_at = 2026-02-01T20:50:00Z</td></tr><tr><td>3</td><td>task_id = 0007<br>task_code = PUTAWAY<br>started_at = 2026-02-02T11:40:00Z<br>completed_at = 2026-02-02T11:50:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF01.csv)

## WF01P — Q4

Show the complete recorded history of each warehouse.

Events: **402** · Cases with events: **3** · Activities: **21** · Edges: **29** · Source tables: **8** · SQL tables: **8**

<table><tr><td width="65%" valign="top"><a href="graphs/WF01.svg"><img src="graphs/WF01.svg" width="460" alt="WF01P Gold DFG"></a><br><a href="graphs/WF01.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>dispatch_order</strong> · 20 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>dispatch_id = 001<br>requested_at = 2026-04-11T15:40:00Z<br>approved_at = 2026-04-11T15:50:00Z</td></tr><tr><td>2</td><td>dispatch_id = 004<br>requested_at = 2026-04-12T06:40:00Z<br>approved_at = 2026-04-12T06:50:00Z</td></tr><tr><td>3</td><td>dispatch_id = 007<br>requested_at = 2026-04-12T21:40:00Z<br>approved_at = 2026-04-12T21:50:00Z</td></tr></table><p><strong>goods_movement</strong> · 39 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>movement_id = 0001<br>movement_code = IN<br>occurred_at = 2026-02-01T05:35:00Z</td></tr><tr><td>2</td><td>movement_id = 0004<br>movement_code = IN<br>occurred_at = 2026-02-01T20:35:00Z</td></tr><tr><td>3</td><td>movement_id = 0007<br>movement_code = IN<br>occurred_at = 2026-02-02T11:35:00Z</td></tr></table><p><strong>goods_receipt</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>receipt_id = 001<br>received_at = 2026-02-01T05:32:00Z</td></tr><tr><td>2</td><td>receipt_id = 004<br>received_at = 2026-02-01T20:32:00Z</td></tr><tr><td>3</td><td>receipt_id = 007<br>received_at = 2026-02-02T11:32:00Z</td></tr></table><p><strong>handling_history</strong> · 41 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>handling_id = 0001<br>handling_code = UNLOAD<br>started_at = 2026-02-01T05:20:00Z<br>completed_at = 2026-02-01T05:30:00Z</td></tr><tr><td>2</td><td>handling_id = 0004<br>handling_code = UNLOAD<br>started_at = 2026-02-01T20:20:00Z<br>completed_at = 2026-02-01T20:30:00Z</td></tr><tr><td>3</td><td>handling_id = 0007<br>handling_code = UNLOAD<br>started_at = 2026-02-02T11:20:00Z<br>completed_at = 2026-02-02T11:30:00Z</td></tr></table><p><strong>receiving_request</strong> · 26 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>request_id = 001<br>submitted_at = 2026-02-01T05:00:00Z</td></tr><tr><td>2</td><td>request_id = 004<br>submitted_at = 2026-02-01T20:00:00Z</td></tr><tr><td>3</td><td>request_id = 007<br>submitted_at = 2026-02-02T11:00:00Z</td></tr></table><p><strong>request_action</strong> · 56 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>action_id = 0001<br>action_code = CHECK<br>occurred_at = 2026-02-01T05:05:00Z</td></tr><tr><td>2</td><td>action_id = 0002<br>action_code = RELEASE<br>occurred_at = 2026-02-01T05:12:00Z</td></tr><tr><td>3</td><td>action_id = 0007<br>action_code = CHECK<br>occurred_at = 2026-02-01T20:05:00Z</td></tr></table><p><strong>warehouse_audit</strong> · 9 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>audit_id = 001<br>started_at = 2026-05-16T05:40:00Z<br>completed_at = 2026-05-16T06:20:00Z</td></tr><tr><td>2</td><td>audit_id = 004<br>started_at = 2026-05-16T10:40:00Z<br>completed_at = 2026-05-16T11:20:00Z</td></tr><tr><td>3</td><td>audit_id = 007<br>started_at = 2026-05-16T15:40:00Z<br>completed_at = 2026-05-16T16:20:00Z</td></tr></table><p><strong>warehouse_task_history</strong> · 63 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>task_id = 0001<br>task_code = PUTAWAY<br>started_at = 2026-02-01T05:40:00Z<br>completed_at = 2026-02-01T05:50:00Z</td></tr><tr><td>2</td><td>task_id = 0004<br>task_code = PUTAWAY<br>started_at = 2026-02-01T20:40:00Z<br>completed_at = 2026-02-01T20:50:00Z</td></tr><tr><td>3</td><td>task_id = 0007<br>task_code = PUTAWAY<br>started_at = 2026-02-02T11:40:00Z<br>completed_at = 2026-02-02T11:50:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF01P.csv)

## WF02 — Q3

Extract the full recorded lifecycle for each goods type.

Events: **385** · Cases with events: **6** · Activities: **19** · Edges: **25** · Source tables: **7** · SQL tables: **7**

<table><tr><td width="65%" valign="top"><a href="graphs/WF02.svg"><img src="graphs/WF02.svg" width="460" alt="WF02 Gold DFG"></a><br><a href="graphs/WF02.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>dispatch_order</strong> · 20 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>dispatch_id = 001<br>requested_at = 2026-04-11T15:40:00Z<br>approved_at = 2026-04-11T15:50:00Z</td></tr><tr><td>2</td><td>dispatch_id = 007<br>requested_at = 2026-04-12T21:40:00Z<br>approved_at = 2026-04-12T21:50:00Z</td></tr><tr><td>3</td><td>dispatch_id = 013<br>requested_at = 2026-04-14T03:40:00Z<br>approved_at = 2026-04-14T03:50:00Z</td></tr></table><p><strong>goods_movement</strong> · 39 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>movement_id = 0001<br>movement_code = IN<br>occurred_at = 2026-02-01T05:35:00Z</td></tr><tr><td>2</td><td>movement_id = 0007<br>movement_code = IN<br>occurred_at = 2026-02-02T11:35:00Z</td></tr><tr><td>3</td><td>movement_id = 0013<br>movement_code = IN<br>occurred_at = 2026-02-03T17:35:00Z</td></tr></table><p><strong>goods_receipt</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>receipt_id = 001<br>received_at = 2026-02-01T05:32:00Z</td></tr><tr><td>2</td><td>receipt_id = 007<br>received_at = 2026-02-02T11:32:00Z</td></tr><tr><td>3</td><td>receipt_id = 013<br>received_at = 2026-02-03T17:32:00Z</td></tr></table><p><strong>handling_history</strong> · 41 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>handling_id = 0001<br>handling_code = UNLOAD<br>started_at = 2026-02-01T05:20:00Z<br>completed_at = 2026-02-01T05:30:00Z</td></tr><tr><td>2</td><td>handling_id = 0007<br>handling_code = UNLOAD<br>started_at = 2026-02-02T11:20:00Z<br>completed_at = 2026-02-02T11:30:00Z</td></tr><tr><td>3</td><td>handling_id = 0013<br>handling_code = UNLOAD<br>started_at = 2026-02-03T17:20:00Z<br>completed_at = 2026-02-03T17:30:00Z</td></tr></table><p><strong>receiving_request</strong> · 26 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>request_id = 001<br>submitted_at = 2026-02-01T05:00:00Z</td></tr><tr><td>2</td><td>request_id = 007<br>submitted_at = 2026-02-02T11:00:00Z</td></tr><tr><td>3</td><td>request_id = 013<br>submitted_at = 2026-02-03T17:00:00Z</td></tr></table><p><strong>request_action</strong> · 56 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>action_id = 0001<br>action_code = CHECK<br>occurred_at = 2026-02-01T05:05:00Z</td></tr><tr><td>2</td><td>action_id = 0002<br>action_code = RELEASE<br>occurred_at = 2026-02-01T05:12:00Z</td></tr><tr><td>3</td><td>action_id = 0015<br>action_code = CHECK<br>occurred_at = 2026-02-02T11:05:00Z</td></tr></table><p><strong>warehouse_task_history</strong> · 63 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>task_id = 0001<br>task_code = PUTAWAY<br>started_at = 2026-02-01T05:40:00Z<br>completed_at = 2026-02-01T05:50:00Z</td></tr><tr><td>2</td><td>task_id = 0007<br>task_code = PUTAWAY<br>started_at = 2026-02-02T11:40:00Z<br>completed_at = 2026-02-02T11:50:00Z</td></tr><tr><td>3</td><td>task_id = 0013<br>task_code = PUTAWAY<br>started_at = 2026-02-03T17:40:00Z<br>completed_at = 2026-02-03T17:50:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF02.csv)

## WF02P — Q4

Build the entire recorded timeline associated with every goods type.

Events: **385** · Cases with events: **6** · Activities: **19** · Edges: **25** · Source tables: **7** · SQL tables: **7**

<table><tr><td width="65%" valign="top"><a href="graphs/WF02.svg"><img src="graphs/WF02.svg" width="460" alt="WF02P Gold DFG"></a><br><a href="graphs/WF02.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>dispatch_order</strong> · 20 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>dispatch_id = 001<br>requested_at = 2026-04-11T15:40:00Z<br>approved_at = 2026-04-11T15:50:00Z</td></tr><tr><td>2</td><td>dispatch_id = 007<br>requested_at = 2026-04-12T21:40:00Z<br>approved_at = 2026-04-12T21:50:00Z</td></tr><tr><td>3</td><td>dispatch_id = 013<br>requested_at = 2026-04-14T03:40:00Z<br>approved_at = 2026-04-14T03:50:00Z</td></tr></table><p><strong>goods_movement</strong> · 39 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>movement_id = 0001<br>movement_code = IN<br>occurred_at = 2026-02-01T05:35:00Z</td></tr><tr><td>2</td><td>movement_id = 0007<br>movement_code = IN<br>occurred_at = 2026-02-02T11:35:00Z</td></tr><tr><td>3</td><td>movement_id = 0013<br>movement_code = IN<br>occurred_at = 2026-02-03T17:35:00Z</td></tr></table><p><strong>goods_receipt</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>receipt_id = 001<br>received_at = 2026-02-01T05:32:00Z</td></tr><tr><td>2</td><td>receipt_id = 007<br>received_at = 2026-02-02T11:32:00Z</td></tr><tr><td>3</td><td>receipt_id = 013<br>received_at = 2026-02-03T17:32:00Z</td></tr></table><p><strong>handling_history</strong> · 41 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>handling_id = 0001<br>handling_code = UNLOAD<br>started_at = 2026-02-01T05:20:00Z<br>completed_at = 2026-02-01T05:30:00Z</td></tr><tr><td>2</td><td>handling_id = 0007<br>handling_code = UNLOAD<br>started_at = 2026-02-02T11:20:00Z<br>completed_at = 2026-02-02T11:30:00Z</td></tr><tr><td>3</td><td>handling_id = 0013<br>handling_code = UNLOAD<br>started_at = 2026-02-03T17:20:00Z<br>completed_at = 2026-02-03T17:30:00Z</td></tr></table><p><strong>receiving_request</strong> · 26 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>request_id = 001<br>submitted_at = 2026-02-01T05:00:00Z</td></tr><tr><td>2</td><td>request_id = 007<br>submitted_at = 2026-02-02T11:00:00Z</td></tr><tr><td>3</td><td>request_id = 013<br>submitted_at = 2026-02-03T17:00:00Z</td></tr></table><p><strong>request_action</strong> · 56 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>action_id = 0001<br>action_code = CHECK<br>occurred_at = 2026-02-01T05:05:00Z</td></tr><tr><td>2</td><td>action_id = 0002<br>action_code = RELEASE<br>occurred_at = 2026-02-01T05:12:00Z</td></tr><tr><td>3</td><td>action_id = 0015<br>action_code = CHECK<br>occurred_at = 2026-02-02T11:05:00Z</td></tr></table><p><strong>warehouse_task_history</strong> · 63 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>task_id = 0001<br>task_code = PUTAWAY<br>started_at = 2026-02-01T05:40:00Z<br>completed_at = 2026-02-01T05:50:00Z</td></tr><tr><td>2</td><td>task_id = 0007<br>task_code = PUTAWAY<br>started_at = 2026-02-02T11:40:00Z<br>completed_at = 2026-02-02T11:50:00Z</td></tr><tr><td>3</td><td>task_id = 0013<br>task_code = PUTAWAY<br>started_at = 2026-02-03T17:40:00Z<br>completed_at = 2026-02-03T17:50:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF02P.csv)

## WF03 — Q3

Extract the full recorded lifecycle for each worker.

Events: **299** · Cases with events: **6** · Activities: **16** · Edges: **24** · Source tables: **5** · SQL tables: **5**

<table><tr><td width="65%" valign="top"><a href="graphs/WF03.svg"><img src="graphs/WF03.svg" width="460" alt="WF03 Gold DFG"></a><br><a href="graphs/WF03.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>goods_receipt</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>receipt_id = 001<br>received_at = 2026-02-01T05:32:00Z</td></tr><tr><td>2</td><td>receipt_id = 007<br>received_at = 2026-02-02T11:32:00Z</td></tr><tr><td>3</td><td>receipt_id = 013<br>received_at = 2026-02-03T17:32:00Z</td></tr></table><p><strong>handling_history</strong> · 41 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>handling_id = 0001<br>handling_code = UNLOAD<br>started_at = 2026-02-01T05:20:00Z<br>completed_at = 2026-02-01T05:30:00Z</td></tr><tr><td>2</td><td>handling_id = 0007<br>handling_code = UNLOAD<br>started_at = 2026-02-02T11:20:00Z<br>completed_at = 2026-02-02T11:30:00Z</td></tr><tr><td>3</td><td>handling_id = 0013<br>handling_code = UNLOAD<br>started_at = 2026-02-03T17:20:00Z<br>completed_at = 2026-02-03T17:30:00Z</td></tr></table><p><strong>request_action</strong> · 56 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>action_id = 0001<br>action_code = CHECK<br>occurred_at = 2026-02-01T05:05:00Z</td></tr><tr><td>2</td><td>action_id = 0002<br>action_code = RELEASE<br>occurred_at = 2026-02-01T05:12:00Z</td></tr><tr><td>3</td><td>action_id = 0015<br>action_code = CHECK<br>occurred_at = 2026-02-02T11:05:00Z</td></tr></table><p><strong>warehouse_audit</strong> · 9 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>audit_id = 001<br>started_at = 2026-05-16T05:40:00Z<br>completed_at = 2026-05-16T06:20:00Z</td></tr><tr><td>2</td><td>audit_id = 007<br>started_at = 2026-05-16T15:40:00Z<br>completed_at = 2026-05-16T16:20:00Z</td></tr><tr><td>3</td><td>audit_id = 002<br>started_at = 2026-05-16T07:20:00Z<br>completed_at = 2026-05-16T08:00:00Z</td></tr></table><p><strong>warehouse_task_history</strong> · 63 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>task_id = 0001<br>task_code = PUTAWAY<br>started_at = 2026-02-01T05:40:00Z<br>completed_at = 2026-02-01T05:50:00Z</td></tr><tr><td>2</td><td>task_id = 0007<br>task_code = PUTAWAY<br>started_at = 2026-02-02T11:40:00Z<br>completed_at = 2026-02-02T11:50:00Z</td></tr><tr><td>3</td><td>task_id = 0013<br>task_code = PUTAWAY<br>started_at = 2026-02-03T17:40:00Z<br>completed_at = 2026-02-03T17:50:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF03.csv)

## WF03P — Q4

Show every worker's full recorded history.

Events: **299** · Cases with events: **6** · Activities: **16** · Edges: **24** · Source tables: **5** · SQL tables: **5**

<table><tr><td width="65%" valign="top"><a href="graphs/WF03.svg"><img src="graphs/WF03.svg" width="460" alt="WF03P Gold DFG"></a><br><a href="graphs/WF03.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>goods_receipt</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>receipt_id = 001<br>received_at = 2026-02-01T05:32:00Z</td></tr><tr><td>2</td><td>receipt_id = 007<br>received_at = 2026-02-02T11:32:00Z</td></tr><tr><td>3</td><td>receipt_id = 013<br>received_at = 2026-02-03T17:32:00Z</td></tr></table><p><strong>handling_history</strong> · 41 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>handling_id = 0001<br>handling_code = UNLOAD<br>started_at = 2026-02-01T05:20:00Z<br>completed_at = 2026-02-01T05:30:00Z</td></tr><tr><td>2</td><td>handling_id = 0007<br>handling_code = UNLOAD<br>started_at = 2026-02-02T11:20:00Z<br>completed_at = 2026-02-02T11:30:00Z</td></tr><tr><td>3</td><td>handling_id = 0013<br>handling_code = UNLOAD<br>started_at = 2026-02-03T17:20:00Z<br>completed_at = 2026-02-03T17:30:00Z</td></tr></table><p><strong>request_action</strong> · 56 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>action_id = 0001<br>action_code = CHECK<br>occurred_at = 2026-02-01T05:05:00Z</td></tr><tr><td>2</td><td>action_id = 0002<br>action_code = RELEASE<br>occurred_at = 2026-02-01T05:12:00Z</td></tr><tr><td>3</td><td>action_id = 0015<br>action_code = CHECK<br>occurred_at = 2026-02-02T11:05:00Z</td></tr></table><p><strong>warehouse_audit</strong> · 9 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>audit_id = 001<br>started_at = 2026-05-16T05:40:00Z<br>completed_at = 2026-05-16T06:20:00Z</td></tr><tr><td>2</td><td>audit_id = 007<br>started_at = 2026-05-16T15:40:00Z<br>completed_at = 2026-05-16T16:20:00Z</td></tr><tr><td>3</td><td>audit_id = 002<br>started_at = 2026-05-16T07:20:00Z<br>completed_at = 2026-05-16T08:00:00Z</td></tr></table><p><strong>warehouse_task_history</strong> · 63 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>task_id = 0001<br>task_code = PUTAWAY<br>started_at = 2026-02-01T05:40:00Z<br>completed_at = 2026-02-01T05:50:00Z</td></tr><tr><td>2</td><td>task_id = 0007<br>task_code = PUTAWAY<br>started_at = 2026-02-02T11:40:00Z<br>completed_at = 2026-02-02T11:50:00Z</td></tr><tr><td>3</td><td>task_id = 0013<br>task_code = PUTAWAY<br>started_at = 2026-02-03T17:40:00Z<br>completed_at = 2026-02-03T17:50:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF03P.csv)

## WF04 — Q3

Extract the full recorded lifecycle for each receiving request.

Events: **219** · Cases with events: **26** · Activities: **10** · Edges: **10** · Source tables: **6** · SQL tables: **6**

<table><tr><td width="65%" valign="top"><a href="graphs/WF04.svg"><img src="graphs/WF04.svg" width="460" alt="WF04 Gold DFG"></a><br><a href="graphs/WF04.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>goods_movement</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>movement_id = 0001<br>movement_code = IN<br>occurred_at = 2026-02-01T05:35:00Z</td></tr><tr><td>2</td><td>movement_id = 0002<br>movement_code = IN<br>occurred_at = 2026-02-01T10:35:00Z</td></tr><tr><td>3</td><td>movement_id = 0003<br>movement_code = IN<br>occurred_at = 2026-02-01T15:35:00Z</td></tr></table><p><strong>goods_receipt</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>receipt_id = 001<br>received_at = 2026-02-01T05:32:00Z</td></tr><tr><td>2</td><td>receipt_id = 002<br>received_at = 2026-02-01T10:32:00Z</td></tr><tr><td>3</td><td>receipt_id = 003<br>received_at = 2026-02-01T15:32:00Z</td></tr></table><p><strong>handling_history</strong> · 24 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>handling_id = 0001<br>handling_code = UNLOAD<br>started_at = 2026-02-01T05:20:00Z<br>completed_at = 2026-02-01T05:30:00Z</td></tr><tr><td>2</td><td>handling_id = 0002<br>handling_code = UNLOAD<br>started_at = 2026-02-01T10:20:00Z<br>completed_at = 2026-02-01T10:30:00Z</td></tr><tr><td>3</td><td>handling_id = 0003<br>handling_code = UNLOAD<br>started_at = 2026-02-01T15:20:00Z<br>completed_at = 2026-02-01T15:30:00Z</td></tr></table><p><strong>receiving_request</strong> · 26 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>request_id = 001<br>submitted_at = 2026-02-01T05:00:00Z</td></tr><tr><td>2</td><td>request_id = 002<br>submitted_at = 2026-02-01T10:00:00Z</td></tr><tr><td>3</td><td>request_id = 003<br>submitted_at = 2026-02-01T15:00:00Z</td></tr></table><p><strong>request_action</strong> · 56 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>action_id = 0001<br>action_code = CHECK<br>occurred_at = 2026-02-01T05:05:00Z</td></tr><tr><td>2</td><td>action_id = 0002<br>action_code = RELEASE<br>occurred_at = 2026-02-01T05:12:00Z</td></tr><tr><td>3</td><td>action_id = 0003<br>action_code = CHECK<br>occurred_at = 2026-02-01T10:05:00Z</td></tr></table><p><strong>warehouse_task_history</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>task_id = 0001<br>task_code = PUTAWAY<br>started_at = 2026-02-01T05:40:00Z<br>completed_at = 2026-02-01T05:50:00Z</td></tr><tr><td>2</td><td>task_id = 0002<br>task_code = PUTAWAY<br>started_at = 2026-02-01T10:40:00Z<br>completed_at = 2026-02-01T10:50:00Z</td></tr><tr><td>3</td><td>task_id = 0003<br>task_code = PUTAWAY<br>started_at = 2026-02-01T15:40:00Z<br>completed_at = 2026-02-01T15:50:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF04.csv)

## WF04P — Q4

Trace each receiving request through its complete recorded lifecycle.

Events: **219** · Cases with events: **26** · Activities: **10** · Edges: **10** · Source tables: **6** · SQL tables: **6**

<table><tr><td width="65%" valign="top"><a href="graphs/WF04.svg"><img src="graphs/WF04.svg" width="460" alt="WF04P Gold DFG"></a><br><a href="graphs/WF04.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>goods_movement</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>movement_id = 0001<br>movement_code = IN<br>occurred_at = 2026-02-01T05:35:00Z</td></tr><tr><td>2</td><td>movement_id = 0002<br>movement_code = IN<br>occurred_at = 2026-02-01T10:35:00Z</td></tr><tr><td>3</td><td>movement_id = 0003<br>movement_code = IN<br>occurred_at = 2026-02-01T15:35:00Z</td></tr></table><p><strong>goods_receipt</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>receipt_id = 001<br>received_at = 2026-02-01T05:32:00Z</td></tr><tr><td>2</td><td>receipt_id = 002<br>received_at = 2026-02-01T10:32:00Z</td></tr><tr><td>3</td><td>receipt_id = 003<br>received_at = 2026-02-01T15:32:00Z</td></tr></table><p><strong>handling_history</strong> · 24 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>handling_id = 0001<br>handling_code = UNLOAD<br>started_at = 2026-02-01T05:20:00Z<br>completed_at = 2026-02-01T05:30:00Z</td></tr><tr><td>2</td><td>handling_id = 0002<br>handling_code = UNLOAD<br>started_at = 2026-02-01T10:20:00Z<br>completed_at = 2026-02-01T10:30:00Z</td></tr><tr><td>3</td><td>handling_id = 0003<br>handling_code = UNLOAD<br>started_at = 2026-02-01T15:20:00Z<br>completed_at = 2026-02-01T15:30:00Z</td></tr></table><p><strong>receiving_request</strong> · 26 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>request_id = 001<br>submitted_at = 2026-02-01T05:00:00Z</td></tr><tr><td>2</td><td>request_id = 002<br>submitted_at = 2026-02-01T10:00:00Z</td></tr><tr><td>3</td><td>request_id = 003<br>submitted_at = 2026-02-01T15:00:00Z</td></tr></table><p><strong>request_action</strong> · 56 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>action_id = 0001<br>action_code = CHECK<br>occurred_at = 2026-02-01T05:05:00Z</td></tr><tr><td>2</td><td>action_id = 0002<br>action_code = RELEASE<br>occurred_at = 2026-02-01T05:12:00Z</td></tr><tr><td>3</td><td>action_id = 0003<br>action_code = CHECK<br>occurred_at = 2026-02-01T10:05:00Z</td></tr></table><p><strong>warehouse_task_history</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>task_id = 0001<br>task_code = PUTAWAY<br>started_at = 2026-02-01T05:40:00Z<br>completed_at = 2026-02-01T05:50:00Z</td></tr><tr><td>2</td><td>task_id = 0002<br>task_code = PUTAWAY<br>started_at = 2026-02-01T10:40:00Z<br>completed_at = 2026-02-01T10:50:00Z</td></tr><tr><td>3</td><td>task_id = 0003<br>task_code = PUTAWAY<br>started_at = 2026-02-01T15:40:00Z<br>completed_at = 2026-02-01T15:50:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF04P.csv)

## WF05 — Q3

Extract the full recorded lifecycle for each receipt record.

Events: **46** · Cases with events: **23** · Activities: **2** · Edges: **1** · Source tables: **2** · SQL tables: **2**

<table><tr><td width="65%" valign="top"><a href="graphs/W14.svg"><img src="graphs/W14.svg" width="460" alt="WF05 Gold DFG"></a><br><a href="graphs/W14.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>goods_movement</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>movement_id = 0001<br>movement_code = IN<br>occurred_at = 2026-02-01T05:35:00Z</td></tr><tr><td>2</td><td>movement_id = 0002<br>movement_code = IN<br>occurred_at = 2026-02-01T10:35:00Z</td></tr><tr><td>3</td><td>movement_id = 0003<br>movement_code = IN<br>occurred_at = 2026-02-01T15:35:00Z</td></tr></table><p><strong>goods_receipt</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>receipt_id = 001<br>received_at = 2026-02-01T05:32:00Z</td></tr><tr><td>2</td><td>receipt_id = 002<br>received_at = 2026-02-01T10:32:00Z</td></tr><tr><td>3</td><td>receipt_id = 003<br>received_at = 2026-02-01T15:32:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF05.csv)

## WF05P — Q4

Show the entire recorded history associated with each individual receipt record.

Events: **46** · Cases with events: **23** · Activities: **2** · Edges: **1** · Source tables: **2** · SQL tables: **2**

<table><tr><td width="65%" valign="top"><a href="graphs/W14.svg"><img src="graphs/W14.svg" width="460" alt="WF05P Gold DFG"></a><br><a href="graphs/W14.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>goods_movement</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>movement_id = 0001<br>movement_code = IN<br>occurred_at = 2026-02-01T05:35:00Z</td></tr><tr><td>2</td><td>movement_id = 0002<br>movement_code = IN<br>occurred_at = 2026-02-01T10:35:00Z</td></tr><tr><td>3</td><td>movement_id = 0003<br>movement_code = IN<br>occurred_at = 2026-02-01T15:35:00Z</td></tr></table><p><strong>goods_receipt</strong> · 23 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>receipt_id = 001<br>received_at = 2026-02-01T05:32:00Z</td></tr><tr><td>2</td><td>receipt_id = 002<br>received_at = 2026-02-01T10:32:00Z</td></tr><tr><td>3</td><td>receipt_id = 003<br>received_at = 2026-02-01T15:32:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF05P.csv)

## WF06 — Q3

Extract the full recorded lifecycle for each dispatch order.

Events: **166** · Cases with events: **20** · Activities: **9** · Edges: **9** · Source tables: **4** · SQL tables: **4**

<table><tr><td width="65%" valign="top"><a href="graphs/WF06.svg"><img src="graphs/WF06.svg" width="460" alt="WF06 Gold DFG"></a><br><a href="graphs/WF06.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>dispatch_order</strong> · 20 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>dispatch_id = 001<br>requested_at = 2026-04-11T15:40:00Z<br>approved_at = 2026-04-11T15:50:00Z</td></tr><tr><td>2</td><td>dispatch_id = 002<br>requested_at = 2026-04-11T20:40:00Z<br>approved_at = 2026-04-11T20:50:00Z</td></tr><tr><td>3</td><td>dispatch_id = 003<br>requested_at = 2026-04-12T01:40:00Z<br>approved_at = 2026-04-12T01:50:00Z</td></tr></table><p><strong>goods_movement</strong> · 16 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>movement_id = 0024<br>movement_code = OUT<br>occurred_at = 2026-04-11T16:45:00Z</td></tr><tr><td>2</td><td>movement_id = 0025<br>movement_code = OUT<br>occurred_at = 2026-04-11T21:45:00Z</td></tr><tr><td>3</td><td>movement_id = 0026<br>movement_code = OUT<br>occurred_at = 2026-04-12T02:45:00Z</td></tr></table><p><strong>handling_history</strong> · 17 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>handling_id = 0025<br>handling_code = LOAD<br>started_at = 2026-04-11T16:30:00Z<br>completed_at = 2026-04-11T16:40:00Z</td></tr><tr><td>2</td><td>handling_id = 0026<br>handling_code = LOAD<br>started_at = 2026-04-11T21:30:00Z<br>completed_at = 2026-04-11T21:40:00Z</td></tr><tr><td>3</td><td>handling_id = 0027<br>handling_code = LOAD<br>started_at = 2026-04-12T02:30:00Z<br>completed_at = 2026-04-12T02:40:00Z</td></tr></table><p><strong>warehouse_task_history</strong> · 40 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>task_id = 0024<br>task_code = PICK<br>started_at = 2026-04-11T16:00:00Z<br>completed_at = 2026-04-11T16:10:00Z</td></tr><tr><td>2</td><td>task_id = 0025<br>task_code = PACK<br>started_at = 2026-04-11T16:15:00Z<br>completed_at = 2026-04-11T16:25:00Z</td></tr><tr><td>3</td><td>task_id = 0026<br>task_code = PICK<br>started_at = 2026-04-11T21:00:00Z<br>completed_at = 2026-04-11T21:10:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF06.csv)

## WF06P — Q4

Build a complete recorded timeline for every dispatch order.

Events: **166** · Cases with events: **20** · Activities: **9** · Edges: **9** · Source tables: **4** · SQL tables: **4**

<table><tr><td width="65%" valign="top"><a href="graphs/WF06.svg"><img src="graphs/WF06.svg" width="460" alt="WF06P Gold DFG"></a><br><a href="graphs/WF06.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>dispatch_order</strong> · 20 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>dispatch_id = 001<br>requested_at = 2026-04-11T15:40:00Z<br>approved_at = 2026-04-11T15:50:00Z</td></tr><tr><td>2</td><td>dispatch_id = 002<br>requested_at = 2026-04-11T20:40:00Z<br>approved_at = 2026-04-11T20:50:00Z</td></tr><tr><td>3</td><td>dispatch_id = 003<br>requested_at = 2026-04-12T01:40:00Z<br>approved_at = 2026-04-12T01:50:00Z</td></tr></table><p><strong>goods_movement</strong> · 16 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>movement_id = 0024<br>movement_code = OUT<br>occurred_at = 2026-04-11T16:45:00Z</td></tr><tr><td>2</td><td>movement_id = 0025<br>movement_code = OUT<br>occurred_at = 2026-04-11T21:45:00Z</td></tr><tr><td>3</td><td>movement_id = 0026<br>movement_code = OUT<br>occurred_at = 2026-04-12T02:45:00Z</td></tr></table><p><strong>handling_history</strong> · 17 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>handling_id = 0025<br>handling_code = LOAD<br>started_at = 2026-04-11T16:30:00Z<br>completed_at = 2026-04-11T16:40:00Z</td></tr><tr><td>2</td><td>handling_id = 0026<br>handling_code = LOAD<br>started_at = 2026-04-11T21:30:00Z<br>completed_at = 2026-04-11T21:40:00Z</td></tr><tr><td>3</td><td>handling_id = 0027<br>handling_code = LOAD<br>started_at = 2026-04-12T02:30:00Z<br>completed_at = 2026-04-12T02:40:00Z</td></tr></table><p><strong>warehouse_task_history</strong> · 40 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>task_id = 0024<br>task_code = PICK<br>started_at = 2026-04-11T16:00:00Z<br>completed_at = 2026-04-11T16:10:00Z</td></tr><tr><td>2</td><td>task_id = 0025<br>task_code = PACK<br>started_at = 2026-04-11T16:15:00Z<br>completed_at = 2026-04-11T16:25:00Z</td></tr><tr><td>3</td><td>task_id = 0026<br>task_code = PICK<br>started_at = 2026-04-11T21:00:00Z<br>completed_at = 2026-04-11T21:10:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF06P.csv)

## WF07 — Q3

Extract the full recorded lifecycle for each stock audit.

Events: **17** · Cases with events: **9** · Activities: **2** · Edges: **1** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W04.svg"><img src="graphs/W04.svg" width="460" alt="WF07 Gold DFG"></a><br><a href="graphs/W04.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>warehouse_audit</strong> · 9 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>audit_id = 001<br>started_at = 2026-05-16T05:40:00Z<br>completed_at = 2026-05-16T06:20:00Z</td></tr><tr><td>2</td><td>audit_id = 002<br>started_at = 2026-05-16T07:20:00Z<br>completed_at = 2026-05-16T08:00:00Z</td></tr><tr><td>3</td><td>audit_id = 003<br>started_at = 2026-05-16T09:00:00Z<br>completed_at = 2026-05-16T09:40:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF07.csv)

## WF07P — Q4

Show the full recorded history of each stock audit.

Events: **17** · Cases with events: **9** · Activities: **2** · Edges: **1** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W04.svg"><img src="graphs/W04.svg" width="460" alt="WF07P Gold DFG"></a><br><a href="graphs/W04.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>warehouse_audit</strong> · 9 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>audit_id = 001<br>started_at = 2026-05-16T05:40:00Z<br>completed_at = 2026-05-16T06:20:00Z</td></tr><tr><td>2</td><td>audit_id = 002<br>started_at = 2026-05-16T07:20:00Z<br>completed_at = 2026-05-16T08:00:00Z</td></tr><tr><td>3</td><td>audit_id = 003<br>started_at = 2026-05-16T09:00:00Z<br>completed_at = 2026-05-16T09:40:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF07P.csv)

## WF08 — Q3

Extract the full recorded lifecycle for each stock movement record.

Events: **39** · Cases with events: **39** · Activities: **2** · Edges: **0** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W05.svg"><img src="graphs/W05.svg" width="460" alt="WF08 Gold DFG"></a><br><a href="graphs/W05.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>goods_movement</strong> · 39 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>movement_id = 0001<br>movement_code = IN<br>occurred_at = 2026-02-01T05:35:00Z</td></tr><tr><td>2</td><td>movement_id = 0002<br>movement_code = IN<br>occurred_at = 2026-02-01T10:35:00Z</td></tr><tr><td>3</td><td>movement_id = 0003<br>movement_code = IN<br>occurred_at = 2026-02-01T15:35:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF08.csv)

## WF08P — Q4

Trace each individual stock movement record through its entire recorded history.

Events: **39** · Cases with events: **39** · Activities: **2** · Edges: **0** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W05.svg"><img src="graphs/W05.svg" width="460" alt="WF08P Gold DFG"></a><br><a href="graphs/W05.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>goods_movement</strong> · 39 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>movement_id = 0001<br>movement_code = IN<br>occurred_at = 2026-02-01T05:35:00Z</td></tr><tr><td>2</td><td>movement_id = 0002<br>movement_code = IN<br>occurred_at = 2026-02-01T10:35:00Z</td></tr><tr><td>3</td><td>movement_id = 0003<br>movement_code = IN<br>occurred_at = 2026-02-01T15:35:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF08P.csv)

## WF09 — Q3

Extract the full recorded lifecycle for each request action record.

Events: **56** · Cases with events: **56** · Activities: **3** · Edges: **0** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W06.svg"><img src="graphs/W06.svg" width="460" alt="WF09 Gold DFG"></a><br><a href="graphs/W06.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>request_action</strong> · 56 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>action_id = 0001<br>action_code = CHECK<br>occurred_at = 2026-02-01T05:05:00Z</td></tr><tr><td>2</td><td>action_id = 0002<br>action_code = RELEASE<br>occurred_at = 2026-02-01T05:12:00Z</td></tr><tr><td>3</td><td>action_id = 0003<br>action_code = CHECK<br>occurred_at = 2026-02-01T10:05:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF09.csv)

## WF09P — Q4

Show the complete recorded history of every individual request action record.

Events: **56** · Cases with events: **56** · Activities: **3** · Edges: **0** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W06.svg"><img src="graphs/W06.svg" width="460" alt="WF09P Gold DFG"></a><br><a href="graphs/W06.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>request_action</strong> · 56 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>action_id = 0001<br>action_code = CHECK<br>occurred_at = 2026-02-01T05:05:00Z</td></tr><tr><td>2</td><td>action_id = 0002<br>action_code = RELEASE<br>occurred_at = 2026-02-01T05:12:00Z</td></tr><tr><td>3</td><td>action_id = 0003<br>action_code = CHECK<br>occurred_at = 2026-02-01T10:05:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF09P.csv)

## WF10 — Q3

Extract the full recorded lifecycle for each warehouse task.

Events: **123** · Cases with events: **63** · Activities: **6** · Edges: **3** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W07.svg"><img src="graphs/W07.svg" width="460" alt="WF10 Gold DFG"></a><br><a href="graphs/W07.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>warehouse_task_history</strong> · 63 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>task_id = 0001<br>task_code = PUTAWAY<br>started_at = 2026-02-01T05:40:00Z<br>completed_at = 2026-02-01T05:50:00Z</td></tr><tr><td>2</td><td>task_id = 0002<br>task_code = PUTAWAY<br>started_at = 2026-02-01T10:40:00Z<br>completed_at = 2026-02-01T10:50:00Z</td></tr><tr><td>3</td><td>task_id = 0003<br>task_code = PUTAWAY<br>started_at = 2026-02-01T15:40:00Z<br>completed_at = 2026-02-01T15:50:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF10.csv)

## WF10P — Q4

Build the full recorded lifecycle of each warehouse task.

Events: **123** · Cases with events: **63** · Activities: **6** · Edges: **3** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W07.svg"><img src="graphs/W07.svg" width="460" alt="WF10P Gold DFG"></a><br><a href="graphs/W07.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>warehouse_task_history</strong> · 63 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>task_id = 0001<br>task_code = PUTAWAY<br>started_at = 2026-02-01T05:40:00Z<br>completed_at = 2026-02-01T05:50:00Z</td></tr><tr><td>2</td><td>task_id = 0002<br>task_code = PUTAWAY<br>started_at = 2026-02-01T10:40:00Z<br>completed_at = 2026-02-01T10:50:00Z</td></tr><tr><td>3</td><td>task_id = 0003<br>task_code = PUTAWAY<br>started_at = 2026-02-01T15:40:00Z<br>completed_at = 2026-02-01T15:50:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF10P.csv)

## WF11 — Q3

Extract the full recorded lifecycle for each handling record.

Events: **80** · Cases with events: **41** · Activities: **4** · Edges: **2** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W08.svg"><img src="graphs/W08.svg" width="460" alt="WF11 Gold DFG"></a><br><a href="graphs/W08.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>handling_history</strong> · 41 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>handling_id = 0001<br>handling_code = UNLOAD<br>started_at = 2026-02-01T05:20:00Z<br>completed_at = 2026-02-01T05:30:00Z</td></tr><tr><td>2</td><td>handling_id = 0002<br>handling_code = UNLOAD<br>started_at = 2026-02-01T10:20:00Z<br>completed_at = 2026-02-01T10:30:00Z</td></tr><tr><td>3</td><td>handling_id = 0003<br>handling_code = UNLOAD<br>started_at = 2026-02-01T15:20:00Z<br>completed_at = 2026-02-01T15:30:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF11.csv)

## WF11P — Q4

Trace every individual handling record through its complete recorded history.

Events: **80** · Cases with events: **41** · Activities: **4** · Edges: **2** · Source tables: **1** · SQL tables: **1**

<table><tr><td width="65%" valign="top"><a href="graphs/W08.svg"><img src="graphs/W08.svg" width="460" alt="WF11P Gold DFG"></a><br><a href="graphs/W08.svg">Open full-size DFG</a></td><td width="35%" valign="top"><h4>Original tables</h4><p>Up to 3 matched rows per table. Shows keys, event times and carrier values.</p><p><strong>handling_history</strong> · 41 matched rows</p><table><tr><th>Row</th><th>Source values</th></tr><tr><td>1</td><td>handling_id = 0001<br>handling_code = UNLOAD<br>started_at = 2026-02-01T05:20:00Z<br>completed_at = 2026-02-01T05:30:00Z</td></tr><tr><td>2</td><td>handling_id = 0002<br>handling_code = UNLOAD<br>started_at = 2026-02-01T10:20:00Z<br>completed_at = 2026-02-01T10:30:00Z</td></tr><tr><td>3</td><td>handling_id = 0003<br>handling_code = UNLOAD<br>started_at = 2026-02-01T15:20:00Z<br>completed_at = 2026-02-01T15:30:00Z</td></tr></table></td></tr></table>

[Gold CSV](../../../datasets/warehouseflow_new/private/gold_logs/WF11P.csv)
