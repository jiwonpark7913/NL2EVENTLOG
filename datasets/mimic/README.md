# MIMIC-IV Demo 2.2 — dataset workspace

This is a **real, de-identified, publicly available demo** from PhysioNet, distinct from the **synthetic** `datasets/hospitalflow`.

**Status:** ingestion and ERD generator are provided, but generated binaries and diagrams are **not yet checked in**. Do not treat planned artifacts, the example query, or any human-review UI as verified Gold.

- [PhysioNet official demo](https://physionet.org/content/mimic-iv-demo/2.2/) (100 patients; ODbL)
- [Reproducible CSV → SQLite + data dictionary + ERD generator](build.py)
- [Proposed admission timeline example (not validated Gold)](review/admission_timeline.json)
- [Interactive review GUI](review/index.html) (download HTML; GitHub does not run HTML)
- Generated after running builder: `input/database.sqlite`, `input/data_dictionary.json`, `docs/schema.svg`, `docs/schema.drawio`, optional `docs/schema.png`, `docs/schema.html`, `docs/data_dictionary.md`.

## Reproduce

Download the *public MIMIC-IV Clinical Database Demo v2.2* from PhysioNet; verify file hashes with the upstream `SHA256SUMS.txt` before importing. Extract the download into a local folder. Then:

```bash
python datasets/mimic/build.py --source /path/to/extracted/mimic-iv-demo
python datasets/mimic/build.py --source /path/to/extracted/mimic-iv-demo --png  # optional: requires cairosvg
```

The generator expects the original `hosp/` and `icu/` CSV (or CSV.GZ) structure. It uses original column names, stores raw values as TEXT for lossless ingestion (with empty fields as NULL), and does not implement formal physical PK/FK constraints absent from the downloaded CSV. Key relationships in ERD are **inferred by documented column conventions** and labeled accordingly; do not treat these as declared constraints. CSV columns with names indicating chart/observation, effective, planned, start or end times are highlighted **sky blue**, and administrative storage/recording columns (`storetime`, `*_storetime`, `modifieddate`, `updated_at`) **yellow**. A blue column is only a time *candidate*, not a confirmed event. Tables are arranged by patient/admission, clinical orders, ICU measurements, and reference tables, with temporal tables to the left.

To use the example as Gold, inspect source values and row counts, inspect event-level evidence, resolve time semantics, verify case population and exports, and approve the checklist. The example is a review hypothesis, not a published ground truth.
