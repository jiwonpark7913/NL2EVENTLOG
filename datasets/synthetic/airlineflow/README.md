# AirlineFlow

AirlineFlow is an authored synthetic aviation example for NL2EventLog. It provides four nested databases with **5, 10, 15 and 20 tables**, together with twelve current pilot requests. It covers inbound-to-outbound aircraft turnaround, departure preparation, passenger processing, checked baggage and airport-linked security visits.

All records are synthetic. The study window contains 48 inbound flights, 48 outbound flights and 48 turnarounds across 12 days. The sample passengers and bags represent selected example records. Flight-level operational completion is recorded separately from individual scans. Each of the 96 legs has an origin boarding session and origin/departure and destination/arrival actual movement messages. All timestamps use KST.

## Inspect the scenario

![Five-table layout](variants/l05/docs/schema.svg)

The left ERD column marks PK, FK and single-column UQ constraints. Arrows point from child references to parent keys. The schema also declares a composite UNIQUE(ticket_id, flight_id) constraint in passenger_legs.

Download and open the [scenario viewer](docs/scenario.html) in a browser to view all four ERDs, embedded dictionaries and an example turnaround trace. Open **Raw tables** to browse SQLite rows or download a complete table as CSV.

## Four database sizes

| Variant | Tables | Added domain | Database | Dictionary | ERD |
|---|---:|---|---|---|---|
| l05 | 5 | Flight, turnaround, boarding session, handling job, movement report | [SQLite](variants/l05/input/database.sqlite) | [Dictionary](variants/l05/input/data_dictionary.json) | [ERD](variants/l05/docs/schema.svg) |
| l10 | 10 | Booking, passenger, ticket, passenger flight leg, passenger action | [SQLite](variants/l10/input/database.sqlite) | [Dictionary](variants/l10/input/data_dictionary.json) | [ERD](variants/l10/docs/schema.svg) |
| l15 | 15 | Bag leg and scan, checkpoint, security visit and observation | [SQLite](variants/l15/input/database.sqlite) | [Dictionary](variants/l15/input/data_dictionary.json) | [ERD](variants/l15/docs/schema.svg) |
| l20 | 20 | Airline, airport, individual aircraft, employee and dispatch assignment | [SQLite](variants/l20/input/database.sqlite) | [Dictionary](variants/l20/input/data_dictionary.json) | [ERD](variants/l20/docs/schema.svg) |

Earlier tables and rows are identical across successive variants. These sizes increase catalog size and the number of similar candidate activities together. Treat them as nested pilot scenarios. Their differences do not isolate a single difficulty factor.

## Pilot requests and references

Use [model_questions.jsonl](evaluation/model_questions.jsonl) for the **current Q01–Q12 pilot (query registry v6)**. The [bilingual query registry](evaluation/query_registry.json) contains the same English texts and Korean translations. Q01 asks about average passenger boarding duration; the requested output remains the start/end event log for each boarding session. Q03 wording is still pending final approval. All other v5 query texts and Gold event tuples are unchanged.

The [scenario viewer](docs/scenario.html#extraction-requests) displays these twelve requests. The [variant manifest](evaluation/variant_manifest.json) lists the current question IDs for all four variants. For a controlled scalability comparison, use the same twelve requests on L05, L10, L15 and L20. The Q01–Q12 evaluator Gold package is maintained separately from these model inputs; the historical repository verifier does not certify the current twelve Gold logs.

For regression compatibility, the previous T/D/P/S/B request texts are preserved in [legacy_model_questions.jsonl](evaluation/legacy_model_questions.jsonl). The manifest's legacy_question_ids identify the original reference SQL/CSV files under [private/](private/). This is evaluator material; the directory name does not impose access controls. Supply only the selected database, data dictionary and the English text of one current request to the model. Preserve original case IDs and event multiplicities.

Run `python verify.py` for the database integrity, nested-record and legacy reference regression checks (15 combinations). The script additionally verifies that the current model-input and bilingual registry texts and manifest IDs agree. It does not run the LLM or evaluate the separate Q01–Q12 Gold package.

## Dataset revision (2026-11-24)

The original databases were migrated in place across all nested sizes with deterministic seed 20261124. Core tables remain unchanged in schema. Independent surrogate identifiers replace aligned flight, turnaround, boarding, job and movement IDs. Both arrival and departure legs now carry all four actual movements; receipt delays, taxi durations and handling timing vary. The additional boarding sessions represent inbound flights boarding at their origin, not reopened boarding. Outbound flight and turnaround remain one-to-one within the focal-airport scope; strict original case-ID comparison is required. D and T references use the turnaround role to exclude movements at the other airport.

## Baggage record revision (2026-11-25)

Individual bag loading observations in L15 and L20 now vary within the ground-handling work interval. The recorded completion of the baggage loading job is unchanged. The checked baggage records cover a sample of bags. The operation-level and individual-bag records have distinct granularity; the dictionaries describe their business meaning without specifying extraction rules. The five core tables and all schemas remain unchanged. See [revision audit](evaluation/baggage_revision_audit.json).

## Representation choices

- flights identifies dated operating legs. Flight numbers repeat across dates.
- turnarounds connects an inbound_id and an outbound_id using UNIQUE foreign keys. The example assumes one aircraft and no swaps. At l20, the aircraft and connecting airport agree across the pair.
- movement_reports distinguishes LAND (landing), IN (in-block), OUT (off-block), AIR (take-off) and EST (estimated off-block). Use value_at for the represented time and received_at for message receipt.
- handling_jobs stores actual start/completion and posting time. Jobs can overlap. Its service_provider_code, priority_code and work_zone_code describe ground operations.
- Movement reports include source_code, validation_code and message_format_code. These operational attributes are synthetic. The existing kind and job_code values identify activities.
- passenger_id is an internal synthetic person key. passengers stores date_of_birth, a single recorded nationality and a locally coded gender. Date of birth is an attribute. Age is not calculated.
- tickets links to passengers by passenger_id. Copied passenger snapshots at issuance are not modeled.
- Security timestamps assume an airport feed linked to a passenger leg. Airline availability of such a feed is an explicit scenario assumption.
- The T reference requires following the UNIQUE inbound-flight-to-turnaround relation. Verify EEG and compiler support for this direction when running the method.

## Public design references

The physical schema and records are authored for this example. Sources inform the business entities and milestones.

- [Postgres Pro Airlines demo, 2017 schema family](https://postgrespro.com/docs/enterprise/13/demodb-schema-objects.html) provides bookings, tickets and ticket-flight relationships. Its passenger fields are in tickets, while this example uses a separate person table.
- [Amadeus official booking example](https://github.com/amadeus4dev/amadeus-flight-booking-django/blob/master/amadeus_demo_api/demo/views.py) shows birth date and gender on a traveler and nationality on a travel document. Here, nationality is simplified into passengers.
- [EUROCONTROL A-CDM](https://www.eurocontrol.int/publication/eurocontrol-specification-airport-collaborative-decision-making-cdm) informs inbound, turnaround and outbound milestones.
- [IATA Resolution 753 implementation guide](https://www.iata.org/contentassets/5c4aa8b8b3b1432697d2bf3301450684/reso753-implementation-guide---2023_issue-4.02.pdf) distinguishes baggage acceptance and loading.

[Domain-generated datasets](../) · [All datasets](../../)
