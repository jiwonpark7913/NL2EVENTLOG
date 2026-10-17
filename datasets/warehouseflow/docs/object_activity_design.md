# Object activity storage

- Actual one-time milestone columns and retained row histories are used together. Events are extracted once, not mirrored in two places.
- Original event IDs and occurrence times are preserved. All added fields are authored synthetic extensions.

| Object | Activities | Storage |
|---|---|---|
| transaction_record | Receiving Requested; Receiving Scheduled; Receiving Inspection Completed; Goods Put Away; Dispatch Requested; Dispatch Approved; Goods Picked; Goods Packed | Actual milestone columns on transaction_record; remaining repeatable actions stay in transaction_record_activity |
