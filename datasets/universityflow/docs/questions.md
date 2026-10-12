# Question types and paired requests

- Q1 and Q2 specify a case concept and activities. Q2 uses alternate wording for the exact same scope.
- Q3 and Q4 specify a case concept without listing activities. Their Gold scope uses the declared task catalog.
- Every Q2 is paired with Q1; every Q4 is paired with Q3. Pairs have identical ES, Gold CSV and answerability.
- Answerability is independent of type. Existing unavailable actions remain unavailable and receive Q2 pairs. No evidence is fabricated.
- `answerability` is an evaluation annotation: exclude it from model inputs. `question_type` defines the taxonomy; legacy `category` records question origin.
- These are authored English paraphrases; there is no claim of model-generated linguistic diversity.
- Existing IDs are preserved. Added E/EP IDs select explicit activity subsets; added P IDs are paired paraphrases.

| Type | Included information | Answerability | Meaning |
|---|---|---|---|
| Q1 Explicit | Process View + Activities | O / X | Case concept and exact business activity labels |
| Q2 Paraphrased | Process View + Activities | O / X | Same scope as Q1, expressed with alternate business wording |
| Q3 Full Lifecycle | Process View | O / X | Case concept only; default recorded scope from catalog |
| Q4 Full Lifecycle Paraphrased | Process View | O / X | Alternate wording of Q3 with identical default scope |

