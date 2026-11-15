# Microsoft AdventureWorks OLTP

A SQLite snapshot of Microsoft's **AdventureWorks 2025 OLTP installation exports**, covering sales, purchasing, manufacturing, personnel and shared reference data. This is a publicly available Microsoft sample database, **not real enterprise transaction data**. It is separate from AdventureWorksDW and AdventureWorksLT.

## Explore the database

- [Model inputs: database and data dictionary](input/)
- [Editable draw.io schema](docs/schema.drawio): all 71 tables and all declared foreign keys, plus separate pages for each SQL Server schema. Date/time columns are highlighted in amber. Arrows show declared physical many-to-one references; optionality is not depicted.
- [Database inspection and first 10 actual rows per table](review/database/README.md)
- [Readable data dictionary](docs/data_dictionary.md)
- [SQLite DDL](evaluation/schema.sql)
- [Original Microsoft SQL Server installation script](source/instawdb.sql)
- [Pinned source, file hashes, row counts and validation results](source/provenance.json)

| Tables | Exported records | Declared foreign-key constraints | Business schemas |
|---:|---:|---:|---:|
| 71 | 759,240 | 90 | 5 + dbo administration |

`DatabaseLog` and `ErrorLog` are retained as empty tables: the source exports contain no rows for them, and SQL Server setup-generated log records are not fabricated. `AWBuildVersion` uses the supplied export rather than the local build time. No tables or exported business rows are sampled or synthesized.

## Model input boundary

Supply exactly these two files:

1. [`input/database.sqlite`](input/database.sqlite)
2. [`input/data_dictionary.json`](input/data_dictionary.json)

The dictionary combines physical SQLite constraints with Microsoft's original `MS_Description` table/column descriptions and SQL Server column declarations. Descriptions include business code meanings where Microsoft supplied them. It does **not** add authored Entity Types, event candidates, case notions, join paths, event labels, or assumed row-grain explanations.

The upstream installation script omits descriptions for two tables (`WorkOrder`, `WorkOrderRouting`) and 25 columns. These descriptions remain empty in the JSON and explicitly absent in the readable DD; they are not silently inferred. The exact omissions are listed in the provenance manifest. In particular, a missing official description is not evidence that a column is irrelevant.

Questions, reference logs, Gold SQL and Gold DFGs have **not been authored or evaluated** for this addition. This is a source database for discovery and extraction experiments, rather than a fifth completed gold-labelled benchmark. Natural-language requests should be supplied separately.

## SQLite conversion

- Original unqualified table and column names are preserved. SQL Server schemas are recorded as `source_schema` in the DD; queries use e.g. `"SalesOrderHeader"`, not `Sales.SalesOrderHeader`. All original table names are unique across schemas.
- All 71 tables, primary keys, composite keys, and 90 declared foreign-key constraints are preserved. SQL Server triggers, views, procedures, indexes other than primary keys, default evaluation, and CHECK constraints are not implemented. This snapshot is intended for read-only extraction.
- Integer types and flags map to SQLite `INTEGER`. Decimal/money values remain exact source strings in `TEXT`; arithmetic queries must cast explicitly. Dates/times retain their source strings and precision. **No timezone is inferred** from these timezone-naive exports.
- XML, GUID and hierarchyid export representations remain text; geography and binary/image exports are decoded from hexadecimal into BLOBs. SQL Server type methods are unavailable.
- Computed columns are **materialized using their supplied export values**, preserving the snapshot; computed expressions are retained in `source_declaration`. They are not recomputed when rows are edited.
- Bulk export field/row terminators are interpreted per source table, including embedded newlines. CRLF becomes LF. A single NUL character represents an empty string; empty nullable fields become SQL NULL, matching SQL Server bulk export conventions.
- Keep planned, actual, valid-time and maintenance timestamps as supplied. A current status plus `ModifiedDate` does not establish a full status-transition history.

## Reproduce

Requires Python 3 with its standard library and network access to Microsoft's GitHub repository:

```bash
python datasets/adventureworks/build.py --cache /tmp/adventureworks-source
python datasets/adventureworks/validate.py
python tools/build_dataset_review.py --dataset adventureworks
```

The [dataset build workflow](../../.github/workflows/adventureworks-dataset.yml) also performs these steps and commits the validated SQLite snapshot when the builder or pinned source manifest changes.

The builder verifies every downloaded file against the pinned Git blob hashes, builds the DB and DD, checks SQLite integrity and foreign keys, and writes the editable draw.io schema. The cache is an intermediate download directory, not model input.

## Source and license

- [Official Microsoft OLTP source](https://github.com/microsoft/sql-server-samples/tree/8fe3fd0c9a825fef3ae6d601e97537b612d7b214/samples/databases/adventure-works/oltp-install-script)
- [Microsoft installation instructions](https://learn.microsoft.com/en-us/sql/samples/adventureworks-install-configure)
- Upstream commit: `8fe3fd0c9a825fef3ae6d601e97537b612d7b214`.
- [Microsoft sample license (MIT)](source/LICENSE.txt). Original source descriptions and records retain Microsoft's copyright and license.
