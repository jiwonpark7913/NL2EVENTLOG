-- evaluator-only Q22
SELECT case_id,activity,timestamp FROM (
SELECT s0.leg_id AS case_id, 'Passenger Boarding Confirmed' AS activity, s0.action_at AS timestamp FROM passenger_actions s0 WHERE s0.action_code='BD'
UNION ALL
SELECT s0.leg_id AS case_id, 'Scan Rejected' AS activity, s0.action_at AS timestamp FROM passenger_actions s0 WHERE s0.action_code='RJ'
) ORDER BY case_id,timestamp,activity;
