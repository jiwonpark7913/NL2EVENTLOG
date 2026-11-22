# Order Management

This database is reconstructed from a simulated order-management OCEL. Use the known event–object links to evaluate whether an extraction recovers the correct events for each case.

## Source and conversion

[Source record and conversion workflow](../README.md#verified-upstream-sources) · [Get the SQLite database and references](../README.md#obtain-the-database-and-references)

## Relational schema

The published [dictionary](input/data_dictionary.json) describes 15 tables. `activity_subject` associates an `activity_record` with a `business_entity`; `entity_link` stores direct object-to-object relations when supplied. The converted dictionary declares no foreign-key constraints. Typed observation tables supplement the event and object relation tables.

| Table | Rows in the published dictionary | Primary key |
|---|---:|---|
| `activity_record` | 21,008 | `record_id` |
| `activity_subject` | 147,463 | `record_id`, `entity_id`, `role` |
| `business_entity` | 10,840 | `entity_id` |
| `entity_link` | 28,391 | `source_entity_id`, `target_entity_id`, `relation_role` |
| `observations_ConfirmOrder` | 2,000 | `record_id` |
| `observations_CreatePackage` | 1,128 | `record_id` |
| `observations_FailedDelivery` | 311 | `record_id` |
| `observations_ItemOutOfStock` | 1,544 | `record_id` |
| `observations_PackageDelivered` | 1,128 | `record_id` |
| `observations_PayOrder` | 2,000 | `record_id` |
| `observations_PaymentReminder` | 566 | `record_id` |
| `observations_PickItem` | 7,659 | `record_id` |
| `observations_PlaceOrder` | 2,000 | `record_id` |
| `observations_ReorderItem` | 1,544 | `record_id` |
| `observations_SendPackage` | 1,128 | `record_id` |

## Questions, EEG and Gold

| Resource | Availability |
|---|---|
| Natural-language requests | No authored question set is checked in. The conversion produces reference case views by object type. |
| Runtime EEG | [Local EEG reviewer](../../../tools/review_gui/) accepts an external Step 1 export after the DB is available. No runtime graph is bundled. |
| Reference event logs | The workflow artifact includes per-type event and case CSVs under `review/gold_flatten/`. [Reference semantics](../README.md#read-the-reference) |

[Event-log-derived datasets](../) · [All datasets](../../)
