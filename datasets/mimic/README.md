# MIMIC-IV Demo 2.2 — relational benchmark workspace

This dataset is distinct from the synthetic `hospitalflow`. Official source: [PhysioNet MIMIC-IV Demo 2.2](https://physionet.org/content/mimic-iv-demo/2.2/), 100 deidentified patients, ODbL.

## Outputs
- [Scrollable ERD](docs/schema.html) (download and open locally)
- [SVG](docs/schema.svg) · [PNG](docs/schema.png) · [Editable draw.io](docs/schema.drawio)
- [Data dictionary](docs/data_dictionary.md)
- [Human-only database inspection](review/database/README.md)
- [Admission lifecycle review GUI](review/index.html) (download and open locally)
- [Proposed example](review/admission_timeline.json) — **not Gold**
- Model inputs: `input/data_dictionary.json` and the **decompressed** `input/database.sqlite`. GitHub currently stores `input/database.sqlite.gz` to satisfy its file-size limit. Do not pass the compressed `.gz` directly to the SQLite reader.

## Restore SQLite from GitHub\n\n```bash\ngzip -dk datasets/mimic/input/database.sqlite.gz\n# Run this only in an environment where the uncompressed DB is absent.\n```\n\nThe GitHub Actions builder produces the uncompressed DB locally, audits it, then compresses it for committing.\n\n## Reproduction
```bash
python -m pip install cairosvg==2.8.2
python datasets/mimic/build.py --source /path/to/mimic-iv-demo --png
```

Original CSVs are imported losslessly into TEXT values (empty → NULL), without fabricating declared PK/FK constraints. Timestamp candidate fields are blue; administrative storage time fields are yellow. A highlighted column alone does **not** establish that it is an event timestamp. Human review remains required.

The generated artifacts and review pages are produced by the GitHub Actions workflow and may not yet be present after source changes. The review GUI exports a *draft* JSON; approval must be independently verified.

## Integrity and semantic limitations

- Automated audit: `python tools/audit_benchmark.py --dataset mimic --report datasets/mimic/review/integrity_audit.json`.
- `itemid` is dictionary-specific: `labevents.itemid → d_labitems.itemid`; ICU event tables typically reference `d_items.itemid`. Relations in the DD are **candidate** links rather than declared FKs.
- draw.io and SVG expose candidate timestamp fields, but temporal classification does not establish observed event semantics. `storetime` is maintenance/recording time, not automatically an occurrence.
- No approved reference log for the admission example yet. Its review JSON explicitly has `approved: false`.

## Official documentation and Data Dictionary provenance

The data and descriptions have **different upstream sources**. The actual rows originate from [PhysioNet MIMIC-IV Demo 2.2](https://physionet.org/content/mimic-iv-demo/2.2/); column definitions, original PostgreSQL types, and table purposes are derived from the [official MIMIC-IV Data Dictionary / documentation](https://mimic.mit.edu/docs/iv/). These are MIMIC-IV documentation pages, not synthetic HospitalFlow annotations. The official documentation URLs are maintained in this README rather than repeated per column in JSON. Documentation definitions are condensed and must be checked against source semantics.

**Official module documentation:** [Hospital (hosp)](https://mimic.mit.edu/docs/iv/modules/hosp/) · [ICU](https://mimic.mit.edu/docs/iv/modules/icu/).

**Hospital tables (22)**: [admissions](https://mimic.mit.edu/docs/iv/modules/hosp/admissions.html), [d_hcpcs](https://mimic.mit.edu/docs/iv/modules/hosp/d_hcpcs.html), [d_icd_diagnoses](https://mimic.mit.edu/docs/iv/modules/hosp/d_icd_diagnoses.html), [d_icd_procedures](https://mimic.mit.edu/docs/iv/modules/hosp/d_icd_procedures.html), [d_labitems](https://mimic.mit.edu/docs/iv/modules/hosp/d_labitems.html), [diagnoses_icd](https://mimic.mit.edu/docs/iv/modules/hosp/diagnoses_icd.html), [drgcodes](https://mimic.mit.edu/docs/iv/modules/hosp/drgcodes.html), [emar](https://mimic.mit.edu/docs/iv/modules/hosp/emar.html), [emar_detail](https://mimic.mit.edu/docs/iv/modules/hosp/emar_detail.html), [hcpcsevents](https://mimic.mit.edu/docs/iv/modules/hosp/hcpcsevents.html), [labevents](https://mimic.mit.edu/docs/iv/modules/hosp/labevents.html), [microbiologyevents](https://mimic.mit.edu/docs/iv/modules/hosp/microbiologyevents.html), [omr](https://mimic.mit.edu/docs/iv/modules/hosp/omr.html), [patients](https://mimic.mit.edu/docs/iv/modules/hosp/patients.html), [pharmacy](https://mimic.mit.edu/docs/iv/modules/hosp/pharmacy.html), [poe](https://mimic.mit.edu/docs/iv/modules/hosp/poe.html), [poe_detail](https://mimic.mit.edu/docs/iv/modules/hosp/poe_detail.html), [prescriptions](https://mimic.mit.edu/docs/iv/modules/hosp/prescriptions.html), [procedures_icd](https://mimic.mit.edu/docs/iv/modules/hosp/procedures_icd.html), [provider](https://mimic.mit.edu/docs/iv/modules/hosp/provider.html), [services](https://mimic.mit.edu/docs/iv/modules/hosp/services.html), [transfers](https://mimic.mit.edu/docs/iv/modules/hosp/transfers.html).

**ICU tables (9)**: [caregiver](https://mimic.mit.edu/docs/iv/modules/icu/caregiver.html), [chartevents](https://mimic.mit.edu/docs/iv/modules/icu/chartevents.html), [d_items](https://mimic.mit.edu/docs/iv/modules/icu/d_items.html), [datetimeevents](https://mimic.mit.edu/docs/iv/modules/icu/datetimesevents.html), [icustays](https://mimic.mit.edu/docs/iv/modules/icu/icustays.html), [ingredientevents](https://mimic.mit.edu/docs/iv/modules/icu/ingredientevents.html), [inputevents](https://mimic.mit.edu/docs/iv/modules/icu/inputevents.html), [outputevents](https://mimic.mit.edu/docs/iv/modules/icu/outputevents.html), [procedureevents](https://mimic.mit.edu/docs/iv/modules/icu/procedureevents.html).

The JSON `input/data_dictionary.json` is the live model-input dictionary. It contains `definition`, `source_type` (official native type, when verified), `sql_type` (actual SQLite storage type), and `metadata_id`. Dataset-level official documentation links are listed above; columns do not duplicate those URLs. `temporal_role` and `timestamp_semantics` are not stored in the model-input JSON. Unknown definitions are `null`, not made-up explanations. Inferred relationships are identified separately from declared foreign keys. The auto-enrichment script is `enrich_dictionary.py` and runs after building the physical database.

**Common schema:** [NL2EventLog canonical Data Dictionary contract](../../docs/data_dictionary_contract.md). Existing datasets use several legacy JSON shapes; `tools/normalize_data_dictionaries.py` maps all six datasets to the same logical field contract without breaking their current readers. The standardized projection for MIMIC is generated as `docs/data_dictionary.standard.json`.

**Metadata completeness:** The dictionary contains 313/342 non-empty column definitions in the latest inspected commit; the GitHub Actions enrichment step is configured to collect official descriptions. A non-empty definition alone does not certify that its source semantics are correct. Do not interpret a successful build as proof that all 342 columns are documented. Check `metadata_coverage` and the enrichment log for exact coverage.

**EEG temporal screening policy:** use `source_type` for native temporal type candidates (such as `timestamp`, `date`, `time`), then interpret the field's `definition` to distinguish observed, planned, validity and maintenance timestamps. The converted SQLite `sql_type=TEXT` does not reflect the original temporal type. A column with `source_type=null` requires fallback to physical schema, column name, representative values and documented semantics. The ERD uses a separate layout-only heuristic for blue/yellow highlights, not a Gold event label.
