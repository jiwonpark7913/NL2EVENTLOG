SELECT * FROM (
SELECT t.turn_id AS case_id,CASE m.kind WHEN 'LAND' THEN 'Inbound landed' ELSE 'Inbound in-block' END AS activity,m.value_at AS timestamp FROM turnarounds t JOIN movement_reports m ON m.flight_id=t.inbound_id WHERE m.kind IN ('LAND','IN')
UNION ALL SELECT turn_id,'Ground handling started',handling_started_at FROM turnarounds
UNION ALL SELECT turn_id,CASE job_code WHEN 'DP' THEN 'Disembarkation completed' WHEN 'UL' THEN 'Baggage unloading completed' WHEN 'CL' THEN 'Cabin cleaning completed' WHEN 'FU' THEN 'Refuelling completed' WHEN 'CA' THEN 'Catering completed' WHEN 'BL' THEN 'Baggage loading closed' END,finished_at FROM handling_jobs WHERE job_code IN ('DP','UL','CL','FU','CA','BL')
UNION ALL SELECT t.turn_id,'Boarding started',b.started_at FROM turnarounds t JOIN boarding_sessions b ON b.flight_id=t.outbound_id
UNION ALL SELECT t.turn_id,'Boarding closed',b.closed_at FROM turnarounds t JOIN boarding_sessions b ON b.flight_id=t.outbound_id
UNION ALL SELECT turn_id,'Aircraft ready',ready_at FROM turnarounds
UNION ALL SELECT t.turn_id,CASE m.kind WHEN 'OUT' THEN 'Off-block' ELSE 'Outbound take-off' END,m.value_at FROM turnarounds t JOIN movement_reports m ON m.flight_id=t.outbound_id WHERE m.kind IN ('OUT','AIR')
) ORDER BY case_id,timestamp,activity;
