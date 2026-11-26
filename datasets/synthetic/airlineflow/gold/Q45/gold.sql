-- evaluator-only Q45
SELECT case_id,activity,timestamp FROM (
SELECT s1.outbound_id AS case_id, 'Cabin Cleaning Complete' AS activity, s0.finished_at AS timestamp FROM handling_jobs s0 JOIN turnarounds s1 ON s0.turn_id=s1.turn_id WHERE s0.job_code='CL'
UNION ALL
SELECT s1.flight_id AS case_id, 'Passenger Boarding Confirmed' AS activity, s0.action_at AS timestamp FROM passenger_actions s0 JOIN passenger_legs s1 ON s0.leg_id=s1.leg_id JOIN turnarounds scope_t ON scope_t.outbound_id=s1.flight_id WHERE s0.action_code='BD'
) ORDER BY case_id,timestamp,activity;
