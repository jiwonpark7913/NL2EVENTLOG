# HospitalFlow — reference provenance

HospitalFlow uses **wholly synthetic records**. Public MIMIC-IV schema documentation informed its table and column conventions, but no real patient record was used.

- [MIMIC-IV overview](https://mimic.mit.edu/docs/iv/)
- [Hospital module](https://mimic.mit.edu/docs/iv/modules/hosp/)
- [Admissions](https://mimic.mit.edu/docs/iv/modules/hosp/admissions.html)
- [Patients](https://mimic.mit.edu/docs/iv/modules/hosp/patients.html)
- [Transfers](https://mimic.mit.edu/docs/iv/modules/hosp/transfers.html)
- [Laboratory events](https://mimic.mit.edu/docs/iv/modules/hosp/labevents.html)

The research-authored extension tables (e.g. `lab_order`, `admission_detail`, `order_history`, `procedure_order`, `procedure_episode`) do not correspond one-to-one to MIMIC-IV native tables.

Current schema: [schema overview](../docs/schema_overview.md).
