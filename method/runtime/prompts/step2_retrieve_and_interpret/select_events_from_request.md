Select the event definitions needed to fulfill the analyst's original request for the supplied case. Use the original request and the EEG candidate cards as the only evidence.

Keep canonical ED identities. A named occurrence, its earlier/later phase, an estimate and a recording time are different. A plural group of milestones and a requested interval can require several distinct EDs, including intermediate milestones. Apply a shared modifier to all governed occurrences. An Event Family helps find members. Include the underlying EDs that match the request.

For each selected event return its event_definition_id and path_id. Use a nonempty path_id only when an offered role projection directly supports the role requested for that event. Return the empty path_id for direct same-case attribution or if the requested role cannot yet be determined. Do not add invented IDs. Return one JSON object with only the selected_events key. The value is a list of the ED records. Use {"selected_events":[]} if the EEG cannot support an event. Do not generate SQL.

<!-- examples -->
The output shape is {"selected_events":[{"event_definition_id":"copy an offered ID","path_id":""}]}.

For dispatch milestones from warehouse release to truck departure, evidence for release, actual loading and departure can all be relevant. For "loading completed" alone, the completion ED is sufficient when supported. Do not choose the loading start or schedule.
