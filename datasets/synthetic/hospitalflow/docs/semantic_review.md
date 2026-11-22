# HospitalFlow — current semantic evidence review

This document refers to the current **12-table synthetic HospitalFlow**, not the historical patient-profile split version.

- `patients` stores patient attributes and MIMIC-style de-identification anchors.
- `admissions` stores `admittime`, `dischtime`, `deathtime`, `edregtime`, and `edouttime`; the old `discharge_authorized_at` column no longer exists.
- `transfers` records care-unit intervals with `eventtype`, `careunit`, `intime`, and `outtime`; only `eventtype='transfer'` at `intime` contributes `Care Unit Transferred`.
- `storetime` is not automatically a business event timestamp; refer to the authored Gold bindings for its use in a given table.
- Activity codes require context-sensitive interpretation; the model-visible dictionary is the source for documented meanings.

[Current Data Dictionary](data_dictionary.md) · [Gold source inventory](../review/gold_dfg/event_graph.md) · [Question-level Gold SQL](../review/gold_dfg/README.md)
