"""Bounded public evidence retrieval for PI review; retrieval never approves a rule or case."""

from __future__ import annotations
import hashlib
import json
import re
from src.common.runtime_input_contract import sanitize_dictionary, validate_runtime_graph, require_no_oracle_payload
from src.common.rank_evidence_documents import rank_documents, reciprocal_rank_fusion
from src.common.local_semantic_embeddings import local_semantic_encoder
from src.step2_retrieve_and_interpret.event_definition_details import get_event_definition_details
from src.common.schema_metadata import normalize
VERSION = 'pi-public-evidence-v1'
AUTO_ENCODER = object()


def _carrier_values(binding):
    """PURPOSE: Preserve observed carrier literals, including zero and one-character codes.
    INPUT: One runtime Event definition. OUTPUT: Deduplicated typed scalar values; no DB scans.
    """
    values = list(binding.get('raw_values') or [])
    for field in ('alpha', 'activity_source'):
        source = binding.get(field) or {}
        if isinstance(source, dict) and source.get('kind') == 'value' and 'value' in source:
            values.append(source['value'])
    return list({json.dumps(v, sort_keys=True): v for v in values if isinstance(v, (str, int, float, bool))}.values())


def public_evidence_documents(graph):
    """PURPOSE: Index only allowlisted public DD fields and EEG semantic evidence.
    INPUT: Runtime EEG; no paths, Gold, sibling files or evaluator assets are read.
    OUTPUT: Stable scoped text chunks with provenance, event/ET links and documented value meanings.
    """
    validate_runtime_graph(graph)
    dd, _ = sanitize_dictionary(graph.get('data_dictionary') or {})
    definitions = graph.get('event_definitions', [])
    documents = {}

    def add(text, kind, source, *, table=None, column=None, event_ids=(), et_ids=(), value=None, terms=()):
        """PURPOSE: Preserve literal source chunks and their exact offsets.
        INPUT: Original text plus scope and optional code/aliases. OUTPUT: Updates this index only.
        """
        if not isinstance(text, str) or not text.strip():
            return
        linked = set(event_ids)
        if table:
            for binding in definitions:
                names = {binding.get('activity_column'), *(binding.get('timestamp_columns') or [])}
                names.add((binding.get('alpha') or {}).get('column'))
                names.add((binding.get('activity_source') or {}).get('column'))
                if binding.get('source_table', binding.get('table')) != table or column and column not in names:
                    continue
                if value is None or str(value) in {str(v) for v in _carrier_values(binding)}:
                    linked.add(binding['id'])
        for start in range(0, len(text), 900):
            chunk = text[start:start+900]
            if not chunk.strip():
                continue
            identity = json.dumps([source, start, chunk], ensure_ascii=False)
            identifier = 'EV:' + hashlib.sha256(identity.encode()).hexdigest()[:20]
            documents[identifier] = {
                'id': identifier, 'text': chunk, 'kind': kind,
                'event_ids': sorted(linked), 'entity_type_ids': sorted(set(et_ids)),
                'source': {'ref': source, 'table': table, 'column': column,
                           'start': start, 'end': start+len(chunk)},
                'terms': list(dict.fromkeys(str(t) for t in terms if str(t).strip())),
                'value': value}

    columns = {}
    for table in dd.get('tables', []):
        name = table.get('table', table.get('table_name', table.get('name')))
        for field in ('definition', 'description', 'row_grain', 'row_meaning', 'readable_name'):
            add(table.get(field), 'dictionary', f'T:{name}:{field}', table=name)
        for column in table.get('columns', []):
            col = column.get('column', column.get('column_name', column.get('name')))
            columns[name, col] = column
    for column in dd.get('columns', []):
        name = column.get('table', column.get('table_name'))
        col = column.get('column', column.get('column_name', column.get('name')))
        columns[name, col] = column
    for (table, column), record in sorted(columns.items(), key=lambda item: str(item[0])):
        for field in ('definition', 'description', 'readable_name'):
            add(record.get(field), 'dictionary', f'C:{table}.{column}:{field}', table=table, column=column)
        for index, synonym in enumerate(record.get('synonyms') or []):
            add(synonym, 'dictionary_alias', f'C:{table}.{column}:synonym:{index}', table=table, column=column)
        domains = record.get('value_domain') or record.get('code_domain') or {}
        for domain_name, domain in [('domain', domains), ('meaning', record.get('code_meanings') or {})]:
            if not isinstance(domain, dict):
                continue
            for code, info in domain.items():
                meanings = ([info] if isinstance(info, str) else
                            [info.get(k) for k in ('label', 'meaning', 'definition')] if isinstance(info, dict) else [])
                aliases = info.get('aliases', info.get('synonyms', [])) if isinstance(info, dict) else []
                aliases = [aliases] if isinstance(aliases, str) else aliases
                terms = [str(code), *[x for x in meanings if isinstance(x, str)], *aliases]
                for index, meaning in enumerate([*meanings, *aliases]):
                    add(meaning, 'value_meaning', f'C:{table}.{column}:{domain_name}:{code}:{index}',
                        table=table, column=column, value=code, terms=terms)
    for field in ('semantic_statements', 'processes', 'business_rules', 'business_process_overview'):
        items = dd.get(field) or []
        items = [items] if isinstance(items, (str, dict)) else items
        for index, item in enumerate(items):
            if isinstance(item, str):
                add(item, 'business_context', f'DD:{field}:{index}')
            elif isinstance(item, dict):
                add(item.get('text', item.get('definition')), 'business_context',
                    str(item.get('id') or f'DD:{field}:{index}'),
                    table=item.get('table'), column=item.get('column'))
    for binding in definitions:
        identifier = binding['id']
        semantics = binding.get('activity_semantics') or {}
        for field in ('meaning', 'description', 'code_meaning'):
            add(semantics.get(field), 'event_semantics', f'{identifier}:{field}', event_ids=[identifier])
        for field in ('evidence', 'citations'):
            for index, item in enumerate(semantics.get(field) or []):
                if isinstance(item, dict):
                    add(item.get('quote', item.get('text', item.get('detail'))), 'event_semantics',
                        f'{identifier}:{field}:{index}', event_ids=[identifier])
        label = binding.get('activity_label') or binding.get('activity')
        add(label, 'event_label', f'{identifier}:label', event_ids=[identifier])
        for value in _carrier_values(binding):
            add(str(value), 'observed_value', f'{identifier}:value:{json.dumps(value)}',
                event_ids=[identifier], value=value, terms=[str(value)])
    for et in graph.get('entity_types', graph.get('table_key_records', [])):
        for field in ('business_definition', 'business_meaning', 'instance_granularity'):
            add(et.get(field), 'entity_definition', f"{et['id']}:{field}", et_ids=[et['id']])
    return sorted(documents.values(), key=lambda d: d['id'])


