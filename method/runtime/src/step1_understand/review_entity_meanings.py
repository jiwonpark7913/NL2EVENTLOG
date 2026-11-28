"""Global, evidence-grounded review of business Object Types."""

from __future__ import annotations
from src.common.runtime_input_contract import POLICY_VERSION, require_no_oracle_payload
from src.common.entity_identity import correspondence_judgment
from collections import Counter
from copy import deepcopy
from src.common.prompt_loader import load_prompt
from typing import Any
from jsonschema import Draft202012Validator
import hashlib
import json
import re
PROMPT_VERSION = "entity-target-review-v7-identification-contract"
TASK_PROMPT_VERSIONS = {'entity_type_naming': 'entity-type-naming-review-v8-business-entity-role'}
SCHEMA_NAMES = {'entity_type_naming': 'entity_type_naming_review'}
NAMING_TASKS = {'entity_type_naming'}
NAMING_ROLES = ('business_entity', 'event_record', 'association_record', 'reference_data', 'unknown')
OPERATIONS = {"MERGE", "SPLIT", "SEMANTIC_GROUP", "SAME_TYPE", "TYPE_SEPARATE"}
from src.common.llm_usage import chat_settings


def response_schema(task):
    """PURPOSE: Constrain model proposals independently of physical/evidence validation.
    INPUT: Global, targeted or naming role. OUTPUT: Strict JSON Schema; no graph mutation.
    """
    string = {'type': 'string'}
    citation = {'type': 'object', 'properties': {'id': string, 'quote': string},
                'required': ['id','quote'], 'additionalProperties': False}
    evidence = {'type': 'array', 'items': citation}

    def record(properties):
        """PURPOSE: Require every declared JSON field. INPUT: Field schemas. OUTPUT: Closed object schema."""
        return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

    roles = {'type': 'array', 'items': {'type': 'string', 'enum': [
        'business_object','event_record','association_record','reference_data','unknown']}}
    # Default-path naming uses the Entity term; the legacy targeted review keeps its contract.
    naming_roles = {'type': 'array', 'items': {'type': 'string', 'enum': list(NAMING_ROLES)}}
    judgment = {'type': 'string', 'enum': ['YES','NO','UNKNOWN']}
    if task == 'identification':
        return record({'descriptions': {'type': 'array', 'items': record({
            'target_id': string, 'business_meaning': string, 'instance_granularity': string,
            'representation_role': {'type': 'string', 'enum': ['primary_subject','additional_attributes',
                'alternate_identifier','reference','event_subject','storage_record']},
            'status': {'type': 'string', 'enum': ['supported','uncertain','rejected']},
            'evidence': evidence, 'reason': string})}})
    if task == 'classification':
        return record({'pair_decisions': {'type': 'array', 'items': record({
            'left': string, 'right': string, 'same_business_kind': judgment,
            'same_granularity': judgment, 'evidence': evidence, 'reason': string})}})
    
    
    
    name_roles = naming_roles if task == 'entity_type_naming' else roles
    return record({'names': {'type':'array','items':record({'concept_id':string,'name':string,
        'business_definition':string,'roles':name_roles,'evidence':evidence})},
        'representation_names': {'type':'array','items':record({'representation_id':string,
            'readable_name':string,'roles':name_roles,'evidence':evidence})}})


