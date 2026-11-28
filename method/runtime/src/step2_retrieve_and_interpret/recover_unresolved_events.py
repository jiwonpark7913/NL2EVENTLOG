"""Recover narrowly scoped selectors from the unresolved EEG metadata."""

from copy import deepcopy
import re

from src.common.project_recovered_events import project_recovered_events
from src.common.schema_metadata import stable_id
from src.step1_understand.resolve_activity_meanings import activity_label_issue
from src.step2_retrieve_and_interpret.interpret_and_verify_process import candidate_catalog, legacy_selection, validate_state
from src.step2_retrieve_and_interpret.verify_activity_requirements import verify_activity

_PHASES = {
    "start": re.compile(r"\b(?:start(?:ed|ing)?|beg(?:in|an)|commenc(?:e|ed))\b|시작|착수", re.I),
    "complete": re.compile(r"\b(?:complet(?:e|ed|ion)|finish(?:ed|ing)?)\b|완료|종료", re.I),
}
_COMPARISON = re.compile(r"(?<![<>=!])[<>=](?![=])")
_EXCLUSION = re.compile(
    r"\b(?:not|never|except|exclude|excluding|without|besides|other than|ignore|skip)\b|!=|<>|제외|아닌|말고|빼고",
    re.I)
_UNSUPPORTED_MODIFIER = re.compile(
    r"\b(?:first|last|earliest|latest|before|after|since|between|until|beforehand)\b|최초|가장 최근|이후|이전", re.I)


def _selector(record, text):
    """PURPOSE: Find an exact positive column/value selector in the original request.
    INPUT: Unresolved candidate and text. OUTPUT: Verbatim selector or None.
    """
    value = re.escape(str(record["value"]))
    column = re.escape(record["carrier"])
    literal = r"(?<!\w)[`'\"]?" + value + r"[`'\"]?(?![\w-])"
    match = re.search(r"(?<!\w)[`\"]?(?i:" + column + r")[`\"]?\s*=\s*" + literal, text)
    if not match:
        match = re.search(r"\b(?i:code)\s+" + literal + r"|" + literal + r"\s*코드", text)
    return match.group() if match else None


def _meaning(record, question):
    """PURPOSE: Read only an explicit user assertion that connects an exact code and meaning.
    INPUT: One observed candidate and original question. OUTPUT: Verbatim assertion and meaning, or None.
    """
    value = re.escape(str(record["value"]))
    code = r"(?<!\w)[`'\"]?" + value + r"[`'\"]?"
    english = re.finditer(code + r"\s+(?i:means|stands for)\s+[\"]?([^.;!?\n]{1,100}?)[\"]?(?=[.;!?\n]|$)", question)
    korean = re.finditer(code + r"\s*[은는]\s+([^.;!?\n]{1,100}?)\s*(?:이라는 뜻|라는 뜻|입니다|이다)(?=[.;!?\n]|$)", question)
    matches = [(evidence.group(), evidence[1].strip(" `'\"")) for evidence in (*english, *korean)]
    if len({label.casefold() for _, label in matches}) != 1:
        return None
    evidence, label = matches[0]
    if activity_label_issue(label, identifier_values=[record["value"]]) or any(p.search(label) for p in _PHASES.values()):
        return None
    return evidence, label



def _mentions_action(action, text):
    """PURPOSE: Verify a literal row-clock expression in a request span.
    INPUT: Documented row action noun and request text. OUTPUT: True for a noun/inflection or explicit Korean equivalent.
    """
    noun = {"activities": "activity"}.get(action, action)
    if noun.endswith("s"):
        noun = noun[:-1]
    forms = {"scan": r"scan(?:s|ned|ning)?|스캔", "observation": r"observ(?:ation(?:s)?|e|ed)|관측|관찰",
             "occurrence": r"occurr?(?:ence(?:s)?|ed|ing)|발생"}.get(noun, re.escape(noun) + "s?")
    return bool(re.search(r"(?<![A-Za-z])(?:" + forms + r")(?![A-Za-z])", text, re.I))

def _explicit_options(graph, question, requirement, single):
    """PURPOSE: Retrieve bounded locally relevant candidates supported by literal or asserted evidence.
    INPUT: Metadata and grounded activity requirement. OUTPUT: Per-phase candidates and compact decision facts.
    """
    span = requirement["span"]
    phase_phrases = [span, *[q for q in requirement.get("qualifiers", []) if q in question]]
    phases = {name for name, pattern in _PHASES.items() if any(pattern.search(text) for text in phase_phrases)}
    if not phases and single:
        phases = {name for name, pattern in _PHASES.items() if pattern.search(question)}
    if (len(phases) > 1 or _EXCLUSION.search(question) or _UNSUPPORTED_MODIFIER.search(span)
            or len(_COMPARISON.findall(question)) > 1):
        return []
    options = []
    for item in graph.get("unresolved_event_evidence", {}).get("pairs", []):
        if not item["raw_clock_validated"] or item["value_semantics_status"] != "unresolved":
            continue
        action = item.get("raw_clock_action")
        matched_clock = (not phases and any(_mentions_action(action, text) for text in phase_phrases)
                         if action else item["raw_clock_phase"] in phases)
        if not matched_clock:
            continue
        query_selector = _selector(item, question if single else span)
        asserted = _meaning(item, question)
        if not query_selector and asserted and any(asserted[1].casefold() in text.casefold()
                                                  for text in (span, requirement["meaning"])):
            query_selector = asserted[0]
        if not query_selector:
            continue
        if any(not (any(pattern.search(q) for pattern in _PHASES.values()) or _selector(item, q)
                    or (action and _mentions_action(action, q)))
               for q in requirement.get("qualifiers", [])):
            continue
        options.append((item, {"basis": "user_asserted_code_meaning" if asserted else "explicit_raw_code",
                               "request_quote": query_selector,
                               **({"asserted_meaning": asserted[1], "meaning_quote": asserted[0]} if asserted else {})}))
    return options


