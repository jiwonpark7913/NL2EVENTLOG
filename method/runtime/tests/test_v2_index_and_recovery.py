"""Request-local indexed extraction and recovery on independent SQLite fixtures."""

from src.eeg.eeg_store import EEGStore, write_index
from src.pipeline import run_pipeline
from src.eeg.evidence_graph_cache import load_or_build
import test_pipeline_runtime as runtime_fixture
from test_pipeline_runtime import ScriptedClient


def fixture(tmp_path):
    """PURPOSE: Supply the existing public order fixture with an offline role client.
    INPUT: Per-test temporary directory. OUTPUT: DB, DD, config and canonical runtime graph.
    """
    test = runtime_fixture.StandaloneRuntimeTests()
    test.setUp()
    try:
        client = ScriptedClient()
        graph, _ = load_or_build(test.db, test.dd, client=client, config=test.config,
                                 directory=tmp_path / 'cache', prepare_summary=True)
        database = tmp_path / 'database.sqlite'
        database.write_bytes(test.db.read_bytes())
        from src.common.schema_metadata import database_fingerprint
        graph = dict(graph, database=str(database), database_fingerprint=database_fingerprint(database))
        return database, test.dd, test.config, graph
    finally:
        test.doCleanups()


def event_contract(result):
    """PURPOSE: Inspect physical identity independently of a display name.
    INPUT: Completed pipeline result. OUTPUT: Sorted immutable physical occurrence tuples.
    """
    return sorted((r['case_id'], r['source_record_id'], r['timestamp'], r['source_occurrence_id'])
                  for r in result['execution']['event_log'])


def test_index_preserves_espec_and_avoids_full_cache_restore(tmp_path, monkeypatch):
    """PURPOSE: Ensure warm indexed loading avoids read_eeg_layers and preserves output identity.
    INPUT: Public order DB and scripted model. OUTPUT: Same Case and occurrence rows as full graph.
    """
    database, dd, config, graph = fixture(tmp_path)
    question = 'Extract Approved for each order.'
    baseline = run_pipeline(database, dd, question, graph=graph, client=ScriptedClient(), config=config,
                            evidence_retrieval=False)
    from src.eeg import evidence_graph_cache
    directory = tmp_path / 'warm'
    cached, _ = load_or_build(database, dd, client=ScriptedClient(), config=config, directory=directory,
                              indexed=True, include_native=False)

    def unexpected_restore(*args):
        """PURPOSE: Make full graph restoration fail. INPUT: Any call. OUTPUT: Assertion error."""
        raise AssertionError('warm index must not restore all canonical sections')

    monkeypatch.setattr(evidence_graph_cache, 'read_eeg_layers', unexpected_restore)
    warm, _ = load_or_build(database, dd, client=ScriptedClient(), config=config, directory=directory,
                            indexed=True, include_native=False)
    assert cached.path == warm.path
    result = run_pipeline(database, dd, question, graph=warm, client=ScriptedClient(), config=config,
                          evidence_retrieval=False)
    assert result['es']['status'] == baseline['es']['status'] == 'accepted'
    assert event_contract(result) == event_contract(baseline)
    assert result['execution']['sql'] == baseline['execution']['sql']
    assert result['graph']['index_scope']['exhaustive_cases'] is False
    assert result['manifest']['measurements']['lookup']['records_read']


def test_source_recovery_rediscovery_is_verified_and_request_local(tmp_path):
    """PURPOSE: Reconstruct an omitted ED from public evidence and re-run normal PI.
    INPUT: Canonical graph with its only documented ED intentionally omitted.
    OUTPUT: Recovery produces the correct events once, with no mutation or cross-query promotion.
    """
    database, dd, config, graph = fixture(tmp_path)
    question = 'Extract Approved for each order.'
    baseline = run_pipeline(database, dd, question, graph=graph, client=ScriptedClient(), config=config,
                            evidence_retrieval=False)
    assert len(event_contract(baseline)) == 2
    broken = dict(graph, event_definitions=[], attribution_paths=[], event_families=[],
                  event_definition_pair_relationships=[], unresolved_event_evidence={'pairs': []})
    path = tmp_path / 'index.sqlite'
    write_index(path, broken, 'source-loss')
    index = EEGStore(path, 'source-loss')
    result = run_pipeline(database, dd, question, graph=index, client=ScriptedClient(), config=config,
                          evidence_retrieval=False)
    assert result['manifest']['recovery']['source']['status'] == 'accepted', result['manifest']['recovery']
    assert event_contract(result) == event_contract(baseline)
    assert result['manifest']['recovery']['added_provider_usage']['calls'] > 0
    with index.open(database) as lookup:
        assert lookup.records('event_definitions') == []
    declined = run_pipeline(database, dd, question, graph=index, client=ScriptedClient(), config=config,
                            recovery_enabled=False, evidence_retrieval=False)
    assert declined['query']['status'] != 'ready'


