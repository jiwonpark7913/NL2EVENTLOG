-- evaluator-only Q67
SELECT case_id,activity,timestamp FROM (
SELECT s1.turn_id AS case_id, 'Landing' AS activity, s0.value_at AS timestamp FROM movement_reports s0 JOIN turnarounds s1 ON s0.flight_id=s1.inbound_id WHERE s0.kind='LAND'
UNION ALL
SELECT s1.turn_id AS case_id, 'Boarding Close' AS activity, s0.closed_at AS timestamp FROM boarding_sessions s0 JOIN turnarounds s1 ON s0.flight_id=s1.inbound_id
) ORDER BY case_id,timestamp,activity;
