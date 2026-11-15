# WarehouseFlow — Gold source inventory

**Legacy author annotations.** Physical storage is described as Tables and Keys. A table may identify or reference several Entity Types through different keys; a single Entity can appear in several tables. The displayed type labels are legacy author annotations, not validated semantic ET truth. Type classification, Entity identity resolution, and event attribution are separate decisions.

| Physical table | Entity Type candidate | Gold activity source labels |
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

[Table/key review inventory](entity_model_candidates.json) — reviewer-only, not model input.
