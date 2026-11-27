# AirlineFlow — Stochastic-v2-ShortIDs-20261127

Synthetic relational event-log extraction benchmark. **100 turnarounds, 200 operating legs, 6,885 passenger legs; 72 requests / 108 DB–request conditions. Short opaque identifiers (4–5 digits); flight number remains a distinct operational attribute.**

## Database variants
| Variant | Tables | Rows | Inputs |
|---|---:|---:|---|
| [L05](variants/l05/README.md) | 5 | 2100 | [SQLite](variants/l05/input/database.sqlite) · [DD](variants/l05/input/data_dictionary.json) |
| [L10](variants/l10/README.md) | 10 | 34563 | [SQLite](variants/l10/input/database.sqlite) · [DD](variants/l10/input/data_dictionary.json) |
| [L15](variants/l15/README.md) | 15 | 80077 | [SQLite](variants/l15/input/database.sqlite) · [DD](variants/l15/input/data_dictionary.json) |
| [L20](variants/l20/README.md) | 20 | 80289 | [SQLite](variants/l20/input/database.sqlite) · [DD](variants/l20/input/data_dictionary.json) |

## Review
- [Integrated reference review](docs/scenario.html) (download and open locally; evaluator-only).
- [Query catalog](docs/queries.md) · [Gold summary](evaluation/gold_summary.csv) · [Registry](evaluation/query_registry.csv)
- [Design](docs/stochastic_fixture_v2.md) · [Generator configuration](source/stochastic_v2_config.json) · [Realized population](source/stochastic_v2_generator_preview.json)
- [Verification receipt](evaluation/verification.json) · [Analysis](docs/dataset_analysis.md)

## Reproduce
Run node source/generate_records_v2.mjs EMPTY_OUTPUT_DIRECTORY to regenerate records. Run python verify.py for read-only checks. The release build script regenerate_v2.py requires Node, Python and Graphviz and is intended for an isolated checkout.

## Validation
108 SQLite-query comparisons and 72 independent occurrence reconstructions passed in the release build. Human review and production scorer integration remain pending. No model inference performed. The older PM-Scope1 fixture remains in git history. Model input is only the chosen DB, its general DD, and request text. Never include evaluator metadata or the review HTML.

## Canonical vs enriched reference logs

Each Gold directory includes `events.csv` (scoring only) and `events_enriched.csv` (inspection/analysis). The integrated review provides both modes and independent `flight_no` / `operating_date` columns. Short numeric IDs remain the primary case identifiers. See [Gold log documentation](gold/README.md) and [verification](evaluation/verification.json).
