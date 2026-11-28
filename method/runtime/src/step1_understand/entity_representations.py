"""Schema-level entity representations, semantic types and executable identity populations."""

from __future__ import annotations
from src.common.entity_identity import typed_entity_key
from copy import deepcopy
from contextlib import closing
import hashlib
import json
import re
from src.common.graph_identifiers import table_key_id
from src.eeg.evidence_graph_models import representative_key
from src.common.database_io import connect_readonly


def contract_id(prefix, value):
    """PURPOSE: Identify immutable contracts without display names or current instance values.
    INPUT: Namespace and JSON contract. OUTPUT: Deterministic digest ID.
    """
    return prefix + ':' + hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:20]


def build_representations(tables, dd, objects=()):
    """PURPOSE: Retain every table, including tables without an admissible record key.
    INPUT: Physical schema, filtered DD and optional existing keyed Objects. OUTPUT: Table inventory.
    """
    definitions = {t['table']: t for t in dd.get('tables', [])}
    physical = {o['table']: o for o in objects}
    result = []
    for table in tables:
        key = representative_key(table)
        definition = definitions.get(table.name, {})
        source = physical.get(table.name, {})
        result.append({'id': table_key_id(table.name), 'node_type': 'entity_representation',
            'table': table.name, 'readable_name': definition.get('readable_name') or source.get('name') or
                table.name.replace('_', ' ').title(),
            'definition': definition.get('definition', ''), 'row_grain': definition.get('row_grain', ''),
            'record_key': list(source.get('pk', key[0] if key else [])), 'record_identity_status': 'pending_validation' if key else 'unknown',
            'entity_mapping_status': 'unknown', 'roles': ['unknown'], 'entity_type_id': None,
            'evidence': deepcopy(source.get('evidence', []))})
    return sorted(result, key=lambda r: r['id'])


def _key_type(table, columns):
    """PURPOSE: Record actual declared key affinities for deterministic typed encoding.
    INPUT: Table and ordered key. OUTPUT: SQLite affinity tags; no lossy value coercion.
    """
    types = {c.name: c.declared_type.upper() for c in table.columns}
    return ['integer' if 'INT' in types[c] else 'text' if any(x in types[c] for x in ('CHAR', 'TEXT', 'CLOB'))
            else 'real' if any(x in types[c] for x in ('REAL', 'FLOA', 'DOUB')) else 'dynamic' for c in columns]


def representation_role(definition):
    """PURPOSE: Distinguish explicitly documented storage roles from business entity meaning.
    INPUT: Public table definition and row grain, excluding table-name heuristics.
    OUTPUT: Role and independent-ET decision; uncertain business meaning remains visible.
    """
    if not definition.strip():
        return "unresolved_business_meaning", False
    occurrence_grain = bool(re.search(
        r"\b(?:one|each|a) (?:row|record) (?:per|for each|represents?|captures?) "
        r"(?:recorded )?(?:\w+ ){0,3}(?:event|activity|transition|occurrence)\b", definition, re.I))
    if occurrence_grain:
        return "event_storage", False
    if re.search(r"\b(?:independent|business)\s+(?:entity|object)\b", definition, re.I) and not re.search(
            r"\bnot (?:an? )?business (?:entity|object)\b", definition, re.I):
        return "business_entity", True
    if re.search(r"\b(?:event|activity|transition) (?:storage|log|history|stream)\b|"
                 r"\b(?:history|log) of (?:\w+ ){0,3}(?:events|activities|transitions)\b", definition, re.I):
        return "event_storage", False
    for role, pattern in (
        ("event_storage", r"\b(event storing|storage-only history|event log only)\b"),
        ("code_description", r"\b(code dictionary|code lookup|code description|code explanation|code meanings)\b"),
        ("relationship", r"\b(link only|linking only|relationship only|association only|link-only|linking-only|relationship-only|not a business case|not a business entity|auxiliary extraction index)\b")):
        if re.search(pattern, definition, re.I):
            return role, False
    if re.search(r"\b(?:independent|business)\s+(?:entity|object)\b|"
                 r"\b(?:entity|object)\s+(?:with|having)\s+(?:its own|independent)\s+identity\b|"
                 r"\b(?:same|one) (?:\w+ ){0,2}(?:entity|business instance)\b", definition, re.I):
        return "business_entity", True
    if re.search(r"\bone row per (?!event\b|activity\b|transition\b|occurrence\b)\w+", definition, re.I):
        return "business_entity", True
    return "unresolved_business_meaning", False


