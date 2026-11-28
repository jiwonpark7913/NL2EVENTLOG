"""Read immutable EEG metadata by indexed evidence and execution dependencies."""

from collections import defaultdict
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3
from tempfile import NamedTemporaryFile
from time import perf_counter
from urllib.parse import quote

from src.common.attribution_policy import attribution_adjacency
from src.common.graph_identifiers import content_hash
from src.common.runtime_input_contract import validate_runtime_graph
from src.common.schema_metadata import database_fingerprint

INDEX_VERSION = 'eeg-index-v14-integrated'
COLLECTIONS = (
    'entity_types', 'event_definitions', 'attribution_paths', 'tables', 'relationships',
    'table_key_records', 'rollups', 'event_entity_associations', 'event_entity_links',
    'event_definition_pair_relationships', 'occurrence_identity_rules', 'event_families',
    'view_candidates', 'identification_rules', 'entity_instance_maps', 'entity_case_populations',
)
METADATA = (
    'schema_graph_version', 'database', 'database_fingerprint', 'profile_mode',
    'relationship_budget_exhausted', 'entity_model_version', 'entity_build_stages',
    'activity_semantics_version', 'runtime_input_policy', 'input_contract_audit',
    'build_configuration', 'semantic_policy_version', 'event_binding_schema_version',
    'event_semantic_signature_schema_version', 'eeg_contract_version', 'input_contract',
    'entity_linking_policy', 'source_discovery_contract', 'carrier_event_policy', 'canonical_activity_policy',
)
DD_COLLECTIONS = ('tables', 'columns', 'relations', 'semantic_statements')
VALID_ATTRIBUTION = {'valid', 'rule_confirmed_no_occurrences'}
GROUPING = re.compile(r'\b(?:for\s+(?:each|every)|per)\s+([^,.;?!]+)', re.I)


def _json(value):
    """PURPOSE: Encode a metadata record deterministically.
    INPUT: JSON-compatible EEG metadata. OUTPUT: UTF-8 bytes."""
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True).encode()


def _words(text):
    """PURPOSE: Normalize search phrases while retaining non-ASCII terms.
    INPUT: Public metadata or request text. OUTPUT: Case-folded tokens joined by spaces."""
    return ' '.join(re.findall(r'[^\W_]+', str(text).casefold()))


def _aliases(record):
    """PURPOSE: Generate exact searchable entity names from documented labels.
    INPUT: Entity type; generic case metawords provide no evidence.
    OUTPUT: Normalized names and stored aliases, including simple plurals.
    """
    values = [record.get(k) for k in ('name', 'label', 'canonical_name', 'display_name')]
    values.extend(a for key in ('aliases', 'lexical_aliases') for a in record.get(key, []) if isinstance(a, str))
    names = {_words(v) for v in values if v}
    names -= {'case', 'cases', 'record', 'records', 'event', 'events'}
    return names | {name + 's' for name in names if not name.endswith('s')}


def _related(record):
    """PURPOSE: Index a metadata record under its explicit structural dependencies.
    INPUT: Runtime EEG record. OUTPUT: Case, Event Definition and table adjacency keys."""
    case_keys = ('to', 'object_concept_id', 'target_entity_type_id', 'entity_type_id',
                 'owner_entity_type_id', 'anchor_object_type_id', 'parent_object_id', 'child_object_id',
                 'parent_table_key_id', 'child_table_key_id', 'target_table_key_id', 'anchor_entity_type_id')
    event_keys = ('event_definition_id', 'binding_id', 'owner_event_definition_id', 'broad_event_definition_id')
    table_keys = ('source_table', 'anchor_table', 'table', 'table_name', 'left_table', 'right_table', 'child_table', 'parent_table')
    return {
        'case': {record[k] for k in case_keys if isinstance(record.get(k), str)},
        'event': ({record[k] for k in event_keys if isinstance(record.get(k), str)} |
                  set(record.get('binding_pair', [])) | set(record.get('member_event_definition_ids', []))),
        'table': {record[k] for k in table_keys if isinstance(record.get(k), str)},
    }


