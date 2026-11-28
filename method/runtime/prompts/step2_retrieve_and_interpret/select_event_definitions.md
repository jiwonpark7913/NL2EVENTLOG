Propose event definitions for each activity the analyst explicitly requests.

# Input
- original_request is the analyst's question.
- activity_requirements gives each stable requirement ID, exact source span, intended meaning and qualifiers.
- case is the chosen entity type. Each activities card provides an event definition ID, the occurrence and time evidence, verified case roles, and requirement_ids allowed by the case-role checks.

# Output
Return matches containing {requirement_id, event_definition_ids}. Use each requirement ID at most once and use only eligible definition IDs shown for that requirement. Match the occurrence and its timing: a scheduled timestamp, message receipt, start, and completion describe different events. Match business meaning across synonyms. Respect the request's subject roles and modifiers. Omit requirements without a suitable definition. For coverage=all select every complementary ED that belongs to the family, including intermediate events inside requested phase boundaries. When granularity is distinct, select definitions that distinguish the required members. When it is coarse, select all complementary definitions that cover the requested scope. Preserve each selected definition and its canonical activity. Keep occurrence type, clock, and row coverage aligned. For coverage=one, multiple plausible matching definitions indicate unresolved alternatives.

<!-- examples -->
For requirements R1 Checked out and R2 Returned, matching ED:lib:checkout and ED:lib:return, return:
{"matches":[{"requirement_id":"R1","event_definition_ids":["ED:lib:checkout"]},{"requirement_id":"R2","event_definition_ids":["ED:lib:return"]}]}

If only the checkout is supported, return:
{"matches":[{"requirement_id":"R1","event_definition_ids":["ED:lib:checkout"]}]}
