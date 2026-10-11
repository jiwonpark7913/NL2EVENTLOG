# UniversityFlow — student academic activities

- This English-language synthetic dataset combines three actual SchemaAgent/RSchema university examples.
- The examples cover course registration, course design with experiments and theses, and online assignment grading.
- Shared Student IDs connect the three examples into one student timeline.
- This integration is authored for the benchmark; RSchema does not provide these examples as one integrated database.
- The combined database has **11 tables, 55 columns, 40 students, 148 events and 26 questions**.

## Recorded activities

| Activity | Events | Source table and time | Link to student |
|---|---:|---|---|
| Degree Examination Taken | 40 | degree_examination_result.examination_date | Direct student_id |
| Course Registered | 47 | registration.registration_time | Direct student_id |
| Assignment Graded | 18 | assignment_grading.grading_time | assignment_grading → assignment → student |
| Simulation Experiment Completed | 27 | student_simulation_experiment_result.simulation_date | Direct student_id |
| Thesis Submitted | 16 | thesis.submission_date | Direct student_id |

- Repeated examination attempts, simulation runs and grading actions remain separate events.
- Two grading events are regrading; seven simulation events are repeat runs.
- Some students have only examinations; some assignments remain ungraded and some students have not submitted a thesis.
- Ten students have no recorded events and remain valid cases with empty timelines.
- A student's complete timeline includes all five activity types linked to that student.
- Grouping events into a student timeline does not assert that every action belongs to the same course or one causal chain.

## Tables and source roles

| Table | Rows | What it records |
|---|---:|---|
| student | 40 | Shared student information, eligibility, class and major |
| course | 6 | Course offerings and planned teaching schedules |
| registration | 47 | Successful course registrations |
| degree_examination_result | 40 | Examination results and examination times |
| task | 3 | Course-design task descriptions and scheduled periods |
| simulation_module | 3 | Simulation methods and example code |
| thesis | 16 | Thesis content and actual submission times |
| student_simulation_experiment_result | 27 | Experiment results and actual completion times |
| assignment | 20 | Student assignment content, with no submission timestamp |
| instructor | 3 | Assignment instructor information and course labels |
| assignment_grading | 18 | Scores, feedback and actual grading times |

## The three original examples

| Source example | Record ID | Source line | Tables before merging |
|---|---|---:|---:|
| Course registration | 67552f0b13602ec03b41aaec | 260 | 4 |
| Course design, simulations and theses | 67552f0b13602ec03b41aa43 | 437 | 5 |
| Online assignment management | 67552f0b13602ec03b41ab04 | 474 | 4 |

- Source repository: [hnuGraph/LLM4DBdesign](https://github.com/hnuGraph/LLM4DBdesign).
- Source file: `datasets/RSchema/annotation.jsonl`, commit `5eda099db3d9b768e5b532b5abc9f8fe117be85f`.
- `source/rschema_originals.json` preserves all three original requirements and schemas.
- `source/rschema_original.json` retains the initial course-registration example for reference.
- `design/source_mapping.json` maps every source table, column and key to the combined schema.
- The three Student definitions are merged by Student ID; repeated Name and Class fields are unified.
- The 13 source table definitions become 11 combined tables, and 60 attribute definitions become 55 distinct columns.
- All original table roles, attributes, primary keys and nine distinct foreign-key relationships are retained.
- No new table, column or foreign key is added.
- The conceptual model is derived locally from the combined logical schemas.

## Added assumptions and source gaps

- Shared Student IDs across the three independent examples are an integration assumption.
- SQLite types, required values and checks are added for execution.
- Actual event times use UTC.
- A score of at least 60 permits registration in the simulation; this threshold is not specified by RSchema.
- `examination_date` represents taking the examination, not publishing its score.
- `simulation_date` is interpreted as actual experiment completion; this interpretation is explicitly added.
- `submission_date` records thesis submission and must not be confused with assignment submission.
- Planned task start/end dates and class schedules do not establish actual student actions.
- Task records have no source link to students or experiments; missing links are not invented.
- `course.instructor` and `instructor.course` remain source text fields with no inferred FK between those tables.
- Student eligibility and registration status are current values without change histories.

## Questions and expected results

- U01/U02 select examinations; U03/U04 select registrations.
- U05/U06 select the full academic timeline across all five activities.
- U09/U10 select grading; U11/U12 select simulation experiments; U13/U14 select thesis submissions.
- Each pair tests direct wording and a paraphrase of the same requested scope.
- U07 asks for notifications, U08 for withdrawals, and U15 for assignment submissions.
- These three questions are unsupported because their event times are absent.
- Stored assignment content proves that a record exists but does not supply the submission time; grading time cannot substitute for it.
- The 12 original answerable questions and 10 added object/record-view questions produce SQL results identical to expected logs selected from simulated business history.
- Grading extraction uses the declared assignment-to-student join, and event sources are combined with `UNION ALL`.
- Current extraction specifications use a dataset-specific format; compatibility with the existing NL2EventLog implementation remains untested.

## Additional case choices

- Object-view questions OU01–OU10 cover students, courses, registrations, examination results, simulation modules, theses, experiment results, assignments, instructors and grading records.
- OU11 asks for actual task execution and is unsupported: task periods are schedules, and the source has no timestamped task execution or assignment link.
- Course timelines include registrations, assignment timelines include grading, and instructor timelines include the grading they performed.
- These scopes do not infer joins from course-name strings or copy every student event into every course.
- The original full student-timeline scope is retained.

## Rebuild and evaluation

- Run `python build.py` with Python 3.10 or later; no external package is needed.
- Rebuilding replaces generated DB and expected-result files.
- Provide only `input/` to the model.
- The task scope catalog supplies business activity labels and the default full-timeline rule.
- Keep generation code, source answers, design files, expected answers in `private/`, and validation reports outside the model's context.
- Event logs are ordinary CSV timelines, not OCEL files.
- Validation checks source mappings, declared keys, record integrity, eligibility, simulated action order, repeated-event identities and exact SQL/log agreement.
- These checks establish internal dataset consistency; model accuracy has not been measured.

## Schema and documentation

![Schema](docs/schema.png)

- [Table inventory and relationships](docs/schema_overview.md)
- [English column dictionary](docs/data_dictionary.md)
- [CSV dictionary](docs/data_dictionary.csv)
- [Editable draw.io diagram](docs/schema.drawio)
- [Object-based Gold logs and coverage](docs/object_event_logs.md)
