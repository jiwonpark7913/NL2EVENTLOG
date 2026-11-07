# Objects, activities and situations

| Case type | Cases | Base activity types | Phase-specific labels | Empty cases | Default recorded scope |
| --- | --- | --- | --- | --- | --- |
| Warehouse | 4 | 15 | 21 | 1 | Dispatch Approved, Dispatch Requested, Goods Dispatched, Goods Received, Loading Completed, Loading Started, Packing Completed, Packing Started, Picking Completed, Picking Started, Putaway Completed, Putaway Started, Receipt Registered, Receiving Request Submitted, Request Checked, Request Held, Request Released, Stock Audit Completed, Stock Audit Started, Unloading Completed, Unloading Started |
| Goods | 7 | 14 | 19 | 1 | Dispatch Approved, Dispatch Requested, Goods Dispatched, Goods Received, Loading Completed, Loading Started, Packing Completed, Packing Started, Picking Completed, Picking Started, Putaway Completed, Putaway Started, Receipt Registered, Receiving Request Submitted, Request Checked, Request Held, Request Released, Unloading Completed, Unloading Started |
| Worker | 7 | 10 | 16 | 1 | Loading Completed, Loading Started, Packing Completed, Packing Started, Picking Completed, Picking Started, Putaway Completed, Putaway Started, Receipt Registered, Request Checked, Request Held, Request Released, Stock Audit Completed, Stock Audit Started, Unloading Completed, Unloading Started |
| Receiving Request | 26 | 8 | 10 | 0 | Goods Received, Putaway Completed, Putaway Started, Receipt Registered, Receiving Request Submitted, Request Checked, Request Held, Request Released, Unloading Completed, Unloading Started |
| Receipt | 23 | 2 | 2 | 0 | Goods Received, Receipt Registered |
| Dispatch Order | 20 | 6 | 9 | 0 | Dispatch Approved, Dispatch Requested, Goods Dispatched, Loading Completed, Loading Started, Packing Completed, Packing Started, Picking Completed, Picking Started |
| Stock Audit | 9 | 1 | 2 | 0 | Stock Audit Completed, Stock Audit Started |
| Stock Movement | 39 | 2 | 2 | 0 | Goods Dispatched, Goods Received |
| Request Action | 56 | 3 | 3 | 0 | Request Checked, Request Held, Request Released |
| Warehouse Task | 63 | 3 | 6 | 0 | Packing Completed, Packing Started, Picking Completed, Picking Started, Putaway Completed, Putaway Started |
| Handling Record | 41 | 2 | 4 | 0 | Loading Completed, Loading Started, Unloading Completed, Unloading Started |

- Warehouse and goods views aggregate independent jobs. Worker views include only directly recorded work/receipt/audit/action participation.
- Work and audit records retain their own identities and their separate start and completion instants. No completion is fabricated for an open occurrence.
