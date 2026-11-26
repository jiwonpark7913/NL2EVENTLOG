-- evaluator-only Q72
SELECT case_id,activity,timestamp FROM (
SELECT s1.turn_id AS case_id, 'In-block' AS activity, s0.value_at AS timestamp FROM movement_reports s0 JOIN turnarounds s1 ON s0.flight_id=s1.inbound_id WHERE s0.kind='IN'
UNION ALL
SELECT s1.turn_id AS case_id, 'Boarding Start' AS activity, s0.started_at AS timestamp FROM boarding_sessions s0 JOIN turnarounds s1 ON s0.flight_id=s1.outbound_id
) ORDER BY case_id,timestamp,activity;
