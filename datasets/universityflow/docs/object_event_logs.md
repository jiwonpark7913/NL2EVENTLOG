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
| student | Student | business object | OU01 | 40 | 148 | [CSV](../private/gold_logs/OU01.csv) |
| course | Course | business object | OU02 | 6 | 47 | [CSV](../private/gold_logs/OU02.csv) |
| registration | Student-course registration | association record | OU03 | 47 | 47 | [CSV](../private/gold_logs/OU03.csv) |
| degree_examination_result | Examination result record | event record | OU04 | 40 | 40 | [CSV](../private/gold_logs/OU04.csv) |
| simulation_module | Simulation module | business object | OU05 | 3 | 27 | [CSV](../private/gold_logs/OU05.csv) |
| thesis | Thesis | business object | OU06 | 16 | 16 | [CSV](../private/gold_logs/OU06.csv) |
| student_simulation_experiment_result | Simulation experiment result record | event record | OU07 | 27 | 27 | [CSV](../private/gold_logs/OU07.csv) |
| assignment | Assignment | business object | OU08 | 20 | 18 | [CSV](../private/gold_logs/OU08.csv) |
| instructor | Instructor | business object | OU09 | 3 | 18 | [CSV](../private/gold_logs/OU09.csv) |
| assignment_grading | Assignment grading record | event record | OU10 | 18 | 18 | [CSV](../private/gold_logs/OU10.csv) |

## Scope of each view

- **OU01 — Student:** All five recorded academic activity types linked to this student.
- **OU02 — Course:** Successful registrations for this course offering. Course schedules and text-only instructor labels do not add events.
- **OU03 — Student-course registration:** The successful registration event represented by this student-course pair.
- **OU04 — Examination result record:** The examination occurrence represented by this result ID; score publication is not timestamped.
- **OU05 — Simulation module:** Every recorded student experiment completion using this module, including repeat runs.
- **OU06 — Thesis:** The actual submission event for this thesis; no review events are recorded.
- **OU07 — Simulation experiment result record:** The experiment-completion occurrence identified by student, module and simulation time.
- **OU08 — Assignment:** All recorded grading and regrading actions for this assignment; no submission timestamp is inferred.
- **OU09 — Instructor:** Grading and regrading actions performed by this instructor, without inferring links from course-name strings.
- **OU10 — Assignment grading record:** The single grading action represented by the assignment-instructor-time key.

## Tables without an actual event-log view

- **task:** Task dates are scheduled periods, not actual student actions. No declared task-to-student, task-to-experiment or timestamped task-assignment relationship exists.
