-- evaluator-only Q57
SELECT case_id,activity,timestamp FROM (
SELECT s0.leg_id AS case_id, 'Check-in Complete' AS activity, s0.action_at AS timestamp FROM passenger_actions s0 WHERE s0.action_code='CK'
UNION ALL
SELECT s1.leg_id AS case_id, 'Queue Entry' AS activity, s0.observed_at AS timestamp FROM security_events s0 JOIN security_visits s1 ON s0.visit_id=s1.visit_id WHERE s0.point='Q'
UNION ALL
SELECT s1.leg_id AS case_id, 'Screening Start' AS activity, s0.observed_at AS timestamp FROM security_events s0 JOIN security_visits s1 ON s0.visit_id=s1.visit_id WHERE s0.point='S'
UNION ALL
SELECT s1.leg_id AS case_id, 'Screening Complete' AS activity, s0.observed_at AS timestamp FROM security_events s0 JOIN security_visits s1 ON s0.visit_id=s1.visit_id WHERE s0.point='C'
UNION ALL
SELECT s0.leg_id AS case_id, 'Passenger Boarding Confirmed' AS activity, s0.action_at AS timestamp FROM passenger_actions s0 WHERE s0.action_code='BD'
UNION ALL
SELECT s0.leg_id AS case_id, 'Scan Rejected' AS activity, s0.action_at AS timestamp FROM passenger_actions s0 WHERE s0.action_code='RJ'
) ORDER BY case_id,timestamp,activity;
