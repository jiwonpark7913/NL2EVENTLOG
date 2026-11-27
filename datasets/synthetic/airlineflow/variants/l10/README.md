# AirlineFlow L10 — Passenger and booking

[Dataset home](../../README.md) · [Analysis](../../docs/dataset_analysis.md)

**10 tables · 47 columns · 34,563 rows**. Extends L05 by five tables; shared records are unchanged.

[SQLite database](input/database.sqlite) · [Data dictionary (readable)](docs/data_dictionary.md) · [Data dictionary (JSON)](input/data_dictionary.json) · [SQL DDL](input/schema.sql) · [Reference EEG example](../../docs/eeg_examples.md#l10) · [ERD SVG](docs/schema.svg)

![ERD — L10](docs/schema.svg)

Header colors identify the schema layer: L05 blue, L10 green, L15 amber, L20 purple. Arrows show declared foreign keys; inbound and outbound flight references are distinct.

## Tables introduced at this level

| Table | Rows | Purpose |
|---|---:|---|
| `bookings` | 2,537 | Reservations for groups of travellers. |
| `passengers` | 4,505 | Synthetic passenger register. The dataset records a single nationality, distinct from country of birth, residence or passport issuance. Date of birth is a passenger attribute. |
| `tickets` | 4,505 | Tickets issued to passengers. |
| `passenger_legs` | 6,885 | Ticketed segments linking a passenger ticket to a particular operating leg. |
| `passenger_actions` | 14,031 | Departure processing records for passenger flight legs. |

## Evaluation

12 applicable requests. Only SQLite, JSON dictionary and the request text are model inputs. Reference examples, Gold and review materials are evaluator-only.

Fixture: Stochastic-v2-CompactIDs-20261127.
