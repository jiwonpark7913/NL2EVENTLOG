-- evaluator-only Q65
SELECT case_id,activity,timestamp FROM (
SELECT s1.turn_id AS case_id, 'In-block' AS activity, s0.value_at AS timestamp FROM movement_reports s0 JOIN turnarounds s1 ON s0.flight_id=s1.outbound_id WHERE s0.kind='IN'
UNION ALL
SELECT s1.turn_id AS case_id, 'Off-block' AS activity, s0.value_at AS timestamp FROM movement_reports s0 JOIN turnarounds s1 ON s0.flight_id=s1.outbound_id WHERE s0.kind='OUT'
) ORDER BY case_id,timestamp,activity;
