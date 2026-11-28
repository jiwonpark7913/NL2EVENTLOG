Resolve the unresolved requirements for the selected case. Use only original_request and the supplied EEG cards. Evaluate each pending requirement independently. The controller keeps the verified requirements fixed and sends any edit through a new independent review.

# Input
- original_request is the analyst's full request.
- case and case_scope fix the case identity and any documented role restriction.
- unresolved_requirements contains the only editable IDs. review_findings describes the previous verdict, candidates and reason codes.
- activities contains the ED IDs and their occurrence meaning, clock and role evidence. An offered ID can still be semantically wrong for this request.
- verified_requirement_ids records prior verifications. Do not propose edits for those IDs.

# Output
Return edits only for requirements that can be resolved from the supplied evidence. Each edit contains requirement_id, span, meaning, qualifiers, coverage, granularity and event_definition_ids. Use only IDs supplied in activities. Return {"edits":[]} if every pending item remains unsupported or genuinely ambiguous.

Copy span verbatim from the original request. A full phrase can support several requirement meanings. Re-read the whole clause to resolve shared nouns and modifiers, including common phase words that govern multiple activities. Meaning can state the resolved occurrence in plain language. Preserve timing and role constraints in qualifiers. Treat complementary milestones from a requested plural group as coverage "all"; selecting endpoints alone is insufficient when the request includes intervening milestones. Keep one named activity as coverage "one". Include each compatible ED needed, using its canonical identity. Changing a requirement's meaning, scope or qualifier can resolve it even when the correct ED was already proposed.

<!-- examples -->
If the request says "Include completion of calibration and cleaning" and R2 is the unresolved cleaning item, use "completion of calibration and cleaning" as span, "Cleaning is completed" as meaning, qualifiers ["completion"], and the documented cleaning completion ED. The cleaning start is a separate phase.
