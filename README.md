# NL2EventLog

NL2EventLog studies how to extract a process-mining event log from a relational database and a natural-language request. A request specifies what to follow (for example, each hospital admission) and which events to include. The result groups activity occurrences and their timestamps by case.

This repository publishes benchmark databases, questions, reference extractions and human review tools. The [method specification](docs/system/EEG_ENTITY_MODEL.md) describes how an Event Extraction Graph (EEG) connects database evidence to events and entities. The Step 1 runtime runs separately.

## Start with a dataset

| If you want to… | Start here |
|---|---|
| Follow one request all the way from tables to Gold SQL, an event log and a directly-follows graph (DFG) | [HospitalFlow walkthrough](datasets/synthetic/hospitalflow/) |
| Choose among all 11 datasets by source, domain and available evaluation material | [Dataset catalog](datasets/) |
| Inspect a runtime EEG for a supported dataset | [Local EEG reviewer and export instructions](tools/review_gui/) |

## Repository layout

| Directory | Contents |
|---|---|
| [datasets/](datasets/) | Database inputs, dataset-specific construction notes and evaluation artifacts, grouped by how the database was produced |
| [docs/](docs/) | Method contracts, dictionary specification and benchmark audits |
| [tools/](tools/) | Shared converters, inspection and review generators, question utilities and validation scripts |
| [tests/](tests/) | Checks for converters, dictionary handling, review tools and question processing |
| [.github/workflows/](.github/workflows/) | Reproducible builds, audits and artifact publication |

For an extraction run, supply the selected SQLite database, its data dictionary and one request text. Keep reference SQL, reference events, author mappings and review pages on the evaluator side. The catalog identifies datasets that require decompression or a separate build.
