# Recorded warehouse lifecycle convention

- Requests can select actual recorded starts, completions and point milestones. The full recorded lifecycle includes both actual starts and completions when present; an unfinished occurrence supplies its start only.
- A work kind and its start/completion are distinct concepts. Work attempts retain their identity across phases; different attempts remain separate.
- Warehouse and goods views contain business occurrences directly concerning that warehouse or goods type. They do not treat database maintenance as warehouse work.
- A worker view contains actual recorded actions, receipts, audits and work performed by that worker. A shared warehouse or goods type alone does not attribute another worker's work to them.
- A receiving-request view contains its submission, request actions, unloading, receipt registration, inbound stock posting and putaway work.
- A receipt view contains its registration and the corresponding inbound stock movement.
- A dispatch-order view contains its request/approval, picking, packing, loading and outbound stock movement.
- An individual audit, stock-movement, request-action, task or handling-record view contains only the occurrences documented by that record.
- Full recorded lifecycle means the scope above. It does not infer invoices or customer delivery. Empty cases remain in the population even when no event rows exist.