| ID | Type | Paired with | Answerability | Question |
|---|---|---|---|---|
| U01 | Q1 Explicit | — | O | Extract Degree Examination Taken events for each student. |
| U02 | Q2 Paraphrased | U01 | O | For each student, build a timeline of the student sitting the degree examination. |
| U03 | Q1 Explicit | — | O | Extract Course Registered events for each student. |
| U04 | Q2 Paraphrased | U03 | O | For each student, build a timeline of a successful course sign-up. |
| U05 | Q3 Full Lifecycle | — | O | Extract the full recorded lifecycle event log for each student. |
| U06 | Q4 Full Lifecycle Paraphrased | U05 | O | Show the complete recorded history associated with each student. |
| U07 | Q1 Explicit | — | X | Extract Registration Success Notification Sent events for each student. |
| U08 | Q1 Explicit | — | X | Extract Course Withdrawn events for each student. |
| U09 | Q1 Explicit | — | O | Extract Assignment Graded events for each student. |
| U10 | Q2 Paraphrased | U09 | O | For each student, build a timeline of an instructor assessing the assignment. |
| U11 | Q1 Explicit | — | O | Extract Simulation Experiment Completed events for each student. |
| U12 | Q2 Paraphrased | U11 | O | For each student, build a timeline of a simulation run finishing. |
| U13 | Q1 Explicit | — | O | Extract Thesis Submitted events for each student. |
| U14 | Q2 Paraphrased | U13 | O | For each student, build a timeline of the student handing in a thesis. |
| U15 | Q1 Explicit | — | O | Extract Assignment Submitted events for each student. |
| OU01 | Q3 Full Lifecycle | — | O | Extract the full recorded lifecycle event log for each student. |
| OU02 | Q3 Full Lifecycle | — | O | Extract the full recorded lifecycle event log for each course. |
| OU03 | Q3 Full Lifecycle | — | O | Extract the full recorded lifecycle event log for each student-course registration. |
| OU04 | Q3 Full Lifecycle | — | O | Extract the full recorded lifecycle event log for each examination result record. |
| OU05 | Q3 Full Lifecycle | — | O | Extract the full recorded lifecycle event log for each simulation module. |
| OU06 | Q3 Full Lifecycle | — | O | Extract the full recorded lifecycle event log for each thesis. |
| OU07 | Q3 Full Lifecycle | — | O | Extract the full recorded lifecycle event log for each simulation experiment result record. |
| OU08 | Q3 Full Lifecycle | — | O | Extract the full recorded lifecycle event log for each assignment. |
| OU09 | Q3 Full Lifecycle | — | O | Extract the full recorded lifecycle event log for each instructor. |
| OU10 | Q3 Full Lifecycle | — | O | Extract the full recorded lifecycle event log for each assignment grading record. |
| OU11 | Q3 Full Lifecycle | — | O | Extract the full recorded lifecycle event log for each course-design task. |
| U07P | Q2 Paraphrased | U07 | X | For each student, build a timeline of confirmation messages being sent after a course sign-up. |
| U08P | Q2 Paraphrased | U08 | X | For each student, build a timeline of the student leaving a course after signing up. |
| U15P | Q2 Paraphrased | U15 | O | For each student, build a timeline of the student handing in coursework. |
| OU01P | Q4 Full Lifecycle Paraphrased | OU01 | O | Show the complete recorded history associated with each student. |
| OU01E | Q1 Explicit | — | O | Extract Assignment Assigned, Assignment Submitted, Assignment Graded events for each student. |
| OU01EP | Q2 Paraphrased | OU01E | O | For each student, build a timeline of coursework being set for the student, the student handing in coursework, an instructor assessing the assignment. |
| OU02P | Q4 Full Lifecycle Paraphrased | OU02 | O | Show the complete recorded history associated with each course. |
| OU02E | Q1 Explicit | — | O | Extract Registration Requested, Course Registered, Course Grade Finalized events for each course. |
| OU02EP | Q2 Paraphrased | OU02E | O | For each course, build a timeline of the student requesting a place on a course, a successful course sign-up, the course mark being made final. |
| OU03P | Q4 Full Lifecycle Paraphrased | OU03 | O | Show the complete recorded history associated with each student-course registration. |
| OU03E | Q1 Explicit | — | O | Extract Registration Requested, Course Registered, Course Grade Finalized events for each student-course registration. |
| OU03EP | Q2 Paraphrased | OU03E | O | For each student-course registration, build a timeline of the student requesting a place on a course, a successful course sign-up, the course mark being made final. |
| OU04P | Q4 Full Lifecycle Paraphrased | OU04 | O | Show the complete recorded history associated with each examination result record. |
| OU04E | Q1 Explicit | — | O | Extract Examination Scheduled, Degree Examination Taken, Examination Score Published events for each examination result record. |
| OU04EP | Q2 Paraphrased | OU04E | O | For each examination result record, build a timeline of an examination sitting being arranged, the student sitting the degree examination, the examination mark being released. |
| OU05P | Q4 Full Lifecycle Paraphrased | OU05 | O | Show the complete recorded history associated with each simulation module. |
| OU05E | Q1 Explicit | — | O | Extract Simulation Run Started, Simulation Experiment Completed, Simulation Result Accepted events for each simulation module. |
| OU05EP | Q2 Paraphrased | OU05E | O | For each simulation module, build a timeline of a simulation run beginning, a simulation run finishing, the simulation results receiving approval. |
| OU06P | Q4 Full Lifecycle Paraphrased | OU06 | O | Show the complete recorded history associated with each thesis. |
| OU06E | Q1 Explicit | — | O | Extract Thesis Submitted, Thesis Review Started, Thesis Accepted events for each thesis. |
| OU06EP | Q2 Paraphrased | OU06E | O | For each thesis, build a timeline of the student handing in a thesis, the review of a thesis beginning, a thesis receiving final approval. |
| OU07P | Q4 Full Lifecycle Paraphrased | OU07 | O | Show the complete recorded history associated with each simulation experiment result record. |
| OU07E | Q1 Explicit | — | O | Extract Simulation Run Started, Simulation Experiment Completed, Simulation Result Accepted events for each simulation experiment result record. |
| OU07EP | Q2 Paraphrased | OU07E | O | For each simulation experiment result record, build a timeline of a simulation run beginning, a simulation run finishing, the simulation results receiving approval. |
| OU08P | Q4 Full Lifecycle Paraphrased | OU08 | O | Show the complete recorded history associated with each assignment. |
| OU08E | Q1 Explicit | — | O | Extract Assignment Assigned, Assignment Submitted, Assignment Graded events for each assignment. |
| OU08EP | Q2 Paraphrased | OU08E | O | For each assignment, build a timeline of coursework being set for the student, the student handing in coursework, an instructor assessing the assignment. |
| OU09P | Q4 Full Lifecycle Paraphrased | OU09 | O | Show the complete recorded history associated with each instructor. |
| OU09E | Q1 Explicit | — | O | Extract Assignment Assigned, Assignment Submitted, Assignment Graded events for each instructor. |
| OU09EP | Q2 Paraphrased | OU09E | O | For each instructor, build a timeline of coursework being set for the student, the student handing in coursework, an instructor assessing the assignment. |
| OU10P | Q4 Full Lifecycle Paraphrased | OU10 | O | Show the complete recorded history associated with each assignment grading record. |
| OU10E | Q1 Explicit | — | O | Extract Assignment Graded events for each assignment grading record. |
| OU10EP | Q2 Paraphrased | OU10E | O | For each assignment grading record, build a timeline of an instructor assessing the assignment. |
| OU11P | Q4 Full Lifecycle Paraphrased | OU11 | O | Show the complete recorded history associated with each course-design task. |
| OU11E | Q1 Explicit | — | O | Extract Design Task Approved, Design Task Closed, Design Task Created events for each course-design task. |
| OU11EP | Q2 Paraphrased | OU11E | O | For each course-design task, build a timeline of a design exercise receiving approval, a design exercise being closed, a design exercise being prepared. |
