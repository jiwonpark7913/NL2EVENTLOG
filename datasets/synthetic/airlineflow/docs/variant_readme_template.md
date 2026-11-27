# AirlineFlow @LEVEL@ — @DOMAIN@

[Dataset home](../../README.md) · [Analysis](../../docs/dataset_analysis.md)

**@TABLES@ tables · @COLUMNS@ columns · @COUNT@ rows**. @EXTENDS@

[SQLite database](input/database.sqlite) · [Data dictionary (readable)](docs/data_dictionary.md) · [Data dictionary (JSON)](input/data_dictionary.json) · [SQL DDL](input/schema.sql) · [Reference EEG example](../../docs/eeg_examples.md#@LOWER@) · [ERD SVG](docs/schema.svg)

![ERD — @LEVEL@](docs/schema.svg)

Header colors identify the schema layer: L05 blue, L10 green, L15 amber, L20 purple. Arrows show declared foreign keys; inbound and outbound flight references are distinct.

## Tables introduced at this level

| Table | Rows | Purpose |
|---|---:|---|
@INTRO@

## Evaluation

@SCOPE@ applicable requests. Only SQLite, JSON dictionary and the request text are model inputs. Reference examples, Gold and review materials are evaluator-only.

Fixture: @VERSION@.