def test_deferred_case_catalog_retains_documented_scope_roles(tmp_path):
    """PURPOSE: Preserve Case role choices before any ED body is read.
    INPUT: A catalog with two documented sibling FK roles plus unrelated DD.
    OUTPUT: Both role receipts and zero candidate reads before Case resolution.
    """
    from src.common.attribution_policy import attribution_adjacency, documented_reference_roles

    database, _, _, graph = fixture(tmp_path)
    roles = ('sender', 'receiver')
    relationships = [
        {'id': role, 'left_table': 'dispatch', 'left_columns': [role + '_id'],
         'right_table': 'orders', 'right_columns': ['id'],
         'declared': True, 'child_key_unique': True}
        for role in roles
    ]
    columns = [
        {'id': role, 'table': 'dispatch', 'column': role + '_id', 'definition': f'{role} for the dispatch.'}
        for role in roles
    ]
    dictionary = {**graph['data_dictionary'], 'columns': [*graph['data_dictionary']['columns'], *columns]}
    graph = {**graph, 'relationships': relationships, 'data_dictionary': dictionary}
    path = tmp_path / 'case-index.sqlite'
    write_index(path, graph, 'case-catalog')
    with EEGStore(path, 'case-catalog').open(database) as lookup:
        catalog = lookup.request_graph('Show the order as the receiver for this dispatch.',
                                       defer_unanchored=True)
        restored = documented_reference_roles(attribution_adjacency(catalog['relationships']),
                                             catalog['data_dictionary'])
        assert set(restored) == set(roles)
        assert not catalog['event_definitions'] and not lookup.stats['candidate_records_read']


def test_low_ranked_card_remains_available_for_independent_pi(tmp_path, monkeypatch):
    """PURPOSE: Keep a required ED reviewable when initial semantic ranking supplies no detail.
    INPUT: Low-ranked native ED and an initial proposer that overlooks compact cards.
    OUTPUT: Independent review reaches and selects the ED without a new role call.
    """
    import json

    from src.step2_retrieve_and_interpret import progressive_lookup

    class DetailDependentClient(ScriptedClient):
        """Model initial omission from a terse card while retaining independent review behavior."""

        def create(self, **kwargs):
            """PURPOSE: Inject an empty initial proposal. INPUT: Existing role call. OUTPUT: Scripted reply."""
            response = super().create(**kwargs)
            if kwargs['response_format']['json_schema']['name'] == 'pi_events':
                payload = json.loads(kwargs['messages'][1]['content'].split('\n', 1)[1].rsplit('\n', 1)[0])
                assert payload['activities'] and all('meaning' not in card for card in payload['activities'])
                response.choices[0].message.content = '{"matches":[]}'
            return response

    monkeypatch.setattr(progressive_lookup, 'rank_documents', lambda *args: [])
    database, dd, config, graph = fixture(tmp_path)
    path = tmp_path / 'progressive.sqlite'
    write_index(path, graph, 'low-ranked')
    result = run_pipeline(database, dd, 'Extract Approved for each order.', client=DetailDependentClient(),
                          graph=EEGStore(path, 'low-ranked'), config=config, evidence_retrieval=False)
    assert result['es']['status'] == 'accepted', result['query']['process_view_termination_reason']
    receipt, = result['query']['process_interpretation_trace']['retrieval_coverage']
    assert len(event_contract(result)) == 2 and not receipt['expanded_detail']
    assert receipt['proposal'] == receipt['reviewed']['R1'] == receipt['selected']
    assert result['manifest']['measurements']['provider_usage']['calls'] == 4


def test_catalog_gap_expands_same_case_before_source_recovery(tmp_path, monkeypatch):
    """PURPOSE: Discriminate an indexed retrieval omission from missing EEG knowledge.
    INPUT: One intentional missing semantic body retained in the lightweight catalog and original EEG.
    OUTPUT: Same-Case additional read restores the ED before any source reconstruction.
    """
    from src.eeg.eeg_store import EEGLookup

    database, dd, config, graph = fixture(tmp_path)
    path = tmp_path / 'progressive.sqlite'
    write_index(path, graph, 'retrieval-gap')
    original = EEGLookup.case_graph

    def omit_detail(self, *args, **kwargs):
        """PURPOSE: Simulate a lightweight/body mismatch. INPUT: Catalog read. OUTPUT: Altered semantic view."""
        projected = original(self, *args, **kwargs)
        if kwargs.get('for_pi'):
            projected['event_definitions'] = []
        return projected

    monkeypatch.setattr(EEGLookup, 'case_graph', omit_detail)
    result = run_pipeline(database, dd, 'Extract Approved for each order.', client=ScriptedClient(),
                          graph=EEGStore(path, 'retrieval-gap'), config=config, evidence_retrieval=False)
    assert result['es']['status'] == 'accepted' and len(event_contract(result)) == 2
    assert result['manifest']['measurements']['lookup']['expanded_for_missing_evidence']
    assert not result['manifest']['recovery']['triggered']
    receipt, = result['query']['process_interpretation_trace']['initial_retrieval_coverage']
    assert receipt['retrieval_gaps'] and not receipt['selected']


def test_index_preserves_distinct_recovery_candidates_with_one_clock(tmp_path):
    """PURPOSE: Store distinct unresolved values for the same TimestampUnit.
    INPUT: Two pending codes on one clock. OUTPUT: Both candidates in request-local recovery.
    """
    database, _, _, graph = fixture(tmp_path)
    definitions = graph['event_definitions']
    clock = next(ed['ts_id'] for ed in definitions if ed.get('ts_id'))
    evidence = {'pairs': [{'candidate_id': 'candidate:' + value, 'table': 'orders', 'ts_id': clock, 'value': value}
                          for value in ('missing-B', 'missing-C')]}
    graph = {**graph, 'unresolved_event_evidence': evidence}
    index = tmp_path / 'pending.sqlite'
    write_index(index, graph, 'pending')
    with EEGStore(index, 'pending').open(database) as lookup:
        projection = lookup.request_graph('Extract Approved for each order.')
        restored = lookup.recovery_graph(projection)
    assert restored['unresolved_event_evidence']['pairs'] == evidence['pairs']
