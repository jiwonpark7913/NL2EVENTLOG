-- evaluator-only Q29
SELECT case_id,activity,timestamp FROM (
SELECT s0.turn_id AS case_id, 'Disembarkation Complete' AS activity, s0.finished_at AS timestamp FROM handling_jobs s0 WHERE s0.job_code='DP'
UNION ALL
SELECT s0.turn_id AS case_id, 'Baggage Unloading Complete' AS activity, s0.finished_at AS timestamp FROM handling_jobs s0 WHERE s0.job_code='UL'
UNION ALL
SELECT s1.turn_id AS case_id, 'Landing' AS activity, s0.value_at AS timestamp FROM movement_reports s0 JOIN turnarounds s1 ON s0.flight_id=s1.inbound_id WHERE s0.kind='LAND'
UNION ALL
SELECT s1.turn_id AS case_id, 'In-block' AS activity, s0.value_at AS timestamp FROM movement_reports s0 JOIN turnarounds s1 ON s0.flight_id=s1.inbound_id WHERE s0.kind='IN'
UNION ALL
SELECT s1.turn_id AS case_id, 'Boarding Start' AS activity, s0.started_at AS timestamp FROM boarding_sessions s0 JOIN turnarounds s1 ON s0.flight_id=s1.outbound_id
UNION ALL
SELECT s1.turn_id AS case_id, 'Boarding Close' AS activity, s0.closed_at AS timestamp FROM boarding_sessions s0 JOIN turnarounds s1 ON s0.flight_id=s1.outbound_id
) ORDER BY case_id,timestamp,activity;
