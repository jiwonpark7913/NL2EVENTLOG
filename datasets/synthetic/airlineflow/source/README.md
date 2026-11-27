# Canonical synthetic records

[Dataset home](../README.md)

[records.json](records.json) holds the released synthetic logical records, with columns and row arrays per table. The generator populates each nested schema from these records. This source is for data regeneration and evaluator-side inspection only, not a model input.

The active seed generator is `generate_records_v2.mjs`, with operational attributes defined by `operational_fields_v1.json` and populated by `operational_enrichment.mjs`. Use `python ../generate.py --check` from this directory to compare a fresh seeded generation and four rebuilt databases with the released data. The review publication does not invoke historical migrations.
