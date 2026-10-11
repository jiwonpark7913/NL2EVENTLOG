# UniversityFlow — university course registration

- This English-language synthetic dataset uses an actual SchemaAgent/RSchema requirement and relational schema.
- The scenario follows students taking degree examinations and registering for courses.
- All four source tables, 21 columns, primary keys and three foreign-key relationships are retained.
- The dataset adds no tables or columns.
- The source record is `67552f0b13602ec03b41aaec`, line 260 of `datasets/RSchema/annotation.jsonl`.
- Source repository: [hnuGraph/LLM4DBdesign](https://github.com/hnuGraph/LLM4DBdesign), commit `5eda099db3d9b768e5b532b5abc9f8fe117be85f`.

## Tables and simulated records

| Table | Rows | What it records |
|---|---:|---|
| student | 40 | Student details and current registration eligibility |
| course | 6 | Course titles, credits, instructors and planned teaching schedules |
| registration | 47 | Successful course registrations and actual registration times |
| degree_examination_result | 40 | Examination scores and actual examination times, including retakes |

- There are 87 business events: 40 examinations and 47 successful registrations.
- There are 10 students in each scenario: no examination, failed examination, passed after a retake, and passed on the first attempt.
- The 10 students with no examination or registration are valid cases with empty timelines.
- Student ID defines the case: each student's selected events form one timeline.
- A course schedule does not prove that a class occurred; it is excluded from actual event logs.

## What comes from the source

- The original requirement and schema are preserved in `source/rschema_original.json`.
- The registration key is the pair `(student_id, course_id)`.
- That key does not retain multiple registrations for the same student and course; this dataset keeps the original restriction.
- Examination results use a separate result ID, allowing retakes to remain separate records.
- The requirement mentions successful-registration notifications, but the schema has no notification table or timestamp.
- The conceptual model is documented locally from the original logical schema.

## Assumptions added for simulation

- SQL data types, required values and checks are specified for SQLite.
- Actual times use UTC.
- An examination score of at least 60 makes a student eligible to register in the simulated process.
- The passing score and eligibility codes are authored assumptions; they are not specified by RSchema.
- `examination_date` means when the examination was taken, not when the score was published.
- Student eligibility and registration status are current values; their change histories cannot be reconstructed.

## Questions and expected results

- Eight English questions are supplied.
- U01/U02 select examinations, U03/U04 select registrations, and U05/U06 select the full recorded student timeline.
- Each pair tests the same request with direct wording and a paraphrase.
- U07 asks for notification events, whose times are absent from the source schema.
- U08 asks for withdrawals, whose times and status history are absent.
- All six answerable questions produce SQL results identical to their expected logs.
- SQL uses separate event sources combined with `UNION ALL`.
- Joining examinations directly to registrations by student would pair unrelated rows and lose students with only examinations.

## Rebuild and evaluation

- Run `python build.py` with Python 3.10 or later; no external package is needed.
- Rebuilding replaces generated DB and expected-result files.
- Provide only `input/` to the model.
- The input includes a task scope catalog: a list of allowed business activities and the default scope for a full-timeline request.
- Keep the builder, source annotation, design files, expected answers in `private/`, and validation report outside the model's context.
- Event logs are ordinary CSV timelines; they are not OCEL files.
- Exact SQL agreement checks dataset consistency; model accuracy has not been measured.
- The extraction specification uses a dataset-specific format; compatibility with the existing NL2EventLog implementation has not been tested.

## Schema and documentation

![Schema](docs/schema.png)

- [Table inventory and relationships](docs/schema_overview.md)
- [English column dictionary](docs/data_dictionary.md)
- [CSV dictionary](docs/data_dictionary.csv)
- [Editable draw.io diagram](docs/schema.drawio)
- [SVG diagram](docs/schema.svg)
