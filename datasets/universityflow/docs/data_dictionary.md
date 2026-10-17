# UniversityFlow — data dictionary

## 1. Dictionary basic information

| Field | Value |
| --- | --- |
| dictionary_id | NL2EVENTLOG:universityflow |
| version | 2026-10-12 |
| name | UniversityFlow |
| description | English synthetic relational database for query-conditioned process-view and event-log extraction. |
| language | en |
| timezone | UTC |
| dbms | SQLite |
| namespace | universityflow |
| timestamp_columns | 27 |
| event_timestamp_columns | 26 |
| maintainer | NL2EVENTLOG project maintainers |
| registration_status | Project-maintained draft; not ISO-registered or certified |
| source_policy | Source definitions are retained and authored lifecycle additions are identified in source/design documents. |
| standards_profile | Project profile informed by ISO/IEC 11179-3 and 11179-4 public abstracts; no full clause-by-clause conformance assessment. |
| layout | 1 Dictionary basic information; 2 Table definitions; 3 Column definitions |

- The three-part layout is a project documentation choice, not a mandated ISO/IEC template.
- ISO/IEC 11179-4 addresses semantic definitions rather than prescribing their formatting. Only public standard scope descriptions were consulted.
- SQL keys and constraints are taken from the executable DB. SQLite TEXT has no declared maximum length unless an explicit constraint says otherwise. Examples are observed synthetic values, not additional allowed-value constraints.
- [ISO/IEC 11179-3:2023](https://www.iso.org/standard/78915.html): Registry identification, administration and definition concepts.
- [ISO/IEC 11179-4:2004](https://www.iso.org/standard/35346.html): Semantic formulation of data definitions.

## 2. Table definitions

| Metadata ID | Logical name | Physical name | Rows | PK | FK | Event encoding | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| universityflow.student | Student | student | 40 | student_id | None declared | No event encoding | Unified student information from the three university examples |
| universityflow.course | Course | course | 6 | course_id | None declared | No event encoding | Course offerings and planned teaching schedules |
| universityflow.registration | Registration | registration | 47 | student_id, course_id | course_id → course.course_id; student_id → student.student_id | Mixed (row + column) | Successful registrations; one retained row per student and course |
| universityflow.degree_examination_result | Degree Examination Result | degree_examination_result | 40 | result_id | student_id → student.student_id | Mixed (row + column) | Examination results including retakes |
| universityflow.task | Task | task | 3 | task_id | None declared | No event encoding | Course-design task descriptions and scheduled task periods |
| universityflow.simulation_module | Simulation Module | simulation_module | 3 | module_id | None declared | No event encoding | Simulation module descriptions and example code |
| universityflow.thesis | Thesis | thesis | 16 | thesis_id | student_id → student.student_id | Column encoding | Student theses with actual submission times |
| universityflow.student_simulation_experiment_result | Student Simulation Experiment Result | student_simulation_experiment_result | 27 | student_id, module_id, simulation_date | module_id → simulation_module.module_id; student_id → student.student_id | Row encoding | Student simulation results with actual experiment-completion times |
| universityflow.assignment | Assignment | assignment | 20 | assignment_id | student_id → student.student_id | Column encoding | Student assignment content; submission time is not recorded |
| universityflow.instructor | Instructor | instructor | 3 | instructor_id | None declared | No event encoding | Instructor information from the assignment-management example |
| universityflow.assignment_grading | Assignment Grading | assignment_grading | 18 | assignment_id, instructor_id, grading_time | instructor_id → instructor.instructor_id; assignment_id → assignment.assignment_id | Row encoding | Every recorded grading action, including regrading |
| universityflow.assignment_activity | Assignment Activity | assignment_activity | 21 | event_id | assignment_id → assignment.assignment_id | Row encoding | Authored actual-action history for assignment |
| universityflow.simulation_module_activity | Simulation Module Activity | simulation_module_activity | 11 | event_id | module_id → simulation_module.module_id | Row encoding | Authored actual-action history for simulation_module |
| universityflow.student_simulation_experiment_result_activity | Student Simulation Experiment Result Activity | student_simulation_experiment_result_activity | 104 | event_id | student_id → student_simulation_experiment_result.student_id; module_id → student_simulation_experiment_result.module_id; simulation_date → student_simulation_experiment_result.simulation_date | Row encoding | Authored actual-action history for student_simulation_experiment_result |
| universityflow.thesis_activity | Thesis Activity | thesis_activity | 12 | event_id | thesis_id → thesis.thesis_id | Row encoding | Authored actual-action history for thesis |
| universityflow.course_activity | Course Activity | course_activity | 23 | event_id | course_id → course.course_id | Row encoding | Authored actual-action history for course |
| universityflow.task_activity | Task Activity | task_activity | 11 | event_id | task_id → task.task_id | Row encoding | Authored actual-action history for task |
| universityflow.lifecycle_case_link | Lifecycle Case Link | lifecycle_case_link | 1675 | event_id, case_table, case_id | None declared | No event encoding | Explicit case attribution across typed action histories; auxiliary extraction index, not a business case |

- Row encoding: an event occurrence is represented by a row.
- Column encoding: an object row stores one or more actual business milestone timestamps in dedicated columns.
- No event encoding: contextual, reference, planned or relationship/index data; this does not mean the related business object lacks an event log.
- **student:** Master, plan, reference or relationship/index data; this table does not directly produce an event in the current ES. Related objects can still have logs from other tables.
- **course:** Master, plan, reference or relationship/index data; this table does not directly produce an event in the current ES. Related objects can still have logs from other tables.
- **registration:** Actual milestone columns on the existing business object; NULL means not yet occurred. Authored added event columns: registration_requested_at, registration_approved_at, course_started_at, course_assessment_completed_at, course_grade_finalized_at.
- **degree_examination_result:** Actual milestone columns on the existing business object; NULL means not yet occurred. Authored added event columns: examination_scheduled_at, examination_checked_in_at, examination_score_published_at, examination_result_reviewed_at.
- **task:** Master, plan, reference or relationship/index data; this table does not directly produce an event in the current ES. Related objects can still have logs from other tables.
- **simulation_module:** Master, plan, reference or relationship/index data; this table does not directly produce an event in the current ES. Related objects can still have logs from other tables.
- **thesis:** Actual milestone columns on the existing business object; NULL means not yet occurred. Authored added event columns: thesis_draft_registered_at, thesis_review_started_at, thesis_accepted_at.
- **student_simulation_experiment_result:** One completed simulation run per composite-key row.
- **assignment:** Actual milestone columns on the existing business object; NULL means not yet occurred. Authored added event columns: assignment_assigned_at, assignment_submitted_at, assignment_grade_finalized_at.
- **instructor:** Master, plan, reference or relationship/index data; this table does not directly produce an event in the current ES. Related objects can still have logs from other tables.
- **assignment_grading:** One grading occurrence per composite-key row.
- **assignment_activity:** Each action is a separate row; activity selects its meaning and occurred_at is its actual time.
- **simulation_module_activity:** Each action is a separate row; activity selects its meaning and occurred_at is its actual time.
- **student_simulation_experiment_result_activity:** Each action is a separate row; activity selects its meaning and occurred_at is its actual time.
- **thesis_activity:** Each action is a separate row; activity selects its meaning and occurred_at is its actual time.
- **course_activity:** Each action is a separate row; activity selects its meaning and occurred_at is its actual time.
- **task_activity:** Each action is a separate row; activity selects its meaning and occurred_at is its actual time.
- **lifecycle_case_link:** Master, plan, reference or relationship/index data; this table does not directly produce an event in the current ES. Related objects can still have logs from other tables.

## 3. Column definitions

### student

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| universityflow.student.student_id | Student Id / student_id | Student identifier shared across the three combined examples | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["S001", "S002", "S003"] |
| universityflow.student.name | Name / name | Student name | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Student 01", "Student 02", "Student 03"] |
| universityflow.student.date_of_birth | Date Of Birth / date_of_birth | Birth date; not an academic event | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["2004-01-01"] |
| universityflow.student.phone_number | Phone Number / phone_number | Student contact number | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["+1-555-0001", "+1-555-0002", "+1-555-0003"] |
| universityflow.student.home_address | Home Address / home_address | Student postal address | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Fictional Campus Residence 1", "Fictional Campus Residence 2", "Fictional Campus Residence 3"] |
| universityflow.student.registration_eligibility | Registration Eligibility / registration_eligibility | Current eligibility, ELIGIBLE or INELIGIBLE; changes are not timestamped | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL CHECK(registration_eligibility IN ('ELIGIBLE','INELIGIBLE')) | See column definition; no implicit unit | ["INELIGIBLE", "ELIGIBLE"] |
| universityflow.student.class | Class / class | Student class or cohort | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Cohort 2026"] |
| universityflow.student.major | Major / major | Student major | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Industrial Engineering"] |

- **Declared table constraints:** `CREATE TABLE student (student_id TEXT NOT NULL, name TEXT NOT NULL, date_of_birth TEXT NOT NULL, phone_number TEXT NOT NULL, home_address TEXT NOT NULL, registration_eligibility TEXT NOT NULL CHECK(registration_eligibility IN ('ELIGIBLE','INELIGIBLE')), class TEXT NOT NULL, major TEXT NOT NULL, PRIMARY KEY (student_id))`

### course

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| universityflow.course.course_id | Course Id / course_id | Course-offering identifier | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["C01", "C02", "C03"] |
| universityflow.course.course_name | Course Name / course_name | Course title | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Database Systems", "Statistics", "Operations Research"] |
| universityflow.course.credits | Credits / credits | Academic credit units | Number / INTEGER | Not applicable | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL CHECK(credits > 0) | See column definition; no implicit unit | [3] |
| universityflow.course.instructor | Instructor / instructor | Instructor name as stored in the registration source; no FK to instructor is assumed | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Instructor 1", "Instructor 2", "Instructor 3"] |
| universityflow.course.class_time | Class Time / class_time | Planned teaching time; not proof that a class occurred | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["Monday 09:00"] |
| universityflow.course.class_location | Class Location / class_location | Planned teaching location | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Room 001", "Room 002", "Room 003"] |

- **Declared table constraints:** `CREATE TABLE course (course_id TEXT NOT NULL, course_name TEXT NOT NULL, credits INTEGER NOT NULL CHECK(credits > 0), instructor TEXT NOT NULL, class_time TEXT NOT NULL, class_location TEXT NOT NULL, PRIMARY KEY (course_id))`

### registration

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| universityflow.registration.student_id | Student Id / student_id | Student identifier shared across the three combined examples | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 / student.student_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["S002", "S003", "S006"] |
| universityflow.registration.course_id | Course Id / course_id | Course-offering identifier | Identifier / TEXT | Not bounded by declared SQLite type | yes | 2 / course.course_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["C01", "C06", "C02"] |
| universityflow.registration.registration_time | Registration Time / registration_time | Actual successful registration time in UTC | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-07T11:00:00Z", "2026-02-07T16:00:00Z", "2026-02-08T12:00:00Z"] |
| universityflow.registration.status | Status / status | Current registration status; REGISTERED in the simulated rows; no change history | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL CHECK(status='REGISTERED') | See column definition; no implicit unit | ["REGISTERED"] |
| universityflow.registration.registration_requested_at | Registration Requested At / registration_requested_at | Actual UTC time of Registration Requested. NULL means no recorded occurrence. Authored single-occurrence milestone; not a source-provided field. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-07T07:00:00Z", "2026-02-07T12:00:00Z", "2026-02-08T08:00:00Z"] |
| universityflow.registration.registration_approved_at | Registration Approved At / registration_approved_at | Actual UTC time of Registration Approved. NULL means no recorded occurrence. Authored single-occurrence milestone; not a source-provided field. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-07T09:00:00Z", "2026-02-07T14:00:00Z", "2026-02-08T10:00:00Z"] |
| universityflow.registration.course_started_at | Course Started At / course_started_at | Actual UTC time of Course Started. NULL means no recorded occurrence. Authored single-occurrence milestone; not a source-provided field. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-09T11:00:00Z", "2026-02-09T16:00:00Z", "2026-02-10T12:00:00Z"] |
| universityflow.registration.course_assessment_completed_at | Course Assessment Completed At / course_assessment_completed_at | Actual UTC time of Course Assessment Completed. NULL means no recorded occurrence. Authored single-occurrence milestone; not a source-provided field. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-27T11:00:00Z", "2026-02-27T16:00:00Z", "2026-02-28T12:00:00Z"] |
| universityflow.registration.course_grade_finalized_at | Course Grade Finalized At / course_grade_finalized_at | Actual UTC time of Course Grade Finalized. NULL means no recorded occurrence. Authored single-occurrence milestone; not a source-provided field. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-01T16:00:00Z", "2026-03-02T12:00:00Z", "2026-03-02T15:00:00Z"] |

- **Declared table constraints:** `CREATE TABLE registration (student_id TEXT NOT NULL, course_id TEXT NOT NULL, registration_time TEXT NOT NULL, status TEXT NOT NULL CHECK(status='REGISTERED'), registration_requested_at TEXT, registration_approved_at TEXT, course_started_at TEXT, course_assessment_completed_at TEXT, course_grade_finalized_at TEXT, PRIMARY KEY (student_id,course_id), FOREIGN KEY (student_id) REFERENCES student(student_id), FOREIGN KEY (course_id) REFERENCES course(course_id))`

### degree_examination_result

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| universityflow.degree_examination_result.result_id | Result Id / result_id | Unique examination-result identifier | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["E001-1", "E002-1", "E002-2"] |
| universityflow.degree_examination_result.student_id | Student Id / student_id | Student identifier shared across the three combined examples | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / student.student_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["S001", "S002", "S003"] |
| universityflow.degree_examination_result.examination_name | Examination Name / examination_name | Degree examination name | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Registration Eligibility Examination"] |
| universityflow.degree_examination_result.grade | Grade / grade | Examination score, 0 to 100; 60 is the simulated passing threshold | Number / INTEGER | Not applicable | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL CHECK(grade BETWEEN 0 AND 100) | See column definition; no implicit unit | [33, 32, 88] |
| universityflow.degree_examination_result.examination_date | Examination Date / examination_date | Actual examination time in UTC; not score-publication time | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-02T09:00:00Z", "2026-02-03T09:00:00Z", "2026-02-05T09:00:00Z"] |
| universityflow.degree_examination_result.examination_scheduled_at | Examination Scheduled At / examination_scheduled_at | Actual UTC time of Examination Scheduled. NULL means no recorded occurrence. Authored single-occurrence milestone; not a source-provided field. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-02T07:00:00Z", "2026-02-03T07:00:00Z", "2026-02-05T07:00:00Z"] |
| universityflow.degree_examination_result.examination_checked_in_at | Examination Checked In At / examination_checked_in_at | Actual UTC time of Examination Checked In. NULL means no recorded occurrence. Authored single-occurrence milestone; not a source-provided field. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-02T08:00:00Z", "2026-02-03T08:00:00Z", "2026-02-05T08:00:00Z"] |
| universityflow.degree_examination_result.examination_score_published_at | Examination Score Published At / examination_score_published_at | Actual UTC time of Examination Score Published. NULL means no recorded occurrence. Authored single-occurrence milestone; not a source-provided field. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-02T11:00:00Z", "2026-02-03T11:00:00Z", "2026-02-05T11:00:00Z"] |
| universityflow.degree_examination_result.examination_result_reviewed_at | Examination Result Reviewed At / examination_result_reviewed_at | Actual UTC time of Examination Result Reviewed. NULL means no recorded occurrence. Authored single-occurrence milestone; not a source-provided field. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-03T12:00:00Z", "2026-02-05T12:00:00Z", "2026-02-04T12:00:00Z"] |

- **Declared table constraints:** `CREATE TABLE degree_examination_result (result_id TEXT NOT NULL, student_id TEXT NOT NULL, examination_name TEXT NOT NULL, grade INTEGER NOT NULL CHECK(grade BETWEEN 0 AND 100), examination_date TEXT NOT NULL, examination_scheduled_at TEXT, examination_checked_in_at TEXT, examination_score_published_at TEXT, examination_result_reviewed_at TEXT, PRIMARY KEY (result_id), FOREIGN KEY (student_id) REFERENCES student(student_id))`

### task

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| universityflow.task.task_id | Task Id / task_id | Course-design task identifier | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["T01", "T02", "T03"] |
| universityflow.task.task_title | Task Title / task_title | Task title | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Course Design Task 1", "Course Design Task 2", "Course Design Task 3"] |
| universityflow.task.task_description | Task Description / task_description | Task description | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Analyze simulation output"] |
| universityflow.task.task_start_date | Task Start Date / task_start_date | Scheduled task-period start; not an observed student action | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-01"] |
| universityflow.task.task_end_date | Task End Date / task_end_date | Scheduled task deadline; not proof of completion | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-05-31"] |
| universityflow.task.task_location | Task Location / task_location | Task location | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Teaching Laboratory"] |

- **Declared table constraints:** `CREATE TABLE task (task_id TEXT NOT NULL, task_title TEXT NOT NULL, task_description TEXT NOT NULL, task_start_date TEXT NOT NULL, task_end_date TEXT NOT NULL, task_location TEXT NOT NULL, PRIMARY KEY (task_id))`

### simulation_module

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| universityflow.simulation_module.module_id | Module Id / module_id | Simulation module identifier | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["M01", "M02", "M03"] |
| universityflow.simulation_module.module_name | Module Name / module_name | Module name | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["PCM", "DPCM", "Delta Modulation"] |
| universityflow.simulation_module.module_type | Module Type / module_type | Simulation method, such as PCM or DPCM | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["PCM", "DPCM", "DELTA"] |
| universityflow.simulation_module.module_description | Module Description / module_description | Module description | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Synthetic teaching module"] |
| universityflow.simulation_module.module_code | Module Code / module_code | Example module code; not an event code | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["example_module_1()", "example_module_2()", "example_module_3()"] |

- **Declared table constraints:** `CREATE TABLE simulation_module (module_id TEXT NOT NULL, module_name TEXT NOT NULL, module_type TEXT NOT NULL, module_description TEXT NOT NULL, module_code TEXT NOT NULL, PRIMARY KEY (module_id))`

### thesis

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| universityflow.thesis.thesis_id | Thesis Id / thesis_id | Thesis identifier | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["TH002", "TH003", "TH006"] |
| universityflow.thesis.student_id | Student Id / student_id | Student identifier shared across the three combined examples | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / student.student_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["S002", "S003", "S006"] |
| universityflow.thesis.thesis_title | Thesis Title / thesis_title | Thesis title | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Course Design Thesis"] |
| universityflow.thesis.thesis_content | Thesis Content / thesis_content | Submitted thesis content | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Synthetic thesis content"] |
| universityflow.thesis.submission_date | Submission Date / submission_date | Actual thesis-submission time in UTC | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-23T16:00:00Z", "2026-02-24T16:00:00Z", "2026-02-27T16:00:00Z"] |
| universityflow.thesis.thesis_draft_registered_at | Thesis Draft Registered At / thesis_draft_registered_at | Actual UTC time of Thesis Draft Registered. NULL means no recorded occurrence. Authored single-occurrence milestone; not a source-provided field. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-19T16:00:00Z", "2026-02-20T16:00:00Z", "2026-02-23T16:00:00Z"] |
| universityflow.thesis.thesis_review_started_at | Thesis Review Started At / thesis_review_started_at | Actual UTC time of Thesis Review Started. NULL means no recorded occurrence. Authored single-occurrence milestone; not a source-provided field. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-24T16:00:00Z", "2026-02-25T16:00:00Z", "2026-02-28T16:00:00Z"] |
| universityflow.thesis.thesis_accepted_at | Thesis Accepted At / thesis_accepted_at | Actual UTC time of Thesis Accepted. NULL means no recorded occurrence. Authored single-occurrence milestone; not a source-provided field. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-28T16:00:00Z", "2026-03-03T16:00:00Z", "2026-03-04T16:00:00Z"] |

- **Declared table constraints:** `CREATE TABLE thesis (thesis_id TEXT NOT NULL, student_id TEXT NOT NULL, thesis_title TEXT NOT NULL, thesis_content TEXT NOT NULL, submission_date TEXT NOT NULL, thesis_draft_registered_at TEXT, thesis_review_started_at TEXT, thesis_accepted_at TEXT, PRIMARY KEY (thesis_id), FOREIGN KEY (student_id) REFERENCES student(student_id))`

### student_simulation_experiment_result

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| universityflow.student_simulation_experiment_result.student_id | Student Id / student_id | Student identifier shared across the three combined examples | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 / student.student_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["S002", "S003", "S006"] |
| universityflow.student_simulation_experiment_result.module_id | Module Id / module_id | Simulation module identifier | Identifier / TEXT | Not bounded by declared SQLite type | yes | 2 / simulation_module.module_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["M03", "M01", "M02"] |
| universityflow.student_simulation_experiment_result.simulation_date | Simulation Date / simulation_date | Actual experiment-completion time in UTC; this interpretation is an added simulation assumption | Date/time text / TEXT | Not bounded by declared SQLite type | yes | 3 /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-13T15:00:00Z", "2026-02-14T15:00:00Z", "2026-02-15T15:00:00Z"] |
| universityflow.student_simulation_experiment_result.simulation_result_data | Simulation Result Data / simulation_result_data | Stored experiment output; not a timestamp | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Synthetic output 1", "Synthetic output 2"] |
| universityflow.student_simulation_experiment_result.result_analysis | Result Analysis / result_analysis | Student analysis of the experiment result | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Recorded experiment analysis"] |

- **Declared table constraints:** `CREATE TABLE student_simulation_experiment_result (student_id TEXT NOT NULL, module_id TEXT NOT NULL, simulation_date TEXT NOT NULL, simulation_result_data TEXT NOT NULL, result_analysis TEXT NOT NULL, PRIMARY KEY (student_id,module_id,simulation_date), FOREIGN KEY (student_id) REFERENCES student(student_id), FOREIGN KEY (module_id) REFERENCES simulation_module(module_id))`

### assignment

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| universityflow.assignment.assignment_id | Assignment Id / assignment_id | Assignment identifier | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["A002", "A003", "A006"] |
| universityflow.assignment.student_id | Student Id / student_id | Student identifier shared across the three combined examples | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / student.student_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["S002", "S003", "S006"] |
| universityflow.assignment.assignment_content | Assignment Content / assignment_content | Submitted assignment content; actual submission time is absent | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Synthetic assignment content"] |
| universityflow.assignment.assignment_assigned_at | Assignment Assigned At / assignment_assigned_at | Actual UTC time of Assignment Assigned. NULL means no recorded occurrence. Authored single-occurrence milestone; not a source-provided field. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-07T14:00:00Z", "2026-02-08T14:00:00Z", "2026-02-11T14:00:00Z"] |
| universityflow.assignment.assignment_submitted_at | Assignment Submitted At / assignment_submitted_at | Actual UTC time of Assignment Submitted. NULL means no recorded occurrence. Authored single-occurrence milestone; not a source-provided field. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-09T14:00:00Z", "2026-02-10T14:00:00Z", "2026-02-13T14:00:00Z"] |
| universityflow.assignment.assignment_grade_finalized_at | Assignment Grade Finalized At / assignment_grade_finalized_at | Actual UTC time of Assignment Grade Finalized. NULL means no recorded occurrence. Authored single-occurrence milestone; not a source-provided field. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-14T14:00:00Z", "2026-02-17T14:00:00Z", "2026-02-19T14:00:00Z"] |

- **Declared table constraints:** `CREATE TABLE assignment (assignment_id TEXT NOT NULL, student_id TEXT NOT NULL, assignment_content TEXT NOT NULL, assignment_assigned_at TEXT, assignment_submitted_at TEXT, assignment_grade_finalized_at TEXT, PRIMARY KEY (assignment_id), FOREIGN KEY (student_id) REFERENCES student(student_id))`

### instructor

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| universityflow.instructor.instructor_id | Instructor Id / instructor_id | Instructor identifier | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["I01", "I02", "I03"] |
| universityflow.instructor.instructor_name | Instructor Name / instructor_name | Instructor name | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Instructor 1", "Instructor 2", "Instructor 3"] |
| universityflow.instructor.course | Course / course | Instructor course label from the assignment source; no declared FK to course | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Database Systems", "Statistics", "Operations Research"] |

- **Declared table constraints:** `CREATE TABLE instructor (instructor_id TEXT NOT NULL, instructor_name TEXT NOT NULL, course TEXT NOT NULL, PRIMARY KEY (instructor_id))`

### assignment_grading

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| universityflow.assignment_grading.assignment_id | Assignment Id / assignment_id | Assignment identifier | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 / assignment.assignment_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["A002", "A003", "A006"] |
| universityflow.assignment_grading.instructor_id | Instructor Id / instructor_id | Instructor identifier | Identifier / TEXT | Not bounded by declared SQLite type | yes | 2 / instructor.instructor_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["I03", "I01", "I02"] |
| universityflow.assignment_grading.grading_time | Grading Time / grading_time | Actual grading time in UTC; regrading creates another composite-key row | Date/time text / TEXT | Not bounded by declared SQLite type | yes | 3 /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-11T14:00:00Z", "2026-02-12T14:00:00Z", "2026-02-15T14:00:00Z"] |
| universityflow.assignment_grading.score | Score / score | Assignment grade, 0 to 100 | Number / INTEGER | Not applicable | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL CHECK(score BETWEEN 0 AND 100) | See column definition; no implicit unit | [70, 80] |
| universityflow.assignment_grading.evaluation | Evaluation / evaluation | Instructor feedback | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Initial feedback", "Revised feedback"] |

- **Declared table constraints:** `CREATE TABLE assignment_grading (assignment_id TEXT NOT NULL, instructor_id TEXT NOT NULL, grading_time TEXT NOT NULL, score INTEGER NOT NULL CHECK(score BETWEEN 0 AND 100), evaluation TEXT NOT NULL, PRIMARY KEY (assignment_id,instructor_id,grading_time), FOREIGN KEY (assignment_id) REFERENCES assignment(assignment_id), FOREIGN KEY (instructor_id) REFERENCES instructor(instructor_id))`

### assignment_activity

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| universityflow.assignment_activity.event_id | Event Id / event_id | Stable identity of this actual business action; authored extension | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: PRIMARY KEY | See column definition; no implicit unit | ["LC:assignment:A002:3", "LC:assignment:A002:4", "LC:assignment:A002:5"] |
| universityflow.assignment_activity.assignment_id | Assignment Id / assignment_id | Explicit parent object key; FK to assignment.assignment_id | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / assignment.assignment_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["A002", "A007", "A014"] |
| universityflow.assignment_activity.activity | Activity / activity | Controlled business activity label; not a technical database update | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Assignment Revision Requested", "Assignment Resubmitted", "Assignment Regraded"] |
| universityflow.assignment_activity.occurred_at | Occurred At / occurred_at | Actual occurrence time in UTC, distinct from planned dates | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-11T15:00:00Z", "2026-02-12T14:00:00Z", "2026-02-13T02:00:00Z"] |
| universityflow.assignment_activity.outcome | Outcome / outcome | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["REVISION_REQUIRED", "COMPLETED"] |

- **Declared table constraints:** `CREATE TABLE assignment_activity (event_id TEXT PRIMARY KEY, assignment_id TEXT NOT NULL, activity TEXT NOT NULL, occurred_at TEXT NOT NULL, outcome TEXT NOT NULL, FOREIGN KEY (assignment_id) REFERENCES assignment(assignment_id))`

### simulation_module_activity

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| universityflow.simulation_module_activity.event_id | Event Id / event_id | Stable identity of this actual business action; authored extension | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: PRIMARY KEY | See column definition; no implicit unit | ["LC:simulation_module:M01:1", "LC:simulation_module:M01:2", "LC:simulation_module:M01:3"] |
| universityflow.simulation_module_activity.module_id | Module Id / module_id | Explicit parent object key; FK to simulation_module.module_id | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / simulation_module.module_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["M01", "M02", "M03"] |
| universityflow.simulation_module_activity.activity | Activity / activity | Controlled business activity label; not a technical database update | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Simulation Module Published", "Simulation Module Validated", "Simulation Module Released"] |
| universityflow.simulation_module_activity.occurred_at | Occurred At / occurred_at | Actual occurrence time in UTC, distinct from planned dates | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-11T15:00:00Z", "2026-02-12T15:00:00Z", "2026-02-13T15:00:00Z"] |
| universityflow.simulation_module_activity.outcome | Outcome / outcome | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["COMPLETED", "APPROVED"] |

- **Declared table constraints:** `CREATE TABLE simulation_module_activity (event_id TEXT PRIMARY KEY, module_id TEXT NOT NULL, activity TEXT NOT NULL, occurred_at TEXT NOT NULL, outcome TEXT NOT NULL, FOREIGN KEY (module_id) REFERENCES simulation_module(module_id))`

### student_simulation_experiment_result_activity

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| universityflow.student_simulation_experiment_result_activity.event_id | Event Id / event_id | Stable identity of this actual business action; authored extension | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: PRIMARY KEY | See column definition; no implicit unit | ["LC:student_simulation_experiment_result:S002:M03:2026-02-13T15:00:00Z:1", "LC:student_simulation_experiment_result:S002:M03:2026-02-13T15:00:00Z:2", "LC:student_simulation_experiment_result:S002:M03:2026-02-13T15:00:00Z:3"] |
| universityflow.student_simulation_experiment_result_activity.student_id | Student Id / student_id | Explicit parent object key; FK to student_simulation_experiment_result.student_id | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / student_simulation_experiment_result.student_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["S002", "S003", "S006"] |
| universityflow.student_simulation_experiment_result_activity.module_id | Module Id / module_id | Explicit parent object key; FK to student_simulation_experiment_result.module_id | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / student_simulation_experiment_result.module_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["M03", "M01", "M02"] |
| universityflow.student_simulation_experiment_result_activity.simulation_date | Simulation Date / simulation_date | Explicit parent object key; FK to student_simulation_experiment_result.simulation_date | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  / student_simulation_experiment_result.simulation_date | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-13T15:00:00Z", "2026-02-14T15:00:00Z", "2026-02-15T15:00:00Z"] |
| universityflow.student_simulation_experiment_result_activity.activity | Activity / activity | Controlled business activity label; not a technical database update | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Simulation Run Scheduled", "Simulation Run Started", "Simulation Output Reviewed"] |
| universityflow.student_simulation_experiment_result_activity.occurred_at | Occurred At / occurred_at | Actual occurrence time in UTC, distinct from planned dates | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-13T13:00:00Z", "2026-02-13T14:00:00Z", "2026-02-13T17:00:00Z"] |
| universityflow.student_simulation_experiment_result_activity.outcome | Outcome / outcome | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["COMPLETED", "APPROVED"] |

- **Declared table constraints:** `CREATE TABLE student_simulation_experiment_result_activity (event_id TEXT PRIMARY KEY, student_id TEXT NOT NULL, module_id TEXT NOT NULL, simulation_date TEXT NOT NULL, activity TEXT NOT NULL, occurred_at TEXT NOT NULL, outcome TEXT NOT NULL, FOREIGN KEY (student_id,module_id,simulation_date) REFERENCES student_simulation_experiment_result(student_id,module_id,simulation_date))`

### thesis_activity

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| universityflow.thesis_activity.event_id | Event Id / event_id | Stable identity of this actual business action; authored extension | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: PRIMARY KEY | See column definition; no implicit unit | ["LC:thesis:TH002:3", "LC:thesis:TH002:4", "LC:thesis:TH007:3"] |
| universityflow.thesis_activity.thesis_id | Thesis Id / thesis_id | Explicit parent object key; FK to thesis.thesis_id | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / thesis.thesis_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["TH002", "TH007", "TH018"] |
| universityflow.thesis_activity.activity | Activity / activity | Controlled business activity label; not a technical database update | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Thesis Revision Requested", "Thesis Resubmitted"] |
| universityflow.thesis_activity.occurred_at | Occurred At / occurred_at | Actual occurrence time in UTC, distinct from planned dates | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-25T16:00:00Z", "2026-02-26T16:00:00Z", "2026-03-02T16:00:00Z"] |
| universityflow.thesis_activity.outcome | Outcome / outcome | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["REVISION_REQUIRED", "COMPLETED"] |

- **Declared table constraints:** `CREATE TABLE thesis_activity (event_id TEXT PRIMARY KEY, thesis_id TEXT NOT NULL, activity TEXT NOT NULL, occurred_at TEXT NOT NULL, outcome TEXT NOT NULL, FOREIGN KEY (thesis_id) REFERENCES thesis(thesis_id))`

### course_activity

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| universityflow.course_activity.event_id | Event Id / event_id | Stable identity of this actual business action; authored extension | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: PRIMARY KEY | See column definition; no implicit unit | ["LC:course:C01:1", "LC:course:C01:2", "LC:course:C01:3"] |
| universityflow.course_activity.course_id | Course Id / course_id | Explicit parent object key; FK to course.course_id | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / course.course_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["C01", "C02", "C03"] |
| universityflow.course_activity.activity | Activity / activity | Controlled business activity label; not a technical database update | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Course Offering Proposed", "Course Offering Approved", "Course Offering Published"] |
| universityflow.course_activity.occurred_at | Occurred At / occurred_at | Actual occurrence time in UTC, distinct from planned dates | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-02-04T11:00:00Z", "2026-02-05T11:00:00Z", "2026-02-06T11:00:00Z"] |
| universityflow.course_activity.outcome | Outcome / outcome | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["COMPLETED", "APPROVED"] |

- **Declared table constraints:** `CREATE TABLE course_activity (event_id TEXT PRIMARY KEY, course_id TEXT NOT NULL, activity TEXT NOT NULL, occurred_at TEXT NOT NULL, outcome TEXT NOT NULL, FOREIGN KEY (course_id) REFERENCES course(course_id))`

### task_activity

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| universityflow.task_activity.event_id | Event Id / event_id | Stable identity of this actual business action; authored extension | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: PRIMARY KEY | See column definition; no implicit unit | ["LC:task:T01:1", "LC:task:T01:2", "LC:task:T01:3"] |
| universityflow.task_activity.task_id | Task Id / task_id | Explicit parent object key; FK to task.task_id | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / task.task_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["T01", "T02", "T03"] |
| universityflow.task_activity.activity | Activity / activity | Controlled business activity label; not a technical database update | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Design Task Created", "Design Task Approved", "Design Task Published"] |
| universityflow.task_activity.occurred_at | Occurred At / occurred_at | Actual occurrence time in UTC, distinct from planned dates | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2025-12-31T00:00:00Z", "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"] |
| universityflow.task_activity.outcome | Outcome / outcome | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["COMPLETED", "APPROVED"] |

- **Declared table constraints:** `CREATE TABLE task_activity (event_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, activity TEXT NOT NULL, occurred_at TEXT NOT NULL, outcome TEXT NOT NULL, FOREIGN KEY (task_id) REFERENCES task(task_id))`

### lifecycle_case_link

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| universityflow.lifecycle_case_link.event_id | Event Id / event_id | Validated identity in a typed activity table; polymorphic reference | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["LC:assignment:A002:1", "LC:assignment:A002:2", "LC:assignment:A002:3"] |
| universityflow.lifecycle_case_link.case_table | Case Table / case_table | Controlled existing business table name | Identifier / TEXT | Not bounded by declared SQLite type | yes | 2 /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["registration", "student", "course"] |
| universityflow.lifecycle_case_link.case_id | Case Id / case_id | Serialized primary key of the declared case table; composite parts separated by colon | Identifier / TEXT | Not bounded by declared SQLite type | yes | 3 /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["S002:C01", "S002:C06", "S003:C02"] |

- **Declared table constraints:** `CREATE TABLE lifecycle_case_link(event_id TEXT NOT NULL,case_table TEXT NOT NULL,case_id TEXT NOT NULL,PRIMARY KEY(event_id,case_table,case_id))`

### Business meanings and extraction rules

- Original source layer: The original default questions use students as cases. Object-view questions use the alternative case tables and scope rules listed in the task catalog.
- Original source layer: An examination-result row records one Degree Examination Taken event at examination_date, not score publication.
- Original source layer: A registration row records one Course Registered event at registration_time.
- Original source layer: The default student timeline includes all recorded examinations, registrations, assignment grading, simulation-experiment completions and thesis submissions linked to that student.
- Original source layer: A grading event belongs to the student through assignment_grading.assignment_id → assignment.assignment_id → assignment.student_id. Do not join its instructor course label to every student registration.
- Original source layer: Simulation-result and grading composite keys retain repeated actions at different times. Each occurrence appears once.
- Original source layer: A passing examination score of at least 60 enables subsequent registration in the simulation; the source does not define this threshold.
- Original source layer: Student ID and Name denote shared student information across the three sources. Class is merged between two sources; Major is retained from the course-design source. This shared identity is an integration assumption.
- Original source layer: The student-course registration key is preserved; withdrawals and repeat registrations are not invented.
- Original source layer: Task start/end dates and course schedules are plans, not observed student actions. The source has no task-to-student or task-to-experiment link; none is invented.
- Original source layer: Instructor course labels and course.instructor are text fields retained from different sources. No unprovided FK is inferred between them.
- Original source layer: Actual event times use UTC. simulation_date is interpreted as experiment completion, and submission_date as thesis submission. These meanings are documented adaptations.
- Original source layer: Assignment content does not timestamp assignment submission. Notifications, withdrawals, result publication and eligibility changes cannot be reconstructed.
- Original source layer: Students with no selected events remain in the separately declared case population. The full timeline groups academic actions without asserting they belong to one course or one causal chain.
- Original source rows are preserved. Added typed activity histories are authored synthetic domain extensions, not claimed source fields.
- Only actual occurred_at times generate lifecycle events. Planned dates and technical timestamps remain excluded.
- Lifecycle case links use exact typed object identity. Related cases may share an event; uniqueness is (case_id,event_id).
- Incomplete cases and conditional revision branches are intentional; no final action is inferred for an open case.
- One-time milestone events are stored in named timestamp columns on their business record. They have been removed from generic action rows to prevent duplicate extraction.
- Repeated review/revision/grading/experiment actions remain row encoded; milestone timestamps preserve their original event IDs and actual times.

### Object activity storage

- Actual one-time milestone columns and retained row histories are used together. Events are extracted once, not mirrored in two places.
- Original event IDs and occurrence times are preserved. All added fields are authored synthetic extensions.

| Object | Activities | Storage |
|---|---|---|
| registration | Registration Requested; Registration Approved; Course Started; Course Assessment Completed; Course Grade Finalized | Actual milestone columns on registration |
| degree_examination_result | Examination Scheduled; Examination Checked In; Examination Score Published; Examination Result Reviewed | Actual milestone columns on degree_examination_result |
| assignment | Assignment Assigned; Assignment Submitted; Assignment Revision Requested; Assignment Resubmitted; Assignment Grade Finalized; Assignment Regraded | Actual milestone columns on assignment; remaining repeatable actions stay in assignment_activity |
| simulation_module | Simulation Module Published; Simulation Module Validated; Simulation Module Released; Simulation Module Retired | simulation_module_activity |
| student_simulation_experiment_result | Simulation Run Scheduled; Simulation Run Started; Simulation Output Reviewed; Simulation Result Accepted | student_simulation_experiment_result_activity |
| thesis | Thesis Draft Registered; Thesis Review Started; Thesis Revision Requested; Thesis Resubmitted; Thesis Accepted | Actual milestone columns on thesis; remaining repeatable actions stay in thesis_activity |
| course | Course Offering Proposed; Course Offering Approved; Course Offering Published; Course Offering Closed | course_activity |
| task | Design Task Created; Design Task Approved; Design Task Published; Design Task Closed | task_activity |
