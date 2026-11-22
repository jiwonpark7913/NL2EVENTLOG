# admissions

**Rows:** 15 · **Columns:** 16

## Original records (first 10)

| hadm_id | subject_id | admittime | dischtime | deathtime | admission_type | admit_provider_id | admission_location | discharge_location | insurance | language | marital_status | race | edregtime | edouttime | hospital_expire_flag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20000001 | 10000001 | 2026-01-17T16:12:00Z | 2026-01-19T15:01:00Z | NULL | EW EMER. | PV0001 | EMERGENCY ROOM | HOME | Medicare | ENGLISH | SINGLE | WHITE | 2026-01-17T13:42:00Z | 2026-01-17T15:42:00Z | 0 |
| 20000002 | 10000001 | 2026-01-27T13:19:00Z | 2026-01-29T18:54:00Z | NULL | DIRECT EMER. | PV0002 | PHYSICIAN REFERRAL | HOME | Medicaid | SPANISH | MARRIED | BLACK/AFRICAN AMERICAN | NULL | NULL | 0 |
| 20000003 | 10000002 | 2026-02-03T09:23:00Z | 2026-02-08T20:38:00Z | NULL | URGENT | PV0003 | CLINIC REFERRAL | HOME | Other | ENGLISH | UNKNOWN | ASIAN | 2026-02-03T09:01:00Z | 2026-02-03T09:18:36Z | 0 |
| 20000004 | 10000002 | 2026-02-14T22:40:00Z | 2026-02-19T13:40:00Z | NULL | ELECTIVE | PV0004 | EMERGENCY ROOM | HOME | Medicare | SPANISH | SINGLE | OTHER | NULL | NULL | 0 |
| 20000005 | 10000003 | 2026-02-20T00:15:00Z | 2026-02-26T06:10:00Z | NULL | EW EMER. | PV0005 | PHYSICIAN REFERRAL | HOME | Medicaid | ENGLISH | MARRIED | WHITE | 2026-02-19T21:23:00Z | 2026-02-19T23:40:36Z | 0 |
| 20000006 | 10000003 | 2026-03-06T05:26:00Z | 2026-03-07T17:34:00Z | NULL | DIRECT EMER. | PV0001 | CLINIC REFERRAL | HOME | Other | SPANISH | UNKNOWN | BLACK/AFRICAN AMERICAN | NULL | NULL | 0 |
| 20000007 | 10000004 | 2026-03-08T17:59:00Z | 2026-03-11T13:09:00Z | NULL | URGENT | PV0002 | EMERGENCY ROOM | HOME | Medicare | ENGLISH | SINGLE | ASIAN | 2026-03-08T14:36:00Z | 2026-03-08T17:18:24Z | 0 |
| 20000008 | 10000004 | 2026-03-18T17:20:00Z | 2026-03-24T06:27:00Z | NULL | ELECTIVE | PV0003 | PHYSICIAN REFERRAL | HOME | Medicaid | SPANISH | MARRIED | OTHER | NULL | NULL | 0 |
| 20000009 | 10000005 | 2026-03-25T09:15:00Z | 2026-04-01T16:48:00Z | NULL | EW EMER. | PV0004 | CLINIC REFERRAL | HOME | Other | ENGLISH | UNKNOWN | WHITE | 2026-03-25T08:39:00Z | 2026-03-25T09:07:48Z | 0 |
| 20000010 | 10000006 | 2026-04-11T01:01:00Z | 2026-04-12T13:01:00Z | NULL | DIRECT EMER. | PV0005 | EMERGENCY ROOM | HOME | Medicare | SPANISH | SINGLE | BLACK/AFRICAN AMERICAN | NULL | NULL | 0 |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| hadm_id | INTEGER | True | True |
| subject_id | INTEGER | False | True |
| admittime | TEXT | False | True |
| dischtime | TEXT | False | False |
| deathtime | TEXT | False | False |
| admission_type | TEXT | False | True |
| admit_provider_id | TEXT | False | False |
| admission_location | TEXT | False | False |
| discharge_location | TEXT | False | False |
| insurance | TEXT | False | False |
| language | TEXT | False | False |
| marital_status | TEXT | False | False |
| race | TEXT | False | False |
| edregtime | TEXT | False | False |
| edouttime | TEXT | False | False |
| hospital_expire_flag | INTEGER | False | True |
