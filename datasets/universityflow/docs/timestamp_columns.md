# Timestamp column inventory

- Timestamp columns count physical table.column pairs storing date-and-time instants. Date-only birth/planning fields and recurring class schedules are excluded. Event timestamp columns are the subset actually selected as event times by the current ES; plans, technical times, snapshots, interval starts and copied key timestamps are listed separately.

| Table | Column | Role | Used as event time | Non-null rows |
|---|---|---|---|---:|
| course | course_offering_proposed_at | actual event time | Yes | 6 |
| course | course_offering_approved_at | actual event time | Yes | 6 |
| course | course_offering_published_at | actual event time | Yes | 6 |
| course | course_offering_closed_at | actual event time | Yes | 5 |
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
| task | design_task_created_at | actual event time | Yes | 3 |
| task | design_task_approved_at | actual event time | Yes | 3 |
| task | design_task_published_at | actual event time | Yes | 3 |
| task | design_task_closed_at | actual event time | Yes | 2 |
| simulation_module | simulation_module_published_at | actual event time | Yes | 3 |
| simulation_module | simulation_module_validated_at | actual event time | Yes | 3 |
| simulation_module | simulation_module_released_at | actual event time | Yes | 3 |
| simulation_module | simulation_module_retired_at | actual event time | Yes | 2 |
| thesis | submission_date | actual event time | Yes | 16 |
| thesis | thesis_draft_registered_at | actual event time | Yes | 16 |
| thesis | thesis_review_started_at | actual event time | Yes | 16 |
| thesis | thesis_accepted_at | actual event time | Yes | 13 |
| thesis | thesis_revision_requested_at | actual event time | Yes | 6 |
| thesis | thesis_resubmitted_at | actual event time | Yes | 6 |
| student_simulation_experiment_result | simulation_date | actual event time | Yes | 27 |
| student_simulation_experiment_result | simulation_run_scheduled_at | actual event time | Yes | 27 |
| student_simulation_experiment_result | simulation_run_started_at | actual event time | Yes | 27 |
| student_simulation_experiment_result | simulation_output_reviewed_at | actual event time | Yes | 27 |
| student_simulation_experiment_result | simulation_result_accepted_at | actual event time | Yes | 23 |
| assignment | assignment_assigned_at | actual event time | Yes | 20 |
| assignment | assignment_submitted_at | actual event time | Yes | 16 |
| assignment | assignment_grade_finalized_at | actual event time | Yes | 15 |
| assignment | assignment_revision_requested_at | actual event time | Yes | 7 |
| assignment | assignment_resubmitted_at | actual event time | Yes | 7 |
| assignment_grading | grading_time | actual event time | Yes | 25 |

- Date-only fields excluded: student.date_of_birth, task.task_start_date, task.task_end_date.
- New timestamp questions TS01/TS02/... and their P counterparts explicitly test milestone-column extraction.