def split_execution_map(path, maps):
    """PURPOSE: Separate occurrence-map statements from a path's evidence header.
    INPUT: Path record and private index-build collection. OUTPUT: Independent header, with map saved by ID.
    """
    packed = dict(path)
    if isinstance(packed.get('case_map'), dict):
        case_map = dict(packed['case_map'])
        fields = {key: case_map.pop(key) for key in ('map_sql', 'map_parameters') if key in case_map}
        if fields:
            identifier = 'case-map:' + content_hash(fields)
            maps.setdefault(identifier, {'id': identifier, **fields})
            packed['execution_map_id'] = identifier
        packed['case_map'] = case_map
    return packed


def write_index(path, graph, snapshot_id):
    """PURPOSE: Publish an indexed projection of an immutable EEG without storing original rows.
    INPUT: Local destination, public runtime EEG and snapshot identity.
    OUTPUT: Build seconds, indexed bytes and record count. Publishes atomically.
    """
    validate_runtime_graph(graph)
    started = perf_counter()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, prefix='.eeg-index-', suffix='.sqlite', delete=False) as temp:
        temporary = Path(temp.name)
    try:
        with closing(sqlite3.connect(temporary)) as conn, conn:
            conn.executescript("""
                CREATE TABLE metadata(id INTEGER PRIMARY KEY, body BLOB NOT NULL);
                CREATE TABLE records(kind TEXT, id TEXT, ordinal INTEGER, body BLOB NOT NULL,
                    PRIMARY KEY(kind,id));
                CREATE TABLE links(kind TEXT, axis TEXT, value TEXT, id TEXT,
                    PRIMARY KEY(kind,axis,value,id)) WITHOUT ROWID;
                CREATE TABLE entity_aliases(term TEXT, id TEXT, PRIMARY KEY(term,id)) WITHOUT ROWID;
                CREATE TABLE event_aliases(term TEXT, id TEXT, PRIMARY KEY(term,id)) WITHOUT ROWID;
                CREATE INDEX ordered_records ON records(kind,ordinal);
            """)
            ledger = graph.get('candidate_ledger') or {}
            dd = graph.get('data_dictionary') or {}
            metadata = {k: graph[k] for k in METADATA if k in graph}
            metadata['snapshot_id'] = snapshot_id
            metadata['index_version'] = INDEX_VERSION
            metadata['candidate_ledger'] = {k: v for k, v in ledger.items() if k not in ('candidates', 'discovery_limits', 'audit', 'missing_reviews')}
            if 'audit' in ledger:
                metadata['candidate_ledger']['audit'] = {k: v for k, v in ledger['audit'].items() if not isinstance(v, list)}
            metadata['data_dictionary'] = {k: dd[k] for k in ('name', 'timezone') if k in dd}
            metadata['source_coverage'] = {key: value for key, value in (graph.get('source_coverage') or {}).items()
                                           if key != 'gaps'}
            metadata['native_graph'] = bool(graph.get('dbu_rewrite'))
            conn.execute('INSERT INTO metadata VALUES (1,?)', (_json(metadata),))
            columns = {kind: graph.get(kind) or [] for kind in COLLECTIONS}
            columns.update({'dd.' + kind: dd.get(kind) or [] for kind in DD_COLLECTIONS})
            columns['dd.global'] = [dict(id=kind, value=dd.get(kind) or []) for kind in (
                'business_rules', 'processes', 'polymorphic_references')]
            columns['candidate_ledger'] = ledger.get('candidates', [])
            unresolved = graph.get('unresolved_event_evidence') or {}
            columns['unresolved_pairs'] = unresolved.get('pairs', [])
            columns['unconfirmed_carriers'] = unresolved.get('unconfirmed_carriers', [])
            columns['native_timestamps'] = (graph.get('dbu_rewrite') or {}).get('timestamps', [])
            joins = {}
            compact_paths = []
            execution_maps = {}
            for attribution in columns['attribution_paths']:
                packed = split_execution_map(attribution, execution_maps)
                steps = packed.pop('joins', [])
                path_id = 'join:' + content_hash([attribution.get('from_table'), steps])
                joins.setdefault(path_id, {'id': path_id, 'steps': steps})
                compact_paths.append({**packed, 'join_path_id': path_id})
            columns['event_definitions'] = [
                dict(ed, concept_paths=[split_execution_map(path, execution_maps) for path in ed['concept_paths']])
                if ed.get('concept_paths') else ed for ed in columns['event_definitions']
            ]
            columns['attribution_paths'] = compact_paths
            columns['join_paths'] = list(joins.values())
            columns['path_execution_maps'] = list(execution_maps.values())
            family_ids = defaultdict(list)
            for family in columns['event_families']:
                for identifier in [family.get('broad_event_definition_id'), *family['member_event_definition_ids']]:
                    family_ids[identifier].append(family['id'])
            columns['event_catalog'] = [{
                'id': ed['id'], 'source_table': ed.get('source_table'),
                'activity_identity': ed.get('activity_identity') or ed.get('canonical_activity_id'),
                'label': ed.get('activity_label') or ed.get('activity'),
                'lifecycle': (ed.get('timestamp_pairing') or {}).get('phase') or
                             (ed.get('semantic_signature') or {}).get('temporal_role'),
                'occurrence_unit': ed.get('source_kind'),
                'temporal_type': (ed.get('timestamp_pairing') or {}).get('time_role'),
                'family_ids': family_ids[ed['id']],
            } for ed in columns['event_definitions']]
            columns['event_search'] = [{'id': ed['id'], 'label': ' '.join(filter(None, (
                ed.get('activity_label'), (ed.get('activity_semantics') or {}).get('code_meaning'),
                (ed.get('semantic_signature') or {}).get('description'))))}
                for ed in columns['event_definitions']]
            by_case = defaultdict(set)
            for attribution in columns['attribution_paths']:
                for case in _related(attribution)['case']:
                    by_case[case].update(_related(attribution)['event'])
            by_event = defaultdict(set)
            for case, events in by_case.items():
                for event in events:
                    by_event[event].add(case)
            for definition in columns['event_definitions']:
                for concept_path in definition.get('concept_paths', []):
                    by_event[definition['id']].update(_related(concept_path)['case'])
            total = 0
            for kind, records in columns.items():
                for ordinal, record in enumerate(records):
                    if kind == 'unresolved_pairs':
                        identifier = str(record['candidate_id'])
                    else:
                        identifier = str(record.get('id') or record.get('candidate_id') or record.get('ts_id') or
                                         (record.get('name') if kind == 'tables' else '') or ordinal)
                    axes = _related(record)
                    if kind == 'entity_types':
                        axes['table'].update(record.get('member_tables', ()))
                        axes['table'].update(m['table'] for m in (record.get('population') or {}).get('maps', []))
                        conn.executemany('INSERT OR IGNORE INTO entity_aliases VALUES (?,?)',
                                         ((term, identifier) for term in _aliases(record)))
                    elif kind == 'tables':
                        axes['table'].add(record['name'])
                    elif kind == 'event_catalog':
                        axes['case'].update(by_event[identifier])
                    elif kind == 'event_definitions':
                        terms = {record.get('activity_label'), record.get('activity')}
                        terms.update(a for a in record.get('alternative_labels', []) if isinstance(a, str))
                        semantics = record.get('activity_semantics') or {}
                        terms.add(semantics.get('code_meaning'))
                        conn.executemany('INSERT OR IGNORE INTO event_aliases VALUES (?,?)', (
                            (term, identifier) for raw in terms if raw
                            if (term := _words(raw)) and len(term) > 2))
                        axes['case'].update(by_event[identifier])
                    elif kind == 'candidate_ledger':
                        axes['table'].add(record['source']['table'])
                    elif kind == 'dd.columns':
                        axes['column'] = {_json([record['table'], record['column']]).decode()}
                    elif kind == 'dd.semantic_statements' and not axes['table']:
                        axes['table'].add('')
                    elif kind == 'view_candidates':
                        axes['case'].update(v for k, v in record.items() if k.startswith('anchor_') and isinstance(v, str))
                    body = _json(record)
                    inserted = conn.execute('INSERT OR IGNORE INTO records VALUES (?,?,?,?)',
                                            (kind, identifier, ordinal, body)).rowcount
                    if not inserted:
                        existing, = conn.execute('SELECT body FROM records WHERE kind=? AND id=?',
                                                 (kind, identifier)).fetchone()
                        if existing != body:
                            raise ValueError(f'Conflicting EEG index record: {kind}/{identifier}')
                        continue
                    conn.executemany('INSERT OR IGNORE INTO links VALUES (?,?,?,?)',
                                     ((kind, axis, v, identifier) for axis, values in axes.items() for v in values))
                    total += 1
        size = temporary.stat().st_size
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return {'index_build_seconds': perf_counter() - started, 'index_bytes': size, 'index_records': total,
            'attribution_rules': len(compact_paths), 'join_shapes': len(joins), 'catalogued_join_shapes': len(joins),
            'attribution_expanded_record_bytes': sum(len(_json(rule)) for rule in graph.get('attribution_paths', [])),
            'attribution_indexed_record_bytes': sum(len(_json(rule)) for rule in [*compact_paths, *joins.values(), *execution_maps.values()])}


