-- evaluator-only Q56
SELECT case_id,activity,timestamp FROM (
SELECT s0.visit_id AS case_id, 'Queue Entry' AS activity, s0.observed_at AS timestamp FROM security_events s0 WHERE s0.point='Q'
UNION ALL
SELECT s0.visit_id AS case_id, 'Screening Start' AS activity, s0.observed_at AS timestamp FROM security_events s0 WHERE s0.point='S'
UNION ALL
SELECT s0.visit_id AS case_id, 'Screening Complete' AS activity, s0.observed_at AS timestamp FROM security_events s0 WHERE s0.point='C'
) ORDER BY case_id,timestamp,activity;
