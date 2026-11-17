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
