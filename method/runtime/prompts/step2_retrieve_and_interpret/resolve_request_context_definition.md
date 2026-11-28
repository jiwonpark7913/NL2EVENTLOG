The analyst named activities that no selected or tier-1 definition covers. Decide whether a tier-2 definition can be approved for this one request. Tier 2 means a candidate whose meaning on exactly one axis (card field "axis": activity, occurrence, time or identity) was not confirmed when the data was analysed.

# Input
- definitions: cards {id, tier (1 or 2), activity, axis, source, rows, time, dictionary_ids}.
- dictionary: map from a statement ID to {id, text, table, column, field}. A definition's own statements are the ones listed in its dictionary_ids.
- entity_type, original_request, and missing_spans: the exact request spans still unmatched.

# Procedure, for each span in missing_spans
1. Read ALL tier-1 definitions (and their dictionary text). If any expresses the requested activity (synonyms and other wording included), make no decision for that span.
2. Otherwise look at the tier-2 definitions. Approve one only if its OWN dictionary statements affirmatively say that its rows record this activity happening. The request wording alone never proves an occurrence.
3. Judge only the single unresolved axis in the context of the request. Never propose new definitions, joins, columns or changed predicates.

# Output
decisions: only approvals, at most one per definition ID. Each is {id, span, reason, citations}:
- id: the tier-2 definition ID, copied exactly.
- span: the exact span from missing_spans.
- reason: one sentence saying which statement supports it.
- citations: [{id, quote}] where id is a statement ID from THAT definition's dictionary_ids and quote is the COMPLETE statement text, verbatim (no partial quote, no paraphrase). Never cite another definition's statements.
Return [] when nothing is supported. A decision without valid citations is silently discarded, and an invalid answer is not retried.

<!-- examples -->
Examples (abridged). IDs and domains are illustrative.

Input: {"definitions":[{"activity":"Claim filed","axis":null,"dictionary_ids":["DD:filed"],"id":"ED:ins:filed","source":"claims","tier":1},{"activity":"Site visit","axis":"activity","dictionary_ids":["DD:visit"],"id":"ED:ins:visit","source":"claims","tier":2}],"dictionary":{"DD:filed":{"id":"DD:filed","text":"The insured filed a claim."},"DD:visit":{"id":"DD:visit","text":"The adjuster visited the insured property to inspect the damage."}},"entity_type":{"id":"ET:ins:claim","meaning":"One insurance claim","name":"Claim"},"missing_spans":["Property inspected"],"original_request":"For each claim, extract Claim filed and Property inspected."}
Output: {"decisions":[{"id":"ED:ins:visit","span":"Property inspected","reason":"The definition's own statement says the adjuster inspected the property.","citations":[{"id":"DD:visit","quote":"The adjuster visited the insured property to inspect the damage."}]}]}

Input: {"definitions":[{"activity":"Claim filed","axis":null,"dictionary_ids":["DD:filed"],"id":"ED:ins:filed","source":"claims","tier":1},{"activity":"Site visit","axis":"activity","dictionary_ids":["DD:visit"],"id":"ED:ins:visit","source":"claims","tier":2}],"dictionary":{"DD:filed":{"id":"DD:filed","text":"The insured filed a claim."},"DD:visit":{"id":"DD:visit","text":"Visit code assigned by the field office."}},"entity_type":{"id":"ET:ins:claim","meaning":"One insurance claim","name":"Claim"},"missing_spans":["Property inspected"],"original_request":"For each claim, extract Claim filed and Property inspected."}
Output: {"decisions":[]}

Input: {"definitions":[{"activity":"Claim filed","axis":null,"dictionary_ids":["DD:filed"],"id":"ED:ins:filed","source":"claims","tier":1},{"activity":"Site visit","axis":"activity","dictionary_ids":["DD:visit"],"id":"ED:ins:visit","source":"claims","tier":2}],"dictionary":{"DD:filed":{"id":"DD:filed","text":"The insured filed a claim."},"DD:visit":{"id":"DD:visit","text":"The adjuster visited the insured property to inspect the damage."}},"entity_type":{"id":"ET:ins:claim","meaning":"One insurance claim","name":"Claim"},"missing_spans":["Filing received"],"original_request":"For each claim, extract Filing received."}
Output: {"decisions":[]}
