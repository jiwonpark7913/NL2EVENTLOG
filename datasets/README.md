# Dataset catalog

Choose by **how the relational input was produced**. Record origin is a separate property. For example, AdventureWorks is an imported sample database, while Order Management starts with a simulated event log.

| Database construction | Datasets | When to use them |
|---|---:|---|
| [Import upstream relational tables](source_relational/) | 3 | Study extraction on schemas defined outside this benchmark |
| [Convert an upstream event log](from_event_logs/) | 2 | Compare recovered events and case assignments with direct event–object links in the source log |
| [Generate a domain database](synthetic/) | 6 | Evaluate against authored references or compare controlled physical layouts |

## Choose a domain

| Dataset | Source records or design basis | Base tables | Questions and reference material in this repository |
|---|---|---:|---|
| [AdventureWorks](source_relational/adventureworks/) | Microsoft OLTP sample exports | 71 | Source DB and dictionary |
| [MIMIC-IV Demo](source_relational/mimic/) | Deidentified hospital and ICU records | 31 | Draft admission example for review |
| [Olist](source_relational/olist/) | Anonymized Brazilian marketplace CSV tables | 9 | Source DB and dictionary |
| [BPI Challenge 2019](from_event_logs/bpi2019_ocel/) | Purchasing event log converted to OCEL | 4 | Generated per-object-type reference logs |
| [Order Management](from_event_logs/order_management_ocel/) | Simulated order-management OCEL | 15 | Generated per-object-type reference logs |
| [HospitalFlow](synthetic/hospitalflow/) | MIMIC-IV-inspired hospital simulation | 12 | 40 requests, 40 reference logs |
| [PlateFlow](synthetic/plateflow/) | Steel-plate production simulation | 12 | 40 requests, 40 reference logs |
| [UniversityFlow](synthetic/universityflow/) | RSchema university requirements | 11 | 70 requests, 66 reference logs |
| [WarehouseFlow](synthetic/warehouseflow/) | RSchema warehouse requirements | 12 | 40 requests, 40 reference logs |
| [MaintenanceFlow](synthetic/maintenanceflow/) | Equipment maintenance, 13 layouts | 15 | 40 requests shared across layouts |
| [ProcurementFlow](synthetic/procurementflow/) | Procurement to payment, 6 layouts | 15 | 40 requests shared across layouts |

Table counts refer to the base SQLite layout or, for converted event logs, the published dictionary. A reference-log count is the number of question-specific CSV files. Variant counts include the base layout.

## Find an artifact inside a dataset

| Your question | Where to look |
|---|---|
| Where did the records come from? | Begin with the dataset README. Follow its upstream source, simulation or conversion instructions. |
| What tables and keys are available? | Open the ERD or schema inventory. The machine-readable dictionary is under `input/`. |
| What can the extraction method see? | Use `input/database.sqlite`, `input/data_dictionary.json` and one separately supplied question text. Check the dataset page for compressed or generated DBs. |
| Which requests are available? | Follow the question list in the dataset README. `evaluation/` can also hold answerability and scope annotations for the evaluator. |
| How can I inspect an EEG? | The [reviewer](../tools/review_gui/) accepts a genuine runtime export for its four supported datasets. A Flow dataset’s authored source projection is linked separately. |
| How can I verify a reference? | Follow the dataset’s Gold review page to inspect traces, DFGs and source rows. Authored SQL/CSV is under `private/`; event-log-derived references are generated in `review/gold_flatten/`. |

Not every dataset has a question set, Gold package or runtime EEG. Each dataset page identifies what is available.
