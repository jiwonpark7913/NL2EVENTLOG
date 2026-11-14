# hospitalflow — 식별자와 대상 참조 목록

실제 SQLite의 전체 PK·UNIQUE·FK를 조사한 구조 목록이다. ET 예측이나 table→ET Gold가 아니다.

[개념 설명](../../../docs/system/ENTITY_IDENTITY_AND_STORAGE.md) · [저장 사례](../../ENTITY_STORAGE_CASES.md)

| Table | Rows | 완전한 PK | UNIQUE 인덱스 | 선언된 참조 |
|---|---:|---|---|---|
| admission_detail | 5 | hadm_id |  | (hadm_id) → admissions(hadm_id) |
| admissions | 15 | hadm_id |  | (subject_id) → patients(subject_id) |
| emar | 67 | emar_id |  | (pharmacy_id) → pharmacy(pharmacy_id) |
| lab_order | 34 | order_id |  | (hadm_id) → admissions(hadm_id); (subject_id) → patients(subject_id) |
| labevents | 62 | labevent_id |  | (order_id) → lab_order(order_id) |
| medication_order | 29 | order_id |  | (hadm_id) → admissions(hadm_id) |
| order_history | 203 | history_id |  | (procedure_order_id) → procedure_order(order_id); (medication_order_id) → medication_order(order_id); (lab_order_id) → lab_order(order_id) |
| patients | 12 | subject_id |  |  |
| pharmacy | 34 | pharmacy_id |  | (order_id) → medication_order(order_id) |
| procedure_episode | 23 | procedureevent_id |  | (order_id) → procedure_order(order_id) |
| procedure_order | 17 | order_id |  | (hadm_id) → admissions(hadm_id) |
| transfers | 38 | transfer_id |  | (hadm_id) → admissions(hadm_id); (subject_id) → patients(subject_id) |

UNIQUE 인덱스에는 PK 인덱스도 포함될 수 있다. NULL 허용 UNIQUE는 전체 행의 완전한 식별을 보장하지 않는다. FK가 없는 동일성은 이 구조 목록만으로 판별할 수 없다.
