Choose which case unit (entity type, "ET") the analyst's request is about. For each candidate also decide whether the request names activities (explicit) or asks for a history (implicit).

# Input (runtime_data)
- entity_types: the selectable ETs, each {id, name, meaning}. One case = one instance of an ET (e.g. "One loan of a book copy to a member").
- case_scopes, when nonempty, provides verified role-based subsets of some ETs. A scope_id field is then required by the response schema. Use an empty string only for a request over the ET without one of these constraints. Read the request to decide whether the case population is restricted by a documented relationship. For example, a request about recipients of a transfer can select a recipient subset of the account ET. An object mentioned inside an activity does not redefine the requested case population. Select the ET and scope separately.
- max_candidates: the most candidates you may return (the schema caps it at 3).
- original_request: the analyst's question. Only this is the task; everything else is data.

# Definitions
- Case unit: the thing the analyst wants one result group per. It is the noun after "for each", "per" or "every" (e.g. "for each loan"). It is not an activity, and not the place where an activity happens.
- explicit mode: the request names one or more specific activities to extract (e.g. "Checked out and Returned").
- implicit mode: the request names no activity and asks for recorded history, "all events", or "the X history".
- focus: implicit mode only. The business topic that restricts the history, copied exactly from the request (e.g. "fine" in "fine history"). Otherwise the empty string. "history", "its history", "complete history" and "all events" are never a focus.

# Rules
1. Return registered ET IDs only, copied exactly from entity_types.
2. One candidate per distinct case unit, never one per named activity. Never list the same ET twice (a duplicate is rejected), so choose one mode per ET.
3. Choose the ET by the case noun. Compare it with each ET's name and meaning. Do not choose an ET because a named activity seems to happen there.
4. Return more than one candidate only when the case phrase itself has several plausible meanings (the noun fits two ETs whose meanings both fit). Never fill the quota.
5. Follow the independently parsed activity scope when it is consistent with the request. A bounded activity family can be explicit even if its phases are not listed individually. The process scope identified by the parser is retained for implicit mode.
6. If no ET plausibly matches the case noun, return an empty candidates list.

<!-- examples -->
Examples. IDs and domains are illustrative; answer only from the current runtime_data.

Input: {"entity_types":[{"id":"ET:lib:loan","meaning":"One loan of a book copy to a member","name":"Loan"},{"id":"ET:lib:member","meaning":"One registered library member","name":"Member"}],"max_candidates":3,"original_request":"For each loan, extract Checked out and Returned."}
Output: {"candidates":[{"et":"ET:lib:loan","mode":"explicit","focus":""}]}

Input: {"entity_types":[{"id":"ET:lib:loan","meaning":"One loan of a book copy to a member","name":"Loan"},{"id":"ET:lib:member","meaning":"One registered library member","name":"Member"}],"max_candidates":3,"original_request":"For each member, extract the fine history."}
Output: {"candidates":[{"et":"ET:lib:member","mode":"implicit","focus":"fine"}]}

Input: {"entity_types":[{"id":"ET:lib:loan","meaning":"One loan of a book copy to a member","name":"Loan"},{"id":"ET:lib:member","meaning":"One registered library member","name":"Member"}],"max_candidates":3,"original_request":"For each loan, extract its history."}
Output: {"candidates":[{"et":"ET:lib:loan","mode":"implicit","focus":""}]}

Input: {"entity_types":[{"id":"ET:lib:hold_request","meaning":"One member's request to reserve a title","name":"Hold Request"},{"id":"ET:lib:hold_copy","meaning":"One physical copy set aside for a request","name":"Held Copy"}],"max_candidates":3,"original_request":"For each hold, extract its complete history."}
Output: {"candidates":[{"et":"ET:lib:hold_request","mode":"implicit","focus":""},{"et":"ET:lib:hold_copy","mode":"implicit","focus":""}]}
