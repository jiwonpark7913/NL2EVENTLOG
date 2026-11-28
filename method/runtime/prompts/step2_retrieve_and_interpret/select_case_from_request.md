Select the case entity and the activity scope directly from the analyst's original request using the supplied EEG entity cards and role scopes.

Use the unit that one case represents. A related object mentioned in an activity is not necessarily the case. For a role-restricted case, choose the offered scope ID for that entity. Otherwise return the empty scope ID when the schema includes it.

Return one candidate when a case is well supported. Return multiple distinct candidates only for real ambiguity. Use mode explicit for a named activity or a bounded group of occurrences. Use mode implicit for a full history, case lifecycle, or topic-filtered history. For its object_scope use own for the case entity's own lifecycle or state changes, process_focus for a topic-filtered history, and attributable_history for history across events attributable to that case. Give the exact topic phrase as focus only for process_focus. Use object_scope unresolved and empty focus for explicit selections.

Use only offered IDs. Do not use evaluator knowledge or generate SQL.

<!-- examples -->
For a request about "each purchase order's state transitions", select the offered purchase order entity, mode implicit, object_scope own, and empty focus. For "each outbound shipment, include release and loading", select the shipment entity, outbound scope if offered, mode explicit, object_scope unresolved, and empty focus.
