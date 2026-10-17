# UniversityFlow

- **Situation:** Students take examinations, request course registration, complete course assessment, submit assignments and simulation results, and revise theses. Courses, instructors and modules aggregate their explicitly linked actions.
- **Source:** Three preserved RSchema university requirements and logical schemas. Original source columns and keys are preserved.
- **Extension:** Milestone columns, retained action histories and cross-object attribution rules are authored synthetic domain design. They are not copied from the source or observed production data.
- **Database:** 18 tables; 11 object / case types; 41 activity types; 27 timestamp columns (26 event timestamp columns); 808 distinct events.
- **Gold:** 58 answerable question-specific CSV logs out of 62 questions. Paired requests share the same expected content.
- **Execution:** Run `python datasets/universityflow/build.py` from the repository root, then `python make_docs.py`. Only the Python standard library is needed for DB/log generation; diagrams use PyMuPDF.

## Dataset counts

| Dataset | Tables | Object / case types | Activity types | Timestamp columns | Event timestamp columns | Distinct events | Questions | Gold CSVs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| UniversityFlow | 18 | 11 | 41 | 27 | 26 | 808 | 70 | 66 |

- **Activity types:** distinct business labels across all recorded events in this database, counted once even when shared by several objects.
- **Object / case types:** distinct keyed tables with an answerable object-specific event log, including auxiliary event/association-record cases. This is a type count, not a count of individual object instances.
- Activity-history tables, the case-link index and code reference tables do not add object types.
- Individual cases may contain fewer activities because of incomplete work or conditional branches.

## Objects, activities and situations

| Object / case | Activity types across all cases | Situation / scope | Gold CSV |
|---|---|---|---|
| student | Assignment Assigned; Assignment Grade Finalized; Assignment Graded; Assignment Regraded; Assignment Resubmitted; Assignment Revision Requested; Assignment Submitted; Course Assessment Completed; Course Grade Finalized; Course Registered; Course Started; Degree Examination Taken; Examination Checked In; Examination Result Reviewed; Examination Scheduled; Examination Score Published; Registration Approved; Registration Requested; Simulation Experiment Completed; Simulation Output Reviewed; Simulation Result Accepted; Simulation Run Scheduled; Simulation Run Started; Thesis Accepted; Thesis Draft Registered; Thesis Resubmitted; Thesis Review Started; Thesis Revision Requested; Thesis Submitted | Original recorded actions and authored lifecycle actions explicitly linked to this student. | [CSV](private/gold_logs/OU01.csv) |
| course | Course Assessment Completed; Course Grade Finalized; Course Offering Approved; Course Offering Closed; Course Offering Proposed; Course Offering Published; Course Registered; Course Started; Registration Approved; Registration Requested | Original recorded actions and authored lifecycle actions explicitly linked to this course. | [CSV](private/gold_logs/OU02.csv) |
| registration | Course Assessment Completed; Course Grade Finalized; Course Registered; Course Started; Registration Approved; Registration Requested | Original recorded actions and authored lifecycle actions explicitly linked to this student-course registration. | [CSV](private/gold_logs/OU03.csv) |
| degree_examination_result | Degree Examination Taken; Examination Checked In; Examination Result Reviewed; Examination Scheduled; Examination Score Published | Original recorded actions and authored lifecycle actions explicitly linked to this examination result record. | [CSV](private/gold_logs/OU04.csv) |
| simulation_module | Simulation Experiment Completed; Simulation Module Published; Simulation Module Released; Simulation Module Retired; Simulation Module Validated; Simulation Output Reviewed; Simulation Result Accepted; Simulation Run Scheduled; Simulation Run Started | Original recorded actions and authored lifecycle actions explicitly linked to this simulation module. | [CSV](private/gold_logs/OU05.csv) |
| thesis | Thesis Accepted; Thesis Draft Registered; Thesis Resubmitted; Thesis Review Started; Thesis Revision Requested; Thesis Submitted | Original recorded actions and authored lifecycle actions explicitly linked to this thesis. | [CSV](private/gold_logs/OU06.csv) |
| student_simulation_experiment_result | Simulation Experiment Completed; Simulation Output Reviewed; Simulation Result Accepted; Simulation Run Scheduled; Simulation Run Started | Original recorded actions and authored lifecycle actions explicitly linked to this simulation experiment result record. | [CSV](private/gold_logs/OU07.csv) |
| assignment | Assignment Assigned; Assignment Grade Finalized; Assignment Graded; Assignment Regraded; Assignment Resubmitted; Assignment Revision Requested; Assignment Submitted | Original recorded actions and authored lifecycle actions explicitly linked to this assignment. | [CSV](private/gold_logs/OU08.csv) |
| instructor | Assignment Assigned; Assignment Grade Finalized; Assignment Graded; Assignment Regraded; Assignment Resubmitted; Assignment Revision Requested; Assignment Submitted | Original recorded actions and authored lifecycle actions explicitly linked to this instructor. | [CSV](private/gold_logs/OU09.csv) |
| assignment_grading | Assignment Graded | The single grading action represented by the assignment-instructor-time key. | [CSV](private/gold_logs/OU10.csv) |
| task | Design Task Approved; Design Task Closed; Design Task Created; Design Task Published | Actual creation, publication and closure of this design task; these are authored task-management actions, not inferred student executions. | [CSV](private/gold_logs/OU11.csv) |

