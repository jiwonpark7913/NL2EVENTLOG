# NL2EventLog synthetic development datasets

- Three independent English relational databases support natural-language event-log extraction.
- Original source definitions are retained; typed business-action histories extend the domains with explicitly authored lifecycles.
- Each dataset includes an executable DB, requirements, data dictionary, square-table draw.io/PNG ERDs, questions, ES, SQL and Gold CSVs.

| Dataset | Tables | Object / case types | Activity types | Timestamp columns | Event timestamp columns | Distinct events | Questions | Gold CSVs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| [WarehouseFlow](datasets/warehouseflow/README.md) | 8 | 6 | 10 | 6 | 6 | 394 | 34 | 32 |
| [UniversityFlow](datasets/universityflow/README.md) | 11 | 11 | 41 | 40 | 40 | 808 | 70 | 66 |
| [PlateFlow](datasets/plateflow/README.md) | 9 | 8 | 39 | 39 | 31 | 1108 | 44 | 42 |

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

## Question types and pairs

- **Q1 Explicit:** case concept and exact activities.
- **Q2 Paraphrased:** alternate wording of Q1, with identical Gold scope.
- **Q3 Full Lifecycle:** case concept only, using the declared default recorded scope.
- **Q4 Full Lifecycle Paraphrased:** alternate wording of Q3, with identical Gold scope.
- `question_type`, `question_type_name`, `pair_of` and `answerability` are included in every question and Gold answer.
- Type and answerability are separate: unavailable actions remain unsupported; empty observed logs are not automatically unsupported.
- [warehouseflow question list](datasets/warehouseflow/docs/questions.md)
- [universityflow question list](datasets/universityflow/docs/questions.md)
- [plateflow question list](datasets/plateflow/docs/questions.md)

### Question statistics by dataset and type

| Dataset | Type | Questions | Answerable | Non-answerable | Avg. requested activity types |
|---|---|---:|---:|---:|---:|
| WarehouseFlow | Q1 | 10 | 9 | 1 | 2.50 |
| WarehouseFlow | Q2 | 10 | 9 | 1 | 2.50 |
| WarehouseFlow | Q3 | 7 | 7 | 0 | 10.00 |
| WarehouseFlow | Q4 | 7 | 7 | 0 | 10.00 |
| UniversityFlow | Q1 | 23 | 21 | 2 | 2.35 |
| UniversityFlow | Q2 | 23 | 21 | 2 | 2.35 |
| UniversityFlow | Q3 | 12 | 12 | 0 | 9.92 |
| UniversityFlow | Q4 | 12 | 12 | 0 | 9.92 |
| PlateFlow | Q1 | 13 | 12 | 1 | 2.77 |
| PlateFlow | Q2 | 13 | 12 | 1 | 2.77 |
| PlateFlow | Q3 | 9 | 9 | 0 | 17.33 |
| PlateFlow | Q4 | 9 | 9 | 0 | 17.33 |

- Avg. requested activity types = sum of requested activity-type counts / all questions in that row, including non-answerable questions. Q3/Q4 counts use the Gold catalog scope. This counts distinct activity types, not event occurrences.

- All pairs are one-to-one: Q1 ↔ Q2 and Q3 ↔ Q4. Missing originals/paraphrases are repaired during question construction.
- Process View already includes activity scope; activities are not a separate concept added to it.
- Each question list includes requested and extractable activity counts.

- PlateFlow uses its original nine business-table roles: one-time milestone columns plus repeatable operation-history rows. WarehouseFlow and UniversityFlow retain their existing storage designs.

## Timestamp columns

- Timestamp columns count physical table.column pairs storing date-and-time instants. Date-only birth/planning fields and recurring class schedules are excluded. Event timestamp columns are the subset actually selected as event times by the current ES; plans, technical times, snapshots, interval starts and copied key timestamps are listed separately.

| Dataset | Baseline timestamp columns before milestone expansion | Current timestamp columns | Current event timestamp columns |
|---|---:|---:|---:|
| WarehouseFlow | 2 | 6 | 6 |
| UniversityFlow | 14 | 40 | 40 |
| PlateFlow | 37 | 39 | 31 |
