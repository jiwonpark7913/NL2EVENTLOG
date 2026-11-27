# L15 — data dictionary

[Back to variant](../README.md) · [Original JSON](../input/data_dictionary.json)

15 tables · 64 columns · 80,077 rows

## `bag_legs`

Transport records for a sample of checked bags associated with passenger flight legs. (5,887 rows)

| Column | Declaration | Description |
|---|---|---|
| `bag_leg_id` | `TEXT PRIMARY KEY NOT NULL` | Baggage transport record identifier. |
| `leg_id` | `TEXT NOT NULL REFERENCES passenger_legs(leg_id)` | Passenger flight leg associated with the checked bag. |
| `bag_tag` | `TEXT NOT NULL` | Baggage tag identifier. |

## `bag_scans`

Individual baggage tracking records for the checked bags represented in the dataset. (11,595 rows)

| Column | Declaration | Description |
|---|---|---|
| `scan_id` | `TEXT PRIMARY KEY NOT NULL` | Baggage scan record identifier. |
| `bag_leg_id` | `TEXT NOT NULL REFERENCES bag_legs(bag_leg_id)` | Baggage transport record associated with the scan. |
| `scan_code` | `TEXT NOT NULL` | Baggage tracking event code. B101 indicates that a bag has been accepted. B204 indicates that a bag has been loaded into the aircraft hold. |
| `scanned_at` | `TEXT NOT NULL` | Date and time of the baggage scan. |

## `boarding_sessions`

Flight-level boarding sessions at the origin of every dated operating leg. One session per flight in this example; inbound legs also have origin boarding records. (200 rows)

| Column | Declaration | Description |
|---|---|---|
| `session_id` | `TEXT PRIMARY KEY NOT NULL` | Boarding session identifier. |
| `flight_id` | `TEXT NOT NULL UNIQUE REFERENCES flights(flight_id)` | Operating leg. |
| `started_at` | `TEXT NOT NULL` | Actual start of passenger boarding. |
| `closed_at` | `TEXT NOT NULL` | Actual close of passenger boarding. |

## `bookings`

Reservations for groups of travellers. (2,537 rows)

| Column | Declaration | Description |
|---|---|---|
| `booking_id` | `TEXT PRIMARY KEY NOT NULL` | Booking identifier. |
| `booked_at` | `TEXT NOT NULL` | Time the booking was created. |

## `checkpoints`

Airport security screening checkpoints. (3 rows)

| Column | Declaration | Description |
|---|---|---|
| `checkpoint_id` | `TEXT PRIMARY KEY NOT NULL` | Security checkpoint identifier. |
| `zone` | `TEXT NOT NULL` | Screening zone name. |

## `flights`

Dated operating legs, including both inbound and outbound flights. Flight numbers repeat across dates. (200 rows)

| Column | Declaration | Description |
|---|---|---|
| `flight_id` | `TEXT PRIMARY KEY NOT NULL` | Operating leg identifier. |
| `flight_no` | `TEXT NOT NULL` | Published flight number. |
| `scheduled_offblock` | `TEXT NOT NULL` | Scheduled off-block time. |
| `scheduled_inblock` | `TEXT NOT NULL` | Scheduled in-block time. |

## `handling_jobs`

Ground handling work orders associated with aircraft turnarounds. (600 rows)

| Column | Declaration | Description |
|---|---|---|
| `job_id` | `TEXT PRIMARY KEY NOT NULL` | Handling job identifier. |
| `turn_id` | `TEXT NOT NULL REFERENCES turnarounds(turn_id)` | Aircraft turnaround associated with the job. |
| `job_code` | `TEXT NOT NULL` | Ground crews use CL for cabin cleaning and FU for refuelling. Catering loading is recorded under CA, and baggage loading under BL. DP identifies passenger disembarkation, while UL identifies baggage unloading. |
| `started_at` | `TEXT NOT NULL` | Actual start time of the assigned job. |
| `finished_at` | `TEXT NOT NULL` | Time at which completion of the assigned operation was confirmed. |
| `posted_at` | `TEXT NOT NULL` | Time at which the job record was posted to the system. |
| `service_provider_code` | `TEXT` | Provider assigned to the job. Codes are synthetic and cover airline ground operations and contracted providers. |
| `priority_code` | `TEXT` | Dispatch priority assigned to the job. STANDARD, HIGH and CRITICAL are synthetic operational categories. |
| `work_zone_code` | `TEXT` | Zone where the work was carried out, such as aircraft cabin, cargo hold, ramp or passenger bridge. |

## `movement_reports`

Estimated and actual movement messages for operating legs. Actual OUT and AIR refer to the origin; LAND and IN refer to the destination. Both inbound and outbound legs have all four actual movements; EST estimates origin off-block. (1,000 rows)

