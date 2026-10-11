# UniversityFlow · combined RSchema examples — table and column dictionary

- Generated from the executable SQLite schema and English metadata.

| Table | Rows | Columns | Primary key | Role |
|---|---:|---:|---|---|
| student | 40 | 8 | student_id | Unified student information from the three university examples |
| course | 6 | 6 | course_id | Course offerings and planned teaching schedules |
| registration | 47 | 4 | student_id, course_id | Successful registrations; one retained row per student and course |
| degree_examination_result | 40 | 5 | result_id | Examination results including retakes |
| task | 3 | 6 | task_id | Course-design task descriptions and scheduled task periods |
| simulation_module | 3 | 5 | module_id | Simulation module descriptions and example code |
| thesis | 16 | 5 | thesis_id | Student theses with actual submission times |
| student_simulation_experiment_result | 27 | 5 | student_id, module_id, simulation_date | Student simulation results with actual experiment-completion times |
| assignment | 20 | 3 | assignment_id | Student assignment content; submission time is not recorded |
| instructor | 3 | 3 | instructor_id | Instructor information from the assignment-management example |
| assignment_grading | 18 | 5 | assignment_id, instructor_id, grading_time | Every recorded grading action, including regrading |
| registration_activity | 228 | 6 | event_id | Authored actual-action history for registration |
| degree_examination_result_activity | 154 | 5 | event_id | Authored actual-action history for degree_examination_result |
| assignment_activity | 72 | 5 | event_id | Authored actual-action history for assignment |
| simulation_module_activity | 11 | 5 | event_id | Authored actual-action history for simulation_module |
| student_simulation_experiment_result_activity | 104 | 7 | event_id | Authored actual-action history for student_simulation_experiment_result |
| thesis_activity | 57 | 5 | event_id | Authored actual-action history for thesis |
| course_activity | 23 | 5 | event_id | Authored actual-action history for course |
| task_activity | 11 | 5 | event_id | Authored actual-action history for task |
| lifecycle_case_link | 1675 | 3 | event_id, case_table, case_id | Explicit case attribution across typed action histories; auxiliary extraction index, not a business case |

## Columns

### student

- Unified student information from the three university examples

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| student_id | TEXT | yes | PK | Student identifier shared across the three combined examples |
| name | TEXT | yes |  | Student name |
| date_of_birth | TEXT | yes |  | Birth date; not an academic event |
| phone_number | TEXT | yes |  | Student contact number |
| home_address | TEXT | yes |  | Student postal address |
| registration_eligibility | TEXT | yes |  | Current eligibility, ELIGIBLE or INELIGIBLE; changes are not timestamped |
| class | TEXT | yes |  | Student class or cohort |
| major | TEXT | yes |  | Student major |

### course

- Course offerings and planned teaching schedules

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| course_id | TEXT | yes | PK | Course-offering identifier |
| course_name | TEXT | yes |  | Course title |
| credits | INTEGER | yes |  | Academic credit units |
| instructor | TEXT | yes |  | Instructor name as stored in the registration source; no FK to instructor is assumed |
| class_time | TEXT | yes |  | Planned teaching time; not proof that a class occurred |
| class_location | TEXT | yes |  | Planned teaching location |

### registration

- Successful registrations; one retained row per student and course

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| student_id | TEXT | yes | PK; FK → student.student_id | Student identifier shared across the three combined examples |
| course_id | TEXT | yes | PK; FK → course.course_id | Course-offering identifier |
| registration_time | TEXT | yes |  | Actual successful registration time in UTC |
| status | TEXT | yes |  | Current registration status; REGISTERED in the simulated rows; no change history |

### degree_examination_result

- Examination results including retakes

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| result_id | TEXT | yes | PK | Unique examination-result identifier |
| student_id | TEXT | yes | FK → student.student_id | Student identifier shared across the three combined examples |
| examination_name | TEXT | yes |  | Degree examination name |
| grade | INTEGER | yes |  | Examination score, 0 to 100; 60 is the simulated passing threshold |
| examination_date | TEXT | yes |  | Actual examination time in UTC; not score-publication time |

### task

- Course-design task descriptions and scheduled task periods

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| task_id | TEXT | yes | PK | Course-design task identifier |
| task_title | TEXT | yes |  | Task title |
| task_description | TEXT | yes |  | Task description |
| task_start_date | TEXT | yes |  | Scheduled task-period start; not an observed student action |
| task_end_date | TEXT | yes |  | Scheduled task deadline; not proof of completion |
| task_location | TEXT | yes |  | Task location |

### simulation_module