class EEGStore:
    """Indexed, immutable EEG snapshot. Each request owns a separate read ledger."""

    def __init__(self, path, snapshot_id, cache_audit=None):
        """PURPOSE: Bind lookup to one snapshot without restoring its full graph.
        INPUT: Index path, expected snapshot ID and optional cache disposition.
        OUTPUT: Independent read-only index handle metadata.
        """
        self.path = Path(path)
        self.snapshot_id = snapshot_id
        self.cache_audit = cache_audit or {}

    def open(self, database):
        """PURPOSE: Start one measured, scan-bounded snapshot lookup session.
        INPUT: Public DB path for scope and snapshot validation.
        OUTPUT: Context manager yielding independent request lookups.
        """
        return EEGLookup(self, database)


class EEGLookup:
    """One query's index connection and record-level lookup counters."""

    def __init__(self, store, database):
        """PURPOSE: Configure a lookup session with no database or model traffic yet.
        INPUT: Immutable store reference and original SQLite database path.
        OUTPUT: Session ready for a context-manager entry.
        """
        self.store = store
        self.database = database
        self.stats = {'serialized_bytes_read': 0, 'records_read': 0, 'index_reads': 0,
                      'candidate_records_read': 0, 'elapsed_lookup_seconds': 0.0}
        self.conn = None
        self.metadata = None

    def __enter__(self):
        """PURPOSE: Open a read-only index and check DB and EEG identities.
        INPUT: Configured request session. OUTPUT: Initialized lookup or a snapshot error.
        """
        self.conn = sqlite3.connect('file:' + quote(str(self.store.path.resolve()), safe='/') + '?mode=ro&immutable=1', uri=True)
        try:
            row = self.conn.execute('SELECT body FROM metadata WHERE id=1').fetchone()
            self.metadata = json.loads(row[0])
            self.stats.update(serialized_bytes_read=len(row[0]), records_read=1, index_reads=1)
            if (self.metadata['snapshot_id'] != self.store.snapshot_id
                    or self.metadata['index_version'] != INDEX_VERSION
                    or self.metadata['database_fingerprint'] != database_fingerprint(self.database)):
                raise ValueError('indexed_eeg_snapshot_mismatch')
        except BaseException:
            self.conn.close()
            raise
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """PURPOSE: Close the request-local read connection.
        INPUT: Context manager exit state. OUTPUT: None; original exceptions propagate."""
        self.conn.close()

    def records(self, kind, *, axis=None, values=None, within=None, include_execution=True):
        """PURPOSE: Fetch metadata through primary or adjacency indexes.
        INPUT: Collection, optional ID/adjacency values, and an optional second adjacency constraint.
        OUTPUT: Decoded rows in canonical snapshot order.
        """
        if values is not None and not values:
            return []
        started = perf_counter()
        c = self.conn
        if values is None:
            raw = c.execute('SELECT body FROM records WHERE kind=? ORDER BY ordinal', (kind,)).fetchall()
        else:
            vector = json.dumps(sorted(set(values)))
            if axis is None:
                raw = c.execute('SELECT body FROM records JOIN json_each(?) q ON records.kind=? AND records.id=q.value ORDER BY ordinal',
                                (vector, kind)).fetchall()
            else:
                ids = 'SELECT DISTINCT l.id FROM json_each(?) q JOIN links l ON l.kind=? AND l.axis=? AND l.value=q.value'
                parameters = [vector, kind, axis]
                if within is not None:
                    other_axis, other_values = within
                    if not other_values:
                        return []
                    ids += (' WHERE EXISTS (SELECT 1 FROM json_each(?) s JOIN links x '
                            'ON x.kind=l.kind AND x.axis=? AND x.value=s.value AND x.id=l.id)')
                    parameters.extend((json.dumps(sorted(other_values)), other_axis))
                raw = c.execute('SELECT r.body FROM (' + ids + ') f JOIN records r '
                                'ON r.kind=? AND r.id=f.id ORDER BY r.ordinal', [*parameters, kind]).fetchall()
        self.stats['serialized_bytes_read'] += sum(len(b) for b, in raw)
        self.stats['records_read'] += len(raw)
        self.stats['index_reads'] += 1
        if kind in ('event_definitions', 'candidate_ledger', 'unresolved_pairs'):
            self.stats['candidate_records_read'] += len(raw)
        self.stats['elapsed_lookup_seconds'] += perf_counter() - started
        result = [json.loads(body) for body, in raw]
        if kind == 'attribution_paths' and result:
            shapes = {row['id']: row['steps'] for row in self.records(
                'join_paths', values={row['join_path_id'] for row in result})}
            for row in result:
                row['joins'] = shapes[row.pop('join_path_id')]
            if include_execution:
                result = self.hydrate_paths(result)
        if kind == 'event_definitions' and include_execution:
            embedded = [path for row in result for path in row.get('concept_paths', [])]
            expanded = {path['id']: path for path in self.hydrate_paths(embedded)}
            for row in result:
                if row.get('concept_paths'):
                    row['concept_paths'] = [expanded[path['id']] for path in row['concept_paths']]
        return result

    def hydrate_paths(self, paths):
        """PURPOSE: Fetch the original map SQL only for path records that need a physical proof.
        INPUT: Request-local path headers. OUTPUT: Same ordered paths with original case-map fields.
        """
        if not paths:
            return paths
        references = {path['execution_map_id'] for path in paths if path.get('execution_map_id')}
        maps = {record['id']: {k: v for k, v in record.items() if k != 'id'} for record in self.records(
            'path_execution_maps', values=references)}
        self.stats['path_execution_maps_read'] = self.stats.get('path_execution_maps_read', 0) + len(maps)
        result = []
        for path in paths:
            if path.get('execution_map_id'):
                restored = dict(path)
                identifier = restored.pop('execution_map_id')
                restored['case_map'] = {**restored['case_map'], **maps[identifier]}
                result.append(restored)
            else:
                result.append(path)
        return result

    def matching_cases(self, phrase):
        """PURPOSE: Resolve a positively identified case phrase without scanning the ET catalog.
        INPUT: Literal grouping phrase. OUTPUT: IDs for the longest exact alias prefix and its match length.
        """
        tokens = _words(phrase).split()[:12]
        if not tokens:
            return set(), 0
        started = perf_counter()
        prefixes = [' '.join(tokens[:n]) for n in range(1, len(tokens) + 1)]
        rows = self.conn.execute('SELECT a.term,a.id FROM json_each(?) q JOIN entity_aliases a ON a.term=q.value',
                                 (json.dumps(prefixes),)).fetchall()
        self.stats['index_reads'] += 1
        self.stats['records_read'] += len(rows)
        self.stats['serialized_bytes_read'] += sum(len(term.encode()) + len(i.encode()) for term, i in rows)
        self.stats['elapsed_lookup_seconds'] += perf_counter() - started
        longest = max((len(term.split()) for term, _ in rows), default=0)
        return {i for term, i in rows if len(term.split()) == longest}, longest

    def event_seeds(self, phrase):
        """PURPOSE: Resolve every explicitly named Activity using indexed canonical names and aliases.
        INPUT: Request phrase preceding a Case clause. OUTPUT: ED IDs or an empty set if any term is unresolved.
        """
        activity = re.sub(r'^\s*(?:please\s+)?(?:extract|show|list|return|get)\s+', '', phrase, flags=re.I)
        terms = [_words(term) for term in re.split(r',|\band\b', activity, flags=re.I) if _words(term)]
        if not terms or any(re.search(r'\b(?:all|every|history|timeline|process|except|only)\b', term)
                            for term in terms):
            return set()
        started = perf_counter()
        rows = self.conn.execute(
            'SELECT a.term,a.id FROM event_aliases a JOIN json_each(?) q ON a.term=q.value',
            (json.dumps(terms),)).fetchall()
        self.stats['index_reads'] += 1
        self.stats['records_read'] += len(rows)
        self.stats['serialized_bytes_read'] += sum(len(term.encode()) + len(i.encode()) for term, i in rows)
        self.stats['elapsed_lookup_seconds'] += perf_counter() - started
        return {identifier for _, identifier in rows} if {term for term, _ in rows} == set(terms) else set()

    def request_graph(self, question, *, full=False, mode='graph', semantic_top_k=10, encoder=None,
                      defer_unanchored=False, progressive=False):
        """PURPOSE: Retrieve a Case-aware dependency closure, with full and semantic-only controls.
        INPUT: Request text, retrieval mode, optional ranked baseline encoder and candidate count.
        OUTPUT: Immutable-snapshot projection with admitted attribution and execution metadata.
        """
        if mode not in {'graph', 'full', 'semantic'}:
            raise ValueError('unknown EEG retrieval mode')
        if mode == 'full' or full:
            return self.case_graph()
        spans = list(GROUPING.finditer(question))
        anchored = len(spans) == 1 and not re.search(r'\b(?:or|and)\b', spans[0][1], re.I)
        cases = self.matching_cases(spans[0][1])[0] if anchored else set()
        literal_case = bool(cases)
        if mode == 'graph' and defer_unanchored and not cases:
            graph = self.case_graph(event_ids=set(), case_catalog=True)
            graph['index_scope'].update(mode='graph', literal_case=False, deferred_cases=True)
            return graph
        activity = question[:spans[0].start()] if spans else question
        if mode == 'semantic':
            from src.common.rank_evidence_documents import rank_documents
            from src.common.local_semantic_embeddings import local_semantic_encoder
            if encoder is None:
                encoder, audit = local_semantic_encoder()
                self.stats['semantic_encoder'] = audit
            ranked = rank_documents(activity, [
                {'id': row['id'], 'text': row['label']} for row in self.records('event_search')
            ], method='semantic' if encoder is not None else 'hybrid', encoder=encoder)
            events = {row['id'] for row in ranked[:semantic_top_k]}
            graph = self.case_graph(cases or None, event_ids=events or None)
            graph['index_scope'].update(mode=mode, literal_case=bool(cases), activity_seeded=bool(events))
            return graph
        events = self.event_seeds(activity)
        if not cases and events:
            routes = self.records('attribution_paths', axis='event', values=events, include_execution=False)
            cases = {rule['to'] for rule in routes if rule.get('validation_status') in VALID_ATTRIBUTION}
        graph = self.case_graph(cases or None, include_peers=True, for_pi=progressive)
        graph['index_scope'].update(mode='graph', prioritization_event_ids=sorted(events),
                                    literal_case=literal_case)
        return graph

    def case_hints(self, phrases):
        """PURPOSE: Trace explicit activity aliases back to their possible Case candidates.
        INPUT: Parsed public request phrases. OUTPUT: Structural hints for the existing Case role.
        """
        terms = {_words(text) for text in phrases if text}
        if not terms:
            return {}
        rows = self.conn.execute(
            "SELECT DISTINCT a.id,l.value FROM json_each(?) q JOIN event_aliases a ON a.term=q.value "
            "JOIN links l ON l.kind='event_definitions' AND l.axis='case' AND l.id=a.id",
            (json.dumps(sorted(terms)),)).fetchall()
        self.stats['serialized_bytes_read'] += sum(len(ed.encode()) + len(case.encode()) for ed, case in rows)
        self.stats['records_read'] += len(rows)
        self.stats['index_reads'] += 1
        hints = defaultdict(set)
        for event, case in rows:
            hints[case].add(event)
        return {case: sorted(ids) for case, ids in hints.items()}

    def expand_requirements(self, current, spans):
        """PURPOSE: Locate additional Case/Activity candidates from unresolved literal requirements.
        INPUT: Current graph and exact request spans. OUTPUT: Wider Case scope or unchanged graph plus receipt.
        """
        scope = current.get('index_scope', {})
        known = set(scope.get('selected_case_ids', []))
        if scope.get('exhaustive_cases'):
            return current, {'status': 'case_inventory_already_authoritative'}
        terms = set()
        for span in spans:
            words = _words(span).split()[:64]
            terms.update(' '.join(words[start:stop]) for start in range(len(words))
                         for stop in range(start + 1, min(start + 12, len(words)) + 1))
        if not terms:
            return current, {'status': 'no_literal_requirement'}
        started = perf_counter()
        hits = self.conn.execute('SELECT DISTINCT a.id FROM event_aliases a JOIN json_each(?) q ON a.term=q.value',
                                 (json.dumps(sorted(terms)),)).fetchall()
        self.stats['index_reads'] += 1
        self.stats['records_read'] += len(hits)
        self.stats['serialized_bytes_read'] += sum(len(identifier.encode()) for identifier, in hits)
        self.stats['elapsed_lookup_seconds'] += perf_counter() - started
        events = {identifier for identifier, in hits}
        routes = self.records('attribution_paths', axis='event', values=events, include_execution=False)
        cases = {rule['to'] for rule in routes
                 if rule.get('validation_status') in {'valid', 'rule_confirmed_no_occurrences'}}
        receipt = {'status': 'expanded' if cases - known else 'no_additional_case',
                   'matched_events': len(events), 'added_case_count': len(cases - known)}
        if not cases - known:
            return current, receipt
        expanded = self.case_graph(known | cases, include_peers=True, for_pi=True)
        expanded['index_scope'].update(mode='graph', literal_case=False, prioritization_event_ids=sorted(events))
        return expanded, receipt

    def case_graph(self, case_ids=None, *, event_ids=None, include_peers=False, case_catalog=False, for_pi=False, path_ids=None):
        """PURPOSE: Read a typed Case or executable projection with original rules intact.
        INPUT: Selected Case IDs, optional frozen ED and verified path IDs.
        OUTPUT: Fresh requested dependency graph; canonical snapshot is never rewritten.
        """
        entities = self.records('entity_types', values=case_ids)
        case_refs = {e['id'] for e in entities}
        case_tables = set()
        for entity in entities:
            if entity.get('anchor_entity_type_id'):
                case_refs.add(entity['anchor_entity_type_id'])
            case_refs.update(entity.get('member_object_ids', []))
            case_tables.update(_related(entity)['table'])
            case_tables.update(entity.get('member_tables', []))
            case_tables.update(m['table'] for m in (entity.get('population') or {}).get('maps', []))
        headers = []
        if for_pi and case_ids is not None and event_ids is None:
            linked = self.records('event_catalog', axis='case', values=case_refs)
            direct = self.records('event_catalog', axis='table', values=case_tables)
            headers = list({row['id']: row for row in linked + direct}.values())
        if event_ids is not None:
            definitions = self.records('event_definitions', values=event_ids, include_execution=not for_pi and path_ids is None)
        elif for_pi and case_ids is not None:
            definitions = self.records('event_definitions', values={header['id'] for header in headers},
                                       include_execution=False)
        elif case_ids is None:
            definitions = self.records('event_definitions', include_execution=not for_pi)
        else:
            by_case = self.records('event_definitions', axis='case', values=case_refs, include_execution=not for_pi)
            by_table = self.records('event_definitions', axis='table', values=case_tables, include_execution=not for_pi)
            definitions = list({d['id']: d for d in by_case + by_table}.values())
        definitions.sort(key=lambda d: d['id'])
        ids = {e['id'] for e in definitions}
        if path_ids is None:
            paths = self.records('attribution_paths', axis='event', values=ids, within=('case', case_refs),
                                 include_execution=not for_pi)
        else:
            paths = self.records('attribution_paths', values=path_ids)
            by_id = {path['id']: path for path in paths}
            for definition in definitions:
                if definition.get('concept_paths'):
                    definition['concept_paths'] = [by_id[p['id']] for p in definition['concept_paths'] if p['id'] in by_id]
        paths = [p for p in paths if p.get('to') in case_refs]
        families = self.records('event_families', axis='event', values=ids)
        family_members = {identifier for family in families for identifier in family.get('member_event_definition_ids', [])}
        if event_ids is None or include_peers:
            # Keep documented peer candidates inspectable even when their attribution is missing.
            peers = self.records('event_definitions', values=family_members - ids, include_execution=not for_pi)
            definitions.extend(peers)
            ids.update(e['id'] for e in peers)
            definitions.sort(key=lambda e: e['id'])
            if include_peers and peers:
                paths.extend(self.records('attribution_paths', axis='event',
                    values={e['id'] for e in peers}, within=('case', case_refs), include_execution=not for_pi))
        tables = case_tables | {e['source_table'] for e in definitions if e.get('source_table')}
        from src.common.occurrence_conditions import occurrence_terms
        tables.update(edge['right_table'] for event in definitions
                      for condition in event.get('documented_source_conditions', [])
                      for term in occurrence_terms(condition) for edge in term.get('joins', []))
        tables.update(t for p in paths for join in p.get('joins', [])
                      for t in (join.get('left_table'), join.get('right_table')) if t)
        relationships = self.records('relationships', axis='table', values=tables)
        related = {r.get(k) for r in relationships for k in ('left_table', 'right_table')} - {None}
        # One-hop relationship metadata keeps inbound/outbound population scopes visible.
        tables |= related
        graph = {k: self.metadata[k] for k in METADATA if k in self.metadata}
        graph.update(entity_types=entities, event_definitions=definitions, relationships=relationships,
                     attribution_paths=paths, indexed_request=True, eeg_cache=self.store.cache_audit)
        if case_catalog:
            graph['data_dictionary'] = dict(self.metadata['data_dictionary'])
            role_columns = {
                _json([step['right_table'], column]).decode()
                for steps in attribution_adjacency(relationships).values() for step in steps
                if step['direction'] == 'parent_to_child' for column in step['right_columns']
            }
            graph['data_dictionary']['columns'] = self.records('dd.columns', axis='column', values=role_columns)
            graph['index_scope'] = {'selected_case_ids': sorted(case_refs), 'exhaustive_cases': True,
                                    'table_names': sorted(tables), 'event_definition_count': 0}
            return graph
        for name in ('tables', 'table_key_records'):
            graph[name] = self.records(name, axis='table', values=tables)
        event_collections = ('event_entity_associations', 'event_entity_links', 'event_definition_pair_relationships')
        for name in event_collections if for_pi else (*event_collections, 'occurrence_identity_rules'):
            graph[name] = self.records(name, axis='event', values=ids)
        graph['event_families'] = families
        if for_pi:
            graph['candidate_lookup_catalog'] = sorted(headers, key=lambda header: header['id'])
            graph['family_lookup_gaps'] = sorted(family_members - ids)
        if not for_pi:
            for name in ('rollups', 'view_candidates', 'identification_rules', 'entity_instance_maps',
                         'entity_case_populations'):
                graph[name] = self.records(name, axis='case', values=case_refs)
        dd = dict(self.metadata['data_dictionary'])
        for kind in DD_COLLECTIONS:
            dd[kind] = self.records('dd.' + kind, axis='table', values=tables | ({''} if kind == 'semantic_statements' else set()))
        dd.update({r['id']: r['value'] for r in self.records('dd.global')})
        dd['evidence_text'] = {r['id']: r['text'] for r in dd['semantic_statements'] if r.get('id') and r.get('text')}
        graph['data_dictionary'] = dd
        if self.metadata['native_graph']:
            # Step 4 needs clocks from the native graph, not its complete profiling trace.
            graph['dbu_rewrite'] = {'timestamps': [] if for_pi else
                                    self.records('native_timestamps', axis='table', values=tables)}
        graph['candidate_ledger'] = self.metadata['candidate_ledger']
        graph['source_coverage'] = self.metadata.get('source_coverage', {})
        graph['index_scope'] = {'selected_case_ids': sorted(e['id'] for e in entities), 'exhaustive_cases': case_ids is None,
                                'table_names': sorted(tables), 'event_definition_count': len(ids),
                                'projection': 'semantic' if for_pi else 'executable'}
        return graph

    @staticmethod
    def attach_summary(graph):
        """PURPOSE: Prepare the existing revision aliases only over this lookup's Case inventory.
        INPUT: Scoped runtime graph. OUTPUT: None; sets a deterministic public revision summary.
        """
        from src.step1_understand.describe_business_entities_and_events import summary_inventory
        entities, members, items = summary_inventory(graph)
        paragraph = '. '.join(' '.join(filter(None, [key, item['name'], *(item.get('evidence') or [])[:1]]))
                              for key, item in items.items())
        graph['revision_summary'] = {'paragraph': paragraph, 'et_aliases': entities, 'members': members}

    def recovery_graph(self, graph, *, extra_tables=()):
        """PURPOSE: Load candidate and original clock evidence only when a request has a gap.
        INPUT: Request graph and optionally grounded related source tables.
        OUTPUT: Isolated graph overlay for Targeted Knowledge Recovery.
        """
        tables = set(graph['index_scope']['table_names']) | set(extra_tables)
        return dict(graph, candidate_ledger={**graph['candidate_ledger'],
                    'candidates': self.records('candidate_ledger', axis='table', values=tables)},
                    unresolved_event_evidence={
                        'pairs': self.records('unresolved_pairs', axis='table', values=tables),
                        'unconfirmed_carriers': self.records('unconfirmed_carriers', axis='table', values=tables)})
