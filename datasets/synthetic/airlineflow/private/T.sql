SELECT * FROM (
SELECT t.turn_id AS case_id, CASE m.kind WHEN 'LAND' THEN 'Inbound landed' WHEN 'IN' THEN 'Inbound in-block' END AS activity, m.value_at AS timestamp
FROM turnarounds t JOIN movement_reports m ON m.flight_id=t.inbound_id WHERE m.kind IN ('LAND','IN')
UNION ALL SELECT turn_id, 'Ground handling started', handling_started_at FROM turnarounds
UNION ALL SELECT j.turn_id, CASE j.job_code WHEN 'DP' THEN 'Disembarkation completed' WHEN 'UL' THEN 'Baggage unloading completed' WHEN 'CL' THEN 'Cabin cleaning completed' WHEN 'FU' THEN 'Refuelling completed' WHEN 'CA' THEN 'Catering completed' END, j.finished_at FROM handling_jobs j WHERE j.job_code IN ('DP','UL','CL','FU','CA')
UNION ALL SELECT t.turn_id, d.activity, d.timestamp FROM turnarounds t JOIN (SELECT b.flight_id AS case_id, 'Boarding started' AS activity, b.started_at AS timestamp FROM boarding_sessions b
UNION ALL SELECT flight_id, 'Boarding closed', closed_at FROM boarding_sessions
UNION ALL SELECT t.outbound_id, 'Baggage loading closed', j.finished_at FROM handling_jobs j JOIN turnarounds t ON t.turn_id=j.turn_id WHERE j.job_code='BL'
UNION ALL SELECT outbound_id, 'Aircraft ready', ready_at FROM turnarounds
UNION ALL SELECT flight_id, 'Off-block', value_at FROM movement_reports WHERE kind='OUT') d ON d.case_id=t.outbound_id
UNION ALL SELECT t.turn_id, 'Outbound take-off', m.value_at FROM turnarounds t JOIN movement_reports m ON m.flight_id=t.outbound_id WHERE m.kind='AIR'
) ORDER BY case_id, timestamp, activity;