def validate_entity_attribution(db_path, paths, entity_types):
    """PURPOSE: Keep physical reachability distinct from unique final ET-instance attribution.
    INPUT: Existing executed paths and ET maps. OUTPUT: Same paths, with conflicting namespace/key choices explicit
    and one shared per-event coverage receipt for every (Event definition, ET) cohort of valid paths.
    Each source event is judged on the union of its paths: one Entity via one or more paths is attributed
    (several paths to the same Entity are duplicates, not conflicts); different Entities are a conflict that
    leaves every path of that Event definition–ET pair unresolved; an event no valid path reaches is
    unattributed. Direct equality maps only.
    """
    populations = {e['id']: e['population'] for e in entity_types if e.get('population')}
    cohorts = {}
    for path in paths:
        if path.get('to') in populations and path.get('validation_status') == 'valid' and path.get('cardinality') == 'N:1':
            # Competing roles are separate projections, resolved by PI with request evidence.
            role = (path.get('case_role') or (path.get('role_validation') or {}).get('reference') or {}
                    ).get('step', {}).get('relationship_id')
            cohorts.setdefault((path['event_definition_id'], path['to'], role), []).append(path)
    with closing(connect_readonly(db_path)) as connection:
        for (_, type_id, _), candidates in cohorts.items():
            source_rows = max(p['case_map'].get('validation', {}).get('source_rows', 0) for p in candidates)
            if len(candidates) == 1:
                matched = candidates[0]['case_map'].get('validation', {}).get('matched_source_rows', 0)
                candidates[0]['entity_identity_validation'] = {'status':'pass',
                    'ambiguous_source_count':0,'basis':'single_validated_case_map',
                    'event_coverage': _event_coverage(max(source_rows, matched), matched, 0, 0,
                                                      matched, [candidates[0]['id']])}
                continue
            maps = {m['representation_id']: m for m in populations[type_id]['maps']}
            instances, path_sources, hits = {}, {}, {}
            for path in candidates:
                mapping = maps.get(path.get('target_table_key_id'))
                if mapping is None:
                    continue
                query = path['case_map']
                rows = connection.execute(query['map_sql'], query.get('map_parameters', [])).fetchall()
                sources = set()
                for source_key, case_key in rows:
                    key = json.loads(case_key)
                    instances.setdefault(source_key, set()).add(typed_entity_key(mapping, key))
                    sources.add(source_key)
                for source_key in sources:
                    hits[source_key] = hits.get(source_key, 0) + 1
                path_sources[path['id']] = sources
            ambiguous = {source for source, choices in instances.items() if len(choices) > 1}
            duplicates = sum(1 for source, count in hits.items() if count > 1 and source not in ambiguous)
            unique = len(instances) - len(ambiguous)
            # A conflict leaves the whole Event definition–ET attribution unresolved: no remaining path
            # may deliver a partial history as if the conflict did not exist.
            coverage = _event_coverage(max(source_rows, len(instances)), unique, len(ambiguous), duplicates,
                                       0 if ambiguous else unique, sorted(path_sources))
            if ambiguous:
                coverage.update(resolution='unresolved_conflict', blocked_unique_source_rows=unique)
            for path in candidates:
                carries = bool(path_sources.get(path['id'], set()) & ambiguous)
                path['entity_identity_validation'] = {'status': 'unknown' if ambiguous else 'pass',
                    'ambiguous_source_count': len(ambiguous), 'basis': 'canonical_identification_key_equality',
                    'event_coverage': coverage}
                if ambiguous:
                    path['validation_status'] = 'ambiguous'
                    path['reason_code'] = ('multiple_entity_instance_attributions' if carries
                                           else 'definition_attribution_has_conflict')
    return paths


def _event_coverage(source_rows, attributed, conflicting, duplicates, deliverable, path_ids):
    """PURPOSE: Report per-event attribution of one Event definition to one ET over all its valid paths.
    INPUT: In-scope source rows, uniquely attributed / conflicting / same-Entity multi-path event counts,
           events deliverable (zero when any conflict leaves the pair unresolved), and contributing path IDs.
    OUTPUT: Coverage receipt; unattributed = in-scope rows that no valid path maps to an Entity.
    """
    return {'source_rows': source_rows, 'attributed_source_rows': attributed,
            'same_entity_multi_path_source_rows': duplicates, 'conflicting_source_rows': conflicting,
            'unattributed_source_rows': source_rows - attributed - conflicting,
            'deliverable_source_rows': deliverable, 'path_ids': list(path_ids),
            'scope': 'union_of_valid_paths_per_source_event'}
