CREATE TABLE flights (flight_id TEXT PRIMARY KEY NOT NULL, flight_no TEXT NOT NULL, scheduled_offblock TEXT NOT NULL, scheduled_inblock TEXT NOT NULL);

CREATE TABLE turnarounds (turn_id TEXT PRIMARY KEY NOT NULL, inbound_id TEXT NOT NULL UNIQUE REFERENCES flights(flight_id), outbound_id TEXT NOT NULL UNIQUE REFERENCES flights(flight_id), handling_started_at TEXT NOT NULL, ready_at TEXT NOT NULL, CHECK(inbound_id <> outbound_id));

CREATE TABLE boarding_sessions (session_id TEXT PRIMARY KEY NOT NULL, flight_id TEXT NOT NULL UNIQUE REFERENCES flights(flight_id), started_at TEXT NOT NULL, closed_at TEXT NOT NULL);

CREATE TABLE handling_jobs (job_id TEXT PRIMARY KEY NOT NULL, turn_id TEXT NOT NULL REFERENCES turnarounds(turn_id), job_code TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT NOT NULL, posted_at TEXT NOT NULL);

CREATE TABLE movement_reports (report_id TEXT PRIMARY KEY NOT NULL, flight_id TEXT NOT NULL REFERENCES flights(flight_id), kind TEXT NOT NULL, value_at TEXT NOT NULL, received_at TEXT NOT NULL);

CREATE TABLE bookings (booking_id TEXT PRIMARY KEY NOT NULL, booked_at TEXT NOT NULL);

CREATE TABLE passengers (passenger_id TEXT PRIMARY KEY NOT NULL, display_name TEXT NOT NULL, date_of_birth DATE NOT NULL, nationality_code TEXT CHECK (nationality_code IS NULL OR length(nationality_code)=2), gender_code TEXT NOT NULL CHECK (gender_code IN ('MALE','FEMALE','UNKNOWN')));

CREATE TABLE tickets (ticket_id TEXT PRIMARY KEY NOT NULL, booking_id TEXT NOT NULL REFERENCES bookings(booking_id), passenger_id TEXT NOT NULL REFERENCES passengers(passenger_id));

CREATE TABLE passenger_legs (leg_id TEXT PRIMARY KEY NOT NULL, ticket_id TEXT NOT NULL REFERENCES tickets(ticket_id), flight_id TEXT NOT NULL REFERENCES flights(flight_id), UNIQUE(ticket_id,flight_id));

CREATE TABLE passenger_actions (action_id TEXT PRIMARY KEY NOT NULL, leg_id TEXT NOT NULL REFERENCES passenger_legs(leg_id), action_code TEXT NOT NULL, action_at TEXT NOT NULL);

CREATE TABLE bag_legs (bag_leg_id TEXT PRIMARY KEY NOT NULL, leg_id TEXT NOT NULL REFERENCES passenger_legs(leg_id), bag_tag TEXT NOT NULL);

CREATE TABLE bag_scans (scan_id TEXT PRIMARY KEY NOT NULL, bag_leg_id TEXT NOT NULL REFERENCES bag_legs(bag_leg_id), scan_code TEXT NOT NULL, scanned_at TEXT NOT NULL);

CREATE TABLE checkpoints (checkpoint_id TEXT PRIMARY KEY NOT NULL, zone TEXT NOT NULL);

CREATE TABLE security_visits (visit_id TEXT PRIMARY KEY NOT NULL, leg_id TEXT NOT NULL REFERENCES passenger_legs(leg_id), checkpoint_id TEXT NOT NULL REFERENCES checkpoints(checkpoint_id));

CREATE TABLE security_events (event_id TEXT PRIMARY KEY NOT NULL, visit_id TEXT NOT NULL REFERENCES security_visits(visit_id), point TEXT NOT NULL, observed_at TEXT NOT NULL, received_at TEXT NOT NULL);

CREATE TABLE airlines (airline_id TEXT PRIMARY KEY NOT NULL, name TEXT NOT NULL);

CREATE TABLE airports (airport_id TEXT PRIMARY KEY NOT NULL, city TEXT NOT NULL);

CREATE TABLE aircraft (tail_id TEXT PRIMARY KEY NOT NULL, airline_id TEXT NOT NULL REFERENCES airlines(airline_id), model TEXT NOT NULL);

CREATE TABLE employees (employee_id TEXT PRIMARY KEY NOT NULL, airline_id TEXT NOT NULL REFERENCES airlines(airline_id), role TEXT NOT NULL);

CREATE TABLE flight_dispatch (dispatch_id TEXT PRIMARY KEY NOT NULL, flight_id TEXT NOT NULL UNIQUE REFERENCES flights(flight_id), tail_id TEXT NOT NULL REFERENCES aircraft(tail_id), origin TEXT NOT NULL REFERENCES airports(airport_id), destination TEXT NOT NULL REFERENCES airports(airport_id), dispatcher_id TEXT NOT NULL REFERENCES employees(employee_id), assigned_at TEXT NOT NULL);
