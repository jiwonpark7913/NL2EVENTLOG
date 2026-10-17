# UniversityFlow business-table storage

- Eleven original source business-table roles remain. All six remaining generic activity tables and the case-link index are removed.
- One-time stages are actual-time columns on registration, examination result, assignment, thesis, experiment result, module, course and task records. NULL means not recorded.
- Repeat runs remain distinct experiment-result rows under the source composite key. Grading and reassessments remain separate assignment_grading rows.
- The current simulation has at most one revision branch per assignment/thesis. Multiple revision rounds would require a dedicated submission/review history rather than overwriting these milestone columns.
- Original source keys and business events remain. Added columns, grading_kind and reassessment scores are authored synthetic assumptions.
- Event attribution uses declared keys and existing business JOINs; there is no persisted event-to-case index.

| Business table | Added milestone activities |
|---|---|
| student |  |
| course | Course Offering Proposed; Course Offering Approved; Course Offering Published; Course Offering Closed |
| registration | Registration Requested; Registration Approved; Course Started; Course Assessment Completed; Course Grade Finalized |
| degree_examination_result | Examination Scheduled; Examination Checked In; Examination Score Published; Examination Result Reviewed |
| task | Design Task Created; Design Task Approved; Design Task Published; Design Task Closed |
| simulation_module | Simulation Module Published; Simulation Module Validated; Simulation Module Released; Simulation Module Retired |
| thesis | Thesis Revision Requested; Thesis Resubmitted; Thesis Draft Registered; Thesis Review Started; Thesis Accepted |
| student_simulation_experiment_result | Simulation Run Scheduled; Simulation Run Started; Simulation Output Reviewed; Simulation Result Accepted |
| assignment | Assignment Revision Requested; Assignment Resubmitted; Assignment Assigned; Assignment Submitted; Assignment Grade Finalized |
| instructor |  |
| assignment_grading | Assignment Regraded |
