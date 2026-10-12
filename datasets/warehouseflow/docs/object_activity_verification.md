# Warehouse object–activity association verification

- The same activity-type set across warehouse, goods, workers and job records is expected under the current model: all these case views project the same IN/OUT jobs through declared links.
- Equality of activity labels does not mean equality of case identity, event membership or event counts. This is not six independent causal business processes.
- A transaction or its detail/worker assignment can contain receiving OR dispatch stages, not both. The table-wide activity union combines those two kinds of jobs.
- The original README table showed a union across all instances, which obscured this distinction.

| Case table | Activity types across all cases | Minimum types per active case | Maximum types per active case | Event rows | Mapping |
|---|---:|---:|---:|---:|---|
| warehouse | 10 | 10 | 10 | 394 | transaction_record.warehouse_number |
| goods | 10 | 10 | 10 | 679 | goods_transaction_detail(goods_id, transaction_id) |
| loader | 10 | 10 | 10 | 823 | loader_transaction(loader_id, transaction_id) |
| transaction_record | 10 | 4 | 5 | 394 | transaction_id |
| goods_transaction_detail | 10 | 4 | 5 | 679 | goods_id + transaction_id composite job line |
| loader_transaction | 10 | 4 | 5 | 823 | loader_id + transaction_id composite worker assignment |
