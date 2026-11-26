# AirlineFlow

**A synthetic relational benchmark for natural-language event-log extraction and process mining.**

AirlineFlow models aircraft turnarounds at a focal airport, connecting arriving and departing flight legs to ground services, boarding, passenger processing, baggage and security records. Given a natural-language analysis request, a system extracts an event log with `case_id`, `activity`, and `timestamp` from a relational database and its general data dictionary.

**72 requests · 108 DB–request conditions · 4 nested schemas · 28 reference activity types**

[Database variants](#database-variants) · [Dataset analysis](#dataset-analysis) · [Queries and gold logs](#queries-and-gold-logs) · [Quick start](#quick-start) · [Validation and limitations](#validation-and-limitations)

## What can you use this dataset for?

| Use case | What AirlineFlow provides |
|---|---|
| Natural-language event-log extraction | English requests, SQLite inputs, and reference event triples |
| Process mining | Event logs at flight, turnaround, job, boarding session, passenger-leg and other case granularities |
| Schema scalability | Four nested schemas with unchanged shared records and 12 common pilot requests |
| Semantic and structural difficulty | Five matched-family test dimensions: depth, source diversity, activity count, explicitness, role attribution |
| Reproducible evaluation | Gold SQL, PI, ESpec, CSV, DFG and record-level inspection |

## Database variants

The four variants add five tables at each level. L15 is the main test database. L05–L20 form a nested schema-expansion series, not four independent datasets.

| Variant | Tables | Columns | Rows | Domain extension | Files |
|---|---:|---:|---:|---|---|
| [L05](variants/l05/README.md) | 5 | 30 | 960 | Core aircraft turnaround | [SQLite](variants/l05/input/database.sqlite) · [ERD](variants/l05/docs/schema.svg) · [DD](variants/l05/docs/data_dictionary.md) · [EEG example](docs/eeg_examples.md#l05) |
| [L10](variants/l10/README.md) | 10 | 47 | 2,232 | Passenger and booking | [SQLite](variants/l10/input/database.sqlite) · [ERD](variants/l10/docs/schema.svg) · [DD](variants/l10/docs/data_dictionary.md) · [EEG example](docs/eeg_examples.md#l10) |
| [L15](variants/l15/README.md) | 15 | 64 | 3,818 | Baggage and security | [SQLite](variants/l15/input/database.sqlite) · [ERD](variants/l15/docs/schema.svg) · [DD](variants/l15/docs/data_dictionary.md) · [EEG example](docs/eeg_examples.md#l15) |
| [L20](variants/l20/README.md) | 20 | 81 | 3,925 | Operating resources | [SQLite](variants/l20/input/database.sqlite) · [ERD](variants/l20/docs/schema.svg) · [DD](variants/l20/docs/data_dictionary.md) · [EEG example](docs/eeg_examples.md#l20) |

### Entity–relationship diagram (L20)

![AirlineFlow L20 ERD with color-coded schema layers](variants/l20/docs/schema.svg)

**Header colors:** blue = L05 core operations; green = L10 passenger/booking; amber = L15 baggage/security; purple = L20 resources/dispatch. The same colors are retained in all smaller diagrams.

<details>
<summary>L05 ERD — Core aircraft turnaround</summary>

![L05 ERD](variants/l05/docs/schema.svg)

</details>

<details>
<summary>L10 ERD — Passenger and booking</summary>

![L10 ERD](variants/l10/docs/schema.svg)

</details>

<details>
<summary>L15 ERD — Baggage and security</summary>

![L15 ERD](variants/l15/docs/schema.svg)

</details>

The readable dictionaries describe the business meaning, keys and timestamp columns. The model-facing version is the original JSON. [Reference EEG examples](docs/eeg_examples.md) demonstrate how selected event definitions can be connected to case entities; these are explanatory, not generated EEG outputs or inputs.

## Dataset analysis

![Test-set analysis](docs/dataset_statistics.svg)

The test set contains **60 requests / 49 distinct reference logs / 18 families**. Each of the five axes has 12 requests.

| Split / dimension | Requests | Evaluation conditions |
|---|---:|---:|
| Pilot / schema expansion | 12 | 48 |
| A · Attribution depth | 12 | 12 |
| B · Source diversity | 12 | 12 |
| C · Activity count | 12 | 12 |
| D · Semantic complexity | 12 | 12 |
| E · Attribution role | 12 | 12 |
| Total | 72 | 108 |

[Full dataset analysis and distribution tables](docs/dataset_analysis.md) · [Statistics JSON](docs/dataset_statistics.json) · [Reproduction script](docs/analyze_dataset.py).

## Queries and gold logs

The following request illustrates how a case and event scope are expressed.

> Where is time lost during aircraft turnarounds? For each turnaround, build an event log covering actual inbound arrival movements, the overall start of ground handling, completion of every ground service, boarding start and close, aircraft readiness, and actual outbound departure movements, from inbound landing to outbound take-off.

Q04 has 48 turnaround cases, 14 activity types and 672 event rows. The same business event may be attributed to different cases in other requests.

![Q04 gold DFG](gold/Q04/dfg.svg)

[Q04 Event Log](gold/Q04/events.csv) · [Gold SQL](gold/Q04/gold.sql) · [PI](gold/Q04/pi.json) · [ESpec](gold/Q04/espec.json)

[Browse all 72 requests and references](docs/queries.md) · [Pilot model questions](evaluation/model_questions.jsonl) · [Test model questions](evaluation/model_questions_test.jsonl) · [Full query registry](evaluation/query_registry.csv) · [Test registry](evaluation/test_registry.csv) · [Gold summary](evaluation/gold_summary.csv).

[Integrated reference review (download HTML)](https://raw.githubusercontent.com/jiwonpark7913/NL2EVENTLOG/main/datasets/synthetic/airlineflow/docs/scenario.html) — save the linked file and open it locally to inspect each reference log, DFG, source row and extraction path. It is evaluator-only.

## Quick start

Clone the repository or download the selected SQLite and JSON dictionary from the variant table.

```bash
cd datasets/synthetic/airlineflow
python verify.py
python generate.py /tmp/airlineflow-new
python docs/analyze_dataset.py
```

`verify.py` checks the published fixture against its references; `generate.py` reconstructs the current logical database from the canonical synthetic records in `source/records.json` and the schema DDLs. Use an empty output directory. The regenerated SQLite binary hashes may differ while logical records remain identical.

For model evaluation, provide only the appropriate `variants/lXX/input/database.sqlite`, `data_dictionary.json` and the request text. Do not include reference EEG examples, Gold, evaluator registries, review pages, source records or diagnostic answers in the model input.

## Repository guide

| Path | Purpose |
|---|---|
| [variants/](variants/) | Four SQLite databases, DDL, diagrams and dictionaries |
| [evaluation/](evaluation/README.md) | Requests, registry, manifest, technical receipts and scoring-policy references |
| [gold/](gold/README.md) | Per-request reference logs, SQL, PI, ESpec and DFG |
| [docs/](docs/README.md) | User-facing analysis, examples and inspection tools |
| [source/](source/README.md) | Canonical synthetic records for reproducibility |
| [semantic_check/](semantic_check/README.md) | Separate semantic-evidence diagnostics (not part of the 108 conditions) |
| [private/](private/) | Legacy evaluator-only references retained for compatibility |

## Validation and limitations

The published technical receipt reports 108/108 database–request comparisons. A separate evaluator-side semantic audit reports 72/72 reference multiset comparisons from the canonical records. These are dataset validation records, not model results or proof of completed external human review.

[Semantic review](evaluation/semantic_gold_review_20261127.md) · [Verification receipt](evaluation/verification.json) · [Case policy](evaluation/case_key_policy.json) · [Release history](docs/archive/release_history_20261127.md).

The data is synthetic, with fixed populations and simplified operational assumptions. Shared records and repeated reference logs imply dependence across requests. Test results should be reported separately from pilot; A–C are sensitivity analyses, not fully isolated causal experiments. The standalone scorer is an evaluator reference, not confirmation of production-runner integration. The release preserves timestamp multiplicity and treats equal-time events without inventing order.

Data fixture: `TemporalRevision1-SemanticDD1-CanonicalQ02` · [pinned input and reference commit](https://github.com/jiwonpark7913/NL2EVENTLOG/tree/e4bb9d19081bc8914e45db4acb750e4c581ea3f2/datasets/synthetic/airlineflow/).
