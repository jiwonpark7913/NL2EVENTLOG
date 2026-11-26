-- evaluator-only Q19
SELECT case_id,activity,timestamp FROM (
SELECT s0.leg_id AS case_id, 'Check-in Complete' AS activity, s0.action_at AS timestamp FROM passenger_actions s0 WHERE s0.action_code='CK'
UNION ALL
SELECT s0.leg_id AS case_id, 'Passenger Boarding Confirmed' AS activity, s0.action_at AS timestamp FROM passenger_actions s0 WHERE s0.action_code='BD'
) ORDER BY case_id,timestamp,activity;
