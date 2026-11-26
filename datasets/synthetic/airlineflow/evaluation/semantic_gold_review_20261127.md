# AirlineFlow — Semantic Gold review (2026-11-27 KST)

## Scope and decision

Reviewed fixture: `e98f51c8602c12620baa028b99396522b7613171` (TemporalRevision1-SemanticDD1-CanonicalQ02).
This is an evaluator-side review, not an author approval or a new dataset freeze.
Q02 has the researcher's previously recorded approval. For all other requests this review recommends retaining the current reference logs; final researcher approval remains pending. No model inference, runtime EEG, predicted PI, or predicted SQL was used. No question, database, dictionary, Gold SQL, CSV, ESpec, or evaluation protocol was modified by this review.

## Review plan and completed checks

1. Read the 72 query registry entries, public dictionary, schema context and all 72 reference SQL files. Check the requested case, population, activity semantics/granularity, actual timestamp, source filters, and role-specific attribution.
2. Independently reconstruct the expected event triples directly from canonical `source/records.json` in JavaScript using per-query business selections and key mappings. Do not execute or parse Gold SQL to construct expected rows. Compare sorted multisets, preserving multiplicity, to the 72 `gold/Qxx/events.csv` files.
3. Check source population and discriminator counts and inspect the implicit interpretation alternatives. Separate semantic review from technical execution and author approval.
4. Only change a reference if an independently established requirement disagrees with it. Do not change a correct reference to fit a model prediction.

## Results

All 72 reference SQL files were reviewed; all 72 independent record reconstructions matched their Gold CSV exactly (32,208 event records over the 72 unique requests, counted with multiplicity). Pilot: 12/12, 3,120 records; Test: 60/60, 29,088 records. This is a direct reconstruction from the shared canonical records, not a new execution against the four SQLite binaries. The upstream verification receipt reports 108/108 SQLite-query comparisons; rerun `python verify.py` against the downloaded release before an evaluation freeze. No new SQLite execution or model calls were performed here.

| Group | IDs | Independent CSV comparison | Event rows | Recommendation |
|---|---|---:|---:|---|
| Pilot | Q01–Q12 | 12/12 | 3,120 | Q02 approved; retain remaining 11 subject to researcher approval |
| A Attribution Depth | Q13–Q24 | 12/12 | 6,192 | Retain |
| B Source Diversity | Q25–Q36 | 12/12 | 5,760 | Retain |
| C Activity Count | Q37–Q48 | 12/12 | 5,424 | Retain |
| D Semantic Complexity | Q49–Q60 | 12/12 | 10,560 | Retain primary reference; confirm predeclared alternative policy |
| E Attribution Role | Q61–Q72 | 12/12 | 1,152 | Retain |

## Canonical activity contract for the reference benchmark

Derived from query intent and the public dictionary, not from a method-produced EEG. Canonical labels are reference names, not required output strings. A semantically equivalent label is eligible for the common scoring procedure. Do not add all possible events when a request specifies a subset, and do not conflate event granularity with case granularity.

| Source | Predicate / semantic unit | Occurrence clock | Reference activity |
|---|---|---|---|
| handling_jobs | DP | started_at / finished_at | Disembarkation Start / Disembarkation Complete |
| handling_jobs | UL | started_at / finished_at | Baggage Unloading Start / Baggage Unloading Complete |
| handling_jobs | CL | started_at / finished_at | Cabin Cleaning Start / Cabin Cleaning Complete |
| handling_jobs | FU | started_at / finished_at | Refuelling Start / Refuelling Complete |
| handling_jobs | CA | started_at / finished_at | Catering Loading Start / Catering Loading Complete |
| handling_jobs | BL | started_at / finished_at | Baggage Loading Start / Baggage Loading Close |
| boarding_sessions | session | started_at / closed_at | Boarding Start / Boarding Close |
| turnarounds | coordination / readiness | handling_started_at / ready_at | Handling Start / Aircraft Ready |
| movement_reports | LAND / IN / OUT / AIR | value_at | Landing / In-block / Off-block / Take-off |
| passenger_actions | CK / BD / RJ | action_at | Check-in Complete / Passenger Boarding Confirmed / Scan Rejected |
| security_events | Q / S / C | observed_at | Queue Entry / Screening Start / Screening Complete |
| bag_scans | B101 / B204 | scanned_at | Bag Accepted / Bag Loaded |

These 28 activity labels cover the selected reference activities, not the complete database event universe. The six handling job types each have 48 rows; Q02 yields 288 job cases and 576 events with 12 labels. Do not add posted_at as a work phase or replace actual movement times by scheduled or estimated times. Receipt/posting clocks may describe independent communication events when explicitly relevant, but no current reference asks for them. Individual bag loading is different from the ground-service loading operation closing. Passenger boarding confirmation is different from flight-level boarding session start/close. Role is a case attribution constraint, not automatically an activity label.

