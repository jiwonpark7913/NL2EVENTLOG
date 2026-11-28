"""Reusable Case capabilities and the detailed attribution evidence supplied to both arms."""

from copy import deepcopy
from functools import lru_cache
from pathlib import Path

from development.case_catalog_m0.runtime import load_case, load_catalog
from src.common.schema_metadata import database_fingerprint
from src.step2_retrieve_and_interpret.minimal_evidence import case_evidence


@lru_cache(maxsize=8)
def _build_catalog(database, fingerprint, index_file, index_stat, snapshot_id):
    """PURPOSE: Build the compact Case menu once for each openable immutable EEG/Index.
    INPUT: DB and Index identities, including file version stamps. OUTPUT: Complete activity-aware Case cards.
    """
    from src.eeg.eeg_store import EEGStore

    catalog = []
    index = EEGStore(index_file, snapshot_id)
    with index.open(database) as lookup:
        cards, _ = load_catalog(lookup)
        for card in cards:
            case = card['id']
            graph, evidence, _, _ = load_case(lookup, case)
            definitions = {ed['id']: ed for ed in graph['event_definitions']}
            groups = {}
            for event in case_evidence(evidence, case):
                definition = definitions[event['id']]
                pairing = definition.get('timestamp_pairing') or {}
                clock = definition.get('occurrence_time_source') or {}
                phase = pairing.get('phase')
                time_role = pairing.get('time_role') or clock.get('semantic_role') or clock.get('role')
                key = (event['activity'], phase, time_role)
                roles = groups.setdefault(key, set())
                for path in event['paths']:
                    roles.update(path['role_evidence'] or ['unlabelled'])
            compact = [[activity, phase, time_role, sorted(roles)]
                       for (activity, phase, time_role), roles in sorted(groups.items(), key=lambda row: repr(row[0]))]
            catalog.append({**card, 'connected_activities': compact})
    return catalog


def activity_aware_catalog(database, index):
    """PURPOSE: Reuse a snapshot-keyed capability projection without modifying the frozen Index.
    INPUT: Public DB and EEGStore. OUTPUT: Complete ET cards and concise lifecycle/role summaries.
    """
    path = Path(index.path).resolve()
    stat = path.stat()
    catalog = _build_catalog(str(Path(database).resolve()), database_fingerprint(database), str(path),
                             (stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns), index.snapshot_id)
    return deepcopy(catalog)


def attach_path_reviews(payload, graph, case_id):
    """PURPOSE: Deliver the already grounded review record without elevating it to an execution gate.
    INPUT: Exact selected-Case Event payload and semantic graph. OUTPUT: New Event payload with all offered paths.
    """
    definitions = {ed['id']: ed for ed in graph['event_definitions']}
    events = []
    for event in payload['events']:
        reviews = definitions[event['id']].get('entity_reviews', {}).get(case_id, {}).get('attribution_paths', {})
        paths = []
        for path in event['paths']:
            record = reviews.get(path['id'], {})
            status = record.get('status', 'unreviewed')
            review = {'status': status}
            review.update({key: record[key] for key in ('role', 'reason', 'citations') if key in record})
            paths.append({**path, 'relationship_review': review})
        events.append({**event, 'paths': paths})
    return {**payload, 'events': events}