- Atomic grading and operation records are auxiliary cases; a single occurrence is not expanded into an invented lifecycle.
- Master cases can aggregate unrelated jobs. Multiple activity types do not imply one causal process across all rows.
- Conditional revision branches and incomplete histories are intentional. Repeated activity occurrences keep distinct event IDs.
- Actual activity times are separate from plans, schedules and technical creation/update times.
- Case population includes objects with no selected events; those cases have no CSV rows.
- These are case-based CSV logs, not OCEL.

## Database, extraction and validation

- One-time events use named actual-time columns on the existing business record. Retained `<object>_activity` tables store the remaining row-encoded actions; migrated events are removed from those rows.
- `lifecycle_case_link` is an explicitly validated auxiliary index relating a recorded event to each permitted case. It is not a business object.
- Full ES queries union original milestone sources and new action histories. Object-specific ES queries apply explicit case links and sort by case, time and event ID.
- Gold logs are generated from simulated history and compared against executable SQL on the populated DB. This checks internal consistency, not model accuracy.
- [Detailed activity design](docs/object_activity_design.md)
- [Event-log case scopes and counts](docs/object_event_logs.md)
- [Data dictionary](docs/data_dictionary.md)
- [Schema overview](docs/schema_overview.md)
- [Editable draw.io](docs/schema.drawio)
- [Validation report](validation_report.json)

![Schema](docs/schema.png)

## Question types and pairs

- **Q1 Explicit:** case concept and exact activities.
- **Q2 Paraphrased:** alternate wording of Q1, with identical Gold scope.
- **Q3 Full Lifecycle:** case concept only, using the declared default recorded scope.
- **Q4 Full Lifecycle Paraphrased:** alternate wording of Q3, with identical Gold scope.
- `question_type`, `question_type_name`, `pair_of` and `answerability` are included in every question and Gold answer.
- Type and answerability are separate: unavailable actions remain unsupported; empty observed logs are not automatically unsupported.

| Type | Questions | Answerable | Non-answerable | Avg. requested activity types |
|---|---:|---:|---:|---:|
| Q1 | 23 | 21 | 2 | 2.35 |
| Q2 | 23 | 21 | 2 | 2.35 |
| Q3 | 12 | 12 | 0 | 9.83 |
| Q4 | 12 | 12 | 0 | 9.83 |

- Avg. requested activity types = sum of requested activity-type counts / all questions in that row, including non-answerable questions. Q3/Q4 counts use the Gold catalog scope. This counts distinct activity types, not event occurrences.

- [All question texts, types, pairs and answerability](docs/questions.md)

## Event encoding and data definitions

- [Table-by-table row/column encoding](docs/schema_overview.md)
- [Three-part data dictionary: basic information, table definitions, column definitions](docs/data_dictionary.md)
- [Table definitions CSV](docs/table_definitions.csv)
- Process View includes the case concept and activity scope. Q1/Q2 state the scope explicitly; Q3/Q4 infer it from the declared catalog.
- [Question activity counts and pairs](docs/questions.md): requested and extractable activity counts are shown separately.

## Schema and documentation

- [Table inventory and relationships](docs/schema_overview.md)
- [English column dictionary](docs/data_dictionary.md)
- [CSV dictionary](docs/data_dictionary.csv)
- [Editable draw.io diagram](docs/schema.drawio)
- [Object-based Gold logs and coverage](docs/object_event_logs.md)

## Timestamp columns

- Timestamp columns count physical table.column pairs storing date-and-time instants. Date-only birth/planning fields and recurring class schedules are excluded. Event timestamp columns are the subset actually selected as event times by the current ES; plans, technical times, snapshots, interval starts and copied key timestamps are listed separately.
- [Timestamp inventory and roles](docs/timestamp_columns.md)
- [Milestone-column extraction questions and Gold activity counts](docs/questions.md)
- Single-occurrence milestone times are stored on the existing business record. Repeated actions remain row encoded; the same event is not stored twice.
