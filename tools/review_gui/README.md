# NL2EventLog — EEG review dashboard

Run the reviewer-only Streamlit UI from the repository root:

```bash
python -m pip install -r tools/review_gui/requirements.txt
streamlit run tools/review_gui/app.py
```

The four datasets listed in the sidebar are **MIMIC-IV Demo**, **Microsoft AdventureWorks**, **BPI 2019 OCEL** and **Order Management OCEL**. Browse physical tables, dictionary descriptions, sample values and read-only SQLite rows. Review a real Step 1 Event Extraction Graph (EEG) or import a reviewed/reference event-log CSV. Download a separate reviewer decision JSON.

### Critical availability distinctions

- `datasets/mimic/input/data_dictionary.json` and `datasets/adventureworks/input/data_dictionary.json` exist in the repository.
- MIMIC SQLite may be stored as `input/database.sqlite.gz`; decompress it to `input/database.sqlite` locally. Do not accidentally commit uncompressed copies.
- The BPI 2019 and Order Management OCEL converted databases are **generated GitHub Actions artifacts**, not necessarily committed under `datasets/`. Download the workflow artifacts, extract `input/database.sqlite` and `input/data_dictionary.json` into `datasets/bpi2019_ocel/` and `datasets/order_management_ocel/`.
- **There are not yet verified runtime EEG outputs for these four datasets in this repository.** The schema ERD or an authored Gold evidence graph is *not* a Step 1 EEG. The EEG tab is intentionally empty until given a real export. See `CODEX_EEG_INTEGRATION.md` for the implementation handoff.

### Actual EEG export adapter

The dashboard requires a lightweight **view/export** produced from the genuine Step 1 runtime graph. Do not generate an EEG by simply turning all timestamp columns into events or by reading Gold artifacts.

Write `datasets/<dataset>/review/eeg/actual_eeg.json` with:

```json
{
  "dataset": "mimic",
  "source": "actual_step1_eeg",
  "generator_version": "<commit or version>",
  "nodes": [
    {"id": "table:admissions", "type": "table", "label": "admissions", "status": "observed", "evidence": {"table": "admissions"}},
    {"id": "entity_type:admission", "type": "entity_type", "label": "Hospital Admission", "status": "candidate", "evidence": {"identity_rule": "admissions.hadm_id", "grain": "one hospital admission"}},
    {"id": "event_definition:admitted", "type": "event_definition", "label": "Hospital admission", "status": "candidate", "evidence": {"table": "admissions", "timestamp": "admittime", "time_role": "occurrence", "row_condition": null, "occurrence_id": "source row ID + timestamp role"}}
  ],
  "edges": [
    {"source": "table:admissions", "target": "event_definition:admitted", "type": "source_of"}
  ]
}
```

**The example above is illustrative only; it is NOT an actual EEG and must never be committed as one.** Real exports should include all relevant physical references, entity identification/identity rules, carrier/non-carrier evidence, timestamp interpretations (planned/recording/valid), event definition conditions/occurrence IDs, event–entity attribution paths, ambiguity/conflicts, and validation statuses. Unknown or rejected candidates should remain visible as unresolved nodes, not be silently removed.

The current viewer uses a `nodes[]`/`edges[]` graph adapter and validates ID consistency. The original runtime graph remains the authoritative source; the adapter must preserve provenance rather than fabricate interpretations.

### Manual review protocol

Review **(1) physical evidence**, **(2) EEG semantics**, **(3) natural-language analysis request and reference extraction**, and **(4) approval state** independently. Do not treat an executable query, diagram, or a reviewer's checkbox as semantic Gold approval.

The reference log should preserve an occurrence identifier and the full case population separately from event rows. Null timestamps, duplicate case-event associations, and multi-ET attribution require explicit decisions based on actual source evidence. A DFG aggregates occurrences and cannot substitute for reviewing the raw case traces.

**Isolation:** The dashboard reads `review/` artifacts on demand. Never copy reviewer notes, Gold SQL, reference event logs, or actual evaluation outputs into `input/data_dictionary.json` or model prompts. It is a local human review app, not an authenticated public deployment. Do not expose clinical records through an externally accessible web server.
