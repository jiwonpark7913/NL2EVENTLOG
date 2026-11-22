# universityflow — Question definitions and Gold review

[Interactive question / DFG / source-row review](../review/gold_dfg/index.html)

Q1: explicit; Q2: explicit paraphrase; Q3: lifecycle; Q4: lifecycle paraphrase. Pairs retain the same scope and Gold log. Revised requests and paraphrases are author edits following the 2026-11-20 audit.

| ID | Type | Pair | Case | Process focus | Answerability | Supported activities | Observed activities | Events | Question |
|---|---|---|---|---|---|---:|---:|---:|---|
| U01 | Q1 |  | Student |  | answerable | 1 | 1 | 40 | Extract Degree Examination Taken events for each student. |
| U02 | Q2 | U01 | Student |  | answerable | 1 | 1 | 40 | For each student, build a timeline of the student sitting the degree examination. |
| U03 | Q1 |  | Student |  | answerable | 1 | 1 | 47 | Extract Course Registered events for each student. |
| U04 | Q2 | U03 | Student |  | answerable | 1 | 1 | 47 | For each student, build a timeline of a successful course sign-up. |
| U05 | Q3 |  | Student |  | answerable | 29 | 29 | 763 | Extract the full recorded lifecycle event log for each student. |
| U06 | Q4 | U05 | Student |  | answerable | 29 | 29 | 763 | Show the complete recorded history associated with each student. |
| U07 | Q1 |  | Student |  | unsupported | 1 | 0 | 0 | Extract Registration Success Notification Sent events for each student. |
| U08 | Q1 |  | Student |  | unsupported | 1 | 0 | 0 | Extract Course Withdrawn events for each student. |
| U09 | Q1 |  | Student |  | answerable | 1 | 1 | 18 | Extract Assignment Graded events for each student. |
| U10 | Q2 | U09 | Student |  | answerable | 1 | 1 | 18 | For each student, build a timeline of an instructor assessing the assignment. |
| U11 | Q1 |  | Student |  | answerable | 1 | 1 | 27 | Extract Simulation Experiment Completed events for each student. |
| U12 | Q2 | U11 | Student |  | answerable | 1 | 1 | 27 | For each student, build a timeline of a simulation run finishing. |
| U13 | Q1 |  | Student |  | answerable | 1 | 1 | 16 | Extract Thesis Submitted events for each student. |
| U14 | Q2 | U13 | Student |  | answerable | 1 | 1 | 16 | For each student, build a timeline of the student handing in a thesis. |
| U15 | Q1 |  | Student |  | answerable | 1 | 1 | 16 | Extract Assignment Submitted events for each student. |
| OU01 | Q3 |  | Student |  | answerable | 29 | 29 | 763 | Extract the full recorded lifecycle event log for each student. |
| OU02 | Q3 |  | Course |  | answerable | 10 | 10 | 298 | Extract the full recorded lifecycle event log for each course. |
| OU03 | Q3 |  | Student-course registration |  | answerable | 6 | 6 | 275 | Extract the full recorded lifecycle event log for each student-course registration. |
| OU04 | Q3 |  | Examination result record |  | answerable | 5 | 5 | 194 | Extract the full recorded lifecycle event log for each examination result record. |
| OU05 | Q3 |  | Simulation module |  | answerable | 9 | 9 | 142 | Extract the full recorded lifecycle event log for each simulation module. |
| OU06 | Q3 |  | Thesis |  | answerable | 6 | 6 | 73 | Extract the full recorded lifecycle event log for each thesis. |
| OU07 | Q3 |  | Simulation experiment result record |  | answerable | 5 | 5 | 131 | Extract the full recorded lifecycle event log for each simulation experiment result record. |
| OU08 | Q3 |  | Assignment |  | answerable | 7 | 7 | 90 | Extract the full recorded lifecycle event log for each assignment. |
| OU09 | Q3 |  | Instructor |  | answerable | 7 | 7 | 86 | Extract the full recorded lifecycle event log for each instructor. |
| OU10 | Q3 |  | Instructor | assignment assessment | answerable | 2 | 2 | 25 | Extract the full recorded grading and regrading history for each instructor. |
| OU11 | Q3 |  | Course-design task |  | answerable | 4 | 4 | 11 | Extract the full recorded lifecycle event log for each course-design task. |
| TS01 | Q1 |  | Student |  | answerable | 4 | 4 | 154 | Extract Examination Scheduled, Examination Checked In, Examination Score Published, Examination Result Reviewed events for each student. |
| TS02 | Q1 |  | Student-course registration |  | answerable | 5 | 5 | 228 | Extract Registration Requested, Registration Approved, Course Started, Course Assessment Completed, Course Grade Finalized events for each student-course registration. |
| TS03 | Q1 |  | Assignment |  | answerable | 3 | 3 | 51 | Extract Assignment Assigned, Assignment Submitted, Assignment Grade Finalized events for each assignment. |
| TS04 | Q1 |  | Thesis |  | answerable | 3 | 3 | 45 | Extract Thesis Draft Registered, Thesis Review Started, Thesis Accepted events for each thesis. |
| U07P | Q2 | U07 | Student |  | unsupported | 1 | 0 | 0 | For each student, build a timeline of confirmation messages being sent after a course sign-up. |
| U08P | Q2 | U08 | Student |  | unsupported | 1 | 0 | 0 | For each student, build a timeline of the student leaving a course after signing up. |
| U15P | Q2 | U15 | Student |  | answerable | 1 | 1 | 16 | For each student, build a timeline of the student handing in coursework. |
| TS01P | Q2 | TS01 | Student |  | answerable | 4 | 4 | 154 | For each student, build a timeline of an examination sitting being arranged, the candidate checking in for the examination, the examination mark being released, the examination result being reviewed. |
| TS02P | Q2 | TS02 | Student-course registration |  | answerable | 5 | 5 | 228 | For each student-course registration, build a timeline of the student requesting a place on a course, the request for a course place being accepted, teaching beginning for the enrolled course, the course assessment finishing, the course mark being made final. |
| TS03P | Q2 | TS03 | Assignment |  | answerable | 3 | 3 | 51 | For each assignment, build a timeline of coursework being set for the student, the student handing in coursework, the coursework mark being made final. |
| TS04P | Q2 | TS04 | Thesis |  | answerable | 3 | 3 | 45 | For each thesis, build a timeline of a thesis draft being registered for review, the review of a thesis beginning, a thesis receiving final approval. |
| OU01P | Q4 | OU01 | Student |  | answerable | 29 | 29 | 763 | Show the complete recorded history associated with each student. |
| OU01E | Q1 |  | Student |  | answerable | 3 | 3 | 54 | Extract Assignment Assigned, Assignment Submitted, Assignment Graded events for each student. |
| OU01EP | Q2 | OU01E | Student |  | answerable | 3 | 3 | 54 | For each student, build a timeline of coursework being set for the student, the student handing in coursework, an instructor assessing the assignment. |
| OU02P | Q4 | OU02 | Course |  | answerable | 10 | 10 | 298 | Show the complete recorded history associated with each course. |
| OU02E | Q1 |  | Course |  | answerable | 3 | 3 | 134 | Extract Registration Requested, Course Registered, Course Grade Finalized events for each course. |
| OU02EP | Q2 | OU02E | Course |  | answerable | 3 | 3 | 134 | For each course, build a timeline of the student requesting a place on a course, a successful course sign-up, the course mark being made final. |
| OU03P | Q4 | OU03 | Student-course registration |  | answerable | 6 | 6 | 275 | Show the complete recorded history associated with each student-course registration. |
| OU03E | Q1 |  | Student-course registration |  | answerable | 3 | 3 | 134 | Extract Registration Requested, Course Registered, Course Grade Finalized events for each student-course registration. |
| OU03EP | Q2 | OU03E | Student-course registration |  | answerable | 3 | 3 | 134 | For each student-course registration, build a timeline of the student requesting a place on a course, a successful course sign-up, the course mark being made final. |
| OU04P | Q4 | OU04 | Examination result record |  | answerable | 5 | 5 | 194 | Show the complete recorded history associated with each examination result record. |
| OU04E | Q1 |  | Examination result record |  | answerable | 3 | 3 | 120 | Extract Examination Scheduled, Degree Examination Taken, Examination Score Published events for each examination result record. |
| OU04EP | Q2 | OU04E | Examination result record |  | answerable | 3 | 3 | 120 | For each examination result record, build a timeline of an examination sitting being arranged, the student sitting the degree examination, the examination mark being released. |
| OU05P | Q4 | OU05 | Simulation module |  | answerable | 9 | 9 | 142 | Show the complete recorded history associated with each simulation module. |
| OU05E | Q1 |  | Simulation module |  | answerable | 3 | 3 | 77 | Extract Simulation Run Started, Simulation Experiment Completed, Simulation Result Accepted events for each simulation module. |
| OU05EP | Q2 | OU05E | Simulation module |  | answerable | 3 | 3 | 77 | For each simulation module, build a timeline of a simulation run beginning, a simulation run finishing, the simulation results receiving approval. |
| OU06P | Q4 | OU06 | Thesis |  | answerable | 6 | 6 | 73 | Show the complete recorded history associated with each thesis. |
| OU06E | Q1 |  | Thesis |  | answerable | 3 | 3 | 45 | Extract Thesis Submitted, Thesis Review Started, Thesis Accepted events for each thesis. |
| OU06EP | Q2 | OU06E | Thesis |  | answerable | 3 | 3 | 45 | For each thesis, build a timeline of the student handing in a thesis, the review of a thesis beginning, a thesis receiving final approval. |
| OU07P | Q4 | OU07 | Simulation experiment result record |  | answerable | 5 | 5 | 131 | Show the complete recorded history associated with each simulation experiment result record. |
| OU07E | Q1 |  | Simulation experiment result record |  | answerable | 3 | 3 | 77 | Extract Simulation Run Started, Simulation Experiment Completed, Simulation Result Accepted events for each simulation experiment result record. |
| OU07EP | Q2 | OU07E | Simulation experiment result record |  | answerable | 3 | 3 | 77 | For each simulation experiment result record, build a timeline of a simulation run beginning, a simulation run finishing, the simulation results receiving approval. |
| OU08P | Q4 | OU08 | Assignment |  | answerable | 7 | 7 | 90 | Show the complete recorded history associated with each assignment. |
| OU08E | Q1 |  | Assignment |  | answerable | 3 | 3 | 54 | Extract Assignment Assigned, Assignment Submitted, Assignment Graded events for each assignment. |
| OU08EP | Q2 | OU08E | Assignment |  | answerable | 3 | 3 | 54 | For each assignment, build a timeline of coursework being set for the student, the student handing in coursework, an instructor assessing the assignment. |
| OU09P | Q4 | OU09 | Instructor |  | answerable | 7 | 7 | 86 | Show the complete recorded history associated with each instructor. |
| OU09E | Q1 |  | Instructor |  | answerable | 3 | 3 | 50 | Extract Assignment Assigned, Assignment Submitted, Assignment Graded events for each instructor. |
| OU09EP | Q2 | OU09E | Instructor |  | answerable | 3 | 3 | 50 | For each instructor, build a timeline of coursework being set for the student, the student handing in coursework, an instructor assessing the assignment. |
| OU10P | Q4 | OU10 | Instructor | assignment assessment | answerable | 2 | 2 | 25 | For every instructor, reconstruct the entire recorded history of their initial assignment assessments and reassessments. |
| OU10E | Q1 |  | Assignment grading record |  | answerable | 1 | 1 | 18 | Extract Assignment Graded events for each assignment grading record. |
| OU10EP | Q2 | OU10E | Assignment grading record |  | answerable | 1 | 1 | 18 | For each assignment grading record, build a timeline of an instructor assessing the assignment. |
| OU11P | Q4 | OU11 | Course-design task |  | answerable | 4 | 4 | 11 | Show the complete recorded history associated with each course-design task. |
| OU11E | Q1 |  | Course-design task |  | answerable | 3 | 3 | 8 | Extract Design Task Approved, Design Task Closed, Design Task Created events for each course-design task. |
| OU11EP | Q2 | OU11E | Course-design task |  | answerable | 3 | 3 | 8 | For each course-design task, build a timeline of a design exercise receiving approval, a design exercise being closed, a design exercise being prepared. |
