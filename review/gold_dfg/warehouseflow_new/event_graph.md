# warehouseflow_new · Event graph inventory

**EVALUATION ONLY.** [Back to question and DFG review](README.md).

This page shows the authored benchmark graph. Table bindings identify where events are recorded. Object links identify which activities are attributed to an object, including activities recorded in other tables.

Each documented object view is listed as a singleton OT for review. Tables without a documented object view have no assigned OT here.

## Tables and event sources

| Table | Event classification | Carrier column | Selected event timestamps | Physical object (table · PK) | OT group | Events produced |
|---|---|---|---|---|---|---|
| `dispatch_order` | Event · non-carrier | — | `approved_at`, `requested_at` | `dispatch_order` · `dispatch_id` | Dispatch Order | Dispatch Approved, Dispatch Requested |
| `goods` | Non-event | — | — | `goods` · `goods_id` | Goods | — |
| `goods_movement` | Event · carrier | `movement_code` | `occurred_at` | `goods_movement` · `movement_id` | Stock Movement | Goods Dispatched, Goods Received |
| `goods_receipt` | Event · non-carrier | — | `received_at` | `goods_receipt` · `receipt_id` | Receipt | Receipt Registered |
| `handling_history` | Event · carrier | `handling_code` | `completed_at`, `started_at` | `handling_history` · `handling_id` | Handling Record | Loading Completed, Loading Started, Unloading Completed, Unloading Started |
| `receiving_request` | Event · non-carrier | — | `submitted_at` | `receiving_request` · `request_id` | Receiving Request | Receiving Request Submitted |
| `request_action` | Event · carrier | `action_code` | `occurred_at` | `request_action` · `action_id` | Request Action | Request Checked, Request Held, Request Released |
| `warehouse` | Non-event | — | — | `warehouse` · `warehouse_id` | Warehouse | — |
| `warehouse_audit` | Event · non-carrier | — | `completed_at`, `started_at` | `warehouse_audit` · `audit_id` | Stock Audit | Stock Audit Completed, Stock Audit Started |
| `warehouse_task_history` | Event · carrier | `task_code` | `completed_at`, `started_at` | `warehouse_task_history` · `task_id` | Warehouse Task | Packing Completed, Packing Started, Picking Completed, Picking Started, Putaway Completed, Putaway Started |
| `work_code` | Non-event | — | — | `work_code` · `code_family`, `code` | — | — |
| `worker` | Non-event | — | — | `worker` · `worker_id` | Worker | — |

## Object types and attributed activities

| OT group | Member physical objects | Activities linked to OT |
|---|---|---|
| Warehouse | `warehouse` | Dispatch Approved, Dispatch Requested, Goods Dispatched, Goods Received, Loading Completed, Loading Started, Packing Completed, Packing Started, Picking Completed, Picking Started, Putaway Completed, Putaway Started, Receipt Registered, Receiving Request Submitted, Request Checked, Request Held, Request Released, Stock Audit Completed, Stock Audit Started, Unloading Completed, Unloading Started |
| Goods | `goods` | Dispatch Approved, Dispatch Requested, Goods Dispatched, Goods Received, Loading Completed, Loading Started, Packing Completed, Packing Started, Picking Completed, Picking Started, Putaway Completed, Putaway Started, Receipt Registered, Receiving Request Submitted, Request Checked, Request Held, Request Released, Unloading Completed, Unloading Started |
| Worker | `worker` | Loading Completed, Loading Started, Packing Completed, Packing Started, Picking Completed, Picking Started, Putaway Completed, Putaway Started, Receipt Registered, Request Checked, Request Held, Request Released, Stock Audit Completed, Stock Audit Started, Unloading Completed, Unloading Started |
| Receiving Request | `receiving_request` | Goods Received, Putaway Completed, Putaway Started, Receipt Registered, Receiving Request Submitted, Request Checked, Request Held, Request Released, Unloading Completed, Unloading Started |
| Receipt | `goods_receipt` | Goods Received, Receipt Registered |
| Dispatch Order | `dispatch_order` | Dispatch Approved, Dispatch Requested, Goods Dispatched, Loading Completed, Loading Started, Packing Completed, Packing Started, Picking Completed, Picking Started |
| Stock Audit | `warehouse_audit` | Stock Audit Completed, Stock Audit Started |
| Stock Movement | `goods_movement` | Goods Dispatched, Goods Received |
| Request Action | `request_action` | Request Checked, Request Held, Request Released |
| Warehouse Task | `warehouse_task_history` | Packing Completed, Packing Started, Picking Completed, Picking Started, Putaway Completed, Putaway Started |
| Handling Record | `handling_history` | Loading Completed, Loading Started, Unloading Completed, Unloading Started |

## Physical objects and attributed activities

| Physical object | OT group | Activities linked to this object |
|---|---|---|
| `dispatch_order` | Dispatch Order | Dispatch Approved, Dispatch Requested, Goods Dispatched, Loading Completed, Loading Started, Packing Completed, Packing Started, Picking Completed, Picking Started |
| `goods` | Goods | Dispatch Approved, Dispatch Requested, Goods Dispatched, Goods Received, Loading Completed, Loading Started, Packing Completed, Packing Started, Picking Completed, Picking Started, Putaway Completed, Putaway Started, Receipt Registered, Receiving Request Submitted, Request Checked, Request Held, Request Released, Unloading Completed, Unloading Started |
| `goods_movement` | Stock Movement | Goods Dispatched, Goods Received |
| `goods_receipt` | Receipt | Goods Received, Receipt Registered |
| `handling_history` | Handling Record | Loading Completed, Loading Started, Unloading Completed, Unloading Started |
| `receiving_request` | Receiving Request | Goods Received, Putaway Completed, Putaway Started, Receipt Registered, Receiving Request Submitted, Request Checked, Request Held, Request Released, Unloading Completed, Unloading Started |
| `request_action` | Request Action | Request Checked, Request Held, Request Released |
| `warehouse` | Warehouse | Dispatch Approved, Dispatch Requested, Goods Dispatched, Goods Received, Loading Completed, Loading Started, Packing Completed, Packing Started, Picking Completed, Picking Started, Putaway Completed, Putaway Started, Receipt Registered, Receiving Request Submitted, Request Checked, Request Held, Request Released, Stock Audit Completed, Stock Audit Started, Unloading Completed, Unloading Started |
| `warehouse_audit` | Stock Audit | Stock Audit Completed, Stock Audit Started |
| `warehouse_task_history` | Warehouse Task | Packing Completed, Packing Started, Picking Completed, Picking Started, Putaway Completed, Putaway Started |
| `work_code` | — | No authored object view |
| `worker` | Worker | Loading Completed, Loading Started, Packing Completed, Packing Started, Picking Completed, Picking Started, Putaway Completed, Putaway Started, Receipt Registered, Request Checked, Request Held, Request Released, Stock Audit Completed, Stock Audit Started, Unloading Completed, Unloading Started |
