# L05 — data dictionary

[Back to variant](../README.md) · [Original JSON](../input/data_dictionary.json)

5 tables · 30 columns · 2,100 rows

## `boarding_sessions`

Flight-level boarding sessions at the origin of every dated operating leg. One session per flight in this example; inbound legs also have origin boarding records. (200 rows)

| Column | Declaration | Description |
|---|---|---|
| `session_id` | `TEXT PRIMARY KEY NOT NULL` | Boarding session identifier. |
| `flight_id` | `TEXT NOT NULL UNIQUE REFERENCES flights(flight_id)` | Operating leg. |
| `started_at` | `TEXT NOT NULL` | Actual start of passenger boarding. |
| `closed_at` | `TEXT NOT NULL` | Actual close of passenger boarding. |

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

## `turnarounds`

Ground stay at the focal airport linking an arriving operating leg to the next departing operating leg of the same aircraft. The overall handling start is the start of coordination, which can precede individual jobs. (100 rows)

| Column | Declaration | Description |
|---|---|---|
| `turn_id` | `TEXT PRIMARY KEY NOT NULL` | Turnaround identifier. |
| `inbound_id` | `TEXT NOT NULL UNIQUE REFERENCES flights(flight_id)` | Inbound operating leg. |
| `outbound_id` | `TEXT NOT NULL UNIQUE REFERENCES flights(flight_id)` | Next outbound operating leg. |
| `handling_started_at` | `TEXT NOT NULL` | Actual start of ground handling. |
| `ready_at` | `TEXT NOT NULL` | Actual aircraft ready time. |

