# NL2EventLog Data Dictionary — Common Contract (v1)

The **canonical logical contract** across datasets is:

```text
dictionary_schema_version
name / dataset_id / language / dbms / timezone
tables[]:
  table, metadata_id, definition, source_schema
  row_grain, primary_key, foreign_keys
  columns[]:
    metadata_id, name, sql_type, source_type
    definition, source_references
    required, primary_key_position, foreign_keys
    unit
```

**Evidence and null policy.** A definition describes the field's meaning, not its Gold Event Candidate or its case membership. `null` signifies unavailable or unverified evidence. Any model-created interpretation must be separate and explicitly attributed, never silently copied into a source-derived definition. The representative dataset README records official documentation provenance; source-document URLs are not repeated on every column.

**Temporal screening.** Use source-native type (`source_type`), including DATE/TIME/TIMESTAMP variants, to identify structural temporal candidates when available; also inspect SQLite physical type, declared schema and example values where original typing is missing. The temporal meaning (actual, planned, maintenance or validity) is interpreted from the column `definition` and validated later in EEG, not hard-coded into the data dictionary. A timestamp type alone does not prove an event occurrence.\n\n**Different physical and original types.** `sql_type` reports the actual SQLite representation; `source_type` reports the upstream native type when verified. A MIMIC-IV field imported as SQLite `TEXT` may still have upstream type `TIMESTAMP` or `INTEGER`. Do not falsify SQLite typing to match clinical source typing.

**Relationships.** Only physically declared SQL foreign keys belong in the declared-FK field. Candidate links inferred from matching fields or official documentation are represented separately as such, with provenance and verification status. Object/Event Gold, case notions and extraction specifications are not included.

**Compatibility and rollout.** Existing dictionaries use two legacy shapes (`tables` as a map in MIMIC vs as an array in AdventureWorks/HospitalFlow/etc.), plus `definition` vs `description` and `type` vs `sql_type`. `tools/normalize_data_dictionaries.py` projects each to `docs/data_dictionary.standard.json`, leaving the original `input/data_dictionary.json` untouched to avoid breaking the current NL2EventLog loaders. Standardized projections are now committed as `docs/data_dictionary.standard.json` for AdventureWorks, MIMIC, HospitalFlow, UniversityFlow, PlateFlow, and WarehouseFlow. Regenerate them after source dictionary changes by running the tool in the repository. The unified shape is a *view*, not a destructive migration.

**MIMIC source provenance:** [Official MIMIC-IV documentation](https://mimic.mit.edu/docs/iv/), [hospital module](https://mimic.mit.edu/docs/iv/modules/hosp/), [ICU module](https://mimic.mit.edu/docs/iv/modules/icu/), and [MIMIC-IV Demo 2.2](https://physionet.org/content/mimic-iv-demo/2.2/). The official table pages supply source descriptions and native types, not the synthetic HospitalFlow document.
