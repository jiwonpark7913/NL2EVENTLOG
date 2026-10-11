# UniversityFlow English Data Dictionary

## student

- Unified student information from the three university examples
- Primary key: student_id

| Column | Type | Meaning |
|---|---|---|
| student_id | TEXT | Student identifier shared across the three combined examples |
| name | TEXT | Student name |
| date_of_birth | TEXT | Birth date; not an academic event |
| phone_number | TEXT | Student contact number |
| home_address | TEXT | Student postal address |
| registration_eligibility | TEXT | Current eligibility, ELIGIBLE or INELIGIBLE; changes are not timestamped |
| class | TEXT | Student class or cohort |
| major | TEXT | Student major |

## course

- Course offerings and planned teaching schedules
- Primary key: course_id

| Column | Type | Meaning |
|---|---|---|
| course_id | TEXT | Course-offering identifier |
| course_name | TEXT | Course title |
| credits | INTEGER | Academic credit units |
| instructor | TEXT | Instructor name as stored in the registration source; no FK to instructor is assumed |
| class_time | TEXT | Planned teaching time; not proof that a class occurred |
| class_location | TEXT | Planned teaching location |

## registration

- Successful registrations; one retained row per student and course
- Primary key: student_id, course_id
- Foreign key: student_id → student.student_id
- Foreign key: course_id → course.course_id

| Column | Type | Meaning |
|---|---|---|
| student_id | TEXT | Student identifier shared across the three combined examples |
| course_id | TEXT | Course-offering identifier |
| registration_time | TEXT | Actual successful registration time in UTC |
| status | TEXT | Current registration status; REGISTERED in the simulated rows; no change history |

## degree_examination_result

- Examination results including retakes
- Primary key: result_id
- Foreign key: student_id → student.student_id

| Column | Type | Meaning |
|---|---|---|
| result_id | TEXT | Unique examination-result identifier |
| student_id | TEXT | Student identifier shared across the three combined examples |
| examination_name | TEXT | Degree examination name |
| grade | INTEGER | Examination score, 0 to 100; 60 is the simulated passing threshold |
| examination_date | TEXT | Actual examination time in UTC; not score-publication time |

## task

- Course-design task descriptions and scheduled task periods
- Primary key: task_id

| Column | Type | Meaning |
|---|---|---|
| task_id | TEXT | Course-design task identifier |
| task_title | TEXT | Task title |
| task_description | TEXT | Task description |
| task_start_date | TEXT | Scheduled task-period start; not an observed student action |
| task_end_date | TEXT | Scheduled task deadline; not proof of completion |
| task_location | TEXT | Task location |

## simulation_module

- Simulation module descriptions and example code
- Primary key: module_id

| Column | Type | Meaning |
|---|---|---|
| module_id | TEXT | Simulation module identifier |
| module_name | TEXT | Module name |
| module_type | TEXT | Simulation method, such as PCM or DPCM |
| module_description | TEXT | Module description |
| module_code | TEXT | Example module code; not an event code |

## thesis

- Student theses with actual submission times
- Primary key: thesis_id
- Foreign key: student_id → student.student_id

| Column | Type | Meaning |
|---|---|---|
| thesis_id | TEXT | Thesis identifier |
| student_id | TEXT | Student identifier shared across the three combined examples |
| thesis_title | TEXT | Thesis title |
| thesis_content | TEXT | Submitted thesis content |
| submission_date | TEXT | Actual thesis-submission time in UTC |

## student_simulation_experiment_result

- Student simulation results with actual experiment-completion times
- Primary key: student_id, module_id, simulation_date
- Foreign key: student_id → student.student_id
- Foreign key: module_id → simulation_module.module_id

| Column | Type | Meaning |
|---|---|---|
| student_id | TEXT | Student identifier shared across the three combined examples |
| module_id | TEXT | Simulation module identifier |
| simulation_date | TEXT | Actual experiment-completion time in UTC; this interpretation is an added simulation assumption |
| simulation_result_data | TEXT | Stored experiment output; not a timestamp |
| result_analysis | TEXT | Student analysis of the experiment result |

## assignment

- Student assignment content; submission time is not recorded
- Primary key: assignment_id
- Foreign key: student_id → student.student_id

| Column | Type | Meaning |
|---|---|---|
| assignment_id | TEXT | Assignment identifier |
| student_id | TEXT | Student identifier shared across the three combined examples |
| assignment_content | TEXT | Submitted assignment content; actual submission time is absent |

## instructor

- Instructor information from the assignment-management example
- Primary key: instructor_id

| Column | Type | Meaning |
|---|---|---|
| instructor_id | TEXT | Instructor identifier |
| instructor_name | TEXT | Instructor name |
| course | TEXT | Instructor course label from the assignment source; no declared FK to course |

## assignment_grading

- Every recorded grading action, including regrading
- Primary key: assignment_id, instructor_id, grading_time
- Foreign key: assignment_id → assignment.assignment_id
- Foreign key: instructor_id → instructor.instructor_id

| Column | Type | Meaning |
|---|---|---|
| assignment_id | TEXT | Assignment identifier |
| instructor_id | TEXT | Instructor identifier |
| grading_time | TEXT | Actual grading time in UTC; regrading creates another composite-key row |
| score | INTEGER | Assignment grade, 0 to 100 |
| evaluation | TEXT | Instructor feedback |

## Business rules

- Use each student as a case (one timeline).
- An examination-result row records one Degree Examination Taken event at examination_date, not score publication.
- A registration row records one Course Registered event at registration_time.
- The default student timeline includes all recorded examinations, registrations, assignment grading, simulation-experiment completions and thesis submissions linked to that student.
- A grading event belongs to the student through assignment_grading.assignment_id → assignment.assignment_id → assignment.student_id. Do not join its instructor course label to every student registration.
- Simulation-result and grading composite keys retain repeated actions at different times. Each occurrence appears once.
- A passing examination score of at least 60 enables subsequent registration in the simulation; the source does not define this threshold.
- Student ID and Name denote shared student information across the three sources. Class is merged between two sources; Major is retained from the course-design source. This shared identity is an integration assumption.
- The student-course registration key is preserved; withdrawals and repeat registrations are not invented.
- Task start/end dates and course schedules are plans, not observed student actions. The source has no task-to-student or task-to-experiment link; none is invented.
- Instructor course labels and course.instructor are text fields retained from different sources. No unprovided FK is inferred between them.
- Actual event times use UTC. simulation_date is interpreted as experiment completion, and submission_date as thesis submission. These meanings are documented adaptations.
- Assignment content does not timestamp assignment submission. Notifications, withdrawals, result publication and eligibility changes cannot be reconstructed.
- Students with no selected events remain in the separately declared case population. The full timeline groups academic actions without asserting they belong to one course or one causal chain.
