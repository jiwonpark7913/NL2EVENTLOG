# UniversityFlow · RSchema — Schema overview

![Entity relationship diagram](schema.png)

- [Editable draw.io diagram](schema.drawio) · [Column dictionary](data_dictionary.md) · [CSV dictionary](data_dictionary.csv)

| Table | Rows | Columns | Primary key | Role |
|---|---:|---:|---|---|
| student | 40 | 6 | student_id | Basic student information and current registration eligibility |
| course | 6 | 6 | course_id | Course offerings and teaching schedules |
| registration | 47 | 4 | student_id, course_id | Successful student-course registrations; one row per student and course |
| degree_examination_result | 40 | 5 | result_id | Degree examination results; repeated examinations use separate result IDs |


## Relationships

| Parent | Child | Child FK | Parent key | Parent-to-child count | Kind |
|---|---|---|---|---|---|
| course | registration | course_id | course_id | 1 : 0..N | declared |
| student | registration | student_id | student_id | 1 : 0..N | declared |
| student | degree_examination_result | student_id | student_id | 1 : 0..N | declared |
