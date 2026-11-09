# Warehouseflow — Gold source inventory

**Author annotations.** One identity OT per physical table; event-to-object attribution is a separate relation.

| Physical table | Gold Object Type | Gold activity source labels |
|---|---|---|
| dispatch_order | Dispatch Order | Dispatch Approved, Dispatch Requested |
| goods | Goods | — |
| goods_movement | Stock Movement | Goods Dispatched, Goods Received |
| goods_receipt | Receipt | Receipt Registered |
| handling_history | Handling Record | Loading Completed, Loading Started, Unloading Completed, Unloading Started |
| receiving_request | Receiving Request | Receiving Request Submitted |
| request_action | Request Action | Request Checked, Request Held, Request Released |
| warehouse | Warehouse | — |
| warehouse_audit | Stock Audit | Stock Audit Completed, Stock Audit Started |
| warehouse_task_history | Warehouse Task | Packing Completed, Packing Started, Picking Completed, Picking Started, Putaway Completed, Putaway Started |
| work_code | work_code | — |
| worker | Worker | — |

This is a source-binding projection. The model is not given this file.

[Gold diagram](../database/gold_evidence_graph.svg) · [Gold DFGs](README.md)
