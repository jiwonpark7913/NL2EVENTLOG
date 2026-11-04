# Object activity storage

- Activity values and milestone-column meanings are kept in separate tables. Warehouse extensions remain in the single-carrier action history. Events are extracted once, not mirrored in two places.
- Original event IDs and occurrence times are preserved. All added fields are authored synthetic extensions.

| Object | Activities | Storage |
|---|---|---|
| transaction_record | Receiving Requested; Receiving Scheduled; Receiving Inspection Completed; Goods Put Away; Dispatch Requested; Dispatch Approved; Goods Picked; Goods Packed | transaction_record_activity |
