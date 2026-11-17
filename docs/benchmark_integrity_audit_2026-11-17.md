# Dataset integrity and Gold-readiness audit — 2026-11-17

Scope: AdventureWorks, public MIMIC-IV Demo 2.2, OCEL-derived BPI 2019, and OCEL-derived Order Management. This is a **source-/code-level preliminary audit**, not a certification based on direct execution of every binary dataset. A reproducible executable audit was added as `tools/audit_benchmark.py`; GitHub Actions results must be checked before interpreting PASS/FAIL.

## Evidence inspected

| Dataset | Repository evidence | Current disposition |
|---|---|---|
| AdventureWorks | `source/provenance.json`, `validate.py`, schema and documentation | Source manifest claims 71 tables, 759,240 records and 90 declared FKs. Physical validator exists; independent rerun required. No approved event-log Gold. |
| MIMIC-IV Demo | Committed `input/data_dictionary.json`, 31-table review index, schema SVG/draw.io, draft admission scenario; generated archive commit | Manifest contains **31 tables, 1,398,500 rows and 342 columns**. Existing `itemid` link to `d_items` was semantically wrong for `labevents`; builder corrected to `d_labitems`. Rebuild and audit required. Current dictionary lacks explanatory column descriptions and verified physical PK/FK constraints. |
| BPI 2019 | Zenodo source manifest; converter and streaming pipeline | Source JSON is >2GB uncompressed. Streaming conversion retains event IDs/types/time, object IDs/types and E2O/O2O but **drops other original attributes**. Dataset outputs not in git: supplied as ephemeral Actions artifacts. No independently accepted Gold. |
| Order Management | Converter, passing earlier CI execution (per workflow log) | Similar controlled normalized representation, not a genuine operational ERP schema. No independently accepted Gold, and binary artifact has not been locally examined in this audit. |

## Blocking issues for research publication

1. **Source fidelity:** Compare imported SQLite counts and identities against the upstream source, not only expected table counts. `audit_benchmark.py` checks available original events, objects, E2O tuples, timestamps, and references. Keep immutable upstream checksums and conversion versions.
2. **MIMIC entity keys:** The same column name does not imply the same referenced table. `labevents.itemid` references `d_labitems`, while selected ICU activity tables use `d_items`. Candidate relationships must be checked with the correct namespace and with actual data before being labeled as FKs.
3. **MIMIC diagrams:** Existing draw.io generation originally produced table vertices only, with neither relationship edges nor temporal row coloring. The generator has been amended to add inferred edges and styled timestamp rows; new diagrams must be rebuilt. Candidate links must not be misrepresented as declared physical FKs.
4. **MIMIC dictionary descriptions:** Current JSON is a physical catalog with empty column descriptions. For a true semantic data dictionary, include official descriptions/provenance where available; do not fabricate them.
5. **OCEL-derived ERD:** No standalone draw.io/SVG ERD is yet generated for either OCEL-derived database. The generated schema is the generic normalized OCEL event/object structure and is **not adequate as evidence of independent event discovery**.
6. **Reference definitions:** AdventureWorks has no approved Gold SQL/event log. MIMIC admission example has `approved=false`, `gold_sql=null`, `gold_event_log=null`. OCEL automatic direct E2O flattening produces a *candidate reference*, not independently reviewed semantic Gold.
7. **Gold correctness:** Compare all flattened occurrences as multisets of (case_id, event_id, activity, timestamp, relation_qualifier) and compare full case populations separately, including zero-event cases. Count equality alone is insufficient. The new executable audit checks every row and verifies upstream direct E2O where a source OCEL SQLite is provided.
8. **OCEL coverage:** The BPI 2019 streaming parser intentionally discards event/object attributes, so claims of full OCEL fidelity are invalid. O2O links are retained where present but no propagation semantics are inferred. The BPI 2019 conversion may omit O2O entirely because the source reconstruction lacks it.

## How to reproduce executable checks

```bash
python tools/audit_benchmark.py --dataset adventureworks --report /tmp/aw_audit.json
python tools/audit_benchmark.py --dataset mimic --report /tmp/mimic_audit.json
python tools/audit_benchmark.py --dataset bpi2019 --source /path/to/bpi2019.sqlite --report /tmp/bpi2019_audit.json
python tools/audit_benchmark.py --dataset order_management --source /path/to/order-management.sqlite --report /tmp/order_audit.json
```

GitHub Actions run these audits and retain JSON artifacts. They exit nonzero when a mandatory check fails. **WARN** means a known semantic or structural limitation requiring manual review. A passing automated physical audit does **not** imply a validated benchmark Gold, even if every mandatory check passes.

## Approval gate

Each dataset must have a pinned source revision/checksum, source-to-database content equality, independently verified ERD/DD, written case population semantics, occurrence-level reference checks, explicit event-attribute retention policy, and human approval of each request's reference Extraction Specification before being used for end-to-end exact-match reporting.
