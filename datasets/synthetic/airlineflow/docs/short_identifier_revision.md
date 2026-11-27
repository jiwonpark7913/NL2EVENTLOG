# Short identifier revision

All generated entity identifiers and bag tags use deterministic, collision-free numeric aliases with an entity prefix and 4–5 digits. A separate seeded random stream assigns aliases without changing the underlying operational simulation. Actual airport codes, flight numbers, timestamps, carrier values, relationships, and event occurrence multiplicities remain unchanged. The previous version is retained in Git history.

Flight number is not a primary key: it can repeat across operating dates. The canonical event log remains case_id, activity, timestamp. The review HTML adds flight number and scheduled operating date as display-only metadata. For turnaround-wide ground service events both related flights are shown.

Release checks require equality of all source rows and all 72 Gold multisets (including source occurrence identity) after bijective remapping, followed by 108 SQLite comparisons and HTML evidence checks. No method or query wording change is intended. Production scoring and human review remain separate.