def recover_explicit_events(question, graph, result, max_hops):
    """PURPOSE: Extend independently checked PI with a narrow, physically proved recovery.
    INPUT: Shared EEG, original query and normal PI result. OUTPUT: PI result, request-local EEG view, recovery audit.
    """
    if not graph.get("unresolved_event_evidence") or result["status"] not in {"ready", "partial"}:
        return result, graph, []
    final = result["final_selection"]
    parsed = result.get("requirements") or {}
    current_requirements = result["process_information"].get("activity_requirements")
    if current_requirements is not None:
        parsed = dict(parsed, activity_requirements=current_requirements)
    outcomes = final.get("activity_requirement_results", [])
    target = final.get("target_object_id")
    if not target or final.get("activity_scope") != "explicit" or not outcomes or not parsed.get("activity_requirements"):
        return result, graph, []
    current = {item["id"]: item for item in graph["event_definitions"]}
    by_requirement = {item["id"]: item for item in outcomes}
    admissions, audit = {}, []
    for requirement in parsed["activity_requirements"]:
        old = by_requirement[requirement["id"]]
        if graph.get('indexed_request') and (requirement.get('coverage') == 'all' or
                any(code.startswith('scope_') for code in old.get('reason_codes', []))):
            continue
        options = _explicit_options(graph, question, requirement, len(outcomes) == 1)
        if not options:
            continue
        if len(options) != 1:
            audit.append({"requirement_id": requirement["id"], "status": "ambiguous", "candidates": len(options)})
            continue
        record, decision = options[0]
        if old["status"] == "verified" and (not old["event_definition_ids"] or not all(
                current[e]["source_kind"] == "column_event" and current[e]["source_table"] == record["table"]
                and current[e].get("ts_id") == record["ts_id"] for e in old["event_definition_ids"])):
            continue
        if old["status"] != "verified" and not (
                set(old.get("reason_codes", [])) & {"event_definition_missing", "event_definition_unverified"}):
            continue
        identifier = record["candidate_id"]
        admissions[requirement["id"]] = (identifier, decision, requirement)
        audit.append({"requirement_id": requirement["id"], "candidate_id": identifier, "status": "considered"})
    if not admissions:
        return result, graph, audit
    decisions = {identifier: decision for identifier, decision, _ in admissions.values()}
    local = project_recovered_events(graph, target, decisions)
    rows = candidate_catalog(local, target, max_hops, case_scope=final.get("case_scope"))
    replaced = deepcopy(outcomes)
    accepted = {}
    for index, old in enumerate(replaced):
        if old["id"] not in admissions:
            continue
        identifier, decision, requirement = admissions[old["id"]]
        if identifier not in rows or identifier in accepted:
            continue
        verified = verify_activity(requirement, {"event_definition_ids": [identifier], "role_path_choices": [],
            "semantic_status": "matched", "source_attribution_gap": False, "reason": decision["basis"]},
            rows, [identifier], canonical_only=True)
        if verified["status"] == "verified":
            accepted[identifier] = decision
            replaced[index] = verified
    if not accepted or any(r["status"] != "verified" for r in replaced):
        return result, graph, [*audit, {"status": "incomplete_recovery"}]
    mappings = {r["id"]: r["event_definition_ids"] for r in replaced}
    chosen = [identifier for identifiers in mappings.values() for identifier in identifiers]
    local_defs = {item["id"]: item for item in local["event_definitions"]}
    recovered = [local_defs[i] for i in accepted]
    broad_clocks = {(local_defs[i]["source_table"], local_defs[i].get("ts_id")) for i in chosen
                    if i not in accepted and local_defs[i]["source_kind"] == "column_event"}
    overlap = any((r["source_table"], r.get("ts_id")) in broad_clocks for r in recovered)
    if len(chosen) != len(set(chosen)) or overlap:
        return result, graph, [*audit, {"status": "occurrence_overlap"}]
    state = {"target_ot_id": target, "activity_scope": "explicit", "object_scope": final["scope_policy"],
             "selected_candidate_ids": sorted(chosen)}
    validation = validate_state(local, state, parsed, rows, structural_only=True)
    if validation["status"] != "valid":
        return result, graph, [*audit, {"status": "failed_structural_validation", "warnings": validation["warnings"]}]
    validation.update(mappings=mappings, requirement_results=replaced)
    selected = legacy_selection(state, parsed, validation, rows)
    selected.update(activity_requirement_results=replaced, case_scope=final.get("case_scope"))
    paths = {i: sorted({path for r in replaced for path in r["definition_path_ids"].get(i, [])}) for i in chosen}
    info = {**result["process_information"], "status": "ready", "selected_event_definition_ids": sorted(chosen),
            "activity_requirement_results": replaced, "verified_attribution_paths": paths,
            "recovered_event_decisions": accepted}
    updated = {**result, "status": "ready", "terminal_status": "validated",
               "termination_reason": "explicit_carrier_recovery", "final_selection": selected,
               "final_validation": validation, "final_selection_fingerprint": stable_id("selection", state),
               "final_selection_version": result["final_selection_version"] + 1,
               "validations": [*result["validations"], validation], "process_information": info}
    return updated, local, [*audit, {"status": "validated", "ids": sorted(accepted)}]
