-- evaluator-only Q31
SELECT case_id,activity,timestamp FROM (
SELECT s2.flight_id AS case_id, 'Screening Start' AS activity, s0.observed_at AS timestamp FROM security_events s0 JOIN security_visits s1 ON s0.visit_id=s1.visit_id JOIN passenger_legs s2 ON s1.leg_id=s2.leg_id JOIN turnarounds scope_t ON scope_t.outbound_id=s2.flight_id WHERE s0.point='S'
UNION ALL
SELECT s2.flight_id AS case_id, 'Screening Complete' AS activity, s0.observed_at AS timestamp FROM security_events s0 JOIN security_visits s1 ON s0.visit_id=s1.visit_id JOIN passenger_legs s2 ON s1.leg_id=s2.leg_id JOIN turnarounds scope_t ON scope_t.outbound_id=s2.flight_id WHERE s0.point='C'
UNION ALL
SELECT s0.flight_id AS case_id, 'Boarding Start' AS activity, s0.started_at AS timestamp FROM boarding_sessions s0 JOIN turnarounds scope_t ON scope_t.outbound_id=s0.flight_id
UNION ALL
SELECT s0.flight_id AS case_id, 'Boarding Close' AS activity, s0.closed_at AS timestamp FROM boarding_sessions s0 JOIN turnarounds scope_t ON scope_t.outbound_id=s0.flight_id
) ORDER BY case_id,timestamp,activity;