- Simulation module descriptions and example code

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| module_id | TEXT | yes | PK | Simulation module identifier |
| module_name | TEXT | yes |  | Module name |
| module_type | TEXT | yes |  | Simulation method, such as PCM or DPCM |
| module_description | TEXT | yes |  | Module description |
| module_code | TEXT | yes |  | Example module code; not an event code |

### thesis

- Student theses with actual submission times

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| thesis_id | TEXT | yes | PK | Thesis identifier |
| student_id | TEXT | yes | FK → student.student_id | Student identifier shared across the three combined examples |
| thesis_title | TEXT | yes |  | Thesis title |
| thesis_content | TEXT | yes |  | Submitted thesis content |
| submission_date | TEXT | yes |  | Actual thesis-submission time in UTC |

### student_simulation_experiment_result

- Student simulation results with actual experiment-completion times

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| student_id | TEXT | yes | PK; FK → student.student_id | Student identifier shared across the three combined examples |
| module_id | TEXT | yes | PK; FK → simulation_module.module_id | Simulation module identifier |
| simulation_date | TEXT | yes | PK | Actual experiment-completion time in UTC; this interpretation is an added simulation assumption |
| simulation_result_data | TEXT | yes |  | Stored experiment output; not a timestamp |
| result_analysis | TEXT | yes |  | Student analysis of the experiment result |

### assignment

- Student assignment content; submission time is not recorded

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| assignment_id | TEXT | yes | PK | Assignment identifier |
| student_id | TEXT | yes | FK → student.student_id | Student identifier shared across the three combined examples |
| assignment_content | TEXT | yes |  | Submitted assignment content; actual submission time is absent |

### instructor

- Instructor information from the assignment-management example

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| instructor_id | TEXT | yes | PK | Instructor identifier |
| instructor_name | TEXT | yes |  | Instructor name |
| course | TEXT | yes |  | Instructor course label from the assignment source; no declared FK to course |

### assignment_grading

- Every recorded grading action, including regrading

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| assignment_id | TEXT | yes | PK; FK → assignment.assignment_id | Assignment identifier |
| instructor_id | TEXT | yes | PK; FK → instructor.instructor_id | Instructor identifier |
| grading_time | TEXT | yes | PK | Actual grading time in UTC; regrading creates another composite-key row |
| score | INTEGER | yes |  | Assignment grade, 0 to 100 |
| evaluation | TEXT | yes |  | Instructor feedback |

### registration_activity

- Authored actual-action history for registration

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| event_id | TEXT | yes | PK | Stable identity of this actual business action; authored extension |
| student_id | TEXT | yes | FK → registration.student_id | Explicit parent object key; FK to registration.student_id |
| course_id | TEXT | yes | FK → registration.course_id | Explicit parent object key; FK to registration.course_id |
| activity | TEXT | yes |  | Controlled business activity label; not a technical database update |
| occurred_at | TEXT | yes |  | Actual occurrence time in UTC, distinct from planned dates |
| outcome | TEXT | yes |  | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED |

### degree_examination_result_activity

- Authored actual-action history for degree_examination_result

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| event_id | TEXT | yes | PK | Stable identity of this actual business action; authored extension |
| result_id | TEXT | yes | FK → degree_examination_result.result_id | Explicit parent object key; FK to degree_examination_result.result_id |
| activity | TEXT | yes |  | Controlled business activity label; not a technical database update |
| occurred_at | TEXT | yes |  | Actual occurrence time in UTC, distinct from planned dates |
| outcome | TEXT | yes |  | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED |

### assignment_activity

- Authored actual-action history for assignment

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| event_id | TEXT | yes | PK | Stable identity of this actual business action; authored extension |
| assignment_id | TEXT | yes | FK → assignment.assignment_id | Explicit parent object key; FK to assignment.assignment_id |
| activity | TEXT | yes |  | Controlled business activity label; not a technical database update |
| occurred_at | TEXT | yes |  | Actual occurrence time in UTC, distinct from planned dates |
| outcome | TEXT | yes |  | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED |

### simulation_module_activity

- Authored actual-action history for simulation_module

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| event_id | TEXT | yes | PK | Stable identity of this actual business action; authored extension |
| module_id | TEXT | yes | FK → simulation_module.module_id | Explicit parent object key; FK to simulation_module.module_id |
| activity | TEXT | yes |  | Controlled business activity label; not a technical database update |
| occurred_at | TEXT | yes |  | Actual occurrence time in UTC, distinct from planned dates |
| outcome | TEXT | yes |  | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED |

### student_simulation_experiment_result_activity

