-- evaluator-only Q40
SELECT case_id,activity,timestamp FROM (
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
SELECT s0.turn_id AS case_id, 'Baggage Loading Start' AS activity, s0.started_at AS timestamp FROM handling_jobs s0 WHERE s0.job_code='BL'
UNION ALL
SELECT s0.turn_id AS case_id, 'Baggage Loading Close' AS activity, s0.finished_at AS timestamp FROM handling_jobs s0 WHERE s0.job_code='BL'
UNION ALL
SELECT s0.turn_id AS case_id, 'Disembarkation Start' AS activity, s0.started_at AS timestamp FROM handling_jobs s0 WHERE s0.job_code='DP'
UNION ALL
SELECT s0.turn_id AS case_id, 'Disembarkation Complete' AS activity, s0.finished_at AS timestamp FROM handling_jobs s0 WHERE s0.job_code='DP'
UNION ALL
SELECT s0.turn_id AS case_id, 'Baggage Unloading Start' AS activity, s0.started_at AS timestamp FROM handling_jobs s0 WHERE s0.job_code='UL'
UNION ALL
SELECT s0.turn_id AS case_id, 'Baggage Unloading Complete' AS activity, s0.finished_at AS timestamp FROM handling_jobs s0 WHERE s0.job_code='UL'
) ORDER BY case_id,timestamp,activity;
