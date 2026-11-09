# WarehouseFlow — Gold source inventory

**Legacy author annotations.** Every physical table is an ER. Candidate ET grouping is not yet validated for Identity Namespaces or lifecycle membership.

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

This is a source-binding projection. This is a reviewer-only candidate grouping and is not provided to the model.

[Gold diagram](../database/gold_evidence_graph.svg) · [Gold DFGs](README.md)

[Entity Representation and namespace candidates](entity_model_candidates.json) — review-only; **not validated semantic ET Gold**.
