# AirlineFlow L20 — Operating resources

[Dataset home](../../README.md) · [Analysis](../../docs/dataset_analysis.md)

**20 tables · 81 columns · 80,289 rows**. Extends L15 by five tables; shared records are unchanged.

[SQLite database](input/database.sqlite) · [Data dictionary (readable)](docs/data_dictionary.md) · [Data dictionary (JSON)](input/data_dictionary.json) · [SQL DDL](input/schema.sql) · [Reference EEG example](../../docs/eeg_examples.md#l20) · [ERD SVG](docs/schema.svg)

![ERD — L20](docs/schema.svg)

Header colors identify the schema layer: L05 blue, L10 green, L15 amber, L20 purple. Arrows show declared foreign keys; inbound and outbound flight references are distinct.

## Tables introduced at this level

| Table | Rows | Purpose |
|---|---:|---|
| `airlines` | 2 | Register of operating airlines. |
| `airports` | 3 | Airport register. |
| `aircraft` | 5 | Register of individual aircraft. |
| `employees` | 2 | Register of airline employees. |
| `flight_dispatch` | 200 | Assignments of operating resources to individual dated legs. |

## Evaluation

12 applicable requests. Only SQLite, JSON dictionary and the request text are model inputs. Reference examples, Gold and review materials are evaluator-only.

Fixture: Stochastic-v2-CompactIDs-20261127.
