A reviewer reported differences between a proposed process selection and the analyst's request. Decide whether to keep the selection, change it, or abstain. Use only the request, the current selection, the reported differences, the EEG paragraph and the supplied retrieved_evidence.

# Input (runtime_data)
- original_request: the analyst's question (the only task).
- differences: reported problems, each {kind, target, reason}. Some may be structural warnings from deterministic checks.
- eeg_summary: the complete business paragraph that defines the allowed aliases: ET1, ET2... (case types) and A1, A2... (activities, each listed with the case types it belongs to).
- selection: et, mode, focus, ids (current), classifications, and allowed_by_et (for each ET alias, the A aliases allowed under it). An "X" alias is a current reference that can be removed but never newly added.
- retrieved_evidence: literal semantic sources, candidate-only. Retrieval does not approve attribution or identity; missing or truncated retrieval is not proof that an event is absent.

# Decide
For each difference ask: is the reviewer right?
- keep: every difference is wrong, the current selection already fulfils the request, and no difference is a structural failure.
- change: at least one difference is right. Return the complete corrected selection.
- abstain: the evidence is insufficient or the request is truly ambiguous (e.g. a requested activity exists under no alias, or two case types fit equally). Return et, mode and focus as currently selected, ids [] and resolutions [].
Only two revision proposals exist per run, shared by all candidates. Do not gamble: abstain rather than guess.

# keep checklist (machine-checked; any failure rejects the answer)
1. et, mode, focus and ids are identical to the current selection.
2. resolutions has one entry for EVERY reported difference: {kind, target, span, reason}, kind and target copied from that difference.
3. span is an exact substring of original_request (case-sensitive) that shows why the selection is already right.
4. reason says why the difference does not hold.
A structural failure can never be discharged by keep; change the selection or abstain.

# change checklist
1. Use only ET and A aliases from the paragraph.
2. First choose et, then check that every id is in allowed_by_et for that et. An alias that is not a member of the proposed et is rejected, including when you switch et.
3. Return the full proposed ids, not a delta. For a whole-history request use mode implicit, focus "" and ids []; the controller recomputes the supported events.
4. Do not manufacture a focus. A focus must be an exact substring of the request. Keep the current mode unless the request supports correcting it.
5. resolutions may be [].
6. Do not create new definitions and do not alter the case population.

If you quote evidence in a reason, the quote must be an exact substring of the evidence text.

When unresolved_requirements is supplied, use those stable IDs as unmatched targets. Revisit only those items on the current case. Confirmed items (verified_ids) stay selected. Switch cases only to resolve a supported case mismatch. Return abstain if the missing item or the required role attribution cannot be supported from the existing EEG. A keep resolution does not verify an unresolved activity.

<!-- examples -->
Examples (retrieved_evidence omitted). Aliases and domains are illustrative.

Input: {"differences":[{"kind":"unmatched","reason":"No selected activity describes the copy being brought back.","target":"R2"}],"eeg_summary":"ET1 Loan One loan of a book copy to a member. ET2 Member One registered library member. A1 Checked out (ET1, ET2). A2 Returned (ET1, ET2). A3 Fine assessed (ET2).","original_request":"For each loan, extract Checked out and Returned.","selection":{"allowed_by_et":{"ET1":["A1","A2"],"ET2":["A1","A2","A3"]},"classifications":{},"et":"ET1","focus":"","ids":["A1"],"mode":"explicit"}}
Output: {"action":"change","et":"ET1","mode":"explicit","focus":"","ids":["A1","A2"],"resolutions":[]}

Input: {"differences":[{"kind":"unrequested","reason":"The review could not match the second activity to a request phrase.","target":"A2"}],"eeg_summary":"ET1 Loan One loan of a book copy to a member. ET2 Member One registered library member. A1 Checked out (ET1, ET2). A2 Returned (ET1, ET2). A3 Fine assessed (ET2).","original_request":"For each loan, extract Checked out and Returned.","selection":{"allowed_by_et":{"ET1":["A1","A2"],"ET2":["A1","A2","A3"]},"classifications":{},"et":"ET1","focus":"","ids":["A1","A2"],"mode":"explicit"}}
Output: {"action":"keep","et":"ET1","mode":"explicit","focus":"","ids":["A1","A2"],"resolutions":[{"kind":"unrequested","target":"A2","span":"Returned","reason":"The request names Returned, which is this activity."}]}

Input: {"differences":[{"kind":"case_mismatch","reason":"The request groups by member, not by loan.","target":"ET1"},{"kind":"unmatched","reason":"The selected set lacks the fine activity.","target":"Fine assessed"}],"eeg_summary":"ET1 Loan One loan of a book copy to a member. ET2 Member One registered library member. A1 Checked out (ET1, ET2). A2 Returned (ET1, ET2). A3 Fine assessed (ET2).","original_request":"For each member, extract Fine assessed.","selection":{"allowed_by_et":{"ET1":["A1","A2"],"ET2":["A1","A2","A3"]},"classifications":{},"et":"ET1","focus":"","ids":["A1"],"mode":"explicit"}}
Output: {"action":"change","et":"ET2","mode":"explicit","focus":"","ids":["A3"],"resolutions":[]}

Input: {"differences":[{"kind":"unmatched","reason":"No selected activity describes a renewal.","target":"R2"}],"eeg_summary":"ET1 Loan One loan of a book copy to a member. ET2 Member One registered library member. A1 Checked out (ET1, ET2). A2 Returned (ET1, ET2). A3 Fine assessed (ET2).","original_request":"For each loan, extract Checked out and Renewed.","selection":{"allowed_by_et":{"ET1":["A1","A2"],"ET2":["A1","A2","A3"]},"classifications":{},"et":"ET1","focus":"","ids":["A1"],"mode":"explicit"}}
Output: {"action":"abstain","et":"ET1","mode":"explicit","focus":"","ids":[],"resolutions":[]}
