# WarehouseFlow New construction plan

- Provide four physical patterns: A has one actual timestamp and no activity carrier; B has multiple actual timestamps and no carrier; C has a varying activity-kind code plus one actual timestamp; D has a varying activity-kind code plus separate start/completion times.
- Include two business tables for each pattern plus four context/reference tables. Codes that describe goods category, condition, urgency, worker role, audit result or task outcome must not be interpreted as activity carriers.
- Preserve two axes in private Gold: base_activity and lifecycle_phase. Share occurrence_id for the two phases of the same work attempt while retaining unique event_id for each actual phase. Keep four-column case-based CSV compatibility.
- Full-lifecycle Gold includes both actual starts and completions. A pending attempt contributes its start without fabricated completion. This variant intentionally differs from PlateFlow New's earlier completion-only scope.
- Simulate receiving requests, request checks/holds/releases, unloading, receipt registration, stock movements, putaway, dispatch approval, picking, packing, loading and stock audits. Keep stock within capacity and nonnegative.
- Retain real declared business PK/FKs; no generic event/case index or object/type table is exposed in the input DB. Each request/order has one goods type; multi-line orders are out of scope.
- Freeze Q1/Q3 seeds before assistant-LLM paraphrasing into Q2/Q4. Preserve phase scope and exact Gold pair identity.
- Keep table and activity-carrier classification in README, outside all business dictionary JSON/Markdown/CSV files. Use an explicit model-input allowlist.
- Validate all four patterns against physical schema and independent generation history, not against a learned classifier. Check source/time/code/phase identity, incomplete attempts, repeated work, own/FK attribution, stock, constraints and input leakage.
