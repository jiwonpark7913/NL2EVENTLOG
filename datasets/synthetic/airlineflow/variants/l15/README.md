# AirlineFlow L15 — Baggage and security

[Dataset home](../../README.md) · [Analysis](../../docs/dataset_analysis.md)

**15 tables · 125 columns · 80,077 rows**. Extends L10 by five tables; shared records are unchanged.

[SQLite database](input/database.sqlite) · [Data dictionary (readable)](docs/data_dictionary.md) · [Data dictionary (JSON)](input/data_dictionary.json) · [SQL DDL](input/schema.sql) · [Reference EEG example](../../docs/eeg_examples.md#l15) · [ERD SVG](docs/schema.svg)

![ERD — L15](docs/schema.svg)

Header colors identify the schema layer: L05 blue, L10 green, L15 amber, L20 purple. Arrows show declared foreign keys; inbound and outbound flight references are distinct.

## Tables introduced at this level

| Table | Rows | Purpose |
|---|---:|---|
| `bag_legs` | 5,887 | Transport records for a sample of checked bags associated with passenger flight legs. |
| `bag_scans` | 11,595 | Individual baggage tracking records for the checked bags represented in the dataset. |
| `checkpoints` | 3 | Airport security screening checkpoints. |
| `security_visits` | 7,030 | Airport-provided records of individual passenger visits to security checkpoints. |
| `security_events` | 20,999 | Observations recorded during security checkpoint visits. |

## Evaluation

72 applicable requests. Only SQLite, JSON dictionary and the request text are model inputs. Reference examples, Gold and review materials are evaluator-only.

Fixture: Stochastic-v2-CompactIDs-20261127.
