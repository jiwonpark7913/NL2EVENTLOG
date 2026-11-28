
Additional output field: absent_from_tier1.
runtime_data contains complete_tier1_inventory: every tier-1 (high-confidence) event definition available for the selected case type, selected or not, each {id, name, meaning}.
absent_from_tier1 lists requested activity spans for which NO inventory definition exists. Procedure, for each pending requirement with semantic_status missing:
1. Read the name and meaning of every inventory definition. Synonyms, other tenses, noun/verb forms and different wording count as expressing the activity.
2. Only if none expresses it, copy the exact requirement span into absent_from_tier1. A span that is not also missing in requirement_reviews is ignored.
3. Return [] when no missing span exists or when you are uncertain.
Why this matters: a listed span sends the pipeline to look for lower-confidence (tier-2) definitions of that activity. A wrongly listed span wastes that one-time lookup; a wrongly omitted span leaves a real gap unresolved.
Examples (inventory names: "Checked out", "Returned"): unmatched "Renewed" with no similar inventory definition gives ["Renewed"]. Unmatched "Brought back" gives [], because "Returned" expresses it.
