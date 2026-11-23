CREATE TABLE flights (flight_id TEXT PRIMARY KEY NOT NULL, flight_no TEXT NOT NULL, scheduled_offblock TEXT NOT NULL, scheduled_inblock TEXT NOT NULL);

CREATE TABLE turnarounds (turn_id TEXT PRIMARY KEY NOT NULL, inbound_id TEXT NOT NULL UNIQUE REFERENCES flights(flight_id), outbound_id TEXT NOT NULL UNIQUE REFERENCES flights(flight_id), handling_started_at TEXT NOT NULL, ready_at TEXT NOT NULL, CHECK(inbound_id <> outbound_id));

CREATE TABLE boarding_sessions (session_id TEXT PRIMARY KEY NOT NULL, flight_id TEXT NOT NULL UNIQUE REFERENCES flights(flight_id), started_at TEXT NOT NULL, closed_at TEXT NOT NULL);

CREATE TABLE handling_jobs (job_id TEXT PRIMARY KEY NOT NULL, turn_id TEXT NOT NULL REFERENCES turnarounds(turn_id), job_code TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT NOT NULL, posted_at TEXT NOT NULL);

CREATE TABLE movement_reports (report_id TEXT PRIMARY KEY NOT NULL, flight_id TEXT NOT NULL REFERENCES flights(flight_id), kind TEXT NOT NULL, value_at TEXT NOT NULL, received_at TEXT NOT NULL);