def _call(llm: Any, model: str, task: str, payload: dict[str, Any],
          cache: dict[str, Any] | None) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """PURPOSE: Request one cached, auditable JSON decision about existing Object IDs.
    INPUT: Model client, task, public evidence payload and optional response cache.
    OUTPUT: Parsed JSON or None, plus call/error/usage audit; no graph mutation.
    """
    require_no_oracle_payload(payload)
    filename = {'entity_type_naming': 'name_business_entity_types', 'identification': 'describe_entity_identification', 'classification': 'classify_entity_types'}[task]
    instruction = load_prompt('step1_understand', filename)
    schema = response_schema(task)
    digest = hashlib.sha256(json.dumps({'payload':payload,'system':instruction,'schema':schema},
        sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()
    key = f"{POLICY_VERSION}:{TASK_PROMPT_VERSIONS.get(task, PROMPT_VERSION)}:{task}:{model}:{digest}"
    audit = {"task": task, "cache_key": key, "cache_hit": False,
             "usage": {}, "errors": []}
    schema_name = SCHEMA_NAMES.get(task, 'entity_' + task + '_review')
    if task in NAMING_TASKS:
        audit['request'] = {'model': model, **chat_settings(model),
            'response_format': {'type': 'json_schema', 'json_schema': {'name': schema_name,
                'strict': True, 'schema': deepcopy(schema)}},
            'messages': [{'role': 'system', 'content': instruction},
                         {'role': 'user', 'content': json.dumps(payload,sort_keys=True,ensure_ascii=False,default=str)}]}
    if cache is not None and key in cache:
        audit["cache_hit"] = True
        require_no_oracle_payload(cache[key])
        if task in {'identification','classification'} | NAMING_TASKS:
            errors = list(Draft202012Validator(schema).iter_errors(cache[key]))
            if errors:
                audit['errors'].append('invalid_cached_semantic_review:' + errors[0].message)
                return None, audit
        audit['output'] = deepcopy(cache[key])
        return correspondence_judgment(cache[key]) if task == 'targeted' else cache[key], audit
    if llm is None:
        audit["errors"].append("llm_unavailable")
        return None, audit
    try:
        response = llm.chat.completions.create(
            model=model, **chat_settings(model), response_format={'type':'json_schema','json_schema': {
                'name':schema_name, 'strict':True, 'schema':schema}},
            messages=[{"role": "system", "content": instruction},
                      {"role": "user", "content": json.dumps(payload, sort_keys=True,
                                                               ensure_ascii=False, default=str)}])
        value = json.loads(response.choices[0].message.content)
        if task == 'targeted':
            value = correspondence_judgment(value)
        require_no_oracle_payload(value)
        if not isinstance(value, dict):
            raise ValueError("Model response must be a JSON object")
        if task in {'identification','classification'} | NAMING_TASKS:
            Draft202012Validator(schema).validate(value)
        usage = getattr(response, "usage", None)
        audit["usage"] = {"input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                          "output_tokens": getattr(usage, "completion_tokens", 0) or 0}
        if cache is not None:
            cache[key] = value
        audit['output']=deepcopy(value)
        return value, audit
    except Exception as error:
        audit["errors"].append(f"{type(error).__name__}: {error}")
        return None, audit


def _statements(dd: dict[str, Any], tables: set[str] | None = None) -> list[dict[str, Any]]:
    """PURPOSE: Select exact public dictionary statements for citation checking.
    INPUT: Normalized dictionary and optional table-name filter.
    OUTPUT: Stable statement records, including global process and business rules.
    """
    return [item for item in dd.get("semantic_statements", [])
            if tables is None or item.get("table") in tables or not item.get("table")]


def canonical_dictionary_citations(items,statements):
    """PURPOSE: Ground complete quotes and resolve only exact legacy Table/column definition IDs.
    INPUT: Model citations and the supplied immutable DD statements. OUTPUT: Canonical citations or None on any mismatch.
    Unknown IDs, partial quotes and invented text never support meaning/classification/identity judgments.
    """
    allowed={item['id']:item['text'] for item in statements}
    if not isinstance(items,list) or not items:return None
    result=[]
    for item in items:
        if not isinstance(item,dict):return None
        identifier=item.get('id');quote=item.get('quote')
        if identifier not in allowed and isinstance(identifier,str) and identifier.startswith(('T:','C:')):
            candidate=identifier+':definition'
            if candidate in allowed and quote==allowed[candidate]:identifier=candidate
        if identifier not in allowed or quote!=allowed[identifier]:return None
        result.append({'id':identifier,'quote':quote})
    return result


def _valid_evidence(items,statements):
    """PURPOSE: Reject invented/misquoted semantic evidence. INPUT: Citations and DD. OUTPUT: Full-quote validity boolean."""
    return canonical_dictionary_citations(items,statements) is not None


def naming_words(text):
    """PURPOSE: Check that a display label introduces no unsupported business vocabulary.
    INPUT: Label or supplied dictionary/validated meaning text. OUTPUT: Unicode words with simple inflection folding.
    This is conservative lexical grounding, not a general synonym or semantic entailment engine.
    """
    text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', str(text)).casefold()
    return {w[:-3]+'y' if w.endswith('ies') else w[:-1] if w.endswith('s') and not w.endswith('ss') else w
            for w in re.findall(r'[^\W_]+', text) if w not in {'a','an','the','of','for','and'}}


IDENTIFIER_DESCRIPTION_WORDS = {'identifier', 'integer', 'varchar', 'string', 'boolean', 'uuid', 'key'}


def validated_naming_updates(response, groups, representations, statements):
    """PURPOSE: Validate names and exact public DD citations once for old and final-ET consumers.
    INPUT: Structured model response, existing Entity Types/Tables and supplied statements.
    OUTPUT: Display-only updates by existing ID; identity/membership fields cannot be written.
    """
    updates = {}
    allowed = {g['id'] for g in groups}
    names = (response or {}).get('names', [])
    # Byte-identical repeats of one answer are one answer; differing answers for one ET stay rejected.
    unique = []
    for item in names if isinstance(names, list) else []:
        if item not in unique:
            unique.append(item)
    names = unique
    counts = Counter(item.get('concept_id') for item in names if isinstance(item, dict))
    for item in names:
        if isinstance(item, dict) and counts[item.get('concept_id')] != 1:
            continue
        if not isinstance(item, dict) or item.get('concept_id') not in allowed:
            continue
        name, definition = str(item.get('name','')).strip(), str(item.get('business_definition','')).strip()
        group = next(g for g in groups if g['id'] == item['concept_id'])
        tables = {r.get('table') for r in representations if r['id'] in group.get('members', [])}
        scoped_evidence = [e for e in statements if not e.get('table') or e['table'] in tables]
        known_text = ' '.join(e['text'] for e in scoped_evidence)
        known_text += ' ' + str(group.get('business_meaning', '')) + ' ' + str(group.get('instance_granularity', ''))
        vocabulary = naming_words(known_text) | {'one','instance','individual','represents','unit','business','recorded','with','per'}
        # The name must be grounded and name a business entity, not describe a key or its storage type.
        if (not naming_words(name) or not naming_words(name) <= vocabulary or
                naming_words(name) & IDENTIFIER_DESCRIPTION_WORDS):
            continue

        if (not name or len(name)>80 or not definition or len(definition)>500 or re.search(r'[.!?;:]',name)
                or not _valid_evidence(item.get('evidence'), statements)):
            continue
        update = {'name':name,'entity_type_name':name,'canonical_name':name,
            'display_name':name,'naming_status':'reviewed',
            'name_source':'global_entity_review','naming_evidence':item['evidence'],'naming_version':PROMPT_VERSION}
        # The definition is display prose: ungrounded words ("uniquely", "medical") drop only the definition,
        # never a grounded name; the previous definition is kept and the reason recorded.
        outside = sorted(naming_words(definition) - vocabulary)
        if outside:
            update['naming_warnings'] = [{'kind': 'definition_not_grounded', 'words': outside}]
        else:
            update['business_definition'] = definition
        updates[item['concept_id']] = update
    names = (response or {}).get('representation_names', [])
    allowed = {r['id'] for r in representations}
    for item in names if isinstance(names,list) else []:
        if not isinstance(item,dict):
            continue
        name = str(item.get('readable_name','')).strip()
        if item.get('representation_id') in allowed and name and len(name)<=100 and _valid_evidence(item.get('evidence'),statements):
            updates[item['representation_id']] = {'readable_name':name,'naming_evidence':item['evidence']}
    # Different instance units must not be hidden behind the same proposed display name.
    ambiguous = set()
    for left in groups:
        for right in groups:
            if left['id'] >= right['id']:
                continue
            ln = updates.get(left['id'], {}).get('name', left.get('name', '')).casefold()
            rn = updates.get(right['id'], {}).get('name', right.get('name', '')).casefold()
            lu, ru = left.get('instance_granularity'), right.get('instance_granularity')
            if ln == rn and lu and ru and lu.casefold() != ru.casefold():
                ambiguous.update((left['id'], right['id']))
    return {key:value for key,value in updates.items() if key not in ambiguous}


def business_name_hint(value):
    """PURPOSE: Remove provenance/key-quality wording from fallible naming hints, never from identity evidence.
    INPUT: Previously inferred business label. OUTPUT: Business noun hint or None when context is insufficient.
    Raw DD text and all identifiers remain unchanged and are supplied separately for exact citations.
    """
    hint=re.sub(r'\b(?:stable|unique|synthetic|authored)\b[ -]*','',str(value or ''),flags=re.I).strip()
    return None if hint.casefold() in {'','occurrence','instruction','plan','identifier','identity','key','record'} else hint


def build_naming_payload(entity_model, dd):
    """PURPOSE: Describe already validated ET groups to a display-only naming model.
    INPUT: Built Entity model and public DD. OUTPUT: Exact JSON input without collision-scope semantics.
    """
    groups = entity_model['entity_types']; representations = entity_model['table_semantic_profiles']
    dictionary_statements = _statements(dd)
    value_evidence = deepcopy(entity_model.get('business_value_evidence', []))
    statements = [*dictionary_statements, *value_evidence]
    payload = {'concepts':[{'id':g['id'],'kind':g['kind'],'members':g['members'],
                'business_meaning_hint':business_name_hint(g.get('business_meaning')),
                'instance_granularity_hint':g.get('instance_granularity') if business_name_hint(g.get('business_meaning')) else None,
                'population_status':g.get('population',{}).get('status'),
                'identification_targets':[{k:t[k] for k in ('id','source','business_meaning','instance_granularity','representation_role','status') if k in t}
                    for t in entity_model.get('identification_targets',[]) if t.get('entity_type_id')==g['id']],
                'validation_status':g['validation_status']} for g in groups],
        'tables':representations,'dictionary_statements':dictionary_statements,
        'observed_value_evidence':value_evidence, 'evidence_statements':statements,
        'type_count_policy':'diagnostic only; never optimize group count'}
    return payload


def name_entity_model(entity_model, dd, *, llm, model, cache=None):
    """PURPOSE: Name existing ET groups without changing membership, identity or attribution.
    INPUT: Mutable Entity model, public DD and optional model/cache.
    OUTPUT: Naming call/application audits; disabled models leave deterministic meaning-derived names.
    """
    if llm is None or not entity_model['entity_types']:
        return []
    payload = build_naming_payload(entity_model, dd)
    response, audit = _call(llm, model, 'entity_type_naming', payload, cache)
    return [apply_entity_naming_response(entity_model,response,payload['evidence_statements'],audit)]


def apply_entity_naming_response(entity_model,response,statements,audit=None):
    """PURPOSE: Apply only grounded display names, resolving exact legacy Table citations without relaxing proof.
    INPUT: Entity model, parsed naming response and exact public DD statements; optional existing call audit.
    OUTPUT: Naming audit and display-only mutations. Identity, classification, keys, internal collision components and roles never change.
    A legacy T:table reference maps to T:table:definition only if its full quote equals that statement verbatim.
    """
    groups=entity_model['entity_types'];representations=entity_model['table_semantic_profiles']
    value=deepcopy(response or {});allowed={s['id']:s['text'] for s in statements};resolved=[]
    for field in ('names','representation_names'):
        for item in value.get(field,[]):
            for citation in item.get('evidence',[]):
                original=citation.get('id','');canonical=original+':definition'
                if original not in allowed and original.startswith('T:') and canonical in allowed and citation.get('quote')==allowed[canonical]:
                    citation['id']=canonical;resolved.append({'from':original,'to':canonical})
    updates=validated_naming_updates(value,groups,representations,statements)
    for identifier in list(updates):
        if identifier in {g['id'] for g in groups} and business_name_hint(updates[identifier].get('name')) is None:
            del updates[identifier]
    audit=dict(audit or {})
    audit.update(applied_type_names=sum(g['id'] in updates for g in groups),canonicalized_table_citations=resolved)
    for item in [*groups,*representations]:
        update={k:v for k,v in updates.get(item['id'],{}).items() if k!='roles'}
        item.update(update)
    return audit
