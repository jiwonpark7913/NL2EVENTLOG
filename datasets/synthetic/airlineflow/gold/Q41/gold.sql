-- evaluator-only Q41
SELECT case_id,activity,timestamp FROM (
SELECT s0.turn_id AS case_id, 'Baggage Loading Close' AS activity, s0.finished_at AS timestamp FROM handling_jobs s0 WHERE s0.job_code='BL'
UNION ALL
SELECT s1.turn_id AS case_id, 'Off-block' AS activity, s0.value_at AS timestamp FROM movement_reports s0 JOIN turnarounds s1 ON s0.flight_id=s1.outbound_id WHERE s0.kind='OUT'
) ORDER BY case_id,timestamp,activity;
