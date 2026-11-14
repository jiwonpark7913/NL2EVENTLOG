# universityflow — 식별자와 대상 참조 목록

실제 SQLite의 전체 PK·UNIQUE·FK를 조사한 구조 목록이다. ET 예측이나 table→ET Gold가 아니다.

[개념 설명](../../../docs/system/ENTITY_IDENTITY_AND_STORAGE.md) · [저장 사례](../../ENTITY_STORAGE_CASES.md)

| Table | Rows | 완전한 PK | UNIQUE 인덱스 | 선언된 참조 |
|---|---:|---|---|---|
| assignment | 20 | assignment_id | (assignment_id) | (student_id) → student(student_id) |
| assignment_grading | 25 | assignment_id, instructor_id, grading_time | (reassessment_event_id); (assignment_id, instructor_id, grading_time) | (instructor_id) → instructor(instructor_id); (assignment_id) → assignment(assignment_id) |
| course | 6 | course_id | (course_id) |  |
| degree_examination_result | 40 | result_id | (result_id) | (student_id) → student(student_id) |
| instructor | 3 | instructor_id | (instructor_id) |  |
| registration | 47 | student_id, course_id | (student_id, course_id) | (course_id) → course(course_id); (student_id) → student(student_id) |
| simulation_module | 3 | module_id | (module_id) |  |
| student | 40 | student_id | (student_id) |  |
| student_simulation_experiment_result | 27 | student_id, module_id, simulation_date | (student_id, module_id, simulation_date) | (module_id) → simulation_module(module_id); (student_id) → student(student_id) |
| task | 3 | task_id | (task_id) |  |
| thesis | 16 | thesis_id | (thesis_id) | (student_id) → student(student_id) |

UNIQUE 인덱스에는 PK 인덱스도 포함될 수 있다. NULL 허용 UNIQUE는 전체 행의 완전한 식별을 보장하지 않는다. FK가 없는 동일성은 이 구조 목록만으로 판별할 수 없다.
