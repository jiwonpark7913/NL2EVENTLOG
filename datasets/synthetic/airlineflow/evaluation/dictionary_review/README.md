# Standard data dictionary edition

This edition is an optional, model-facing alternative to the original frozen JSON dictionaries. It is recommended for newly configured evaluations, but does not replace existing inputs or alter the frozen evaluation runner or variant manifest.

| Variant | Original | Standard |
|---|---|---|
| L05 | [Original](../../variants/l05/input/data_dictionary.json) | [Standard](../../variants/l05/input/data_dictionary_standard.json) |
| L10 | [Original](../../variants/l10/input/data_dictionary.json) | [Standard](../../variants/l10/input/data_dictionary_standard.json) |
| L15 | [Original](../../variants/l15/input/data_dictionary.json) | [Standard](../../variants/l15/input/data_dictionary_standard.json) |
| L20 | [Original](../../variants/l20/input/data_dictionary.json) | [Standard](../../variants/l20/input/data_dictionary_standard.json) |

## Changes

[Exact change log](changes.json) records 12 unique description edits and their applicability. All table/column keys, declarations, carrier definitions, timestamp-column definitions, and inbound/outbound roles are preserved. The standard edition removes explicit event-exclusion guidance and fixture-specific coverage or wording. The dataset remains synthetic.

## Evaluation policy

- Supply exactly one dictionary edition to each method, and record its checksum in the execution manifest. Use the same edition within a comparison.
- Existing results retain their original dictionary. Do not reinterpret the existing verification receipt as a new model result.
- No database, DDL, question, Gold, existing dictionary or frozen evaluation manifest is modified by this publication. [Standard manifest](standard_manifest.json) identifies the additional inputs.
- The code-master / distributed-knowledge comparison is a proposed future experiment, not an implemented fixture. Both conditions should share the same DB, questions, Gold and read-only access; only explicit code definitions in the supplied dictionary should differ.

## Validation scope

The publication checks JSON structure, unchanged non-description values, unchanged named carrier definitions, and identical shared table descriptions across the four variants. It does not rerun the SQLite Gold queries, verify the separate local Codex files, or reproduce the local 72-question audit. This change log is an independent GitHub-side implementation of the agreed policy, based on commit `c91a03240750a580c59734d5552fae71c02828d7`.
