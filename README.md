# NL2EventLog synthetic development datasets

- Three independent English relational databases support natural-language event-log extraction.
- Original source definitions are retained; typed business-action histories extend the domains with explicitly authored lifecycles.
- Each dataset includes an executable DB, requirements, data dictionary, square-table draw.io/PNG ERDs, questions, ES, SQL and Gold CSVs.

| Dataset | Tables | Object / case types | Activity types | Distinct events | Questions | Gold CSVs |
|---|---:|---:|---:|---:|---:|---:|
| [WarehouseFlow](datasets/warehouseflow/README.md) | 8 | 6 | 10 | 394 | 13 | 12 |
| [UniversityFlow](datasets/universityflow/README.md) | 20 | 11 | 41 | 808 | 26 | 24 |
| [PlateFlow](datasets/plateflow/README.md) | 16 | 8 | 37 | 1036 | 16 | 15 |


- **Activity types:** distinct recorded business labels across the whole database, counted once across all objects.
- **Object / case types:** keyed tables with answerable object-specific logs, including auxiliary record cases; this counts types, not individual instances. Activity-history tables, extraction indexes and reference tables are excluded.
- **Case:** the object used to group a timeline, such as a transaction, student or plate piece.
- **Event:** one actual recorded action with an event identity and occurrence time.
- **Gold:** expected answer for one question; paraphrase pairs may have identical logs.
- **ES:** extraction specification defining event sources, actual times, case population and explicit case attribution.
- **Activity type:** a business label; repeating one label increases occurrences, not the number of activity types.
- **Source fidelity:** new stages and times are authored additions, not claimed original RSchema/manufacturing fields.
- **Validation:** executable SQL equals Gold history, keys and case links are checked, and generation is deterministic. This is internal consistency, not an NL2EventLog evaluation result.
- **Auxiliary records:** operation/grading occurrence records can still have a single activity; main business-object logs have richer lifecycles.
- [Design methodology](DESIGN_METHODOLOGY.md)

## WarehouseFlow

- [Objects, activities, scenarios and files](datasets/warehouseflow/README.md)

![WarehouseFlow schema](datasets/warehouseflow/docs/schema.png)

## UniversityFlow

- [Objects, activities, scenarios and files](datasets/universityflow/README.md)

![UniversityFlow schema](datasets/universityflow/docs/schema.png)

## PlateFlow

- [Objects, activities, scenarios and files](datasets/plateflow/README.md)

![PlateFlow schema](datasets/plateflow/docs/schema.png)

