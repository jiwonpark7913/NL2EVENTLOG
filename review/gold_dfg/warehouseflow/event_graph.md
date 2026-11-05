# warehouseflow · Event graph inventory

**EVALUATION ONLY.** [Back to question and DFG review](README.md).

This page shows the authored benchmark graph. Table bindings identify where events are recorded. Object links identify which activities are attributed to an object, including activities recorded in other tables.

Each documented object view is listed as a singleton OT for review. Tables without a documented object view have no assigned OT here.

## Tables and event sources

| Table | Event classification | Carrier column | Selected event timestamps | Physical object (table · PK) | OT group | Events produced |
|---|---|---|---|---|---|---|
| `goods` | Non-event | — | — | `goods` · `goods_id` | Goods | — |
| `goods_transaction_detail` | Non-event | — | — | `goods_transaction_detail` · `goods_id`, `transaction_id` | Goods transaction line | — |
| `lifecycle_case_link` | Non-event | — | — | `lifecycle_case_link` · `event_id`, `case_table`, `case_id` | — | — |
| `loader` | Non-event | — | — | `loader` · `loader_id` | Worker | — |
| `loader_transaction` | Non-event | — | — | `loader_transaction` · `loader_id`, `transaction_id` | Worker transaction assignment | — |
| `transaction_record` | Event · carrier | `transaction_type` | `occurred_at` | `transaction_record` · `transaction_id` | Warehouse transaction | Goods Dispatched, Goods Received |
| `transaction_record_activity` | Event · carrier | `activity` | `occurred_at` | `transaction_record_activity` · `event_id` | — | Dispatch Approved, Dispatch Requested, Goods Packed, Goods Picked, Goods Put Away, Receiving Inspection Completed, Receiving Requested, Receiving Scheduled |
| `warehouse` | Non-event | — | — | `warehouse` · `warehouse_number` | Warehouse | — |

## Object types and attributed activities

| OT group | Member physical objects | Activities linked to OT |
|---|---|---|
| Warehouse | `warehouse` | Dispatch Approved, Dispatch Requested, Goods Dispatched, Goods Packed, Goods Picked, Goods Put Away, Goods Received, Receiving Inspection Completed, Receiving Requested, Receiving Scheduled |
| Goods | `goods` | Dispatch Approved, Dispatch Requested, Goods Dispatched, Goods Packed, Goods Picked, Goods Put Away, Goods Received, Receiving Inspection Completed, Receiving Requested, Receiving Scheduled |
| Worker | `loader` | Dispatch Approved, Dispatch Requested, Goods Dispatched, Goods Packed, Goods Picked, Goods Put Away, Goods Received, Receiving Inspection Completed, Receiving Requested, Receiving Scheduled |
| Warehouse transaction | `transaction_record` | Dispatch Approved, Dispatch Requested, Goods Dispatched, Goods Packed, Goods Picked, Goods Put Away, Goods Received, Receiving Inspection Completed, Receiving Requested, Receiving Scheduled |
| Goods transaction line | `goods_transaction_detail` | Dispatch Approved, Dispatch Requested, Goods Dispatched, Goods Packed, Goods Picked, Goods Put Away, Goods Received, Receiving Inspection Completed, Receiving Requested, Receiving Scheduled |
| Worker transaction assignment | `loader_transaction` | Dispatch Approved, Dispatch Requested, Goods Dispatched, Goods Packed, Goods Picked, Goods Put Away, Goods Received, Receiving Inspection Completed, Receiving Requested, Receiving Scheduled |

## Physical objects and attributed activities

| Physical object | OT group | Activities linked to this object |
|---|---|---|
| `goods` | Goods | Dispatch Approved, Dispatch Requested, Goods Dispatched, Goods Packed, Goods Picked, Goods Put Away, Goods Received, Receiving Inspection Completed, Receiving Requested, Receiving Scheduled |
| `goods_transaction_detail` | Goods transaction line | Dispatch Approved, Dispatch Requested, Goods Dispatched, Goods Packed, Goods Picked, Goods Put Away, Goods Received, Receiving Inspection Completed, Receiving Requested, Receiving Scheduled |
| `lifecycle_case_link` | — | No authored object view |
| `loader` | Worker | Dispatch Approved, Dispatch Requested, Goods Dispatched, Goods Packed, Goods Picked, Goods Put Away, Goods Received, Receiving Inspection Completed, Receiving Requested, Receiving Scheduled |
| `loader_transaction` | Worker transaction assignment | Dispatch Approved, Dispatch Requested, Goods Dispatched, Goods Packed, Goods Picked, Goods Put Away, Goods Received, Receiving Inspection Completed, Receiving Requested, Receiving Scheduled |
| `transaction_record` | Warehouse transaction | Dispatch Approved, Dispatch Requested, Goods Dispatched, Goods Packed, Goods Picked, Goods Put Away, Goods Received, Receiving Inspection Completed, Receiving Requested, Receiving Scheduled |
| `transaction_record_activity` | — | No authored object view |
| `warehouse` | Warehouse | Dispatch Approved, Dispatch Requested, Goods Dispatched, Goods Packed, Goods Picked, Goods Put Away, Goods Received, Receiving Inspection Completed, Receiving Requested, Receiving Scheduled |
