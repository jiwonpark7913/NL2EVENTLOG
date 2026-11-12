# WarehouseFlow

WarehouseFlow is a synthetic warehouse operations database covering goods, receiving requests, dispatch, stock movement, handling, worker tasks and audits. It uses authored business records rather than observed warehouse transactions.

[Relational schema](#relational-schema-sql-foreign-keys) · [Table previews](#table-inspector) · [Questions](#questions)

## Dataset overview

| Physical ERs | Entity Type candidates | Core business concepts | Gold SQL/CSV pairs verified |
|---:|---:|---:|---:|
| 12 | 12 | 5 | 50 |

[SQLite database](input/database.sqlite) · [Business Data Dictionary](input/data_dictionary.json) · [Readable dictionary](docs/data_dictionary.md)

## Gold Event Extraction Graph (EEG) Source Projection

![Entity Type candidates → Entity Representations → Activities](review/database/gold_evidence_graph.svg)

The diagram distinguishes core business entity concepts from supporting entity and event-record types. 
Each physical ER has exactly one currently annotated Entity Type candidate. Event-to-entity case attribution is separate from the source ER's provisional ET annotation; FK paths alone do not establish lifecycle membership.

**This is a source-level author-annotated projection, not an inferred EEG or a validated namespace-aware ET Gold.**
Gold SQL and record-level evidence are available in the linked inspection materials; their internal consistency does not validate the target namespace model. The current membership labels originate from the pre-namespace Gold; an independently validated ET/Identity Namespace Gold is a separate evaluation task.



**Entity-model status:** A physical table is one **Entity Representation (ER)**. Its displayed **Entity Type (ET) candidate** comes from legacy Gold annotations. ET semantic grouping and cross-ER instance identity resolution must be validated independently. FK reachability alone does not establish Case Attribution or Lifecycle Membership. [Terminology and namespace contract](../../docs/system/EEG_ENTITY_MODEL.md).

## Relational Schema (SQL foreign keys)

![Relational database schema](review/database/schema.svg)

**Yellow:** Gold event-time source, where established. **Blue:** other temporal columns. A temporal column is not automatically an event timestamp.

[Open full-size ERD](review/database/schema.svg) · [Editable Draw.io diagram](docs/schema.drawio) · [Timestamp inventory and roles](docs/timestamp_columns.md)

## Table inspector

| Physical table | Rows | Columns | ET candidate | First ten records |
|---|---:|---:|---|---|
| dispatch_order | 20 | 7 | Dispatch Order | [Preview](review/database/tables/dispatch_order.md) |
| goods | 7 | 3 | Goods | [Preview](review/database/tables/goods.md) |
| goods_movement | 39 | 9 | Stock Movement | [Preview](review/database/tables/goods_movement.md) |
| goods_receipt | 23 | 5 | Receipt | [Preview](review/database/tables/goods_receipt.md) |
| handling_history | 41 | 8 | Handling Record | [Preview](review/database/tables/handling_history.md) |
| receiving_request | 26 | 5 | Receiving Request | [Preview](review/database/tables/receiving_request.md) |
| request_action | 56 | 6 | Request Action | [Preview](review/database/tables/request_action.md) |
| warehouse | 4 | 5 | Warehouse | [Preview](review/database/tables/warehouse.md) |
| warehouse_audit | 9 | 6 | Stock Audit | [Preview](review/database/tables/warehouse_audit.md) |
| warehouse_task_history | 63 | 9 | Warehouse Task | [Preview](review/database/tables/warehouse_task_history.md) |
| work_code | 10 | 3 | work_code | [Preview](review/database/tables/work_code.md) |
| worker | 7 | 4 | Worker | [Preview](review/database/tables/worker.md) |

## Entity Type candidates vs. core business objects

Legacy identity groups (ET candidates): **12**; principal business object concepts in this domain: **5**. 
The core set is a candidate semantic grouping, not a rule for merging unrelated instances or Identity Namespaces.

**Core business concepts:** Dispatch Order, Goods, Receiving Request, Warehouse, Worker.

Supporting Gold types: Handling Record, Receipt, Request Action, Stock Audit, Stock Movement, Warehouse Task, work_code.

## Evaluation evidence

- Gold SQL/CSV pairs executable and consistent: 50; compared event rows across questions: 5478.
- [Gold source inventory](review/gold_dfg/event_graph.md)
- [Question-level Gold DFGs](review/gold_dfg/README.md)
- [Editable Draw.io schema](docs/schema.drawio)


## Questions

[**Full question list, types and answerability**](docs/questions.md) · [Question texts (JSONL)](evaluation/model_questions.jsonl) · [Question-level Gold DFGs and source records](review/gold_dfg/README.md)

The checked-in question file contains **54 requests**. Explicit requests enumerate activities; implicit requests ask for a recorded lifecycle. Paired paraphrases, where present, are listed in the question documentation.

<details>
<summary>Browse all 54 question texts</summary>

| ID | Request |
|---|---|
| W01 | For each receiving request, extract Receiving Request Submitted events. |
| W01P | For every receiving request, show when it was submitted. |
| W02 | For each receipt record, extract Receipt Registered events. |
| W02P | For each individual receipt record, show when the receipt was registered. |
| W03 | For each dispatch order, extract Dispatch Requested and Dispatch Approved events. |
| W03P | For every dispatch order, show when dispatch was requested and when it was approved. |
| W04 | For each stock audit, extract Stock Audit Started and Stock Audit Completed events. |
| W04P | Show when each stock audit began and when it finished. |
| W05 | For each stock movement record, extract Goods Received and Goods Dispatched events. |
| W05P | For every stock movement record, show the recorded receipt into stock or dispatch from stock, as applicable. |
| W06 | For each request action record, extract Request Checked, Request Held and Request Released events. |
| W06P | For each individual request action record, show the checking, holding or releasing action that was recorded. |
| W07 | For each warehouse task, extract Putaway Started, Putaway Completed, Picking Started, Picking Completed, Packing Started and Packing Completed events. |
| W07P | For every warehouse task, show the recorded beginnings and completions of putaway, picking or packing, as applicable. |
| W08 | For each handling record, extract Unloading Started, Unloading Completed, Loading Started and Loading Completed events. |
| W08P | For each handling record, show when unloading or loading began and finished, as applicable. |
| W09 | For each warehouse, extract Stock Audit Started, Stock Audit Completed, Putaway Started, Putaway Completed, Loading Started and Loading Completed events. |
| W09P | For each warehouse, show the beginnings and completions of its stock audits, putaway work and loading work. |
| W10 | For each receiving request, extract Unloading Started, Unloading Completed, Receipt Registered, Goods Received, Putaway Started and Putaway Completed events. |
| W10P | For every receiving request, show the start and completion of unloading, registration of the receipt, receipt into warehouse stock, and the start and completion of putaway. |
| W11 | For each dispatch order, extract Picking Started, Picking Completed, Packing Started, Packing Completed, Loading Started, Loading Completed and Goods Dispatched events. |
| W11P | For each dispatch order, show when picking, packing and loading began and finished, together with the dispatch of goods from stock. |
| W12 | For each worker, extract Stock Audit Started, Stock Audit Completed, Picking Started and Picking Completed events. |
| W12P | For every worker, show when their stock audits and picking work began and finished. |
| W13 | For each goods type, extract Goods Received and Goods Dispatched events. |
| W13P | For each goods type, show its recorded receipts into warehouse stock and dispatches from stock. |
| W14 | For each receipt record, extract Receipt Registered and Goods Received events. |
| W14P | For every individual receipt record, show its registration and the corresponding receipt of goods into stock. |
| W15 | For each warehouse, extract Invoice Paid events. |
| W15P | For every warehouse, show when its invoices were paid. |
| W16 | For each dispatch order, extract Customer Delivery Completed events. |
| W16P | For each dispatch order, show when delivery to the customer was completed. |
| WF01 | Extract the full recorded lifecycle for each warehouse. |
| WF01P | Show the complete recorded history of each warehouse. |
| WF02 | Extract the full recorded lifecycle for each goods type. |
| WF02P | Build the entire recorded timeline associated with every goods type. |
| WF03 | Extract the full recorded lifecycle for each worker. |
| WF03P | Show every worker's full recorded history. |
| WF04 | Extract the full recorded lifecycle for each receiving request. |
| WF04P | Trace each receiving request through its complete recorded lifecycle. |
| WF05 | Extract the full recorded lifecycle for each receipt record. |
| WF05P | Show the entire recorded history associated with each individual receipt record. |
| WF06 | Extract the full recorded lifecycle for each dispatch order. |
| WF06P | Build a complete recorded timeline for every dispatch order. |
| WF07 | Extract the full recorded lifecycle for each stock audit. |
| WF07P | Show the full recorded history of each stock audit. |
| WF08 | Extract the full recorded lifecycle for each stock movement record. |
| WF08P | Trace each individual stock movement record through its entire recorded history. |
| WF09 | Extract the full recorded lifecycle for each request action record. |
| WF09P | Show the complete recorded history of every individual request action record. |
| WF10 | Extract the full recorded lifecycle for each warehouse task. |
| WF10P | Build the full recorded lifecycle of each warehouse task. |
| WF11 | Extract the full recorded lifecycle for each handling record. |
| WF11P | Trace every individual handling record through its complete recorded history. |

</details>

## Model input boundary

This README, diagrams, table previews and Gold evidence are reader/reviewer material. Do not supply Gold annotations or review materials to the model.
