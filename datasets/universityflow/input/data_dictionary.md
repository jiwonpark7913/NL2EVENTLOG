# UniversityFlow English Data Dictionary

## student

- Basic student information and current registration eligibility
- Primary key: student_id

| Column | Type | Meaning |
|---|---|---|
| student_id | TEXT | Student identifier |
| name | TEXT | Student name |
| date_of_birth | TEXT | Birth date; not an academic event |
| phone_number | TEXT | Student contact number |
| home_address | TEXT | Student postal address |
| registration_eligibility | TEXT | Current eligibility: ELIGIBLE or INELIGIBLE; does not store when eligibility changed |

## course

- Course offerings and teaching schedules
- Primary key: course_id

| Column | Type | Meaning |
|---|---|---|
| course_id | TEXT | Course identifier; one course offering in this dataset |
| course_name | TEXT | Course title |
| credits | INTEGER | Academic credit units |
| instructor | TEXT | Instructor name; the original schema has no separate instructor table |
| class_time | TEXT | Scheduled teaching time; not proof that a class took place |
| class_location | TEXT | Scheduled teaching location |

## registration

- Successful student-course registrations; one row per student and course
- Primary key: student_id, course_id
- Foreign key: student_id → student.student_id
- Foreign key: course_id → course.course_id

| Column | Type | Meaning |
|---|---|---|
| student_id | TEXT | Student identifier |
| course_id | TEXT | Course identifier; one course offering in this dataset |
| registration_time | TEXT | Actual successful course-registration time in UTC |
| status | TEXT | Current registration status; REGISTERED in this dataset; no status-change history is stored |

## degree_examination_result

- Degree examination results; repeated examinations use separate result IDs
- Primary key: result_id
- Foreign key: student_id → student.student_id

| Column | Type | Meaning |
|---|---|---|
| result_id | TEXT | Unique examination-result identifier |
| student_id | TEXT | Student identifier |
| examination_name | TEXT | Degree examination name |
| grade | INTEGER | Examination score from 0 to 100; 60 is the synthetic eligibility threshold |
| examination_date | TEXT | Actual examination time in UTC; not the time its result was published |

## Business rules

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
