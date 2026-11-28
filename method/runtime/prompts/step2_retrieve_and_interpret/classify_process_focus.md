The analyst asked for the history of a business topic (the focus) for each case. Decide, for each activity group, whether that activity belongs to the focus.

# Input (runtime_data)
- activities: groups of event definitions that mean the same business activity. Each group has an id (its representative ID), name, meaning and definitions (all physical definitions in the group).
- case: the chosen entity type. focus: the exact focus wording from the request. original_request: the analyst's question.

# Output
decisions: exactly one {id, decision} per group, using the group's representative ID copied exactly. The decision covers every definition in the group.

# Decisions
- INCLUDE: the activity is the focus process itself: it starts it, is a step in it, advances it, or is its outcome.
- EXCLUDE: the activity belongs to another process, or merely happens before or after the focus process, or only involves the same case, people or objects.
- UNCERTAIN: the answer depends on an assumption that neither the focus nor the activity's meaning states. Do not use UNCERTAIN to avoid deciding: every UNCERTAIN forces an extra review round, and the activity is left out meanwhile.

# Rules
1. Judge business meaning (name and meaning), not word overlap with the focus.
2. Being attributable to the case is not evidence of belonging to the focus.
3. The focus narrows which activities are relevant. It never narrows which cases exist.

<!-- examples -->
Examples. IDs and domains are illustrative; answer only from the current runtime_data.

Input: {"activities":[{"definitions":[{"id":"ED:lib:reserve","meaning":"A member reserved a title.","name":"Reserved"}],"id":"ED:lib:reserve","meaning":"A member reserved a title.","name":"Reserved"},{"definitions":[{"id":"ED:lib:checkout","meaning":"A member borrowed a copy.","name":"Checked out"}],"id":"ED:lib:checkout","meaning":"A member borrowed a copy.","name":"Checked out"},{"definitions":[{"id":"ED:lib:fine","meaning":"A late fee was charged to the member.","name":"Fine assessed"}],"id":"ED:lib:fine","meaning":"A late fee was charged to the member.","name":"Fine assessed"},{"definitions":[{"id":"ED:lib:fine_paid","meaning":"The member paid a late fee.","name":"Fine paid"}],"id":"ED:lib:fine_paid","meaning":"The member paid a late fee.","name":"Fine paid"},{"definitions":[{"id":"ED:lib:return","meaning":"A member brought a copy back.","name":"Returned"}],"id":"ED:lib:return","meaning":"A member brought a copy back.","name":"Returned"}],"case":{"id":"ET:lib:loan","meaning":"One loan of a book copy to a member","name":"Loan"},"focus":"fine","original_request":"For each loan, extract its fine history."}
Output: {"decisions":[{"id":"ED:lib:reserve","decision":"EXCLUDE"},{"id":"ED:lib:checkout","decision":"EXCLUDE"},{"id":"ED:lib:fine","decision":"INCLUDE"},{"id":"ED:lib:fine_paid","decision":"INCLUDE"},{"id":"ED:lib:return","decision":"EXCLUDE"}]}

Input: {"activities":[{"definitions":[{"id":"ED:lib:fee","meaning":"A fee was charged to the member (reason not stated).","name":"Fee charged"}],"id":"ED:lib:fee","meaning":"A fee was charged to the member (reason not stated).","name":"Fee charged"},{"definitions":[{"id":"ED:lib:lost","meaning":"A copy was declared lost.","name":"Marked lost"}],"id":"ED:lib:lost","meaning":"A copy was declared lost.","name":"Marked lost"},{"definitions":[{"id":"ED:lib:checkout","meaning":"A member borrowed a copy.","name":"Checked out"}],"id":"ED:lib:checkout","meaning":"A member borrowed a copy.","name":"Checked out"}],"case":{"id":"ET:lib:loan","meaning":"One loan of a book copy to a member","name":"Loan"},"focus":"lost","original_request":"For each loan, extract its lost-item history."}
Output: {"decisions":[{"id":"ED:lib:fee","decision":"UNCERTAIN"},{"id":"ED:lib:lost","decision":"INCLUDE"},{"id":"ED:lib:checkout","decision":"EXCLUDE"}]}
