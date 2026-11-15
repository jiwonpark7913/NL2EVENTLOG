# NL2EventLog

Four evaluation datasets, an AdventureWorks source database, and author review tools for natural-language-to-event-log extraction. The target method uses Tables and Keys, Entity Types (ETs), Entity identification rules, and Event definitions in a request-independent Event Extraction Graph (EEG).

## Repository map

- [Canonical EEG terminology and stage contracts](docs/system/EEG_ENTITY_MODEL.md)

- [System design](docs/system/) — methodology, event-table scope, paraphrase-generation policy.
- [Dataset inspection](datasets/) — four evaluation datasets plus an AdventureWorks source database, with separate **model input**, **evaluation ground truth**, and **human review** material.
- [Review generator](tools/build_dataset_review.py) — produces an ERD overview and **actual first 10 SQLite rows** per table.

| Dataset | Model input | Database review | Gold DFG review |
|---|---|---|---|
| [HospitalFlow](datasets/hospitalflow/) | [SQLite + dictionary](datasets/hospitalflow/input/) | [Inspection](datasets/hospitalflow/review/database/) | [DFG](datasets/hospitalflow/review/gold_dfg/) |
| [UniversityFlow](datasets/universityflow/) | [SQLite + dictionary](datasets/universityflow/input/) | [Inspection](datasets/universityflow/review/database/) | [DFG](datasets/universityflow/review/gold_dfg/) |
| [PlateFlow](datasets/plateflow/) | [SQLite + dictionary](datasets/plateflow/input/) | [Inspection](datasets/plateflow/review/database/) | [DFG](datasets/plateflow/review/gold_dfg/) |
| [WarehouseFlow](datasets/warehouseflow/) | [SQLite + dictionary](datasets/warehouseflow/input/) | [Inspection](datasets/warehouseflow/review/database/) | [DFG](datasets/warehouseflow/review/gold_dfg/) |
| [Microsoft AdventureWorks OLTP](datasets/adventureworks/) | [SQLite + official dictionary](datasets/adventureworks/input/) | [Inspection](datasets/adventureworks/review/database/) | Not yet authored |

### Strict boundary

**Model-visible**: `datasets/<name>/input/database.sqlite` and `data_dictionary.json` only. Natural-language questions are supplied separately by the evaluation harness; the model must not read `evaluation/`, `private/`, `review/`, `design/`, `source/`, or author documentation.

**Evaluation / author only**: `evaluation/` for question files, DDL, scope context, manifests, and auxiliary inputs; `private/` for Gold Event Logs, Gold SQL, bindings and case populations; `review/` for graph visualizations and actual-source-table inspection. Build scripts are not model inputs.

### Build the database review pages

```bash
python tools/build_dataset_review.py
```

This generates, for each registered dataset, `review/database/README.md`, `schema.svg`, and `tables/<table>.md`. Every table page displays the **real first 10 SQLite rows**, total row count and column definitions. For the four original datasets, it also repositions the editable `docs/schema.drawio` tables and removes stale edge waypoints. Review the generated files before committing.

The generator does **not** change SQLite data or dictionaries. Existing `docs/schema.png` images are legacy until re-exported from the updated draw.io files.

### Caution

This refactor deliberately separates inspection data from model inputs. The original generation scripts and old paths may need their imports and references updated before full dataset rebuilding or evaluation. Do not treat moving the files as a validated end-to-end migration.

## Code organization

- `datasets/<name>/build.py` and `validate.py` contain dataset-specific building and checks.
- `tools/pipeline/` contains shared data-generation utilities previously located at repository root.
- `tools/questions/` contains question paraphrasing scripts.
- `tools/validation/` contains cross-dataset checks (legacy path dependencies may require updates).
- `tools/experiments/` contains ablation preparation.
- `tools/` contains human-review generators.

Python helper scripts are grouped by purpose; the repository root contains only README and Git configuration. The four original databases remain the gold-labelled benchmark source of truth. AdventureWorks adds a complete source snapshot with an official dictionary; its questions, reference logs and Gold DFGs are not yet authored. Generated data and Gold files are unchanged by this structural refactor.

**Evaluation migration status:** stored reference labels and Gold logs retain their original semantics. SQL/CSV consistency is checked separately from semantic ET correctness and target-method validation. The current pipeline contracts are documented as target behavior, not new measured results.
