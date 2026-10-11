# Object-based event logs

- Each answerable row below has its own English question, Gold specification, SQL and CSV event log.
- Business objects, event records and association records are labelled separately; a row-level case is useful for coverage but is not necessarily a rich business lifecycle.
- Case population includes records with no selected events; their event CSV has no row.
- One event may belong to several different cases, such as multiple goods types or workers. These are valid event-to-case links; the same event is not repeated within one case.
- Every view uses the exact scope stated below. Related upstream or downstream events are not automatically included through every reachable join.
- Existing explicit/paraphrase questions are retained. Paired questions may have identical Gold logs.
- Logs are case-based CSVs, not OCEL files.

| Case table | Case concept | Kind | Question | Cases | Event rows | Gold CSV |
|---|---|---|---|---:|---:|---|
| student | Student | business object | OU01 | 40 | 763 | [CSV](../private/gold_logs/OU01.csv) |
| course | Course | business object | OU02 | 6 | 298 | [CSV](../private/gold_logs/OU02.csv) |
| registration | Student-course registration | association record | OU03 | 47 | 275 | [CSV](../private/gold_logs/OU03.csv) |
| degree_examination_result | Examination result record | event record | OU04 | 40 | 194 | [CSV](../private/gold_logs/OU04.csv) |
| simulation_module | Simulation module | business object | OU05 | 3 | 142 | [CSV](../private/gold_logs/OU05.csv) |
| thesis | Thesis | business object | OU06 | 16 | 73 | [CSV](../private/gold_logs/OU06.csv) |
| student_simulation_experiment_result | Simulation experiment result record | event record | OU07 | 27 | 131 | [CSV](../private/gold_logs/OU07.csv) |
| assignment | Assignment | business object | OU08 | 20 | 90 | [CSV](../private/gold_logs/OU08.csv) |
| instructor | Instructor | business object | OU09 | 3 | 86 | [CSV](../private/gold_logs/OU09.csv) |
| assignment_grading | Assignment grading record | event record | OU10 | 18 | 18 | [CSV](../private/gold_logs/OU10.csv) |
| task | Course-design task | business object | OU11 | 3 | 11 | [CSV](../private/gold_logs/OU11.csv) |

## Scope of each view

- **OU01 — Student:** Original recorded actions and authored lifecycle actions explicitly linked to this student.
- **OU02 — Course:** Original recorded actions and authored lifecycle actions explicitly linked to this course.
- **OU03 — Student-course registration:** Original recorded actions and authored lifecycle actions explicitly linked to this student-course registration.
- **OU04 — Examination result record:** Original recorded actions and authored lifecycle actions explicitly linked to this examination result record.
- **OU05 — Simulation module:** Original recorded actions and authored lifecycle actions explicitly linked to this simulation module.
- **OU06 — Thesis:** Original recorded actions and authored lifecycle actions explicitly linked to this thesis.
- **OU07 — Simulation experiment result record:** Original recorded actions and authored lifecycle actions explicitly linked to this simulation experiment result record.
- **OU08 — Assignment:** Original recorded actions and authored lifecycle actions explicitly linked to this assignment.
- **OU09 — Instructor:** Original recorded actions and authored lifecycle actions explicitly linked to this instructor.
- **OU10 — Assignment grading record:** The single grading action represented by the assignment-instructor-time key.
- **OU11 — Course-design task:** Actual creation, publication and closure of this design task; these are authored task-management actions, not inferred student executions.

## Tables without an actual event-log view

- **registration_activity:** Activity storage/index for its parent-object log; not an independent business case.
- **degree_examination_result_activity:** Activity storage/index for its parent-object log; not an independent business case.
- **assignment_activity:** Activity storage/index for its parent-object log; not an independent business case.
- **simulation_module_activity:** Activity storage/index for its parent-object log; not an independent business case.
- **student_simulation_experiment_result_activity:** Activity storage/index for its parent-object log; not an independent business case.
- **thesis_activity:** Activity storage/index for its parent-object log; not an independent business case.
- **course_activity:** Activity storage/index for its parent-object log; not an independent business case.
- **task_activity:** Activity storage/index for its parent-object log; not an independent business case.
- **lifecycle_case_link:** Activity storage/index for its parent-object log; not an independent business case.
