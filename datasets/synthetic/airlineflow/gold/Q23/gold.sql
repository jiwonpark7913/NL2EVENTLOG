-- evaluator-only Q23
SELECT case_id,activity,timestamp FROM (
SELECT s1.ticket_id AS case_id, 'Passenger Boarding Confirmed' AS activity, s0.action_at AS timestamp FROM passenger_actions s0 JOIN passenger_legs s1 ON s0.leg_id=s1.leg_id WHERE s0.action_code='BD'
UNION ALL
SELECT s1.ticket_id AS case_id, 'Scan Rejected' AS activity, s0.action_at AS timestamp FROM passenger_actions s0 JOIN passenger_legs s1 ON s0.leg_id=s1.leg_id WHERE s0.action_code='RJ'
) ORDER BY case_id,timestamp,activity;