| Column | Declaration | Description |
|---|---|---|
| `report_id` | `TEXT PRIMARY KEY NOT NULL` | Movement report identifier. |
| `flight_id` | `TEXT NOT NULL REFERENCES flights(flight_id)` | Operating leg. |
| `kind` | `TEXT NOT NULL` | EST = estimated off-block; OUT = actual off-block; AIR = actual take-off; LAND = actual landing; IN = actual in-block. |
| `value_at` | `TEXT NOT NULL` | Timestamp represented by the message. |
| `received_at` | `TEXT NOT NULL` | Time the message was received. |
| `source_code` | `TEXT` | Origin of the report, such as an airport operations database (AODB), a ground handling system (GHS), or an aircraft communications feed (ACARS). |
| `validation_code` | `TEXT` | How a report was checked. AUTO_CHECKED means automated checks. OPS_REVIEWED means operations staff reviewed it. |
| `message_format_code` | `TEXT` | Format of the ingested record, such as AIDX, MVT or a local system record. |

## `passenger_actions`

Departure processing records for passenger flight legs. (14,031 rows)

| Column | Declaration | Description |
|---|---|---|
| `action_id` | `TEXT PRIMARY KEY NOT NULL` | Passenger action identifier. |
| `leg_id` | `TEXT NOT NULL REFERENCES passenger_legs(leg_id)` | Passenger flight leg. |
| `action_code` | `TEXT NOT NULL` | Once check-in is completed, the system records CK. When boarding is confirmed, the system records BD. If a scan is rejected, the system records RJ. |
| `action_at` | `TEXT NOT NULL` | Time the action occurred. |

## `passenger_legs`

Ticketed segments linking a passenger ticket to a particular operating leg. (6,885 rows)

| Column | Declaration | Description |
|---|---|---|
| `leg_id` | `TEXT PRIMARY KEY NOT NULL` | Passenger flight leg identifier. |
| `ticket_id` | `TEXT NOT NULL REFERENCES tickets(ticket_id)` | Associated ticket. |
| `flight_id` | `TEXT NOT NULL REFERENCES flights(flight_id)` | Operating leg. |

## `passengers`

Synthetic passenger register. The dataset records a single nationality, distinct from country of birth, residence or passport issuance. Date of birth is a passenger attribute. (4,505 rows)

| Column | Declaration | Description |
|---|---|---|
| `passenger_id` | `TEXT PRIMARY KEY NOT NULL` | Internal synthetic passenger identifier, distinct from a passport number. |
| `display_name` | `TEXT NOT NULL` | Synthetic passenger display name. |
| `date_of_birth` | `DATE NOT NULL` | Date of birth in YYYY-MM-DD format. A passenger attribute rather than an event timestamp. |
| `nationality_code` | `TEXT CHECK (nationality_code IS NULL OR length(nationality_code)=2)` | Recorded two-letter nationality code (KR, JP, US, DE or SG). NULL means unknown. |
| `gender_code` | `TEXT NOT NULL CHECK (gender_code IN ('MALE','FEMALE','UNKNOWN'))` | Source gender code using the local values MALE, FEMALE and UNKNOWN. |

## `security_events`

Observations recorded during security checkpoint visits. (20,999 rows)

| Column | Declaration | Description |
|---|---|---|
| `event_id` | `TEXT PRIMARY KEY NOT NULL` | Observation identifier. |
| `visit_id` | `TEXT NOT NULL REFERENCES security_visits(visit_id)` | Associated security visit. |
| `point` | `TEXT NOT NULL` | Q = queue entry; S = screening start; C = screening completion. |
| `observed_at` | `TEXT NOT NULL` | Time the observation was made on site. |
| `received_at` | `TEXT NOT NULL` | Time the receiving system received the record. |

## `security_visits`

Airport-provided records of individual passenger visits to security checkpoints. (7,030 rows)

| Column | Declaration | Description |
|---|---|---|
| `visit_id` | `TEXT PRIMARY KEY NOT NULL` | Security visit identifier. |
| `leg_id` | `TEXT NOT NULL REFERENCES passenger_legs(leg_id)` | Associated passenger flight leg. |
| `checkpoint_id` | `TEXT NOT NULL REFERENCES checkpoints(checkpoint_id)` | Security checkpoint visited. |

## `tickets`

Tickets issued to passengers. (4,505 rows)

| Column | Declaration | Description |
|---|---|---|
| `ticket_id` | `TEXT PRIMARY KEY NOT NULL` | Ticket identifier. |
| `booking_id` | `TEXT NOT NULL REFERENCES bookings(booking_id)` | Associated booking. |
| `passenger_id` | `TEXT NOT NULL REFERENCES passengers(passenger_id)` | Passenger named on the ticket. |

## `turnarounds`

Ground stay at the focal airport linking an arriving operating leg to the next departing operating leg of the same aircraft. The overall handling start is the start of coordination, which can precede individual jobs. (100 rows)

| Column | Declaration | Description |
|---|---|---|
| `turn_id` | `TEXT PRIMARY KEY NOT NULL` | Turnaround identifier. |
| `inbound_id` | `TEXT NOT NULL UNIQUE REFERENCES flights(flight_id)` | Inbound operating leg. |
| `outbound_id` | `TEXT NOT NULL UNIQUE REFERENCES flights(flight_id)` | Next outbound operating leg. |
| `handling_started_at` | `TEXT NOT NULL` | Actual start of ground handling. |
| `ready_at` | `TEXT NOT NULL` | Actual aircraft ready time. |

