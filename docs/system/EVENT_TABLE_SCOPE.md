# Event-table scope audit

All six datasets are audited. (a) one physical timestamp column with one carrier; (b) multiple physical timestamp columns with one carrier; (c) activity from time-column meaning; (d) activity from table meaning. These are representative, non-exclusive patterns. The (a)/(b) distinction uses the physical timestamp inventory. Only selected business-event times produce events; plans, technical timestamps and snapshots may coexist without becoming activities. The selected-time column is listed separately below.

## Findings and repair

- **Structural violation:** WarehouseFlow.transaction_record combined transaction_type/occurred_at with four independently named lifecycle milestones (mixed encoding). The four authored milestone columns were removed; their 160 occurrences now remain in transaction_record_activity with activity/occurred_at. Both tables are now (a). The builder enforces this storage choice.
- **Annotation correction:** UniversityFlow.registration, degree_examination_result and student_simulation_experiment_result are non-carrier (c), although previous documentation called them mixed/row encoded. status, examination_name and result data do not select their activity labels. assignment_grading uses grading_kind and is (a). No UniversityFlow records or Gold events change.
- No additional composite-carrier, multiple-carrier or split activity/time violation was found in the authored extraction bindings. A composite PK is an occurrence identifier, not a composite activity carrier. process_group/code_family are fixed per history table, so one varying code determines the activity. Code-reference dictionaries decode codes; case-attribution JOINs do not split activity and time across event records. Descriptive procedure, medication, item, result and outcome fields are not carriers under the current activity definitions.
- Carrier interval start/completion phases remain allowed under (b). Non-carrier procedure episodes and audits use table meaning plus temporal phase under (d); they may also be described by (c). No extra independent carrier column is introduced.
- Gold ES/SQL were regenerated for the changed storage. Every pre-existing Gold CSV, question, canonical event and case membership was preserved. WarehouseFlow timestamp-column count falls from 6 to 2; event count remains 394 and activity count remains 10.

## Verification

64 physical tables; 47 event-source tables; 282 Gold logs verified. Run `python validate_event_scope.py`. The explicit contracts are author annotations outside model-input manifests. This checks this benchmark and its current authored bindings; it is not a general detector or independent validation of business assumptions.

## warehouseflow

| Table | Pattern | Carrier | Selected event times |
|---|---|---|---|
| goods | No selected events | — | — |
| goods_transaction_detail | No selected events | — | — |
| lifecycle_case_link | No selected events | — | — |
| loader | No selected events | — | — |
| loader_transaction | No selected events | — | — |
| transaction_record | a | transaction_type | occurred_at |
| transaction_record_activity | a | activity | occurred_at |
| warehouse | No selected events | — | — |

## universityflow

| Table | Pattern | Carrier | Selected event times |
|---|---|---|---|
| assignment | c | — | assignment_assigned_at, assignment_grade_finalized_at, assignment_resubmitted_at, assignment_revision_requested_at, assignment_submitted_at |
| assignment_grading | a | grading_kind | grading_time |
| course | c | — | course_offering_approved_at, course_offering_closed_at, course_offering_proposed_at, course_offering_published_at |
| degree_examination_result | c | — | examination_checked_in_at, examination_date, examination_result_reviewed_at, examination_scheduled_at, examination_score_published_at |
| instructor | No selected events | — | — |
| registration | c | — | course_assessment_completed_at, course_grade_finalized_at, course_started_at, registration_approved_at, registration_requested_at, registration_time |
| simulation_module | c | — | simulation_module_published_at, simulation_module_released_at, simulation_module_retired_at, simulation_module_validated_at |
| student | No selected events | — | — |
| student_simulation_experiment_result | c | — | simulation_date, simulation_output_reviewed_at, simulation_result_accepted_at, simulation_run_scheduled_at, simulation_run_started_at |
| task | c | — | design_task_approved_at, design_task_closed_at, design_task_created_at, design_task_published_at |
| thesis | c | — | submission_date, thesis_accepted_at, thesis_draft_registered_at, thesis_resubmitted_at, thesis_review_started_at, thesis_revision_requested_at |

## plateflow

| Table | Pattern | Carrier | Selected event times |
|---|---|---|---|
| as_rolled_material | c | — | crop_shear_passed_at, furnace_charged_at |
| cutting_finishing_instruction | c | — | cutting_instruction_acknowledged_at, cutting_instruction_closed_at, cutting_setup_verified_at, cutting_work_started_at, released_at |
| furnace_charge_tracking | c | — | furnace_charge_assigned_at, furnace_charge_confirmed_at, furnace_discharge_confirmed_at, yard_instruction_received_at |
| material_operation_history | b | operation_code | completed_at |
| operation_code | No selected events | — | — |
| planned_rolling_instruction | c | — | rolling_plan_approved_at, rolling_plan_created_at, rolling_plan_released_at, rolling_plan_reviewed_at |
| plate_material | c | — | dimension_inspected_at, plate_packed_at, plate_packing_started_at, plate_piece_identified_at, plate_quality_released_at, plate_quality_review_started_at |
| rolling_instruction | c | — | released_at, rolling_instruction_acknowledged_at, rolling_instruction_closed_at, rolling_setup_verified_at, rolling_work_started_at |
| slab_material | c | — | slab_identity_verified_at, slab_quality_checked_at, slab_received_at, slab_released_for_rolling_at |

## hospitalflow

| Table | Pattern | Carrier | Selected event times |
|---|---|---|---|
| admission_detail | c | — | discharge_summary_signed_at |
| admissions | c | — | admittime, discharge_authorized_at, dischtime, edregtime |
| emar | b | event_txt | charttime |
| lab_order | c | — | results_verified_at, specimen_received_at |
| labevents | c | — | charttime, storetime |
| medication_order | c | — | stopped_at |
| order_history | a | action | occurred_at |
| patient_profile | c | — | profile_verified_at |
| patients | No selected events | — | — |
| pharmacy | c | — | dispensed_at |
| procedure_episode | d | — | endtime, starttime |
| procedure_order | c | — | preparation_completed_at |

## plateflow_new

| Table | Pattern | Carrier | Selected event times |
|---|---|---|---|
| as_rolled_material | No selected events | — | — |
| dimension_inspection | d | — | inspected_at |
| equipment | No selected events | — | — |
| finishing_operation_history | b | operation_code | finished_at |
| furnace_operation_history | b | operation_code | finished_at |
| planned_rolling_instruction | c | — | approved_at, released_at, submitted_at |
| plate_material | c | — | identified_at, packed_at, released_at |
| plate_quality_review | d | — | finished_at |
| process_code | No selected events | — | — |
| rolling_instruction | d | — | issued_at |
| rolling_operation_history | b | phase_code | finished_at |
| slab_material | c | — | received_at, released_at, verified_at |

## warehouseflow_new

| Table | Pattern | Carrier | Selected event times |
|---|---|---|---|
| dispatch_order | c | — | approved_at, requested_at |
| goods | No selected events | — | — |
| goods_movement | a | movement_code | occurred_at |
| goods_receipt | d | — | received_at |
| handling_history | b | handling_code | completed_at, started_at |
| receiving_request | c | — | submitted_at |
| request_action | a | action_code | occurred_at |
| warehouse | No selected events | — | — |
| warehouse_audit | d | — | completed_at, started_at |
| warehouse_task_history | b | task_code | completed_at, started_at |
| work_code | No selected events | — | — |
| worker | No selected events | — | — |
