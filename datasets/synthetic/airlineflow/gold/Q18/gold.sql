-- evaluator-only Q18
SELECT case_id,activity,timestamp FROM (
SELECT s2.flight_id AS case_id, 'Queue Entry' AS activity, s0.observed_at AS timestamp FROM security_events s0 JOIN security_visits s1 ON s0.visit_id=s1.visit_id JOIN passenger_legs s2 ON s1.leg_id=s2.leg_id WHERE s0.point='Q'
UNION ALL
SELECT s2.flight_id AS case_id, 'Screening Start' AS activity, s0.observed_at AS timestamp FROM security_events s0 JOIN security_visits s1 ON s0.visit_id=s1.visit_id JOIN passenger_legs s2 ON s1.leg_id=s2.leg_id WHERE s0.point='S'
UNION ALL
SELECT s2.flight_id AS case_id, 'Screening Complete' AS activity, s0.observed_at AS timestamp FROM security_events s0 JOIN security_visits s1 ON s0.visit_id=s1.visit_id JOIN passenger_legs s2 ON s1.leg_id=s2.leg_id WHERE s0.point='C'
) ORDER BY case_id,timestamp,activity;
