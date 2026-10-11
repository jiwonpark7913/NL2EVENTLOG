# Object-based event logs

- Each answerable row below has its own English question, Gold specification, SQL and CSV event log.
- Business objects, event records and association records are labelled separately; a row-level case is useful for coverage but is not necessarily a rich business lifecycle.
- Case population includes records with no selected events; their event CSV has no row.
- One event may belong to several different cases, such as multiple goods types or workers. These are valid event-to-case links; the same event is not repeated within one case.
- Every view uses the exact scope stated below. Related upstream or downstream events are not automatically included through every reachable join.
- Existing explicit/paraphrase questions are retained. Paired questions may have identical Gold logs.
- Logs are case-based CSVs, not OCEL files.

| Case table | Case concept | Kind | Question | Cases | Event rows | Gold CSV |
|---|---|---|---|---:|---:|---|
| warehouse | Warehouse | business object | OW01 | 4 | 80 | [CSV](../private/gold_logs/OW01.csv) |
| goods | Goods | business object | OW02 | 6 | 138 | [CSV](../private/gold_logs/OW02.csv) |
| loader | Worker | business object | OW03 | 5 | 167 | [CSV](../private/gold_logs/OW03.csv) |
| transaction_record | Warehouse transaction | event record | OW04 | 80 | 80 | [CSV](../private/gold_logs/OW04.csv) |
| goods_transaction_detail | Goods transaction line | association record | OW05 | 138 | 138 | [CSV](../private/gold_logs/OW05.csv) |
| loader_transaction | Worker transaction assignment | association record | OW06 | 167 | 167 | [CSV](../private/gold_logs/OW06.csv) |

## Scope of each view

- **OW01 — Warehouse:** All receiving and dispatching tasks recorded for this warehouse.
- **OW02 — Goods:** Receiving and dispatching tasks that contain this goods type; one event per goods type and transaction.
- **OW03 — Worker:** Receiving and dispatching tasks assigned to this worker; one event per worker and transaction.
- **OW04 — Warehouse transaction:** The single receiving or dispatching event represented by this transaction.
- **OW05 — Goods transaction line:** The transaction event linked to this composite-key goods line.
- **OW06 — Worker transaction assignment:** The transaction event linked to this composite-key worker assignment.

## Tables without an actual event-log view

- Every keyed table in this database has an actual recorded-event view.
