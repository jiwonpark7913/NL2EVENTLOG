-- evaluator-only Q44
SELECT case_id,activity,timestamp FROM (
SELECT s0.turn_id AS case_id, 'Baggage Loading Close' AS activity, s0.finished_at AS timestamp FROM handling_jobs s0 WHERE s0.job_code='BL'
UNION ALL
SELECT s1.turn_id AS case_id, 'Off-block' AS activity, s0.value_at AS timestamp FROM movement_reports s0 JOIN turnarounds s1 ON s0.flight_id=s1.outbound_id WHERE s0.kind='OUT'
UNION ALL
SELECT s0.turn_id AS case_id, 'Baggage Loading Start' AS activity, s0.started_at AS timestamp FROM handling_jobs s0 WHERE s0.job_code='BL'
UNION ALL
SELECT s1.turn_id AS case_id, 'Take-off' AS activity, s0.value_at AS timestamp FROM movement_reports s0 JOIN turnarounds s1 ON s0.flight_id=s1.outbound_id WHERE s0.kind='AIR'
UNION ALL
SELECT s0.turn_id AS case_id, 'Cabin Cleaning Start' AS activity, s0.started_at AS timestamp FROM handling_jobs s0 WHERE s0.job_code='CL'
UNION ALL
SELECT s0.turn_id AS case_id, 'Cabin Cleaning Complete' AS activity, s0.finished_at AS timestamp FROM handling_jobs s0 WHERE s0.job_code='CL'
UNION ALL
SELECT s0.turn_id AS case_id, 'Refuelling Start' AS activity, s0.started_at AS timestamp FROM handling_jobs s0 WHERE s0.job_code='FU'
UNION ALL
SELECT s0.turn_id AS case_id, 'Refuelling Complete' AS activity, s0.finished_at AS timestamp FROM handling_jobs s0 WHERE s0.job_code='FU'
UNION ALL
SELECT s0.turn_id AS case_id, 'Catering Loading Start' AS activity, s0.started_at AS timestamp FROM handling_jobs s0 WHERE s0.job_code='CA'
UNION ALL
SELECT s0.turn_id AS case_id, 'Catering Loading Complete' AS activity, s0.finished_at AS timestamp FROM handling_jobs s0 WHERE s0.job_code='CA'
UNION ALL
SELECT s0.turn_id AS case_id, 'Disembarkation Start' AS activity, s0.started_at AS timestamp FROM handling_jobs s0 WHERE s0.job_code='DP'
UNION ALL
SELECT s0.turn_id AS case_id, 'Disembarkation Complete' AS activity, s0.finished_at AS timestamp FROM handling_jobs s0 WHERE s0.job_code='DP'
) ORDER BY case_id,timestamp,activity;
