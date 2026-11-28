"""Meaning-first Entity Types and row-to-Entity identification rules; no oracle access."""


from __future__ import annotations


from collections import defaultdict, Counter


from contextlib import closing


from copy import deepcopy


from itertools import combinations


import re


from src.common.entity_identity import identity_scope_id


from src.common.attribution_policy import forward_adjacency, reference_constraint_issues, MAX_ATTRIBUTION_HOPS, bounded_hops, reference_path_row_states


from src.step1_understand.entity_representations import contract_id, build_representations, representation_role, _key_type


from src.common.database_io import quote_identifier as qi


from src.step1_understand.verify_entity_identity_mappings import assess_key_identity_mappings


from src.common.normalize_relation_assessments import rename_identity_references


from src.common.database_io import connect_readonly


VERSION = 'meaning-first-identification-v3'


IDENTITY_CONTRACT = 'validated-identification-correspondence-v1'


SUBJECT_ROLES = {'primary_subject', 'additional_attributes', 'alternate_identifier', 'event_subject'}


def meaning_key(text):
    """PURPOSE: Normalize documented business units without using key values or table overlap.
    INPUT: Business meaning/granularity text. OUTPUT: Stable lexical key, not a similarity score.
    """
    words = re.findall(r'[^\W_]+', re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', str(text)).casefold())
    return ' '.join(w[:-1] if w.endswith('s') and not w.endswith(('ss', 'status')) else w for w in words)


def business_unit_phrase(value):
    """PURPOSE: Normalize business descriptors without interpreting identifier quality as a type.
    INPUT: DD phrase or model description. OUTPUT: Non-generic noun phrase or empty; never examines data values.
    """
    text=re.sub(r'\b(?:synthetic|authored|unique|stable|global|local)\b[ -]*','',str(value or ''),flags=re.I).strip(' .;')
    text=re.sub(r'^(?:(?:the|same|one|optional|an?) )+','',text,flags=re.I).strip()
    generic={'','id','identity','identifier','key','record','row','object','entity','instance',
             'occurrence','event','activity','business record','business object','business entity'}
    return '' if meaning_key(text) in generic else text


def _documented_unit(table_dd, key_dd):
    """PURPOSE: Describe what an identifier denotes without treating row uniqueness as business meaning.
    INPUT: Public Table definition and complete key-column descriptions.
    OUTPUT: Conservative unit hint; composite keys need whole-row meaning, not the first component's noun.
    """
    text=' '.join(str(table_dd.get(k,'')) for k in ('row_grain','definition'))
    row_unit=''
    compound_unit=False
    for pattern in (r'one (?:retained )?row per (?:business )?([\w -]+?)(?:[.,;]| and |$)',
                    r'\b(?:one|an?|same) ([\w -]+?) (?:business )?(?:entity|object|instance)\b',
                    r'(?:^|[.;]\s*)(?:independent )?([\w -]+?) business (?:entity|object|record)\b'):
        match=re.search(pattern,text.strip(),re.I)
        if match:
            compound_unit=match[0].casefold().endswith(' and ') and not re.match(r'(?:its|their|the same)\b',text[match.end():],re.I)
            row_unit=business_unit_phrase(re.sub(r'^(?:the |same |one |optional )+','',match[1].strip(),flags=re.I))
            if row_unit:break
    if len(key_dd)!=1:
        # "student AND course" is a combination, not one Student entity.
        if row_unit and not re.search(r'\b(?:and|by|per)\b',row_unit,re.I) and not compound_unit:return row_unit
        return ''
    definition=str(key_dd[0].get('definition',''))
    # An explicitly owned identifier (e.g. payroll number of the employee) denotes that row unit.
    # Keep references/associated-object identifiers separate so a Table may still identify several ETs.
    if (row_unit and re.search(r'\b(?:identifier|identity|key|number|ID)\s+(?:of|for)\s+(?:the )?' +
            re.escape(row_unit) + r'\b', definition, re.I) and not re.search(
                r'\b(?:reference|references|foreign|related|associated)\b', definition, re.I)):
        return row_unit
    match=re.search(r'\b([\w -]+?) (?:identifier|identity|key|number|ID)\b',definition,re.I)
    unit=business_unit_phrase(match[1]) if match else ''
    if row_unit and re.search(r'\b(?:alternate|same)\b',definition,re.I) and meaning_key(row_unit) in meaning_key(unit):return row_unit
    if unit and not re.search(r'\b(row|record|history|storage|code)\b',unit,re.I):
        return unit
    return row_unit


def _documented_artifact_unit(table_dd, key_dd):
    """PURPOSE: Recognize a named business artifact independently of the activity it records.
    INPUT: Public table and column descriptions for one local identifier.
    OUTPUT: The documented artifact unit when both descriptions support it, or an empty string.
    """
    if len(key_dd) != 1:
        return ''
    key_text = key_dd[0].get('definition', '').strip()
    table_text = ' '.join(str(table_dd.get(field, '')) for field in ('definition', 'row_grain'))
    if re.search(r'\b(?:audit|debug|telemetry|storage[- ]only|technical|system log|not a business (?:entity|record))\b',
                 key_text + ' ' + table_text, re.I):
        return ''
    match = re.fullmatch(r'([\w -]+?)\s+(?:identifier|id|number)\.?', key_text, re.I)
    unit = business_unit_phrase(match[1]) if match else ''
    words = meaning_key(unit).split()
    artifact_terms = {'report', 'message', 'notice', 'document'}
    table_words = set(meaning_key(table_text).split())
    if len(words) < 2 or words[-1] not in artifact_terms or not table_words & artifact_terms:
        return ''
    return unit if set(words[:-1]) & table_words else ''


def _identifier_profile(connection, table, columns):
    """PURPOSE: Measure complete ordered identifier usage, including repeated reference values.
    INPUT: Read-only DB, physical table and nonempty column list.
    OUTPUT: Exact row/null/distinct/repetition counts plus bounded display sample metadata.
    """
    projection = ','.join(qi(c) for c in columns)
    nulls = ' OR '.join(qi(c) + ' IS NULL' for c in columns)
    source = qi(table)
    total = connection.execute(f'SELECT COUNT(*) FROM {source}').fetchone()[0]
    null_count = connection.execute(f'SELECT COUNT(*) FROM {source} WHERE {nulls}').fetchone()[0]
    distinct = connection.execute(f'SELECT COUNT(*) FROM (SELECT DISTINCT {projection} FROM {source} WHERE NOT ({nulls}))').fetchone()[0]
    sample = connection.execute(f'SELECT DISTINCT {projection} FROM {source} WHERE NOT ({nulls}) ORDER BY {projection} LIMIT 8').fetchall()
    return {'row_count': total, 'null_count': null_count, 'distinct_count': distinct,
            'repeated_non_null_rows': total - null_count - distinct,
            'unique_non_null': null_count == 0 and distinct == total,
            'sample': [list(row) for row in sample], 'counts_scope': 'complete_scan',
            'sample_scope': 'first_eight_distinct_tuples_display_only'}


def discover_identification_targets(db_path, tables, dd, objects, key_profiles, references):
    """PURPOSE: Inventory what each PK/UNIQUE/FK identifies, without first assigning tables to ETs.
    INPUT: Public schema/DD, physical record objects, exact profiles and verified reference inventory.
    OUTPUT: Identifier interpretations retaining complete components, immutable sources and uncertainty.
    """
    td = {t['table']: t for t in dd.get('tables', [])}
    cd = {(c['table'], c['column']): c for c in dd.get('columns', [])}
    primary = {o['table']: o for o in objects}
    targets = []
    with closing(connect_readonly(db_path)) as connection:
        for table in tables:
            for key in [k for k in key_profiles if k['table'] == table.name]:
                columns = list(key['columns'])
                docs = [cd.get((table.name, c), {}) for c in columns]
                definition = td.get(table.name, {})
                role, _ = representation_role(definition.get('definition', '') + ' ' + definition.get('row_grain', ''))
                main = primary.get(table.name, {}).get('pk') == columns
                artifact_unit = _documented_artifact_unit(definition, docs) if main else ''
                unit = artifact_unit or _documented_unit(definition, docs)
                representation_role_name = ('primary_subject' if artifact_unit else
                    'storage_record' if role in {'event_storage', 'code_description', 'relationship'} else
                    'additional_attributes' if re.search(r'\b(extension|additional attributes|same .*instance)\b', definition.get('definition', ''), re.I) else
                    'primary_subject' if main else 'alternate_identifier')
                supported = bool(unit) and representation_role_name != 'storage_record'
                evidence = [e for e in dd.get('semantic_statements', []) if e.get('table') == table.name and
                    (not e.get('column') or e.get('column') in columns)]
                target = {'id': contract_id('IT', [table.name, columns, key['kind']]),
                    'source': {'table': table.name, 'columns': columns, 'constraint': key['id']},
                    'constraint_kind': key['kind'], 'business_meaning': unit,
                    'instance_granularity': 'one ' + meaning_key(unit) if unit else '',
                    'representation_role': representation_role_name,
                    'status': 'supported' if supported else 'rejected' if representation_role_name == 'storage_record' else 'uncertain',
                    'semantic_basis': ('documented_artifact_identity' if artifact_unit else
                                       'documented_business_unit' if supported else role),
                    'evidence': evidence, 'structural_validation': deepcopy(key),
                    'observations': _identifier_profile(connection, table.name, columns),
                    'table_definition': definition.get('definition', ''), 'row_grain': definition.get('row_grain', ''),
                    'key_dictionary': deepcopy(docs), 'entity_type_id': None}
                targets.append(target)
        for child, edges in forward_adjacency(references).items():
            for edge in edges:
                columns = edge['left_columns']
                source_definition = td.get(child, {}).get('definition', '') + ' ' + td.get(child, {}).get('row_grain', '')
                targets.append({'id': contract_id('IT', [child, columns, edge['relationship_id']]),
                    'source': {'table': child, 'columns': list(columns), 'constraint': edge['relationship_id']},
                    'constraint_kind': 'reference', 'reference': deepcopy(edge),
                    'business_meaning': '', 'instance_granularity': '', 'representation_role': 'reference',
                    'status': 'uncertain', 'semantic_basis': 'referenced_target_pending',
                    'evidence': [e for e in dd.get('semantic_statements', []) if e.get('table') == child and
                                 (not e.get('column') or e.get('column') in columns)],
                    'structural_validation': {'forward_reference': True, 'child_uniqueness_required': False},
                    'observations': _identifier_profile(connection, child, columns),
                    'table_definition': source_definition, 'row_grain': td.get(child, {}).get('row_grain', ''),
                    'key_dictionary': [deepcopy(cd.get((child, c), {})) for c in columns], 'entity_type_id': None})
    return sorted(targets, key=lambda t: t['id'])


def interpret_identification_targets(targets, dd, llm, model, cache, value_evidence=()):
    """PURPOSE: Resolve uncertain business descriptions in bounded, cited semantic reviews.
    INPUT: Immutable target sources and public DD, optional model/cache.
    OUTPUT: Updated descriptions and audits; invented target IDs/citations never change the schema.
    """
    from src.step1_understand.review_entity_meanings import _call, _valid_evidence, canonical_dictionary_citations
    audits = []
    # An explicit 'extension of <table>' describes the same business unit, not instance identity.
    # Resolve that semantic reference before validating values or constructing internal collision-prevention components.
    for target in targets:
        match = re.search(r'\bextension of (?:the )?([\w]+)\b', target['table_definition'], re.I)
        parent = next((t for t in targets if match and t['source']['table'].casefold() == match[1].casefold()
                       and t['representation_role'] == 'primary_subject' and t['status'] == 'supported'), None)
        if parent and target['representation_role'] == 'additional_attributes':
            target.update(business_meaning=parent['business_meaning'], instance_granularity=parent['instance_granularity'],
                          status='supported', semantic_basis='explicit_additional_representation_of_business_unit')
            target['evidence'] = [*target['evidence'], *deepcopy(parent['evidence'])]
    pending = [t for t in targets if t['constraint_kind'] != 'reference']
    for offset in range(0, len(pending), 20):
        if llm is None:
            break
        batch = pending[offset:offset+20]
        tables = {t['source']['table'] for t in batch}
        # Global process/rule statements have no table key. They remain public dictionary evidence and must
        # not disappear merely because this batch is table-scoped.
        dictionary_statements = [e for e in dd.get('semantic_statements', [])
                                 if not e.get('table') or e.get('table') in tables]
        observed_statements = [e for e in value_evidence if e.get('table') in tables]
        statements = [*dictionary_statements, *observed_statements]
        # Observed business attributes may disambiguate documented meaning, but cannot alone justify an ET.
        semantic_targets=[{k:deepcopy(t[k]) for k in ('id','source','constraint_kind','business_meaning',
            'instance_granularity','representation_role','status','table_definition','row_grain','key_dictionary','evidence') if k in t}
            for t in batch]
        response, audit = _call(llm, model, 'identification', {'targets': semantic_targets,
            'dictionary_statements': dictionary_statements, 'observed_value_evidence': observed_statements}, cache)
        audits.append(audit)
        if not response or not isinstance(response.get('descriptions'), list):
            continue
        by_id = {t['id']: t for t in batch}
        seen = set()
        counts = Counter(d.get('target_id') for d in response['descriptions'] if isinstance(d, dict))
        for description in response['descriptions']:
            identifier = description.get('target_id') if isinstance(description, dict) else None
            if identifier in seen or counts[identifier] != 1:
                audit.setdefault('validation_errors', []).append('duplicate_target_description:' + str(identifier))
                continue
            seen.add(identifier)
            target = by_id.get(identifier)
            citations = canonical_dictionary_citations(description.get('evidence'), statements)
            cited_dictionary = any(item.get('id') in {e['id'] for e in dictionary_statements}
                                   for item in citations or [])
            if (not target or description.get('status') not in {'supported','uncertain','rejected'} or
                    description.get('representation_role') not in SUBJECT_ROLES | {'storage_record','reference','event_subject'} or
                    citations is None or description.get('status') == 'supported' and not cited_dictionary or
                    description.get('status')=='supported' and not business_unit_phrase(description.get('business_meaning')) or
                    not isinstance(description.get('business_meaning'), str) or
                    not isinstance(description.get('instance_granularity'), str) or
                    description.get('status') == 'supported' and not all(description.get(k, '').strip()
                        for k in ('business_meaning','instance_granularity','reason'))):
                audit.setdefault('validation_errors', []).append('invalid_target_description:' + str(identifier))
                continue
            if target['semantic_basis'] == 'documented_artifact_identity':
                # Preserve the documented unit when a model interprets the recorded action instead.
                audit.setdefault('documented_artifact_targets_retained', []).append(identifier)
                continue
            description={**description,'evidence':citations}
            target.update({k: deepcopy(description[k]) for k in
                ('business_meaning','instance_granularity','representation_role','status','evidence')})
            target['business_meaning']=business_unit_phrase(target['business_meaning'])
            target['semantic_basis'] = 'cited_identifier_interpretation'
            target['semantic_evidence_sources'] = sorted({
                'observed_value' if item['id'].startswith('V:') else 'dictionary_or_schema'
                for item in description['evidence']})
    # A repeated FK still identifies its target. It does not need to identify a source record.
    for target in targets:
        if target['constraint_kind'] != 'reference':
            continue
        edge = target['reference']
        parent = next((t for t in targets if t['source']['table'] == edge['right_table'] and
            t['source']['columns'] == edge['right_columns'] and t['constraint_kind'] != 'reference'), None)
        if parent and parent['status'] == 'supported':
            target.update(business_meaning=parent['business_meaning'], instance_granularity=parent['instance_granularity'],
                          status='supported', target_identifier_id=parent['id'], semantic_basis='documented_reference_target')
            unit = meaning_key(parent['business_meaning'])
            source_text = meaning_key(target['table_definition'])
            store = representation_role(target['table_definition'])[0] == 'event_storage'
            # A reference in an event store is the event subject only with subject-specific meaning.
            key_text = ' '.join(str(c.get('definition', '')) for c in target.get('key_dictionary', []))
            actor = bool(re.search(r'\b(actor|operator|resource|approver|reviewer|performed by|user who)\b', key_text, re.I))
            subject = unit and (re.search(r'\b' + re.escape(unit) + r'\s+(?:activit(?:y|ie)|event|transition|occurrence|history)\b', source_text)
                or re.search(r'\b(?:activity|event|transition) (?:of|for|about) (?:the )?' + re.escape(unit) + r'\b', source_text)
                or re.search(r'\b(subject|affected entity)\b', key_text, re.I))
            if store and subject and not actor:
                target['representation_role'] = 'event_subject'
            target['evidence'] = [*target['evidence'], *deepcopy(parent['evidence'])]
    return audits


def classify_entity_types(targets, dd, llm, model, cache):
    """PURPOSE: Classify meaning and instance granularity before any cross-table identity statistics.
    INPUT: Supported business target descriptions and exact public evidence; no overlap/domain inputs.
    OUTPUT: Complete-link semantic groups, pair decisions, consistency diagnostics and model audits.
    """
    from src.step1_understand.review_entity_meanings import _call, _valid_evidence, canonical_dictionary_citations
    supported = [t for t in targets if t['status'] == 'supported' and t['representation_role'] != 'storage_record']
    pairs, audits, diagnostics = {}, [], []
    for left, right in combinations(supported, 2):
        same = (meaning_key(left['business_meaning']) == meaning_key(right['business_meaning']) and
                meaning_key(left['instance_granularity']) == meaning_key(right['instance_granularity']))
        if same:
            pairs[frozenset((left['id'], right['id']))] = {'status': 'supported', 'basis': 'same_documented_meaning_and_unit'}
    if llm is not None and len(supported) > 1:
        descriptions = [{k: deepcopy(t[k]) for k in ('id','source','business_meaning','instance_granularity',
                         'representation_role','status','evidence')} for t in supported]
        # The global classification review sees descriptors, not identity relations, key overlaps or samples.
        required_pairs=[{'left':a['id'],'right':b['id'],'reason':'same_Table primary/alternate semantic comparison; identity is judged later'}
            for a,b in combinations(supported,2) if a['source']['table']==b['source']['table']
            and a['constraint_kind']!='reference' and b['constraint_kind']!='reference'
            and {a['representation_role'],b['representation_role']} & {'alternate_identifier'}]
        response, audit = _call(llm, model, 'classification', {'descriptions': descriptions,
            'required_pairs':required_pairs,'dictionary_statements': dd.get('semantic_statements', [])}, cache)
        audits.append(audit)
        indexed = {t['id']: t for t in supported}
        if response and isinstance(response.get('pair_decisions'), list):
            grouped = defaultdict(list)
            for decision in response['pair_decisions']:
                if not isinstance(decision, dict):
                    continue
                pair = frozenset((decision.get('left'), decision.get('right')))
                if len(pair) != 2 or not pair <= set(indexed) or not _valid_evidence(decision.get('evidence'), dd.get('semantic_statements', [])):
                    diagnostics.append({'reason': 'invalid_semantic_pair', 'decision': decision})
                    continue
                if decision.get('same_business_kind') not in {'YES','NO','UNKNOWN'} or decision.get('same_granularity') not in {'YES','NO','UNKNOWN'}:
                    continue
                decision={**decision,'evidence':canonical_dictionary_citations(decision['evidence'],dd.get('semantic_statements',[]))}
                grouped[pair].append(decision)
            for pair, decisions in grouped.items():
                states = {(d['same_business_kind'], d['same_granularity']) for d in decisions}
                state = next(iter(states)) if len(states) == 1 else ('UNKNOWN','UNKNOWN')
                pairs[pair] = {'status': 'supported' if state == ('YES','YES') else
                    'rejected' if 'NO' in state else 'uncertain', 'basis': 'cited_semantic_group_review', 'decisions': decisions}
    # Exact semantic descriptions are interchangeable evidence, not extra identity judgments.
    # Preserve explicit conflicting pair decisions so complete-link grouping can still abstain.
    by_id={t['id']:t for t in supported}
    for pair,decision in list(pairs.items()):
        if decision['status']!='supported':continue
        left_id,right_id=sorted(pair)
        equivalent=[]
        for identifier in (left_id,right_id):
            target=by_id[identifier]
            equivalent.append([t['id'] for t in supported if
                meaning_key(t['business_meaning'])==meaning_key(target['business_meaning']) and
                meaning_key(t['instance_granularity'])==meaning_key(target['instance_granularity'])])
        for left in equivalent[0]:
            for right in equivalent[1]:
                if left==right:continue
                inferred=frozenset((left,right))
                if inferred not in pairs:pairs[inferred]={'status':'supported',
                    'basis':'substitution_of_identical_meaning_and_unit','supporting_target_ids':sorted(pair)}
    groups = [{t['id']} for t in supported]
    # Every cross-pair must support both kind and unit. A-B plus B-C cannot erase an A-C conflict.
    for pair, decision in sorted(pairs.items(), key=lambda item: sorted(item[0])):
        if decision['status'] != 'supported':
            continue
        touching = [g for g in groups if g & pair]
        if len(touching) != 2:
            continue
        if all(pairs.get(frozenset((a,b)), {}).get('status') == 'supported' for a in touching[0] for b in touching[1]):
            merged = touching[0] | touching[1]
            groups = [g for g in groups if g not in touching] + [merged]
        else:
            diagnostics.append({'reason': 'group_meaning_or_granularity_not_consistent', 'target_ids': sorted(set.union(*touching))})
    return sorted(groups, key=lambda g: sorted(g)), pairs, diagnostics, audits


def _identity_mapping_claim(left, right, relation):
    """PURPOSE: Reuse validated key equality; legacy identifier-scope prose is optional compatibility evidence.
    INPUT: Same-ET primary target descriptions and checked physical identity relation.
    OUTPUT: shared/independent/uncertain key-correspondence result; absence of evidence never merges keys.
    A valid MERGE relation backed by pair-specific evidence already passed the identity validator (type and
    key checks, no collisions, verified key containment); it is reused here, not re-derived from DD wording.
    A MERGE whose only support is another Table's wording stays uncertain.
    """
    text = left['table_definition'] + ' ' + right['table_definition']
    if relation and relation.get('statistics', {}).get('collision_check', {}).get('conflicts'):
        return 'uncertain', 'observable_identifier_conflict'
    if re.search(r'\b(independent|separate|distinct)\b[^.!?]{0,70}\b(namespace|identifier system|id system)\b', text, re.I):
        return 'independent', 'documented_independent_identifier_scope'
    if (relation and relation.get('final_decision') == 'MERGE' and relation.get('validation_status') == 'valid'
            and relation.get('pair_specific_evidence')):
        return 'shared', 'validated_pair_specific_entity_equality'
    addressed = any(re.search(r'\bsame\b[^.!?]{0,90}\b(identity|instance|namespace|identifier)\b', side['table_definition'], re.I)
                    and re.search(r'(?<!\w)' + re.escape(other['source']['table']) + r'(?!\w)', side['table_definition'], re.I)
                    for side,other in ((left,right),(right,left)))
    global_key_scope = all(any(re.search(r'\bglobal\b', c.get('definition',''), re.I)
                              for c in side.get('key_dictionary', [])) for side in (left,right))
    if ((addressed or global_key_scope) and
            re.search(r'\bsame\b[^.!?]{0,70}\b(namespace|identifier scope|identifier space)\b', text, re.I) and
            left['structural_validation'].get('unique') and right['structural_validation'].get('unique')):
        return 'shared', 'legacy_explicit_identifier_equality_rule'
    return 'uncertain', 'same_type_instance_correspondence_unresolved'


def _verified_identifier_links(db_path, primary, targets, references, group_ids):
    """PURPOSE: Reuse verified same-ET PK/UK/FK correspondences independently of DD scope wording.
    INPUT: Already classified primary targets, all typed identifier targets and forward reference inventory.
    OUTPUT: Equality pairs and one-hop canonical projections, backed by full-domain/injective SQL validation.
    No field names, overlap alone, actor/subject role, or LLM namespace answer authorizes a link.
    """
    mains = {t['source']['table']: t for t in primary}
    members = set(group_ids)
    equality, options = set(), defaultdict(list)
    with closing(connect_readonly(db_path)) as connection:
        for child, edges in forward_adjacency(references).items():
            left = mains.get(child)
            if left is None:
                continue
            for edge in edges:
                right = mains.get(edge['right_table'])
                if right is None or right['id'] == left['id'] or reference_constraint_issues(connection, [edge]):
                    continue
                source_key = next((t for t in targets if t['source']['table']==child and
                    len(t['source']['columns'])==len(edge['left_columns']) and
                    set(t['source']['columns'])==set(edge['left_columns']) and t['constraint_kind']!='reference'
                    and t['id'] in members and t['structural_validation'].get('unique')), None)
                target_key = next((t for t in targets if t['source']['table']==edge['right_table'] and
                    len(t['source']['columns'])==len(edge['right_columns']) and
                    set(t['source']['columns'])==set(edge['right_columns']) and t['constraint_kind']!='reference'
                    and t['id'] in members and t['structural_validation'].get('unique')), None)
                if source_key is None or target_key is None:
                    continue
                states = reference_path_row_states(connection, child, [edge], right['source']['columns'])
                # A provider projection must account for every source row; NULL references cannot erase a population.
                if states['null_reference_rows'] or states['unmatched_reference_rows']:
                    continue
                left_cols, right_cols = edge['left_columns'], edge['right_columns']
                join = ' AND '.join(f's.{qi(a)}=p.{qi(b)}' for a,b in zip(left_cols,right_cols))
                key = ','.join(f'p.{qi(c)}' for c in right['source']['columns'])
                mapped = connection.execute(f'SELECT COUNT(*),COUNT(DISTINCT json_array({key})) '
                    f'FROM {qi(child)} s JOIN {qi(edge["right_table"])} p ON {join}').fetchone()
                if mapped[0] != states['scope_rows'] or mapped[1] != states['scope_rows']:
                    continue
                same_columns = (left_cols == left['source']['columns'] and
                                right_cols == right['source']['columns'])
                if same_columns:
                    from src.step1_understand.verify_entity_identity_mappings import _physical_key_types, _type_affinity
                    lt = _physical_key_types(connection, {'table': child, 'pk': left_cols})
                    rt = _physical_key_types(connection, {'table': edge['right_table'], 'pk': right_cols})
                    same_types = [_type_affinity(lt[c]) for c in left_cols] == [_type_affinity(rt[c]) for c in right_cols]
                    different_storage = ' OR '.join(f'typeof(s.{qi(a)})!=typeof(p.{qi(b)})'
                                                               for a,b in zip(left_cols,right_cols))
                    storage_conflicts = connection.execute(f'SELECT COUNT(*) FROM {qi(child)} s '
                        f'JOIN {qi(edge["right_table"])} p ON {join} WHERE {different_storage}').fetchone()[0]
                    if same_types and storage_conflicts == 0:
                        equality.add(frozenset((left['id'], right['id'])))
                        continue
                options[child].append({'target_table': edge['right_table'], 'joins':[deepcopy(edge)],
                                       'canonical_target_id': right['id']})
    projections = {}
    for child, choices in sorted(options.items()):
        if len(choices) != 1:
            continue  # Competing same-ET references require the existing conflict machinery, never arbitrary choice.
        choice = choices[0]
        cursor, seen = choice['target_table'], {child}
        while cursor in projections and cursor not in seen:
            seen.add(cursor); cursor = projections[cursor]['target_table']
        if cursor in seen:
            continue
        projections[child] = choice
    return equality, projections


def resolve_instance_identity(db_path, group, targets, objects, tables, dd, references, config, llm, cache):
    """PURPOSE: Resolve Entity equality only inside one already classified ET.
    INPUT: Semantic group, typed keys, verified references, public DB/DD and optional identity reviewer.
    OUTPUT: Executable population provider maps, key-correspondence decisions, identity relations and projections.
    """
    indexed = {t['id']: t for t in targets}
    by_object = {o['table']: o for o in objects}
    schema = {t.name: t for t in tables}
    mains = {t['source']['table']: t for t in targets if t['id'] in group and t['representation_role'] in SUBJECT_ROLES and t['constraint_kind'] != 'reference'
             and t['source']['columns'] == by_object.get(t['source']['table'], {}).get('pk')}
    primary = list(mains.values())
    verified_equalities, projections = _verified_identifier_links(db_path, primary, targets, references, group)
    physical = [by_object[t['source']['table']] for t in primary if t['source']['table'] not in projections]
    overrides = {frozenset(by_object[indexed[i]['source']['table']]['id'] for i in pair): {
        'same_entity_type': 'YES', 'identity_correspondence': 'YES', 'row_grain_compatible': 'YES',
        'explicit_identity_mapping': 'PRESENT', 'semantic_decision': 'SUPPORT',
        'correspondence_evidence_validated': True, 'reason': 'Reused verified same-ET identifier FK.'}
        for pair in verified_equalities}
    relations = assess_key_identity_mappings(db_path, physical, dd,
        overlap_threshold=config.identity_candidate_overlap_threshold,
        llm=llm if config.pairwise_identity_llm else None, model=config.model, cache=cache,
        semantic_overrides=overrides, unresolved_only=True)
    relations_by_pair = {frozenset((r['left_table'], r['right_table'])): r for r in relations}
    decisions = []
    for left, right in combinations(primary, 2):
        relation = relations_by_pair.get(frozenset((left['source']['table'], right['source']['table'])))
        status, basis = _identity_mapping_claim(left, right, relation)
        if (frozenset((left['id'], right['id'])) in verified_equalities and not
                (relation or {}).get('statistics', {}).get('collision_check', {}).get('conflicts')):
            status, basis = 'shared', 'validated_identifier_fk_equality'
        if _key_type(schema[left['source']['table']], left['source']['columns']) != _key_type(schema[right['source']['table']], right['source']['columns']):
            if status == 'shared':
                status, basis = 'uncertain', 'key_correspondence_type_mismatch'
        if status == 'shared' and relation and relation.get('validator', {}).get('type_compatible') is False:
            status,basis = 'uncertain','key_correspondence_type_mismatch'
        decisions.append({'left': left['id'], 'right': right['id'], 'status': status, 'basis': basis,
                          'identity_relation_id': relation.get('id') if relation else None})
    parent = {t['id']: t['id'] for t in primary}
    def root(identifier):
        """PURPOSE: Resolve a validated key-equality component. INPUT: Target ID. OUTPUT: Component root."""
        while parent[identifier] != identifier:
            identifier = parent[identifier]
        return identifier
    for decision in decisions:
        if decision['status'] != 'shared':
            continue
        a,b = root(decision['left']), root(decision['right'])
        combined = {i for i in parent if root(i) in {a,b}}
        conflicts = [d for d in decisions if {d['left'],d['right']} <= combined and (d['status'] == 'independent' or
                    d['basis'] in {'observable_identifier_conflict','key_correspondence_type_mismatch'})]
        if conflicts:
            decision.update(status='uncertain', basis='identity_component_conflict')
        else:
            parent[b] = a
    for decision in decisions:
        if decision['status'] == 'uncertain' and root(decision['left']) == root(decision['right']):
            decision.update(status='shared', basis='validated_mapping_transitivity')
    # Only already verified same-ET identifier correspondences project to a canonical provider.
    # Projected tables reuse canonical identification and do not introduce duplicate population providers.
    for decision in decisions:
        left,right = indexed[decision['left']], indexed[decision['right']]
        projection = projections.get(left['source']['table']) or projections.get(right['source']['table'])
        if projection and projection['target_table'] in {left['source']['table'], right['source']['table']}:
            decision.update(status='mapped', basis='declared_unique_identifier_projection')
    providers = []
    for target in primary:
        table = target['source']['table']
        if table in projections:
            continue
        namespace_members = sorted(i for i in parent if root(i) == root(target['id']))
        namespace = contract_id('NS', ['declared_identifier_scope', namespace_members])
        # Legacy serialized alias; this component prevents collisions and is never an LLM judgment.
        validation = target['structural_validation']
        item = {'representation_id': by_object[table]['id'], 'table': table,
            'key_columns': list(target['source']['columns']), 'key_types': _key_type(schema[table], target['source']['columns']),
            'identity_scope_id': namespace, 'namespace_id': namespace,
            'legacy_internal_fields': ['namespace_id'], 'mapping_kind': 'direct_key', 'scope': 'all_rows',
            'identification_target_id': target['id'],
            'validation': {'status': 'pass' if validation.get('unique') else 'fail', 'executed': True,
                           'row_count': validation.get('row_count'), 'null_count': validation.get('null_count'),
                           'distinct_count': validation.get('distinct_count')}}
        providers.append(item)
    provider_target_ids = {p['identification_target_id'] for p in providers}
    complete = bool(providers) and all(p['validation']['status'] == 'pass' for p in providers) and all(
        d['status'] in {'shared','independent','mapped'} or root(d['left']) == root(d['right'])
        for d in decisions if {d['left'],d['right']} <= provider_target_ids)
    return providers, decisions, relations, projections, complete


def build_identification_rules(db_path, targets, entity_types, references, max_hops=MAX_ATTRIBUTION_HOPS):
    """PURPOSE: Compile partial row-to-canonical-Entity rules, including repeated FK and alternate-key lookup.
    INPUT: Classified targets, resolved population providers and immutable forward reference catalog.
    OUTPUT: Deterministic SQL projection rules with null/unmatched/ambiguity validation; no generated SQL.
    """
    max_hops = bounded_hops(max_hops)
    adjacency = forward_adjacency(references)
    result = []
    with closing(connect_readonly(db_path)) as connection:
        adjacency = {table: [edge for edge in edges if not reference_constraint_issues(connection, [edge])]
                     for table, edges in adjacency.items()}
        for target in targets:
            entity = next((e for e in entity_types if e['id'] == target.get('entity_type_id')), None)
            if entity is None:
                continue
            source = target['source']['table']
            options = []
            for mapping in entity['population']['maps']:
                queue = [(source, [], {source})]
                while queue:
                    table, joins, seen = queue.pop(0)
                    if table == mapping['table'] and (target['constraint_kind'] != 'reference' or joins):
                        options.append((mapping, joins))
                        continue
                    for edge in adjacency.get(table, []):
                        identifier_lookup = (not joins and target['constraint_kind'] == 'reference'
                                             and edge['relationship_id'] == target['reference']['relationship_id'])
                        if edge['right_table'] in seen and not identifier_lookup:
                            continue
                        # A reference target's interpretation must use that exact first reference.
                        if not joins and target['constraint_kind'] == 'reference' and edge['relationship_id'] != target['reference']['relationship_id']:
                            continue
                        queue.append((edge['right_table'], [*joins, edge], seen | {edge['right_table']}))
            if not options:
                result.append({'id': contract_id('IR', target['id']), 'target_id': target['id'],
                    'entity_type_id': entity['id'], 'source': deepcopy(target['source']), 'status': 'uncertain',
                    'role':'references' if target['constraint_kind']=='reference' else 'identifies',
                    'row_condition':{'kind':'all_not_null','columns':list(target['source']['columns'])},
                    'reason': 'canonical_identification_projection_unavailable'})
                continue
            for mapping, joins in options:
                aliases = ['s0'] + ['j' + str(i+1) for i in range(len(joins))]
                from_sql = qi(source) + ' s0'
                for i, edge in enumerate(joins):
                    conditions = ' AND '.join(f'{aliases[i]}.{qi(a)} = {aliases[i+1]}.{qi(b)}'
                                              for a,b in zip(edge['left_columns'], edge['right_columns']))
                    from_sql += f" LEFT JOIN {qi(edge['right_table'])} {aliases[i+1]} ON {conditions}"
                nonnull = ' AND '.join(f's0.{qi(c)} IS NOT NULL' for c in target['source']['columns'])
                canonical = ','.join(f'{aliases[-1]}.{qi(c)}' for c in mapping['key_columns'])
                present = ' AND '.join(f'{aliases[-1]}.{qi(c)} IS NOT NULL' for c in mapping['key_columns'])
                # Same NULL policy as event attribution paths: a NULL reference at any hop is excluded and
                # reported; only a fully non-NULL reference without a target row is unmatched.
                states = reference_path_row_states(connection, source, joins, mapping['key_columns'],
                                                   predicate=nonnull)
                total = states['scope_rows'] - states['null_reference_rows']
                matched = states['matched_rows']
                source_tuple = 'json_array(' + ','.join(f's0.{qi(c)}' for c in target['source']['columns']) + ')'
                ambiguity_sql = (f'SELECT COUNT(*) FROM (SELECT {source_tuple} AS identifier FROM {from_sql} '
                    f'WHERE {nonnull} AND {present} GROUP BY {source_tuple} HAVING COUNT(DISTINCT json_array({canonical})) > 1)')
                ambiguous = connection.execute(ambiguity_sql).fetchone()[0]
                identifier_nulls = connection.execute(
                    f'SELECT COUNT(*) FROM {qi(source)} s0 WHERE NOT ({nonnull})').fetchone()[0]
                # An all-NULL reference proves no attribution; population providers are judged by their own keys.
                no_identifier = (target['constraint_kind'] == 'reference' and total == 0
                                 and states['null_reference_rows'] + identifier_nulls > 0)
                passed = (states['unmatched_reference_rows'] == 0 and ambiguous == 0 and not no_identifier
                          and mapping['validation']['status'] == 'pass')
                result.append({'id': contract_id('IR', [target['id'], mapping['id'], [e['relationship_id'] for e in joins]]),
                    'target_id': target['id'], 'entity_type_id': entity['id'], 'source': deepcopy(target['source']),
                    'representation_role': target['representation_role'], 'status': 'supported' if passed else 'uncertain',
                    'role':'references' if target['constraint_kind']=='reference' else 'identifies',
                    'row_condition':{'kind':'all_not_null','columns':list(target['source']['columns'])},
                    'identity_scope_id': identity_scope_id(mapping), 'namespace_id': mapping['namespace_id'],
                    'legacy_internal_fields': ['namespace_id'], 'canonical_table': mapping['table'],
                    'canonical_columns': list(mapping['key_columns']), 'entity_instance_map_id': mapping['id'],
                    'joins': deepcopy(joins), 'projection_sql': f'SELECT json_array({canonical}) AS entity_key FROM {from_sql} WHERE {nonnull} AND {present}',
                    'validation': {'executed': True, 'scope_rows': states['scope_rows'] + identifier_nulls,
                                   'null_reference_rows': states['null_reference_rows'] + identifier_nulls,
                                   'non_null_source_rows': total, 'matched_rows': matched,
                                   'unmatched_rows': states['unmatched_reference_rows'], 'ambiguous_identifier_tuples': ambiguous,
                                   'source_uniqueness_required': False,
                                   'scope': 'complete_non_null_identifier_domain'},
                    **({'reason': 'no_non_null_identifier'} if no_identifier else {}),
                    'null_policy': 'undefined_entity_for_null_identifier', 'evidence': deepcopy(target['evidence'])})
    return result


def build_meaning_first_model(db_path, tables, dd, objects, key_profiles, references, config,
                              llm=None, cache=None, value_evidence=()):
    """PURPOSE: Execute target discovery → semantic ET classification → within-ET identity → row rules.
    INPUT: Public physical evidence and immutable config; identities never seed semantic ET groups.
    OUTPUT: Native ET/population/rule inventories and complete ordered stage/call audits.
    """
    stages = []
    targets = discover_identification_targets(db_path, tables, dd, objects, key_profiles, references)
    stages.append('discover_identification_targets')
    reviewer = llm if config.global_ot_review else None
    audits = interpret_identification_targets(targets, dd, reviewer, config.model, cache, value_evidence)
    stages.append('interpret_meaning_and_granularity')
    groups, pairs, diagnostics, group_audits = classify_entity_types(targets, dd, reviewer, config.model, cache)
    audits.extend(group_audits)
    stages.extend(['classify_entity_types', 'review_group_consistency'])
    indexed = {t['id']: t for t in targets}
    entity_types, maps, populations, identity_relations, identity_decisions = [], [], [], [], []
    for group in groups:
        descriptions = [indexed[i] for i in sorted(group)]
        subjects = [t for t in descriptions if t['representation_role'] in SUBJECT_ROLES and t['constraint_kind'] != 'reference']
        if not subjects:
            continue
        provider_maps, decisions, relations, projections, complete = resolve_instance_identity(
            db_path, group, targets, objects, tables, dd, references, config, llm, cache)
        identity_relations.extend(relations)
        audits.extend(r['semantic_judge_audit'] for r in relations if r.get('semantic_judge_audit'))
        label = sorted(subjects, key=lambda t: (t['representation_role'] != 'primary_subject', len(t['business_meaning']), t['id']))[0]['business_meaning']
        et_id = contract_id('ET', {'meaning_and_units': sorted({(meaning_key(t['business_meaning']), meaning_key(t['instance_granularity'])) for t in descriptions}),
                                 'classified_target_contracts': sorted(group)})
        for target in descriptions:
            target['entity_type_id'] = et_id
        for mapping in provider_maps:
            mapping['entity_type_id'] = et_id
            mapping['id'] = contract_id('IM', {k:v for k,v in mapping.items() if k != 'validation'})
        population = {'entity_type_id': et_id, 'maps': provider_maps, 'set_semantics': 'DISTINCT_UNION',
            'status': 'valid' if complete else 'unresolved', 'identity_complete': complete,
            # Serialized copies point at identity_mapping_assessments; the POP contract ID below is still
            # computed from the unchanged internal decision records, so existing IDs stay stable.
            'unresolved_identity_pairs': rename_identity_references(
                [d for d in decisions if d['status'] == 'uncertain']),
            'version': VERSION, 'selection_independent': True}
        population['id'] = contract_id('POP', {'entity_type_id': et_id, 'maps': [m['id'] for m in provider_maps],
                                                'identity_decisions': decisions})
        members = sorted({'O:' + t['source']['table'] for t in subjects if any(o['table'] == t['source']['table'] for o in objects)})
        canonical = provider_maps[0]['representation_id'] if provider_maps else members[0] if members else None
        canonical_columns = provider_maps[0]['key_columns'] if provider_maps else []
        from src.step1_understand.entity_naming_metadata import naming_metadata
        naming = naming_metadata(label.title(), [{'name': label.title(), 'score': 1, 'basis': 'documented_business_meaning'}],
                                 [deepcopy(e) for t in descriptions for e in t['evidence']])
        entity_types.append({**naming, 'id': et_id, 'entity_type_id': et_id, 'node_type': 'entity_type',
            'kind': 'entity_type', 'name': label.title(), 'canonical_name': label.title(), 'display_name': label.title(),
            'business_definition': ' '.join(dict.fromkeys(t['table_definition'] for t in subjects)),
            'business_meaning': label, 'instance_granularity': subjects[0]['instance_granularity'],
            'members': members, 'representation_ids': members, 'table_key_ids': members,
            'identification_target_ids': sorted(group), 'identification_rules': [],
            'semantic_status': 'supported', 'validation_status': 'valid', 'selectable': bool(members),
            'semantic_classification_policy':'meaning_and_instance_unit_only',
            'roles': ['business_entity'], 'population': population,
            'identity_decisions': rename_identity_references(decisions),
            'identity_scope_ids': sorted({m['identity_scope_id'] for m in provider_maps}),
            'identity_namespace_ids': sorted({m['namespace_id'] for m in provider_maps}),
            'legacy_internal_fields': ['identity_namespace_ids'],
            'identity_contract': IDENTITY_CONTRACT,
            'case_key': {'canonical_member': canonical, 'member_keys': {'O:'+t['source']['table']: t['source']['columns'] for t in subjects},
                         'fields': list(canonical_columns)},
            'key': list(canonical_columns), 'case_id_map': {'status': 'valid' if complete else 'unresolved',
                                                          'executed': True, 'identity_complete': complete},
            'rollups': [], 'evidence': [deepcopy(e) for t in descriptions for e in t['evidence']],
            'classification_basis': 'business_meaning_and_instance_granularity_before_identity'})
        maps.extend(provider_maps); populations.append(population)
        identity_decisions.extend({**d,'entity_type_id':et_id} for d in decisions)
    stages.append('resolve_instance_identity_within_types')
    rules = build_identification_rules(db_path, targets, entity_types, references, max_hops=config.max_hops)
    for entity in entity_types:
        entity['identification_rules'] = [r for r in rules if r['entity_type_id'] == entity['id']]
        # An incomplete projection of a primary representation leaves overall population unresolved.
        if any(r['status'] != 'supported' and indexed[r['target_id']]['representation_role'] in SUBJECT_ROLES and indexed[r['target_id']]['constraint_kind'] != 'reference' for r in entity['identification_rules']):
            entity['population'].update(status='unresolved', identity_complete=False)
    for entity in entity_types:
        entity['case_id_map'].update(status=entity['population']['status'],
                                     identity_complete=entity['population']['identity_complete'])
    stages.append('build_validated_identification_rules')
    representations = build_representations(tables, dd, objects)
    for representation in representations:
        local = [t for t in targets if t['source']['table'] == representation['table']]
        main = next((t for t in local if t['source']['columns'] == representation['record_key'] and t['constraint_kind'] != 'reference'), None)
        types = sorted({t['entity_type_id'] for t in local if t.get('entity_type_id')})
        representation.update(identification_target_ids=[t['id'] for t in local], entity_type_ids=types,
            entity_type_id=main.get('entity_type_id') if main else None,
            roles=[main['representation_role']] if main else ['unknown'],
            record_identity_status='valid' if main and main['structural_validation'].get('unique') else 'unknown',
            entity_mapping_status='valid' if main and main.get('entity_type_id') else
                                  'not_applicable' if main and main['status'] == 'rejected' else 'unresolved',
            entity_decision={'reason':'identifier_level_classification','target_status':main['status'] if main else 'uncertain'})
    return {'entity_model_version': VERSION, 'identification_targets': targets,
        'entity_types': entity_types, 'table_semantic_profiles': representations,
        'entity_instance_maps': maps, 'entity_case_populations': populations, 'identification_rules': rules,
        'entity_identity_decisions': identity_decisions, 'entity_model_diagnostics': diagnostics,
        'semantic_classification_pairs': [{'target_ids': sorted(k), **v} for k,v in pairs.items()],
        'entity_build_stages': stages, 'entity_review_audits': audits,
        'entity_identity_relations': identity_relations, 'semantic_entity_memberships': [],
        'business_value_evidence': deepcopy(list(value_evidence)),
        'entity_model_contract': 'meaning_and_unit_before_instance_identity'}