## Query-level review ledger

All rows below passed the independent CSV multiset comparison. Counts refer to a single reference, not repeated schema levels. R = recommend retain (human approval pending); A = researcher approval previously recorded; R* = retain with interpretation-policy note.

| ID | Case / intended scope | Activity or selection rationale | Events | Decision |
|---|---|---|---:|---|
| Q01 | Boarding Session, all 96 | Session start/close | 192 | R |
| Q02 | Handling Job, all 288 | Six job types, actual start and finish; no posting | 576 | A |
| Q03 | Outbound Flight | Session start/close, BL close, ready, actual OUT | 240 | R |
| Q04 | Turnaround | Inbound LAND/IN, coordination start, six job completions, outbound session start/close, ready, OUT/AIR | 672 | R |
| Q05 | Turnaround | Coordination start, CL/FU complete, ready | 192 | R |
| Q06 | Outbound Flight | Session start/close, OUT/AIR | 192 | R |
| Q07 | Outbound Flight | UL/CL/FU/CA/BL completions in preparing turnaround; no DP because not requested | 240 | R |
| Q08 | Turnaround | Inbound LAND/IN and outbound OUT/AIR only | 192 | R |
| Q09 | Outbound Flight | OUT/AIR, implicit case | 96 | R* |
| Q10 | Dated outbound Flight | Session start/close and OUT; not flight number alone | 144 | R |
| Q11 | Boarding Session, all 96 | Session start/close, not passenger actions | 192 | R |
| Q12 | Outbound Flight | Session start/close and OUT/AIR, implicit case | 192 | R* |
| Q13 | Bag Leg | B101/B204 | 288 | R |
| Q14 | Passenger Leg | B101/B204 attributed through bag leg | 288 | R |
| Q15 | Flight | B101/B204 via bag and passenger legs | 288 | R |
| Q16 | Security Visit | Q/S/C | 864 | R |
| Q17 | Passenger Leg | Q/S/C via visit | 864 | R |
| Q18 | Flight | Q/S/C via visit and passenger leg; preserve repeated triples | 864 | R |
| Q19 | Passenger Leg | CK/BD | 576 | R |
| Q20 | Ticket | CK/BD via passenger leg | 576 | R |
| Q21 | Booking | CK/BD via leg and ticket | 576 | R |
| Q22 | Passenger Leg | BD/RJ | 336 | R |
| Q23 | Ticket | BD/RJ, including cases with no RJ | 336 | R |
| Q24 | Booking | BD/RJ, including cases with no RJ | 336 | R |
| Q25 | Turnaround | CL/FU/CA/BL complete, outbound session start/close | 288 | R |
| Q26 | Turnaround | CL/FU complete, outbound session start/close, OUT/AIR | 288 | R |
| Q27 | Turnaround | CL/FU complete, outbound session close, ready, OUT/AIR | 288 | R |
| Q28 | Turnaround | DP/UL/CL/FU complete, outbound session start/close | 288 | R |
| Q29 | Turnaround | DP/UL complete, inbound LAND/IN, outbound session start/close | 288 | R |
| Q30 | Turnaround | DP/UL complete, inbound LAND/IN, outbound session start, coordination start | 288 | R |
| Q31 | Outbound Flight | Individual screening start/complete and session start/close | 672 | R |
| Q32 | Outbound Flight | CK, screening complete, session start/close | 672 | R |
| Q33 | Outbound Flight | CK, screening complete, session close, ready | 672 | R |
| Q34 | Outbound Flight | Queue entry, screening complete, session start/close | 672 | R |
| Q35 | Outbound Flight | Screening complete, individual BD, session start/close | 672 | R |
| Q36 | Outbound Flight | Screening complete, individual BD, session close, ready | 672 | R |
| Q37 | Turnaround | CL start/complete | 96 | R |
| Q38 | Turnaround | CL/FU start/complete | 192 | R |
| Q39 | Turnaround | CL/FU/CA/BL start/complete | 384 | R |
| Q40 | Turnaround | All six job types, 12 phases (same definition set as Q02, different case) | 576 | R |
| Q41 | Turnaround | BL close and outbound OUT | 96 | R |
| Q42 | Turnaround | BL start/close, outbound OUT/AIR | 192 | R |
| Q43 | Turnaround | CL/FU/BL start/complete, outbound OUT/AIR | 384 | R |
| Q44 | Turnaround | DP/CL/FU/CA/BL start/complete, outbound OUT/AIR | 576 | R |
| Q45 | Outbound Flight | CL complete, individual BD | 336 | R |
| Q46 | Outbound Flight | CL start/complete, CK/BD | 672 | R |
| Q47 | Outbound Flight | CL/FU/CA start/complete, CK/BD | 864 | R |
| Q48 | Outbound Flight | UL/CL/FU/CA/BL start/complete, CK/BD | 1,056 | R |
| Q49 | Bag Leg | B101/B204 | 288 | R |
| Q50 | Bag Leg | Implicit handling journey, B101/B204 | 288 | R |
| Q51 | Bag Leg | B101/B204, implicit case | 288 | R* |
| Q52 | Bag Leg | B101/B204, implicit case and activity | 288 | R* |
| Q53 | Security Visit | Q/S/C | 864 | R |
| Q54 | Security Visit | Implicit waiting/screening, Q/S/C | 864 | R |
| Q55 | Security Visit | Q/S/C, implicit case | 864 | R* |
| Q56 | Security Visit | Q/S/C, implicit case and activity | 864 | R* |
| Q57 | Passenger Leg | CK/Q/S/C/RJ/BD | 1,488 | R |
| Q58 | Passenger Leg | Same six activities, including failed scan attempts | 1,488 | R |
| Q59 | Passenger Leg | Same six activities, implicit case | 1,488 | R* |
| Q60 | Passenger Leg | Same six activities, implicit case and activity | 1,488 | R* |
| Q61 | Turnaround | Inbound LAND/AIR | 96 | R |
| Q62 | Turnaround | Outbound LAND/AIR | 96 | R |
| Q63 | Turnaround | Inbound LAND, outbound AIR | 96 | R |
| Q64 | Turnaround | Inbound IN/OUT | 96 | R |
| Q65 | Turnaround | Outbound IN/OUT | 96 | R |
| Q66 | Turnaround | Inbound IN, outbound OUT | 96 | R |
| Q67 | Turnaround | Inbound session close and LAND | 96 | R |
| Q68 | Turnaround | Outbound session close and LAND | 96 | R |
| Q69 | Turnaround | Inbound LAND, outbound session close | 96 | R |
| Q70 | Turnaround | Inbound session start and IN | 96 | R |
| Q71 | Turnaround | Outbound session start and IN | 96 | R |
| Q72 | Turnaround | Inbound IN, outbound session start | 96 | R |

