# UniversityFlow · RSchema — table and column dictionary

- Generated from the executable SQLite schema and English metadata.

| Table | Rows | Columns | Primary key | Role |
|---|---:|---:|---|---|
| student | 40 | 6 | student_id | Basic student information and current registration eligibility |
| course | 6 | 6 | course_id | Course offerings and teaching schedules |
| registration | 47 | 4 | student_id, course_id | Successful student-course registrations; one row per student and course |
| degree_examination_result | 40 | 5 | result_id | Degree examination results; repeated examinations use separate result IDs |

## Columns

### student

- Basic student information and current registration eligibility

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| student_id | TEXT | yes | PK | Student identifier |
| name | TEXT | yes |  | Student name |
| date_of_birth | TEXT | yes |  | Birth date; not an academic event |
| phone_number | TEXT | yes |  | Student contact number |
| home_address | TEXT | yes |  | Student postal address |
| registration_eligibility | TEXT | yes |  | Current eligibility: ELIGIBLE or INELIGIBLE; does not store when eligibility changed |

### course

- Course offerings and teaching schedules

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| course_id | TEXT | yes | PK | Course identifier; one course offering in this dataset |
| course_name | TEXT | yes |  | Course title |
| credits | INTEGER | yes |  | Academic credit units |
| instructor | TEXT | yes |  | Instructor name; the original schema has no separate instructor table |
| class_time | TEXT | yes |  | Scheduled teaching time; not proof that a class took place |
| class_location | TEXT | yes |  | Scheduled teaching location |

### registration

- Successful student-course registrations; one row per student and course

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| student_id | TEXT | yes | PK; FK → student.student_id | Student identifier |
| course_id | TEXT | yes | PK; FK → course.course_id | Course identifier; one course offering in this dataset |
| registration_time | TEXT | yes |  | Actual successful course-registration time in UTC |
| status | TEXT | yes |  | Current registration status; REGISTERED in this dataset; no status-change history is stored |

### degree_examination_result

- Degree examination results; repeated examinations use separate result IDs

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| result_id | TEXT | yes | PK | Unique examination-result identifier |
| student_id | TEXT | yes | FK → student.student_id | Student identifier |
| examination_name | TEXT | yes |  | Degree examination name |
| grade | INTEGER | yes |  | Examination score from 0 to 100; 60 is the synthetic eligibility threshold |
| examination_date | TEXT | yes |  | Actual examination time in UTC; not the time its result was published |

## Value domains and business rules

- ELIGIBLE: Student may register after passing the simulated examination
- INELIGIBLE: Student has no passing examination in the simulated history
- REGISTERED: A successful course registration

- Use each student as a case (one timeline).
- An examination-result row records one Degree Examination Taken event at examination_date. The timestamp does not establish when the result was published.
- A registration row records one Course Registered event at registration_time.
- The default student timeline contains recorded examination events and successful registrations.
- Students may retake the examination. In this simulation a score of at least 60 permits subsequent registration. The source does not specify this threshold.
- The student-course composite key allows only one retained registration per pair. Repeated registrations and withdrawals are not added.
- Eligibility and status are current values. Their transitions cannot be reconstructed.
- Birth dates and scheduled class times are not academic process events.
- The requirement mentions notification and information checks, but their execution times are not stored.
- Students with no selected events remain in the separately declared case population.
