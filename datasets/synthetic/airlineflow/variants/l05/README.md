# AirlineFlow L05 — Core aircraft turnaround

[Dataset home](../../README.md) · [Analysis](../../docs/dataset_analysis.md)

**5 tables · 30 columns · 960 rows**. Base schema.

[SQLite database](input/database.sqlite) · [Data dictionary (readable)](docs/data_dictionary.md) · [Data dictionary (JSON)](input/data_dictionary.json) · [SQL DDL](input/schema.sql) · [Reference EEG example](../../docs/eeg_examples.md#l05) · [ERD SVG](docs/schema.svg)

![L05 entity relationship diagram](docs/schema.svg)

The header colors identify the schema level where each table first appears: L05 blue, L10 green, L15 amber, L20 purple. Arrows show declared foreign keys; both inbound and outbound flight references are distinct.

## Tables introduced at this level

| Table | Rows | Purpose |
|---|---:|---|
| `boarding_sessions` | 96 | Flight-level boarding sessions at the origin of every dated operating leg. One session per flight in this example; inbound legs also have origin boarding records. |
| `flights` | 96 | Dated operating legs, including both inbound and outbound flights. Flight numbers repeat across dates. |
| `handling_jobs` | 288 | Ground handling work orders associated with aircraft turnarounds. |
| `movement_reports` | 432 | Estimated and actual movement messages for operating legs. Actual OUT and AIR refer to the origin; LAND and IN refer to the destination. Both inbound and outbound legs have all four actual movements; EST estimates origin off-block. |
| `turnarounds` | 48 | Ground stay at the focal airport linking an arriving operating leg to the next departing operating leg of the same aircraft. The overall handling start is the start of coordination, which can precede individual jobs. |

## Evaluation

12 shared pilot requests; the 60 held-out test requests are evaluated only at L15 under the release manifest.

Use the database and JSON dictionary as method inputs. The reference examples, Gold SQL/PI/ESpec, review workspace and statistics are evaluator-only; do not expose them to a model.
