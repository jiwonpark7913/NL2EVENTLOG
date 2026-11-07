# hospitalflow — Database Inspection

Original SQLite records; **not model input**. Click a table name to inspect its actual first 10 rows.

![Interactive table overview](schema.svg)

| Table | Rows | Columns | Open preview |
|---|---:|---:|---|
| admission_detail | 5 | 2 | [First 10 rows](tables/admission_detail.md) |
| admissions | 15 | 6 | [First 10 rows](tables/admissions.md) |
| emar | 67 | 5 | [First 10 rows](tables/emar.md) |
| lab_order | 34 | 5 | [First 10 rows](tables/lab_order.md) |
| labevents | 62 | 7 | [First 10 rows](tables/labevents.md) |
| medication_order | 29 | 4 | [First 10 rows](tables/medication_order.md) |
| order_history | 203 | 6 | [First 10 rows](tables/order_history.md) |
| patient_profile | 6 | 3 | [First 10 rows](tables/patient_profile.md) |
| patients | 12 | 2 | [First 10 rows](tables/patients.md) |
| pharmacy | 34 | 3 | [First 10 rows](tables/pharmacy.md) |
| procedure_episode | 23 | 5 | [First 10 rows](tables/procedure_episode.md) |
| procedure_order | 17 | 4 | [First 10 rows](tables/procedure_order.md) |

The table links are the dependable GitHub navigation path; SVG click-through may vary by GitHub's rendering/security restrictions.
FK arrows are based on declared SQLite foreign keys. Informal semantic links are not asserted as physical FKs.
