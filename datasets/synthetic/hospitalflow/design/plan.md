# HospitalFlow — active benchmark design

HospitalFlow is a synthetic MIMIC-IV-inspired relational database for natural-language event-log extraction.

**Physical schema:** 12 tables, including patient master `patients`, encounter `admissions`, and care-unit interval `transfers`.

**Object identity:** 11 legacy Entity Type candidates. `admissions` and `admission_detail` are merged by shared `hadm_id`; all other physical tables represent distinct entity or occurrence identities. Related objects are linked by FKs, not merged.

**Event semantics:** Gold activities are grounded in specific timestamp columns or event-bearing rows. `transfers.eventtype='transfer'` is extracted at `intime`; `admit` and `discharge` interval records are not duplicate events.

**Evaluation:** 44 questions, 42 answerable, 627 unique Gold events. The question-specific SQL and Gold CSV files are the executable oracle.

[Current schema](../docs/schema_overview.md) · [legacy Entity Type candidates](../docs/object_type_verification.md) · [Gold question DFGs](../review/gold_dfg/README.md)
