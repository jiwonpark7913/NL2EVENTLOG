# Task

Review the relationship between each supplied event definition and the specified Entity Type. The event label, occurrence clock, source predicate and occurrence key are fixed. A message receipt and the occurrence described by the message are distinct events. Assess the documented relationship for each supplied path.

Return one decision per event ID and account for every supplied path exactly once. For each path return its path_id, status, role, reason, and citations.

- Use supported when public documentation supports attributing the occurrence through this relationship. Use incompatible only when documentation contradicts this particular attribution. Use uncertain when the documentation leaves the relationship unresolved.
- Use subject when the entity instance undergoes or performs this occurrence. Use related for a documented relationship to another subject and unspecified when the subject cannot be established.
- Cite exact public dictionary excerpts by ID. A passing JOIN establishes a physical mapping. Use the description of the relationship to judge its business meaning. Do not infer incompatibility from process preference, the fact that a different occurrence has a different clock, or a role absent from the request. This stage has no user request.
- Leave duplicate_of empty unless two definitions document the same business occurrence for this Entity Type. Cite the evidence and give a reason for any duplicate nomination. Distinct start/completion and repeated instances are distinct occurrences. The controller independently checks the underlying Case and clock observations.
