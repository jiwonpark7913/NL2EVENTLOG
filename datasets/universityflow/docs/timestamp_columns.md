# Timestamp column inventory

- Timestamp columns count physical table.column pairs storing date-and-time instants. Date-only birth/planning fields and recurring class schedules are excluded. Event timestamp columns are the subset actually selected as event times by the current ES; plans, technical times, snapshots, interval starts and copied key timestamps are listed separately.

| Table | Column | Role | Used as event time | Non-null rows |
|---|---|---|---|---:|
| registration | registration_time | actual event time | Yes | 47 |
| registration | registration_requested_at | actual event time | Yes | 47 |
| registration | registration_approved_at | actual event time | Yes | 47 |
| registration | course_started_at | actual event time | Yes | 47 |
| registration | course_assessment_completed_at | actual event time | Yes | 47 |
| registration | course_grade_finalized_at | actual event time | Yes | 40 |
| degree_examination_result | examination_date | actual event time | Yes | 40 |
| degree_examination_result | examination_scheduled_at | actual event time | Yes | 40 |
| degree_examination_result | examination_checked_in_at | actual event time | Yes | 40 |
| degree_examination_result | examination_score_published_at | actual event time | Yes | 40 |
| degree_examination_result | examination_result_reviewed_at | actual event time | Yes | 34 |
| thesis | submission_date | actual event time | Yes | 16 |
| thesis | thesis_draft_registered_at | actual event time | Yes | 16 |
| thesis | thesis_review_started_at | actual event time | Yes | 16 |
| thesis | thesis_accepted_at | actual event time | Yes | 13 |
| student_simulation_experiment_result | simulation_date | actual event time | Yes | 27 |
| assignment | assignment_assigned_at | actual event time | Yes | 20 |
| assignment | assignment_submitted_at | actual event time | Yes | 16 |
| assignment | assignment_grade_finalized_at | actual event time | Yes | 15 |
| assignment_grading | grading_time | actual event time | Yes | 18 |
| assignment_activity | occurred_at | actual event time | Yes | 21 |
| simulation_module_activity | occurred_at | actual event time | Yes | 11 |
| student_simulation_experiment_result_activity | simulation_date | copied timestamp in parent identity | No | 104 |
| student_simulation_experiment_result_activity | occurred_at | actual event time | Yes | 104 |
| thesis_activity | occurred_at | actual event time | Yes | 12 |
| course_activity | occurred_at | actual event time | Yes | 23 |
| task_activity | occurred_at | actual event time | Yes | 11 |

- Date-only fields excluded: student.date_of_birth, task.task_start_date, task.task_end_date.
- New timestamp questions TS01/TS02/... and their P counterparts explicitly test milestone-column extraction.
