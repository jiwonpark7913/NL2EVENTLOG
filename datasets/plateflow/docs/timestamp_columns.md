# Timestamp column inventory

- Timestamp columns count physical table.column pairs storing date-and-time instants. Date-only birth/planning fields and recurring class schedules are excluded. Event timestamp columns are the subset actually selected as event times by the current ES; plans, technical times, snapshots, interval starts and copied key timestamps are listed separately.

| Table | Column | Role | Used as event time | Non-null rows |
|---|---|---|---|---:|
| slab_material | slab_received_at | actual event time | Yes | 36 |
| slab_material | slab_identity_verified_at | actual event time | Yes | 36 |
| slab_material | slab_quality_checked_at | actual event time | Yes | 36 |
| slab_material | slab_released_for_rolling_at | actual event time | Yes | 30 |
| planned_rolling_instruction | planned_reheat_at | planned instant | No | 36 |
| planned_rolling_instruction | rolling_plan_created_at | actual event time | Yes | 36 |
| planned_rolling_instruction | rolling_plan_reviewed_at | actual event time | Yes | 36 |
| planned_rolling_instruction | rolling_plan_approved_at | actual event time | Yes | 36 |
| planned_rolling_instruction | rolling_plan_released_at | actual event time | Yes | 30 |
| rolling_instruction | released_at | actual event time | Yes | 36 |
| rolling_instruction | rolling_instruction_acknowledged_at | actual event time | Yes | 36 |
| rolling_instruction | rolling_setup_verified_at | actual event time | Yes | 34 |
| rolling_instruction | rolling_work_started_at | actual event time | Yes | 24 |
| rolling_instruction | rolling_instruction_closed_at | actual event time | Yes | 20 |
| as_rolled_material | furnace_charged_at | actual event time | Yes | 30 |
| as_rolled_material | crop_shear_passed_at | actual event time | Yes | 18 |
| as_rolled_material | latest_operation_completed_at | latest-operation snapshot | No | 24 |
| as_rolled_material | created_at | technical record timestamp | No | 36 |
| as_rolled_material | updated_at | technical record timestamp | No | 36 |
| furnace_charge_tracking | yard_instruction_received_at | actual event time | Yes | 30 |
| furnace_charge_tracking | lot_charging_started_at | lot-level instant outside material-event scope | No | 30 |
| furnace_charge_tracking | furnace_charge_assigned_at | actual event time | Yes | 30 |
| furnace_charge_tracking | furnace_charge_confirmed_at | actual event time | Yes | 29 |
| furnace_charge_tracking | furnace_discharge_confirmed_at | actual event time | Yes | 20 |
| cutting_finishing_instruction | released_at | actual event time | Yes | 18 |
| cutting_finishing_instruction | cutting_instruction_acknowledged_at | actual event time | Yes | 18 |
| cutting_finishing_instruction | cutting_setup_verified_at | actual event time | Yes | 18 |
| cutting_finishing_instruction | cutting_work_started_at | actual event time | Yes | 18 |
| cutting_finishing_instruction | cutting_instruction_closed_at | actual event time | Yes | 15 |
| plate_material | dimension_inspected_at | actual event time | Yes | 39 |
| plate_material | latest_operation_completed_at | latest-operation snapshot | No | 39 |
| plate_material | plate_piece_identified_at | actual event time | Yes | 39 |
| plate_material | plate_quality_released_at | actual event time | Yes | 39 |
| plate_material | plate_packed_at | actual event time | Yes | 33 |
| plate_material | plate_quality_review_started_at | actual event time | Yes | 39 |
| plate_material | plate_packing_started_at | actual event time | Yes | 33 |
| material_operation_history | started_at | operation interval start, not a separately selected event | No | 216 |
| material_operation_history | completed_at | actual event time | Yes | 216 |
| material_operation_history | created_at | technical record timestamp | No | 216 |

- Date-only fields excluded: None.
- New timestamp questions TS01/TS02/... and their P counterparts explicitly test milestone-column extraction.
