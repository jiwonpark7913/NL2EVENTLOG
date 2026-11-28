"""Offline release entry-point controls for S0 and the final paper arms."""

from contextlib import contextmanager
import json
from types import SimpleNamespace

import pytest

from evaluation_harness import final_runner as runner
from evaluation_harness.contract import digest, read, value_digest, write
from src.__main__ import main as cli
from src.eeg.eeg_store import write_index
from src.release_runtime import HAIKU, METHOD_VERSION, prepare_eeg
from src.step1_understand.eeg_configuration import DbuConfig
from test_minimal_step2 import logistics, pairs, scripted_plan
from test_pipeline_runtime import ScriptedClient

QUESTION = 'Show actual commissioning for each depot.'
SQL = """SELECT id AS case_id, 'Commissioning' AS activity, commissioned_at AS timestamp,
    'depots' AS source_table, id AS source_record_id, 'commissioned_at' AS source_timestamp_column,
    '' AS occurrence_key FROM depots"""


def commissioning(cards):
    """PURPOSE: Bind the fixture's documented direct commissioning event.
    INPUT: Event cards. OUTPUT: Existing ED and path identifiers.
    """
    return pairs(cards, lambda card: 'commissioned_at' in card['clock_id'])


@pytest.fixture
def snapshot(tmp_path):
    """PURPOSE: Supply a portable prepared graph/index. INPUT: Scratch directory. OUTPUT: DB, DD and verified snapshot."""
    database, graph = logistics(tmp_path)
    dictionary = tmp_path/'dictionary.json'
    path = tmp_path/'snapshot'
    stamp = value_digest(graph)
    write(path/'eeg.json', graph)
    write_index(path/'index.sqlite', graph, stamp)
    write(path/'snapshot.json', {'eeg_sha256': stamp, 'index_sha256': digest(path/'index.sqlite')})
    return database, dictionary, path


class ReplayClient:
    """Use the existing S0 selector double and a separate recorded-style SQL response."""

    def __init__(self, *, abstain=False):
        """PURPOSE: Isolate modeled roles and Direct wires. INPUT: Optional Event abstention. OUTPUT: SDK-style client."""
        self.roles = []
        self.direct = []
        self.s0 = scripted_plan('Logistics Depot', commissioning,
                                selection_status='insufficient_evidence' if abstain else 'selected')
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **options):
        """PURPOSE: Receive a role without touching a provider. INPUT: Actual role wire. OUTPUT: Local reply."""
        role = options['response_format']['json_schema']['name']
        self.roles.append(role)
        if role == 'direct_sql_self_correct':
            self.direct.append(json.loads(options['messages'][-1]['content'])['runtime_evidence'])
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                content=json.dumps({'status':'sql','sql':SQL,'reason':'fixture','evidence':[]})))])
        return self.s0.create(**options)

    def reset_request_state(self):
        """PURPOSE: Match the runner client boundary. INPUT: None. OUTPUT: Compatible stateless reset."""
        return None


def install_replay(monkeypatch, client):
    """PURPOSE: Eliminate all network calls in both public CLIs. INPUT: Monkeypatch and fake client. OUTPUT: Two patched factories."""
    @contextmanager
    def native(*args, **kwargs):
        """PURPOSE: Yield an SDK double with an available guard. INPUT: Unused transport options. OUTPUT: Client and guard maps."""
        yield {HAIKU:client}, {HAIKU:SimpleNamespace(blocked=None)}

    monkeypatch.setattr('src.release_providers.release_clients', native)
    monkeypatch.setattr(runner, 'release_clients', native)


def test_default_cli_writes_s0_and_verified_snapshot(snapshot, tmp_path, monkeypatch):
    """PURPOSE: Test the normal CLI path and reusable artifacts. INPUT: Prepared snapshot and saved-style roles. OUTPUT: S0 only."""
    database, dictionary, path = snapshot
    client = ReplayClient()
    install_replay(monkeypatch, client)
    output = tmp_path/'cli'

    def reject_legacy(*args, **kwargs):
        """PURPOSE: Fail on retired orchestration. INPUT: Any legacy call. OUTPUT: Assertion."""
        raise AssertionError('Legacy pipeline invoked')

    monkeypatch.setattr('src.pipeline.run_pipeline', reject_legacy)
    assert cli(['--database',str(database),'--dictionary',str(dictionary),'--question',QUESTION,
                '--eeg-snapshot',str(path),'--max-usd','1.5','--output-dir',str(output)]) == 0
    assert client.roles == ['minimal_intent','minimal_case','minimal_events']
    result = read(output/'receipt.json')
    assert result['outcome']['status'] == 'accepted' and len(result['outcome']['rows']) == 3
    assert read(output/'manifest.json')['method'] == METHOD_VERSION
    assert prepare_eeg(database, dictionary, snapshot=output/'eeg').identity['eeg_sha256'] == result['release']['eeg_sha256']
    dictionary.write_text(json.dumps({'name':'Another original dictionary'}))
    with pytest.raises(ValueError, match='Original DD'):
        prepare_eeg(database, dictionary, snapshot=path)


def test_build_and_reuse_official_index(snapshot, tmp_path):
    """PURPOSE: Exercise real Stage 1 integration with scripted model replies. INPUT: Public fixture. OUTPUT: Built then cached index."""
    database, dictionary, _ = snapshot
    config = DbuConfig(model=HAIKU, repair=False, semantic_signatures=False,
                       global_ot_review=False, pairwise_identity_llm=False)
    client = ScriptedClient()
    first = prepare_eeg(database, dictionary, build_client=client, config=config, cache=tmp_path/'cache')
    calls = len(client.calls)
    second = prepare_eeg(database, dictionary, build_client=client, config=config, cache=tmp_path/'cache')
    assert calls > 0 and len(client.calls) == calls
    assert first.identity['origin'] == 'built' and second.identity['origin'] == 'disk_hit'
    assert first.identity['eeg_sha256'] == second.identity['eeg_sha256']
    assert first.identity['index_sha256'] == second.identity['index_sha256']


