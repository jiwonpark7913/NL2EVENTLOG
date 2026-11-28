Decide how to handle ONE diagnostic finding on an executed extraction specification: keep the current physical rule, leave the finding unresolved, or propose exactly one of the listed repair candidates. You only choose; code applies the repair, re-executes it and may still reject it. Do not write SQL and do not invent rules or IDs.

# Input (plain JSON)
- request: the analyst's question.
- pi: the frozen interpretation: case (entity type ID), selected_definitions, activities, focus. You cannot change it.
- finding: the single finding to decide on. id is always "D1". check is a code such as live_attribution, timestamp_binding, selected_clock_drift or singleton_cases. severity is "violation" (a confirmed error) or "signal" (a pattern that may be normal). impact only ranks findings; it proves nothing.
- es: a short summary of the case table and case selection.
- candidates: C* -> card. Each card replaces one physical field of existing rules: operation (replace_attribution_path or replace_timestamp), current_field (what is used now), field (the replacement), definition and rule_ids (which selected event it affects), basis (why the EEG lists it), evidence_ids (its own pair: one W* and one E*). Candidate numbers can have gaps.
- evidence.W* (source-row witness): sample source rows, keyed by occurrence, each with "old" (current rule) and "new" (this candidate) projections: cid = case ID as a JSON string, or null when the row reaches no case; stamp = occurrence time, or null; ref_state = matched / null_reference / unmatched_reference. A sample, not a proof.
- evidence.E* (EEG evidence): ids (original EEG IDs), meaning (activity signature, dictionary statements, the frozen activity), role_evidence (documented statements about which relationship role the path represents; often empty).

# Definitions
- Frozen: the case entity type and case population, the selected activities and their occurrence granularity, and each event's source table, key and row predicate. Only the attribution path or the occurrence-time expression of an existing rule may change.
- Recover the rows: in the witness, "new" gives each row a non-null cid with ref_state matched.
- Disagree on case: two path candidates both recover the same rows but give some row different cids.
- Role: which relationship a path represents (e.g. "the loan the return belongs to" versus "a loan referenced for another reason"). Several paths can reach the same case table in different roles.

# Decide in this order
1. Pick only candidates that address finding D1 and affect the selected events.
2. Attribution path candidates: a candidate is supported when its witness recovers rows that the current rule loses (old cid null, or outside the case table) AND its E* role_evidence or dictionary statements say this path is the role the case needs. If two path candidates disagree on case and neither the request nor the dictionary identifies the role, answer UNRESOLVED / insufficient_evidence. The same two candidates become a PATCH as soon as one of them has a role statement saying it is the case's relationship. Never decide the role from row counts (recovering more rows is not proof) or from column names such as id, ref, type, parent, or a name that resembles the case noun.
3. Timestamp candidates: supported only when the E* dictionary or signature says the new expression records when the selected activity actually happened, and the current one is a different clock (recording, loading, scheduling) or is missing. A new stamp of null means the event would lose its time; count that against the candidate.
4. PATCH when exactly one candidate is supported. Choose by evidence, never by a nicer process shape.
5. KEEP / explained only for a signal that the request or the evidence explains as normal (e.g. one requested activity gives one event per case; an activity can truly have no events), or when no candidate is better supported than the current rule. KEEP never clears a violation; for a violation that no candidate fixes, use UNRESOLVED.
6. UNRESOLVED / needs_pi_change when the evidence shows that no physical repair can work because the frozen interpretation itself is wrong: the rows belong to a different entity type or the event is a different activity. This only flags Step 2; it changes nothing.
7. UNRESOLVED / insufficient_evidence for everything else: missing, conflicting or role-ambiguous evidence.

# Output (strict; any violation makes the proposal invalid and ends repair)
Return {"proposal": {...}} with exactly these keys:
- decision: "PATCH", "KEEP" or "UNRESOLVED".
- diagnostic_id: "D1". hypothesis_code: copy finding.check exactly.
- PATCH: operation = the chosen card's operation; candidate_id = its C* key; evidence_ids = exactly that card's evidence_ids (its W* and its E*, nothing else, no other candidate's evidence); reason_code = null.
- KEEP: operation null, candidate_id null, evidence_ids [], reason_code "explained".
- UNRESOLVED: operation null, candidate_id null, evidence_ids [], reason_code "insufficient_evidence" or "needs_pi_change".
null means JSON null, not the string "null". There is no free-text field.