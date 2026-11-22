# BPI Challenge 2019

This database is reconstructed from purchasing records from the BPI Challenge 2019 OCEL conversion. Use the known event–object links to evaluate whether an extraction recovers the correct events for each case.

## Source and conversion

[Source record and conversion workflow](../README.md#verified-upstream-sources) · [Get the SQLite database and references](../README.md#obtain-the-database-and-references)

## Relational schema

The published [dictionary](input/data_dictionary.json) describes 4 tables. `activity_subject` associates an `activity_record` with a `business_entity`; `entity_link` stores direct object-to-object relations when supplied. The converted dictionary declares no foreign-key constraints. The streaming conversion retains identifiers, types, timestamps and direct links. Attribute histories are outside this representation.

| Table | Rows in the published dictionary | Primary key |
|---|---:|---|
| `activity_record` | 1,595,923 | `record_id` |
| `activity_subject` | 5,984,602 | `record_id`, `entity_id`, `role` |
| `business_entity` | 330,685 | `entity_id` |
| `entity_link` | 0 | `source_entity_id`, `target_entity_id`, `relation_role` |

## Questions, EEG and Gold

| Resource | Availability |
|---|---|
| Natural-language requests | No authored question set is checked in. The conversion produces reference case views by object type. |
| Runtime EEG | [Local EEG reviewer](../../../tools/review_gui/) accepts an external Step 1 export after the DB is available. No runtime graph is bundled. |
| Reference event logs | The workflow artifact includes per-type event and case CSVs under `review/gold_flatten/`. [Reference semantics](../README.md#read-the-reference) |

[Event-log-derived datasets](../) · [All datasets](../../)