def retrieval_queries(question, requirements=None, issues=(), definitions=()):
    """PURPOSE: Search the original request and grounded requirement/focus phrases.
    INPUT: Request, independently parsed requirements and current differences/definition labels.
    OUTPUT: Unique queries; implicit requests never acquire an invented activity list.
    """
    queries = []
    by_id = {d['id']: d for d in definitions}
    for issue in issues:
        target = issue.get('target')
        if target and target in question:
            queries.append(target)
        elif target in by_id:
            item = by_id[target]
            queries.append(question + ' ' + str(item.get('activity_label') or item.get('activity') or ''))
    requirements = requirements or {}
    for item in [*requirements.get('activity_requirements', []),
                 requirements.get('process_focus') or {}, requirements.get('case_requirement') or {}]:
        if item.get('span') and item['span'] in question:
            queries.append(' '.join([item['span'], item.get('meaning', ''), *item.get('qualifiers', [])]))
    queries.append(question)
    return list(dict.fromkeys(q for q in queries if q.strip()))


def _mentions(term, query):
    """PURPOSE: Match short codes and documented aliases without substring collisions.
    INPUT: One source term and query. OUTPUT: Token-boundary exact match, including one-character terms.
    """
    term = str(term)
    if len(term) == 1 and term.isascii() and term.isalpha():
        return bool(re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', query))
    term, query = normalize(term), normalize(query)
    return bool(term) and bool(re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', query))


def _supported_hit(record):
    """PURPOSE: Exclude arbitrary zero-score or weak character-only retrieval.
    INPUT: Ranked document. OUTPUT: Whether any independent retrieval channel supports a hit.
    """
    score = record['similarity']
    return score['bm25'] > 0 or score['cosine'] >= .25 or score['semantic_rank'] is not None


def link_values(query, documents, *, encoder=None, top_k=10):
    """PURPOSE: Prefer documented code/alias meanings, then exact observed values, then fuzzy candidates.
    INPUT: Grounded query and scoped value evidence; optional independent semantic channel.
    OUTPUT: Candidate documents and stage audit; ambiguous columns stay separate and never auto-approve.
    """
    values = [d for d in documents if d['value'] is not None]
    documented = [d for d in values if d['kind'] == 'value_meaning'
                  and any(_mentions(term, query) for term in d['terms'])]
    exact = [d for d in values if _mentions(d['value'], query)]
    if documented or exact:
        matches, stage = (documented, 'documented_code_or_alias') if documented else (exact, 'exact_observed_value')
    else:
        matches = [d for d in rank_documents(query, [
            dict(d, text=' '.join([d['text'], *d['terms']])) for d in values], encoder=encoder) if _supported_hit(d)]
        stage = 'unresolved_parallel_search'
    return matches[:top_k], {'query': query, 'stage': stage, 'candidate_count': len(matches),
                             'truncated': len(matches) > top_k, 'candidate_only': True}


class PIEvidenceRetriever:
    """Index once per interpretation and serve bounded original evidence to review/revision."""

    def __init__(self, graph, *, encoder=AUTO_ENCODER):
        """PURPOSE: Bind an immutable EEG to a public evidence index.
        INPUT: Runtime graph and optional injected encoder (None means sparse only).
        OUTPUT: Request-local retriever with lazy offline encoder loading.
        """
        self.graph, self.encoder = graph, encoder
        self.documents = public_evidence_documents(graph)
        self.semantic_audit = {'status': 'injected' if encoder is not None else 'disabled'}
        self.audits = []

    def retrieve(self, question, state, requirements, catalog, *, issues=(), aliases=None,
                 top_k=10, max_chars=12000):
        """PURPOSE: Supply ranked literal evidence without filtering the selectable EEG universe.
        INPUT: Request/current PI, parser, current ET catalog, optional aliases and evidence budgets.
        OUTPUT: Small model payload plus saved score/provenance audit; graph and PI are unchanged.
        """
        if top_k < 1 or max_chars < 1:
            raise ValueError('invalid_evidence_retrieval_budget')
        if self.encoder is AUTO_ENCODER:
            self.encoder, self.semantic_audit = local_semantic_encoder()
        queries = retrieval_queries(question, requirements, issues, self.graph.get('event_definitions', []))
        ranked_lists, value_audits, scores = [], [], {}
        for query in queries:
            ranked = rank_documents(query, self.documents, encoder=self.encoder)
            hits = [d for d in ranked if _supported_hit(d)][:top_k]
            linked, value_audit = link_values(query, self.documents, encoder=self.encoder, top_k=top_k)
            value_audits.append(value_audit)
            ranked_lists.append([d['id'] for d in linked])
            ranked_lists.append([d['id'] for d in hits])
            scores[query] = {d['id']: d['similarity'] for d in hits}
        fused = reciprocal_rank_fusion(ranked_lists)
        ordered = sorted(fused, key=lambda identifier: (-fused[identifier], identifier))
        lookup = {d['id']: d for d in self.documents}
        selected, used, omitted, provenance = [], 0, [], {}
        for identifier in ordered:
            record = lookup[identifier]
            event_ids = record['event_ids']
            visible_events = [aliases.get(e) for e in event_ids if e in aliases] if aliases is not None else event_ids
            visible_ets = [aliases.get(e) for e in record['entity_type_ids'] if e in aliases] if aliases is not None else record['entity_type_ids']
            item = {'evidence_id': identifier, 'kind': record['kind'], 'text': record['text'],
                    'event_definition_ids': sorted(set(visible_events)),
                    'entity_type_ids': sorted(set(visible_ets)), 'candidate_only': True,
                    'definition_status': [{
                        'id': aliases[eid] if aliases is not None else eid,
                        'eligible': bool(catalog[eid].get('eligible')),
                        'history_supported': bool(catalog[eid].get('binding_policy', {}).get('history_supported')),
                        'attribution_status': catalog[eid].get('attribution', {}).get('status', 'unknown')}
                        for eid in event_ids if eid in catalog and (aliases is None or eid in aliases)]}
            if record['value'] is not None:
                item['value'] = record['value']
            size = len(json.dumps(item, ensure_ascii=False))
            if used + size > max_chars or len(selected) >= top_k:
                omitted.append(identifier)
                continue
            selected.append(item)
            provenance[identifier] = dict(record['source'], event_definition_ids=event_ids)
            used += size
        # Reuse the section/scoped-ID guard; details stay in audit, while model evidence is literal text.
        retrieved_ids = sorted({eid for d in selected for eid in lookup[d['evidence_id']]['event_ids']
                                if eid in catalog})
        details = get_event_definition_details(
            self.graph, retrieved_ids, state['et'], ['activity_semantics', 'dictionary'],
            allowed_event_definition_ids=list(catalog), catalog=catalog) if retrieved_ids else None
        audit = {'version': VERSION, 'entity_type_id': state['et'], 'queries': queries,
                 'searched_count': len(self.documents), 'semantic_encoder': dict(self.semantic_audit),
                 'scores': scores, 'value_linking': value_audits, 'provenance': provenance,
                 'evidence_ids': [d['evidence_id'] for d in selected],
                 'retrieved_event_definition_ids': retrieved_ids,
                 'detail_schema_version': details['detail_schema_version'] if details else None,
                 'top_k': top_k, 'max_chars': max_chars, 'used_chars': used,
                 'truncated': bool(omitted), 'omitted_count': len(omitted),
                 'exhaustive_semantic_absence': False, 'selection_policy': 'evidence_only_no_auto_approval'}
        self.audits.append(audit)
        payload = {'version': VERSION, 'records': selected, 'truncated': bool(omitted),
                   'exhaustive_semantic_absence': False, 'candidate_only': True}
        require_no_oracle_payload(payload)
        return payload
