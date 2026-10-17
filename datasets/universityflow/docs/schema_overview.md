# UniversityFlow · combined RSchema examples — Schema overview

![Entity relationship diagram](schema.png)

- [Editable draw.io diagram](schema.drawio) · [Column dictionary](data_dictionary.md) · [CSV dictionary](data_dictionary.csv)

| Table | Rows | Columns | Event encoding | Primary key | Role |
|---|---:|---:|---|---|---|
| student | 40 | 8 | No event encoding | student_id | Unified student information from the three university examples |
| course | 6 | 6 | No event encoding | course_id | Course offerings and planned teaching schedules |
| registration | 47 | 9 | Mixed (row + column) | student_id, course_id | Successful registrations; one retained row per student and course |
| degree_examination_result | 40 | 9 | Mixed (row + column) | result_id | Examination results including retakes |
| task | 3 | 6 | No event encoding | task_id | Course-design task descriptions and scheduled task periods |
| simulation_module | 3 | 5 | No event encoding | module_id | Simulation module descriptions and example code |
| thesis | 16 | 8 | Column encoding | thesis_id | Student theses with actual submission times |
| student_simulation_experiment_result | 27 | 5 | Row encoding | student_id, module_id, simulation_date | Student simulation results with actual experiment-completion times |
| assignment | 20 | 6 | Column encoding | assignment_id | Student assignment content; submission time is not recorded |
| instructor | 3 | 3 | No event encoding | instructor_id | Instructor information from the assignment-management example |
| assignment_grading | 18 | 5 | Row encoding | assignment_id, instructor_id, grading_time | Every recorded grading action, including regrading |
| assignment_activity | 21 | 5 | Row encoding | event_id | Authored actual-action history for assignment |
| simulation_module_activity | 11 | 5 | Row encoding | event_id | Authored actual-action history for simulation_module |
| student_simulation_experiment_result_activity | 104 | 7 | Row encoding | event_id | Authored actual-action history for student_simulation_experiment_result |
| thesis_activity | 12 | 5 | Row encoding | event_id | Authored actual-action history for thesis |
| course_activity | 23 | 5 | Row encoding | event_id | Authored actual-action history for course |
| task_activity | 11 | 5 | Row encoding | event_id | Authored actual-action history for task |
| lifecycle_case_link | 1675 | 3 | No event encoding | event_id, case_table, case_id | Explicit case attribution across typed action histories; auxiliary extraction index, not a business case |

- Row encoding: each occurrence is a separate row; its activity comes from a code, label or the table meaning.
- Column encoding: an object row stores actual milestone times in dedicated columns. It can contain one or several milestones.
- No event encoding: the table supplies context, plans, identities or links rather than direct events.
- Planned dates, snapshots and technical timestamps do not automatically become events.


## Relationships

| Parent | Child | Child FK | Parent key | Parent-to-child count | Kind |
|---|---|---|---|---|---|
| course | registration | course_id | course_id | 1 : 0..N | declared |
| student | registration | student_id | student_id | 1 : 0..N | declared |
| student | degree_examination_result | student_id | student_id | 1 : 0..N | declared |
| student | thesis | student_id | student_id | 1 : 0..N | declared |
| simulation_module | student_simulation_experiment_result | module_id | module_id | 1 : 0..N | declared |
| student | student_simulation_experiment_result | student_id | student_id | 1 : 0..N | declared |
| student | assignment | student_id | student_id | 1 : 0..N | declared |
| instructor | assignment_grading | instructor_id | instructor_id | 1 : 0..N | declared |
| assignment | assignment_grading | assignment_id | assignment_id | 1 : 0..N | declared |
| assignment | assignment_activity | assignment_id | assignment_id | 1 : 0..N | declared |
| simulation_module | simulation_module_activity | module_id | module_id | 1 : 0..N | declared |
| student_simulation_experiment_result | student_simulation_experiment_result_activity | student_id | student_id | 1 : 0..N | declared |
| student_simulation_experiment_result | student_simulation_experiment_result_activity | module_id | module_id | 1 : 0..N | declared |
| student_simulation_experiment_result | student_simulation_experiment_result_activity | simulation_date | simulation_date | 1 : 0..N | declared |
| thesis | thesis_activity | thesis_id | thesis_id | 1 : 0..N | declared |
| course | course_activity | course_id | course_id | 1 : 0..N | declared |
| task | task_activity | task_id | task_id | 1 : 0..N | declared |