## Remaining evaluator decisions (not changes to Gold triples)

- Q09/Q12: retain the registered implicit-case secondary/diagnostic treatment for turnaround and session representations; a verified representation of the same canonical case should not be penalized solely for an internal ET label. A different business object merely having a 1:1 relationship does not establish identity.
- Q51/Q52: Bag Leg is the primary per-flight baggage unit. The current fixture has 144 distinct bag tags, 144 bag legs and 144 distinct passenger legs with bags. Tag-only (Bag) secondary and Passenger Leg diagnostic treatment are already registered; this observed 1:1 is not proof of semantic identity.
- Q55/Q56: Security Visit primary. Passenger Leg secondary only under the registered full-scope bijection and exact-log condition. The fixture has 288 visits and 288 distinct associated legs.
- Q59/Q60: per-passenger per-flight processing is the intended unit. Passenger/Ticket alone would aggregate multiple legs; keep Passenger Leg primary and verified same-entity alternate keys. Do not make the implicit cases explicit merely to simplify the task.
- The fixture's standalone normalize_case_keys.py and verify.py describe an older ET-sensitive policy. Do not silently replace the final production end-to-end scorer with this reference utility. The researcher's final policy scores validated case IDs, canonical activity and time multisets; ET/ED/PI/ES correctness is diagnostic. Verify integration locally using the actual frozen evaluator; the local runtime and its latest freeze were not independently accessible during this audit.
- Q04 and Q08 have coarse activity requirements, and their registry mode is implicit while the paper's Q08 illustration labels it explicit. This is a taxonomy/documentation discrepancy, not a wrong Gold triple. Resolve the naming convention separately, without changing the requests after model results are seen.
- A, B, C vary additional properties besides their nominal axis; treat them as sensitivity analyses, not isolated causal effects. Role E is categorical. Test queries contain repeated Gold groups and share source occurrences with Pilot; do not claim all are statistically independent observations.

## Release status

Recommendation: no further activity-label or event-row changes after approved CanonicalQ02. Preserve the 72 query texts and primary Gold files. This audit is evidence for researcher review, not authorization to start Test inference. Author approval, production evaluator integration on the current download, independent SQLite execution of the 108 manifest combinations, and any additional E2 test-schema combinations remain separate checks. All actions above were evaluator-side.