- Authored actual-action history for student_simulation_experiment_result

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| event_id | TEXT | yes | PK | Stable identity of this actual business action; authored extension |
| student_id | TEXT | yes | FK → student_simulation_experiment_result.student_id | Explicit parent object key; FK to student_simulation_experiment_result.student_id |
| module_id | TEXT | yes | FK → student_simulation_experiment_result.module_id | Explicit parent object key; FK to student_simulation_experiment_result.module_id |
| simulation_date | TEXT | yes | FK → student_simulation_experiment_result.simulation_date | Explicit parent object key; FK to student_simulation_experiment_result.simulation_date |
| activity | TEXT | yes |  | Controlled business activity label; not a technical database update |
| occurred_at | TEXT | yes |  | Actual occurrence time in UTC, distinct from planned dates |
| outcome | TEXT | yes |  | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED |

### thesis_activity

- Authored actual-action history for thesis

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| event_id | TEXT | yes | PK | Stable identity of this actual business action; authored extension |
| thesis_id | TEXT | yes | FK → thesis.thesis_id | Explicit parent object key; FK to thesis.thesis_id |
| activity | TEXT | yes |  | Controlled business activity label; not a technical database update |
| occurred_at | TEXT | yes |  | Actual occurrence time in UTC, distinct from planned dates |
| outcome | TEXT | yes |  | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED |

### course_activity

- Authored actual-action history for course

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| event_id | TEXT | yes | PK | Stable identity of this actual business action; authored extension |
| course_id | TEXT | yes | FK → course.course_id | Explicit parent object key; FK to course.course_id |
| activity | TEXT | yes |  | Controlled business activity label; not a technical database update |
| occurred_at | TEXT | yes |  | Actual occurrence time in UTC, distinct from planned dates |
| outcome | TEXT | yes |  | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED |

### task_activity

- Authored actual-action history for task

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| event_id | TEXT | yes | PK | Stable identity of this actual business action; authored extension |
| task_id | TEXT | yes | FK → task.task_id | Explicit parent object key; FK to task.task_id |
| activity | TEXT | yes |  | Controlled business activity label; not a technical database update |
| occurred_at | TEXT | yes |  | Actual occurrence time in UTC, distinct from planned dates |
| outcome | TEXT | yes |  | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED |

### lifecycle_case_link

- Explicit case attribution across typed action histories; auxiliary extraction index, not a business case

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| event_id | TEXT | yes | PK | Validated identity in a typed activity table; polymorphic reference |
| case_table | TEXT | yes | PK | Controlled existing business table name |
| case_id | TEXT | yes | PK | Serialized primary key of the declared case table; composite parts separated by colon |

## Value domains and business rules

- ELIGIBLE: Student may register after passing the simulated examination
- INELIGIBLE: Student has no passing examination
- REGISTERED: Successful registration

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

# Universityflow object activities and scenarios

- Original source requirements, columns and keys remain preserved.
- Every action below is an explicitly authored domain extension; these stages were not present in the source schemas.
- Each added history row records an actual activity, occurrence time, outcome and a declared FK to its object.
- Conditional revision branches and incomplete cases are intentional. Atomic grading/operation records remain auxiliary logs.
- Master-object views aggregate linked work; they do not assert one chronological causal process across unrelated jobs.

| Object | Added activities | Situation | Storage |
|---|---|---|---|
| registration | Registration Requested → Registration Approved → Course Started → Course Assessment Completed → Course Grade Finalized | Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects. | registration_activity |
| degree_examination_result | Examination Scheduled → Examination Checked In → Examination Score Published → Examination Result Reviewed | Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects. | degree_examination_result_activity |
| assignment | Assignment Assigned → Assignment Submitted → Assignment Revision Requested → Assignment Resubmitted → Assignment Grade Finalized → Assignment Regraded | Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects. | assignment_activity |
| simulation_module | Simulation Module Published → Simulation Module Validated → Simulation Module Released → Simulation Module Retired | Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects. | simulation_module_activity |
| student_simulation_experiment_result | Simulation Run Scheduled → Simulation Run Started → Simulation Output Reviewed → Simulation Result Accepted | Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects. | student_simulation_experiment_result_activity |
| thesis | Thesis Draft Registered → Thesis Review Started → Thesis Revision Requested → Thesis Resubmitted → Thesis Accepted | Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects. | thesis_activity |
| course | Course Offering Proposed → Course Offering Approved → Course Offering Published → Course Offering Closed | Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects. | course_activity |
| task | Design Task Created → Design Task Approved → Design Task Published → Design Task Closed | Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects. | task_activity |

- The full ES unions the original milestone sources and the new typed activity histories, then applies explicit event-to-case links.
- Related goods/workers, students/instructors and parent materials receive an event only through a documented business relationship.
- `lifecycle_case_link` is a generated extraction index with validated object identities; it is not an additional business object.
