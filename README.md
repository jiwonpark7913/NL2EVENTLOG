# NL2EventLog synthetic development datasets

- Three independent English relational databases support natural-language event-log extraction.
- Original source definitions are retained; typed business-action histories extend the domains with explicitly authored lifecycles.
- Each dataset includes an executable DB, requirements, data dictionary, square-table draw.io/PNG ERDs, questions, ES, SQL and Gold CSVs.

| Dataset | Tables | Object / case types | Activity types | Distinct events | Questions | Gold CSVs |
|---|---:|---:|---:|---:|---:|---:|
| [WarehouseFlow](datasets/warehouseflow/README.md) | 8 | 6 | 10 | 394 | 32 | 30 |
| [UniversityFlow](datasets/universityflow/README.md) | 20 | 11 | 41 | 808 | 62 | 58 |
| [PlateFlow](datasets/plateflow/README.md) | 9 | 8 | 37 | 1036 | 42 | 40 |

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
| WarehouseFlow | Q1 | 9 | 8 | 1 | 2.33 |
| WarehouseFlow | Q2 | 9 | 8 | 1 | 2.33 |
| WarehouseFlow | Q3 | 7 | 7 | 0 | 10.00 |
| WarehouseFlow | Q4 | 7 | 7 | 0 | 10.00 |
| UniversityFlow | Q1 | 19 | 17 | 2 | 2.05 |
| UniversityFlow | Q2 | 19 | 17 | 2 | 2.05 |
| UniversityFlow | Q3 | 12 | 12 | 0 | 9.83 |
| UniversityFlow | Q4 | 12 | 12 | 0 | 9.83 |
| PlateFlow | Q1 | 12 | 11 | 1 | 2.83 |
| PlateFlow | Q2 | 12 | 11 | 1 | 2.83 |
| PlateFlow | Q3 | 9 | 9 | 0 | 16.44 |
| PlateFlow | Q4 | 9 | 9 | 0 | 16.44 |

- Avg. requested activity types = sum of requested activity-type counts / all questions in that row, including non-answerable questions. Q3/Q4 counts use the Gold catalog scope. This counts distinct activity types, not event occurrences.

- All pairs are one-to-one: Q1 ↔ Q2 and Q3 ↔ Q4. Missing originals/paraphrases are repaired during question construction.
- Process View already includes activity scope; activities are not a separate concept added to it.
- Each question list includes requested and extractable activity counts.

- PlateFlow uses its original nine business-table roles: one-time milestone columns plus repeatable operation-history rows. WarehouseFlow and UniversityFlow retain their existing storage designs.