def test_paper_arms_share_one_s0_and_exact_inputs(snapshot, monkeypatch):
    """PURPOSE: Confirm the paper-arm factors and shared PI/ESpec. INPUT: All structural arms. OUTPUT: One S0 and four SQL roles."""
    from evaluation_harness.final_baselines import direct_context, direct_tools

    database, dictionary, path = snapshot
    eeg = prepare_eeg(database, dictionary, snapshot=path)
    tools = direct_tools()
    base = direct_context(database, dictionary, tools)
    client = ReplayClient()
    payload = runner.companion_worker('compact', input_text=json.dumps(eeg.graph))
    compact = {'eeg_sha256':eeg.identity['eeg_sha256'], 'payload':payload}
    measurements = {}
    monkeypatch.setattr(runner, 'entries', lambda _: client.roles)
    outcomes = runner.run_condition(database, QUESTION, eeg=eeg, client=client, model=HAIKU,
                                    arms=runner.ARMS, base=base, tools=tools, compact=compact,
                                    measurements=measurements, ledgers={HAIKU: path/'fake-ledger.json'})
    assert {name: item['provider_attempt_ranges'][HAIKU] for name, item in measurements.items()} == {
        'M0':[0,1], 'M1':[1,2], 'shared_s0':[2,5], 'M2':[5,6], 'S-LLM':[6,7]}
    assert all(item['wall_seconds'] >= 0 for item in measurements.values())
    assert client.roles == ['direct_sql_self_correct']*2 + ['minimal_intent','minimal_case','minimal_events'] + ['direct_sql_self_correct']*2
    assert all(outcomes[arm]['status']=='accepted' for arm in runner.ARMS)
    assert client.direct[0] == base
    assert client.direct[1] == {**base,'evidence_graph':payload}
    assert client.direct[2]['process_interpretation'] == outcomes['M3']['pi'] == outcomes['M2']['pi']
    assert client.direct[3]['fixed_extraction_ir'] == outcomes['S-Gen']['es'] == outcomes['S-LLM']['es']
    assert outcomes['S-Gen']['sql'] == outcomes['M3']['sql']
    assert outcomes['S-Gen']['rows'] == outcomes['M3']['rows']
    assert outcomes['S-LLM']['es_sha256'] == value_digest(outcomes['M3']['es'])


def test_final_cli_approval_and_separate_v4_scoring(snapshot, tmp_path, monkeypatch, capsys):
    """PURPOSE: Check plan authorization and the isolated offline scoring route.
    INPUT: Public fixture, fake receipt, separately stored reference.
    OUTPUT: Approved M3/Direct result, rejected wrong approval and common v4 grade.
    """
    database,dictionary,path = snapshot
    client = ReplayClient()
    install_replay(monkeypatch, client)
    qfile, approval = tmp_path/'questions.json', tmp_path/'approval.json'
    write(qfile,[{'qid':'X01','question':QUESTION}])
    public = ['--database',str(database),'--dictionary',str(dictionary),'--questions',str(qfile),
              '--eeg-snapshot',str(path),'--phase','development','--model',HAIKU,'--arms','M0','M3']
    runner.main(['plan',*public])
    plan = json.loads(capsys.readouterr().out)
    output = tmp_path/'predictions'
    infer = ['infer',*public,'--output',str(output),'--approval',str(approval)]
    write(approval,{'scope':runner.RUNNER_VERSION,'binding_sha256':'invalid','authorized':True,'max_usd':'1.50'})
    with pytest.raises(ValueError,match='exact final-runner plan'):
        runner.main(infer)
    assert not output.exists() and not client.roles
    write(approval,{'scope':runner.RUNNER_VERSION,'binding_sha256':plan['binding_sha256'],'authorized':True,'max_usd':'1.50'})
    runner.main(infer)
    manifest = read(output/'run.json')
    assert manifest['binding'] == plan['binding']
    assert manifest['eeg']['origin'] == 'supplied_snapshot'
    assert manifest['setup_measurements']['eeg_preparation']['provider_attempt_ranges'][HAIKU] == [0,0]
    assert (output/'complete.json').exists()

    references = tmp_path/'evaluator'/'reference.json'
    receipt = read(output/'X01.json')
    assert set(receipt['_condition']['operations']) == {'M0', 'shared_s0'}
    actual_activity = receipt['M3']['rows'][0]['activity'].replace("'","''")
    write(references,{'database_sha256':digest(database),'timezone':'UTC',
                      'queries':[{'qid':'X01','case_table':'depots','sql':SQL.replace('Commissioning',actual_activity),
                                  'aliases':{actual_activity:['Commissioning']}}]})
    with pytest.raises(ValueError,match='Evaluator-only'):
        runner.main(['plan',*public,'--questions',str(references)])
    scores = tmp_path/'scoring.json'
    runner.main(['score-v4','--database',str(database),'--references',str(references),
                 '--predictions',str(output),'--output',str(scores)])
    outcomes = read(scores)['scores']['X01']
    assert all(outcomes[arm]['extraction']['exact_match'] and outcomes[arm]['semantic']['exact_match']
               for arm in ('M0','M3'))
    assert client.roles == ['direct_sql_self_correct','minimal_intent','minimal_case','minimal_events']
