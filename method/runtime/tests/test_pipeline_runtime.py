"""Offline contracts for the standalone, relocated current runtime."""
import copy
import importlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
from functools import partial
from dataclasses import asdict
from types import SimpleNamespace
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from src.pipeline import _run_pipeline, run_pipeline
from src.__main__ import save_run
from src.step3_execute.pipeline import run_repair_pipeline
from src.step1_understand.eeg_configuration import DbuConfig
from src.eeg.evidence_graph_cache import clear_memory, load_or_build
from src.eeg.evidence_graph_storage import FORMAT_VERSION, json_bytes, read_eeg_layers
from src.step2_retrieve_and_interpret.pipeline import _interpret_process_request
from src.step2_retrieve_and_interpret.eeg_delivery import EEGDelivery
from src.step2_retrieve_and_interpret.execute_model_roles import SCHEMAS, PROMPT_FILES
from src.common.prompt_loader import load_prompt


def scope_judgments(payload, reply):
    """PURPOSE: Supply exhaustive offline judgments for existing scripted PI scenarios.
    INPUT: Wire payload and expected review verdicts. OUTPUT: None; extends the test reply in place.
    """
    review = payload.get('activity_review', {})
    if not review.get('scope_verification'):
        return
    spans = {r['id']: r['span'] for r in review['requirements']}
    for item in reply['requirement_reviews']:
        item.setdefault('candidate_decisions', [
            {'event_definition_id': a['id'], 'decision': 'include' if a['id'] in item['event_definition_ids'] else 'exclude',
             'span': spans[item['requirement_id']], 'quote': (a.get('dictionary_evidence')
                       or payload.get('source_context_by_table', {}).get(a.get('source'))
                       or [a.get('meaning') or a['name']])[0]}
            for a in review['candidates']])


class ScriptedClient:
    """Deterministic schema replies for the small public order fixture."""
    def __init__(self):
        """PURPOSE: Create an offline model double. INPUT: None. OUTPUT: SDK-compatible call ledger."""
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        """PURPOSE: Respond only to expected roles using their supplied public IDs.
        INPUT: Runtime structured-output request. OUTPUT: In-memory SDK-shaped reply; no network.
        """
        self.calls.append(kwargs)
        role = kwargs['response_format']['json_schema']['name']
        raw = kwargs['messages'][1]['content']
        if raw.startswith('<runtime_data>'):
            raw = raw.split('\n', 1)[1].rsplit('\n', 1)[0]
        payload = json.loads(raw)
        if role == 'pi_cases':
            reply = {'candidates': [{'et': payload['entity_types'][0]['id'],
                'mode': 'explicit' if 'Approved' in payload['original_request'] else 'implicit', 'focus': ''}]}
        elif role == 'pi_events':
            reply = {'matches': [{'requirement_id': 'R1', 'event_definition_ids': [a['id']]}
                                 for a in payload['activities'] if a['name'] == 'Approved']}
        elif role == 'semantic_decomposer':
            explicit = 'Approved' in payload['original_request']
            reply = {'activity_scope': 'explicit' if explicit else 'implicit', 'process_focus': None,
                'case_requirement': {'span': 'each order', 'meaning': 'Order'},
                'scope_requirement': {'span': payload['original_request'], 'object_scope': 'own', 'granularity': 'coarse'},
                'activity_requirements': [{'id': 'R1', 'span': 'Approved', 'meaning': 'Approved', 'qualifiers': [], 'coverage': 'one', 'granularity': 'coarse'}]
                    if explicit else []}
            if 'Refunded' in payload['original_request']:
                reply['activity_requirements'].append(
                    {'id': 'R2', 'span': 'Refunded', 'meaning': 'Refunded', 'qualifiers': [], 'coverage': 'one', 'granularity': 'coarse'})
        elif role == 'pi_crosscheck':
            reply = {'differences': []}
            if 'activity_review' in payload:
                review = payload['activity_review']
                approved = [a['id'] for a in review['candidates'] if a['name'] == 'Approved']
                reply['requirement_reviews'] = [
                    {'requirement_id': r['id'], 'event_definition_ids': approved if r['id'] == 'R1' else [],
                     'semantic_status': 'matched' if r['id'] == 'R1' and approved else 'missing',
                     'reviewed_coverage': r['coverage'], 'reviewed_granularity': r['granularity'],
                     'source_attribution_gap': False,
                     'reason': 'Uses the order approval time.' if r['id'] == 'R1' else 'No refund definition.'}
                    for r in review['requirements']]
                if review['initial_proposals']:
                    for verdict in reply['requirement_reviews']:
                        verdict['exclusions'] = []
                if 'complete_tier1_inventory' in payload:
                    reply['absent_from_tier1'] = []
        elif role == 'pi_revise_requirement':
            reply = {'edits': []}
        elif role == 'pi_revise':
            reply = {'action': 'abstain', 'et': payload['selection']['et'], 'mode': 'explicit',
                     'focus': '', 'ids': [], 'resolutions': []}
        elif role == 'entity_identification_review':
            reply = {'descriptions': []}
        elif role == 'entity_event_review':
            reply = {'decisions': [dict(id=d['id'], duplicate_of='', reason='', citations=[],
                paths=[dict(path_id=p['id'], status='uncertain', role='unspecified', reason='', citations=[])
                       for p in d['paths']]) for d in payload['definitions']]}
        elif role == 'eeg_business_descriptions':
            reply = {alias: ('One business order' if alias.startswith('ET') else 'Order approved')
                     for alias in payload}
        else:
            raise AssertionError('Unexpected role: ' + role)
        scope_judgments(payload, reply)
        from jsonschema import validate
        validate(reply, kwargs['response_format']['json_schema']['schema'])
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
            content=json.dumps(reply), refusal=None), finish_reason='stop')],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15))


class RequirementScenarioClient(ScriptedClient):
    """Execute custom offline PI replies while sharing the existing EEG build double."""

    def __init__(self, responses):
        """PURPOSE: Configure role overrides. INPUT: Role-to-payload responder map. OUTPUT: Scripted SDK client."""
        super().__init__()
        self.responses = responses

    def create(self, **options):
        """PURPOSE: Serve an overridden role or defer to the shared fixture. INPUT: Model request. OUTPUT: SDK reply."""
        schema = options['response_format']['json_schema']
        role = schema['name']
        if role not in self.responses and role not in ('pi_cases','pi_crosscheck'):
            return super().create(**options)
        self.calls.append(options)
        raw = options['messages'][1]['content']
        payload = json.loads(raw.split('\n',1)[1].rsplit('\n',1)[0])
        if role in self.responses:
            reply = self.responses[role](payload)
        elif role=='pi_cases':
            reply = {'candidates':[{'et':payload['entity_types'][0]['id'],'mode':'explicit','focus':''}]}
        else:
            reply = self.review_proposals(payload)
        scope_judgments(payload, reply)
        from jsonschema import validate
        validate(reply,schema['schema'])
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
            content=json.dumps(reply),refusal=None))],usage=None)

    @staticmethod
    def review_proposals(payload, replacements=()):
        """PURPOSE: Confirm offered per-item IDs with optional disagreement. INPUT: Review payload. OUTPUT: Verdicts."""
        review = payload['activity_review']
        proposals = {m['requirement_id']:m['event_definition_ids'] for m in review['initial_proposals']}
        proposals.update(review['revised_proposals'])
        proposals.update({m['requirement_id']:m['event_definition_ids'] for m in replacements})
        verdicts = []
        for r in review['requirements']:
            ids = proposals[r['id']]
            item = {'requirement_id':r['id'],'event_definition_ids':ids,
                    'semantic_status':'matched','reviewed_coverage':r['coverage'],
                    'reviewed_granularity':r['granularity'],'source_attribution_gap':False,
                    'reason':'These occurrences match the required phases.'}
            if review['initial_proposals']:
                item['exclusions'] = []
            verdicts.append(item)
        return {'differences':[],'requirement_reviews':verdicts}


class StandaloneRuntimeTests(unittest.TestCase):
    def setUp(self):
        """PURPOSE: Create public DB/DD inputs. INPUT: Test lifecycle. OUTPUT: Isolated fixture and cache."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / 'database.sqlite'
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.executescript("CREATE TABLE orders(id INTEGER PRIMARY KEY,activity TEXT,occurred_at TEXT);"
                "INSERT INTO orders VALUES(1,'A','2025-01-01T00:00:00Z'),(2,'A','2025-01-02T00:00:00Z');")
        self.dd = {'name': 'RuntimeFixture', 'timezone': 'UTC', 'tables': [{'table': 'orders',
            'definition': 'One order business entity, with its recorded activity and actual occurrence time.',
            'primary_key': ['id'], 'columns': [
                {'name': 'id', 'type': 'INTEGER', 'definition': 'Order identifier'},
                {'name': 'activity', 'type': 'TEXT', 'definition': 'Activity status code.', 'code_meanings': {'A': 'Approved'}},
                {'name': 'occurred_at', 'type': 'TEXT', 'definition': 'Actual activity occurrence time'}]}]}
        self.config = DbuConfig(repair=False, semantic_signatures=False,
                                global_ot_review=False, pairwise_identity_llm=False)
        self.env = patch.dict(os.environ, {'NL2EL_EEG_CACHE_DIR': str(self.root/'cache'), 'NL2EL_SEMANTIC_MODEL': 'off'})
        self.env.start(); self.addCleanup(self.env.stop)
        clear_memory(); self.addCleanup(clear_memory)

    def test_coordinated_requirements_keep_literal_evidence_and_retry_fresh(self):
        """PURPOSE: Exercise the retry cache and shared source clauses through Steps 2–4.
        INPUT: Two identical rejected generations and a corrected third generation.
        OUTPUT: Three uncached attempts, distinct normalized occurrences and both extracted activities.
        """
        self.add_requirement_fixture()
        question = 'For each order, include packing start and completion.'
        clause = 'packing start and completion'
        spans = iter(['packing completion', 'packing completion', clause])

        def parse(payload):
            """PURPOSE: Reproduce a nonliteral citation twice. INPUT: Parser payload. OUTPUT: Scripted decomposition."""
            return self.explicit_parse(question, [
                self.requirement('R1', clause, 'Packing started'),
                self.requirement('R2', next(spans), 'Packing completed')])

        def select(payload):
            """PURPOSE: Ground both coordinated phases. INPUT: Offered cards. OUTPUT: One proposed ED per item."""
            return {'matches': [{'requirement_id': r['id'],
                'event_definition_ids': [a['id'] for a in payload['activities'] if a['name']==r['meaning']]}
                for r in payload['activity_requirements']]}

        cache = {}
        client = RequirementScenarioClient({'semantic_decomposer': parse, 'pi_events': select})
        result = run_pipeline(self.db, self.dd, question, client=client, config=self.config,
                              evidence_retrieval=False, response_cache=cache)
        query = result['query']
        calls = [a for a in query['process_interpretation_trace']['model_calls'] if a['role']=='semantic_decomposer']
        self.assertEqual([a['validation'] for a in calls], ['rejected','rejected','accepted'])
        self.assertEqual([a['cache_hit'] for a in calls], [False,False,False])
        self.assertIn('R2.span', calls[1]['rejection'])
        self.assertEqual(calls[1]['cache_key'], calls[2]['cache_key'])
        self.assertNotIn(calls[0]['cache_key'], cache)
        self.assertEqual(cache[calls[2]['cache_key']]['activity_requirements'][1]['span'], clause)
        self.assertEqual(result['es']['status'], 'accepted')
        self.assertCountEqual([r['activity'] for r in result['execution']['event_log']],
                              ['Packing started', 'Packing completed'])

    def test_revision_only_edits_unresolved_requirement_and_rechecks_same_ids(self):
        """PURPOSE: Resolve a shared phase modifier with a local edit.
        INPUT: Verified approval/inspection, ambiguous packing and a revision that keeps the initial packing ED.
        OUTPUT: Stable verified items, an independently reviewed packing correction and exact SQL activities.
        """
        self.add_requirement_fixture()
        question = 'For each order, include approval and completion of inspection and packing.'
        clause = 'completion of inspection and packing'
        reviewed = []

        def revise(payload):
            """PURPOSE: Assert the revision boundary. INPUT: Unresolved R3. OUTPUT: Completed packing edit."""
            self.assertEqual([r['id'] for r in payload['unresolved_requirements']], ['R3'])
            self.assertEqual(payload['verified_requirement_ids'], ['R1', 'R2'])
            self.assertIn('ambiguous_candidates', payload['review_findings'][0]['reason_codes'])
            done = next(a['id'] for a in payload['activities'] if a['name']=='Packing completed')
            item = self.requirement('R3', clause, 'Packing completed')
            item.update(qualifiers=['completion'], event_definition_ids=[done])
            return {'edits': [{'requirement_id': item.pop('id'), **item}]}

        def review(payload):
            """PURPOSE: Keep two requirements locked. INPUT: First review/all and second review/R3. OUTPUT: Verdicts."""
            review_data = payload['activity_review']
            reviewed.append([r['id'] for r in review_data['requirements']])
            if len(reviewed)==1:
                candidates = [{'requirement_id':'R3', 'event_definition_ids': [
                    a['id'] for a in review_data['candidates'] if a['name'].startswith('Packing')]}]
                return RequirementScenarioClient.review_proposals(payload, candidates)
            self.assertEqual(review_data['requirements'][0]['span'], clause)
            self.assertEqual(review_data['requirements'][0]['qualifiers'], ['completion'])
            return RequirementScenarioClient.review_proposals(payload)

        client = RequirementScenarioClient({
            'semantic_decomposer': lambda _: self.explicit_parse(question, [
                self.requirement('R1','approval','Approved'),
                self.requirement('R2',clause,'Inspection completed'),
                self.requirement('R3','packing','Packing')]),
            'pi_events': lambda payload: {'matches': [
                {'requirement_id':rid,'event_definition_ids':[a['id'] for a in payload['activities'] if a['name']==label]}
                for rid,label in [('R1','Approved'),('R2','Inspection completed'),('R3','Packing completed')]]},
            'pi_crosscheck': review,
            'pi_revise_requirement': revise,
        })
        result = run_pipeline(self.db, self.dd, question, client=client, config=self.config, evidence_retrieval=False)
        self.assertEqual(reviewed, [['R1','R2','R3'], ['R3']])
        query = result['query']
        self.assertEqual(result['es']['status'], 'accepted')
        self.assertEqual(query['process_information']['activity_requirements'][-1]['meaning'], 'Packing completed')
        self.assertEqual(query['process_view_revisions'][0]['role'], 'pi_revise_requirement')
        self.assertEqual(sorted(query['process_view_initial_selection']['event_definition_ids']),
                         sorted(query['process_information']['selected_event_definition_ids']))
        self.assertEqual({r['activity'] for r in result['execution']['event_log']},
                         {'Approved','Inspection completed','Packing completed'})

    def test_crosscheck_narrowing_requires_evidence_then_preserves_complementary_events(self):
        """PURPOSE: Prevent an endpoint-only review from silently discarding initial EDs.
        INPUT: A milestone family, three proposed EDs, and a reviewer that initially keeps two.
        OUTPUT: Targeted revision with the missing middle ED in its diagnostic, followed by an exact log.
        """
        self.add_requirement_fixture()
        question = 'For each order, include packing milestones from start to completion.'
        clause = 'packing milestones from start to completion'
        labels = {'Packing started','Inspection completed','Packing completed'}
        reviewed = []

        def review(payload):
            """PURPOSE: Simulate a lossy review and a corrected review. INPUT: Review inventory. OUTPUT: Verdict."""
            reviewed.append(payload['activity_review']['requirements'])
            if len(reviewed)==1:
                endpoints = [a['id'] for a in payload['activity_review']['candidates'] if a['name'].startswith('Packing')]
                return RequirementScenarioClient.review_proposals(payload, [
                    {'requirement_id':'R1','event_definition_ids':endpoints}])
            return RequirementScenarioClient.review_proposals(payload)

        def revise(payload):
            """PURPOSE: Resolve the missed intermediate event. INPUT: Pending milestone requirement. OUTPUT: Family edit."""
            verdict = payload['review_findings'][0]
            self.assertIn('initial_selection_exclusion_unverified', verdict['reason_codes'])
            middle = next(a['id'] for a in payload['activities'] if a['name']=='Inspection completed')
            self.assertEqual(verdict['unaccounted_initial_ed_ids'], [middle])
            item = self.requirement('R1', clause, 'All packing milestones', coverage='all')
            ids = [a['id'] for a in payload['activities'] if a['name'] in labels]
            return {'edits': [{'requirement_id':item.pop('id'), **item, 'event_definition_ids':ids}]}

        client = RequirementScenarioClient({
            'semantic_decomposer': lambda _: self.explicit_parse(
                question,[self.requirement('R1',clause,'Packing milestone')]),
            'pi_events': lambda payload: {'matches': [{'requirement_id':'R1',
                'event_definition_ids':[a['id'] for a in payload['activities'] if a['name'] in labels]}]},
            'pi_crosscheck': review,
            'pi_revise_requirement': revise,
        })
        result = run_pipeline(self.db, self.dd, question, client=client, config=self.config, evidence_retrieval=False)
        self.assertEqual(len(reviewed),2)
        self.assertEqual(result['es']['status'], 'accepted')
        self.assertEqual({r['activity'] for r in result['execution']['event_log']}, labels)

    def add_requirement_fixture(self):
        """PURPOSE: Supply separable phases for regression tests. INPUT: Existing order fixture. OUTPUT: Added activities."""
        self.dd['tables'][0]['columns'][1]['code_meanings'].update(
            B='Packing started', C='Inspection completed', D='Packing completed')
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.executemany('INSERT INTO orders VALUES (?, ?, ?)', [
                (3,'B','2025-01-03T00:00:00Z'), (4,'C','2025-01-04T00:00:00Z'), (5,'D','2025-01-05T00:00:00Z')])

    @staticmethod
    def explicit_parse(question, requirements):
        """PURPOSE: Build a test parse. INPUT: Original text and activities. OUTPUT: Explicit role reply."""
        return {'activity_scope':'explicit','process_focus':None,
                'case_requirement':{'span':'each order','meaning':'Order'},
                'scope_requirement':{'span':question,'object_scope':'own','granularity':'coarse'},
                'activity_requirements':requirements}

    @staticmethod
    def requirement(identifier, span, meaning, coverage='one'):
        """PURPOSE: Build one test requirement. INPUT: Literal and normalized text. OUTPUT: Role-shaped item."""
        return {'id':identifier,'span':span,'meaning':meaning,'qualifiers':[],
                'coverage':coverage,'granularity':'coarse'}

    def test_independent_initial_selection_audits_inputs_and_survives_parser_rejections(self):
        """PURPOSE: Check input separation and parser failure behavior through Steps 2–4.
        INPUT: One case and ED, with accepted and repeatedly malformed decomposition.
        OUTPUT: Independent role sequence and retained proposal only for the experimental arm.
        """
        question = 'Extract Approved for each order.'

        def independent_case(payload):
            """PURPOSE: Check the raw-only case contract. INPUT: Role payload. OUTPUT: Offered case."""
            self.assertNotIn('request_interpretation', payload)
            return {'candidates':[{'et':payload['entity_types'][0]['id'],'mode':'explicit',
                                   'focus':'','object_scope':'unresolved'}]}

        def independent_events(payload):
            """PURPOSE: Check the ED choice has no decomposition. INPUT: Role payload. OUTPUT: Grounded ED."""
            self.assertNotIn('activity_requirements',payload)
            return {'selected_events':[{'event_definition_id':a['id'],'path_id':''} for a in payload['activities']]}

        def independent_review(payload):
            """PURPOSE: Align the separately chosen ED to its requirement. INPUT: Both interpretations. OUTPUT: Verdict."""
            ids = payload['activity_review']['independent_proposal_ids']
            reply = RequirementScenarioClient.review_proposals(payload,[{'requirement_id':'R1','event_definition_ids':ids}])
            reply['requirement_reviews'][0].update(aligned_proposal_ids=ids,exclusions=[])
            return reply

        def interpret(question, graph, **opts):
            """PURPOSE: Enable the experimental controller on Delivery B. INPUT: Pipeline context. OUTPUT: Verified PI."""
            return _interpret_process_request(question,graph,eeg_delivery=EEGDelivery(graph,'layer'),
                                              independent_initial=True,**opts)

        for malformed in (False,True):
            def parse(payload):
                """PURPOSE: Assert the parser only sees the original request. INPUT: Request payload. OUTPUT: Controlled parse."""
                self.assertEqual(set(payload)-{'previous_rejection'}, {'original_request'})
                return self.explicit_parse(question,[
                    self.requirement('R1','invented phrase' if malformed else 'Approved','Approved')])

            responses = {'semantic_decomposer':parse,'pi_cases':independent_case,'pi_events':independent_events,
                         'pi_crosscheck':independent_review}
            result = _run_pipeline(self.db,self.dd,question,client=RequirementScenarioClient(responses),
                                   config=self.config,evidence_retrieval=False,interpret=interpret,response_cache={})
            query = result['query']
            roles = [a['role'] for a in query['process_interpretation_trace']['model_calls']]
            self.assertEqual(roles[:3],['pi_cases','pi_events','semantic_decomposer'])
            self.assertEqual(len(query['process_view_initial_selection']['event_definition_ids']),1)
            if malformed:
                self.assertEqual(roles[-3:], ['semantic_decomposer']*3)
                self.assertEqual(result['es']['status'],'selection_required')
                self.assertFalse(result['execution'])
                control = run_pipeline(self.db,self.dd,question,client=RequirementScenarioClient({'semantic_decomposer':parse}),
                                       config=self.config,evidence_retrieval=False,response_cache={})
                base = control['query']
                self.assertEqual([a['role'] for a in base['process_interpretation_trace']['model_calls']],
                                 ['semantic_decomposer']*3)
                self.assertEqual(base['process_view_initial_selection']['event_definition_ids'],[])
            else:
                self.assertEqual(result['es']['status'],'accepted')
                self.assertEqual(len(result['execution']['event_log']),2)

    def test_full_pipeline_explicit_and_implicit(self):
        """PURPOSE: Exercise all four relocated stages on real SQLite data.
        INPUT: Explicit/implicit requests and an offline schema client.
        OUTPUT: Accepted ES, exact approval rows, and completed physical verification.
        """
        for question in ('Extract Approved for each order.', 'Extract history for each order.'):
            with self.subTest(question=question):
                result = run_pipeline(self.db, self.dd, question, client=ScriptedClient(),
                    config=self.config, evidence_retrieval=False)
                self.assertEqual(result['query']['status'], 'ready', result['query'].get('process_interpretation_trace'))
                self.assertEqual(result['es']['status'], 'accepted', result['verification'])
                self.assertEqual(len(result['execution']['event_log']), 2)
                self.assertEqual({r['activity'] for r in result['execution']['event_log']}, {'Approved'})
                self.assertEqual(result['manifest']['step2']['eeg_delivery'], 'layer')
                self.assertEqual(result['manifest']['step3']['selector'], 'deterministic_pi_materializer')
                self.assertNotEqual(result['manifest']['step3']['verification_and_repair']['status'], 'not_run')
                self.assertTrue(result['graph']['indexed_request'])
                output = self.root / ('explicit' if 'Approved' in question else 'implicit')
                save_run(result, output)
                layer_directory = output / 'eeg'
                manifest = json.loads((layer_directory / 'manifest.json').read_text())
                self.assertEqual(manifest['storage_format'], FORMAT_VERSION)
                restored, native = read_eeg_layers(layer_directory, manifest['artifacts'])
                self.assertIsNone(native)
                self.assertEqual(restored, json.loads((output / 'evidence_graph.json').read_text()))
                self.assertEqual(json.loads((output/'manifest.json').read_text())['status'], 'accepted')
                self.assertIn('Approved', (output/'event_log.csv').read_text())
                self.assertIn('SELECT', (output/'extraction.sql').read_text())


    def test_delivery_modes_keep_the_same_extraction_for_a_fixed_reply(self):
        """PURPOSE: Compare the fixed runtime with historical delivery in the experiment path.
        INPUT: Same public graph and fixed model replies. OUTPUT: Identical PI and verified log.
        """
        question = 'Extract Approved for each order.'
        baseline = run_pipeline(self.db, self.dd, question, client=ScriptedClient(),
                                config=self.config, evidence_retrieval=False)
        self.assertEqual(baseline['manifest']['step2']['eeg_delivery'], 'layer')
        for mode in ('current', 'query'):
            with self.subTest(mode=mode):
                delivery = None if mode == 'current' else EEGDelivery(baseline['graph'], mode)
                result = _run_pipeline(
                    self.db, self.dd, question, client=ScriptedClient(),
                    graph=baseline['graph'], config=self.config, evidence_retrieval=False,
                    interpret=partial(_interpret_process_request, eeg_delivery=delivery))
                self.assertEqual(result['query']['process_information'],
                                 baseline['query']['process_information'])
                self.assertEqual(result['execution']['event_log'], baseline['execution']['event_log'])
                self.assertEqual(result['manifest']['step2']['eeg_delivery'], mode)

    def test_repair_restores_witnessed_clock_without_changing_pi(self):
        """PURPOSE: Exercise the relocated physical repair and source-row witness code.
        INPUT: An executable wrong clock that drops one event and retimes another.
        OUTPUT: Original occurrence clock and two events, with PI and case population preserved.
        """
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute('ALTER TABLE orders ADD COLUMN recorded_at TEXT')
            conn.execute("UPDATE orders SET recorded_at=CASE WHEN id=1 THEN '2030-01-01T00:00:00Z' END")
        self.dd['tables'][0]['columns'].append({'name': 'recorded_at', 'type': 'TEXT',
            'definition': 'Technical insertion time, not a business occurrence.'})
        original = run_pipeline(self.db, self.dd, 'Extract Approved for each order.',
            client=ScriptedClient(), config=self.config, evidence_retrieval=False)
        damaged = copy.deepcopy(original['es'])
        damaged['event_rules'][0]['timestamp']['column'] = 'recorded_at'
        pi = copy.deepcopy(original['query']['process_view'])
        repaired = run_repair_pipeline(self.db, pi, damaged, graph=original['graph'])
        self.assertEqual(repaired['terminal_status'], 'accepted', repaired)
        self.assertEqual(repaired['es']['process_view'], pi)
        self.assertEqual(repaired['es']['case'], original['es']['case'])
        self.assertEqual(len(repaired['report']['execution']['event_log']), 2)
        self.assertTrue(repaired['attempts'])
        counts = repaired['attempts'][0]['diff']['counts']
        self.assertEqual((counts['added'], counts['retimed'], counts['moved']), (1, 1, 0))

    def test_package_imports_from_an_unrelated_directory(self):
        """PURPOSE: Prove source relocation does not require the historical repository.
        INPUT: Isolated Python process with only this project added to its import path.
        OUTPUT: Every runtime module imports, and CLI help requires no API credentials.
        """
        script = """import importlib, pathlib, sys
root = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(root))
for path in (root / 'src').rglob('*.py'):
    name = '.'.join(path.relative_to(root).with_suffix('').parts).removesuffix('.__init__')
    importlib.import_module(name)
assert not any(name == 'nl2el' or name.startswith('nl2el.') for name in sys.modules)
"""
        subprocess.run([sys.executable, '-I', '-B', '-c', script, str(PROJECT)],
                       cwd=self.root, check=True, capture_output=True, text=True)
        result = subprocess.run([sys.executable, '-B', '-m', 'src', '--help'],
                                cwd=PROJECT, check=True, capture_output=True, text=True)
        self.assertIn('--dictionary', result.stdout)

    def test_documented_report_key_survives_storage_only_model_judgment(self):
        """PURPOSE: Preserve a documented report ET and separate its PK from the referenced object.
        INPUT: SQLite reports and assets, public DD and a model that rejects the report as storage.
        OUTPUT: Report remains an independently validated ET; its asset FK still identifies the asset.
        """
        from contextlib import closing
        from src.step1_understand.pipeline import build_evidence_graph
        database = self.root / 'reports.sqlite'
        with closing(sqlite3.connect(database)) as connection, connection:
            connection.executescript(
                "CREATE TABLE assets(asset_id TEXT PRIMARY KEY);"
                "CREATE TABLE reports(report_id TEXT PRIMARY KEY, asset_id TEXT REFERENCES assets(asset_id));"
                "INSERT INTO assets VALUES('A1'); INSERT INTO reports VALUES('R1','A1');")
        dictionary = self.root / 'reports.json'
        dictionary.write_text(json.dumps({
            'assets': {'description': 'One row per registered asset.', 'columns': {
                'asset_id': {'description': 'Asset identifier.'}}},
            'reports': {'description': 'Inspection messages about registered assets.', 'columns': {
                'report_id': {'description': 'Inspection report identifier.'},
                'asset_id': {'description': 'Inspected asset identifier.'}}},
        }))
        response = {'descriptions': []}

        def reject_report(_client, _model, task, payload, _cache):
            """PURPOSE: Reproduce the model's storage-only judgment with genuine dictionary citations.
            INPUT: Step 1 role and payload. OUTPUT: Rejection for the report PK and empty other replies.
            """
            if task == 'identification':
                target = next(t for t in payload['targets'] if t['source']['columns'] == ['report_id'])
                statement = next(s for s in payload['dictionary_statements']
                                 if s['id'] == 'C:reports.report_id:definition')
                response['descriptions'] = [{'target_id': target['id'], 'business_meaning': '',
                    'instance_granularity': '', 'representation_role': 'storage_record', 'status': 'rejected',
                    'evidence': [{'id': statement['id'], 'quote': statement['text']}],
                    'reason': 'The report records an inspection of an asset.'}]
                return response, {'task': task}
            return {}, {'task': task}

        with patch('src.step1_understand.review_entity_meanings._call', side_effect=reject_report):
            graph = build_evidence_graph(database, dictionary, self.config, ScriptedClient()).data
        types = {et['name']: et for et in graph['entity_types']}
        self.assertEqual(types['Inspection Report']['case_key']['fields'], ['report_id'])
        self.assertEqual(types['Inspection Report']['population']['status'], 'valid')
        asset_ref = next(t for t in graph['identification_targets']
                         if t['source']['table'] == 'reports' and t['constraint_kind'] == 'reference')
        self.assertEqual(asset_ref['business_meaning'].lower(), 'asset')
        self.assertNotEqual(asset_ref.get('entity_type_id'), types['Inspection Report']['id'])

    def test_cache_reuse_and_dictionary_invalidation(self):
        """PURPOSE: Verify relocated cache paths and immutable reuse.
        INPUT: Repeated DB/DD and one changed public dictionary.
        OUTPUT: Memory/disk reuse and a new key after the dictionary changes.
        """
        client = ScriptedClient()
        with self.assertRaisesRegex(ValueError, 'requires an LLM client'):
            load_or_build(self.db, self.dd, client=None, config=self.config)
        first, native = load_or_build(self.db, self.dd, client=client, config=self.config)
        second, _ = load_or_build(self.db, self.dd, client=client, config=self.config)
        self.assertEqual(second['eeg_cache']['status'], 'memory_hit')
        clear_memory()
        third, restored_native = load_or_build(self.db, self.dd, client=client, config=self.config)
        self.assertEqual(third.pop('eeg_cache')['status'], 'disk_hit')
        location = Path(first.pop('eeg_cache')['directory'])
        self.assertEqual(json_bytes(first), json_bytes(third))
        self.assertEqual(json_bytes(native.to_dict()), json_bytes(restored_native.to_dict()))
        self.assertEqual(json_bytes([asdict(t) for t in native.physical_tables]),
                         json_bytes([asdict(t) for t in restored_native.physical_tables]))

        entity = json.loads((location / 'entity_layer.json').read_text())['runtime']
        event = json.loads((location / 'event_layer.json').read_text())['runtime']
        db = json.loads((location / 'db_layer.json').read_text())['runtime']
        links = json.loads((location / 'links.json').read_text())['runtime']
        self.assertEqual([row['id'] for row in entity['entity_types']],
                         [row['id'] for row in first['entity_types']])
        definition = first['event_definitions'][0]
        self.assertNotIn('timestamp_candidates', event['event_definitions'][0])
        sources = links['record_links']['event_sources']['event_definitions']
        self.assertEqual(json_bytes(sources[definition['id']]['timestamp_candidates']),
                         json_bytes(definition['timestamp_candidates']))
        self.assertEqual(json_bytes(links['attribution_paths']), json_bytes(first['attribution_paths']))
        self.assertIn('data_dictionary', db)

        (location / 'links.json').write_text('{}')
        clear_memory()
        rebuilt, _ = load_or_build(self.db, self.dd, client=client, config=self.config)
        self.assertEqual(rebuilt['eeg_cache']['status'], 'built')
        changed = copy.deepcopy(self.dd); changed['name'] = 'Changed public dictionary'
        fourth, _ = load_or_build(self.db, changed, client=client, config=self.config)
        self.assertNotEqual(rebuilt['eeg_cache']['key'], fourth['eeg_cache']['key'])

    def test_cache_does_not_publish_an_eeg_when_every_model_call_fails(self):
        """PURPOSE: Reject an apparently built graph after a full provider failure.
        INPUT: Public test inputs and a failing SDK double. OUTPUT: Explicit error and no cache manifest.
        """
        client = ScriptedClient()
        root = self.root / 'failed_build'
        with patch.object(client.chat.completions, 'create', side_effect=RuntimeError('provider unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'did not complete any LLM requests'):
                load_or_build(self.db, self.dd, client=client, config=self.config, directory=root)
        self.assertEqual(list(root.rglob('manifest.json')), [])

    def test_explicit_abstention_preserves_confirmed_items_without_execution(self):
        """PURPOSE: Keep independently verified activities when revision abstains.
        INPUT: One known and one missing activity. OUTPUT: Partial PI and no event log.
        """
        client = ScriptedClient()
        result = run_pipeline(self.db, self.dd, 'Extract Approved and Refunded for each order.',
                              client=client, config=self.config, evidence_retrieval=False)
        query = result['query']
        self.assertEqual(query['status'], 'partial')
        self.assertEqual(query['process_view_termination_reason'], 'revision_abstained')
        pi = query['process_information']
        self.assertTrue(pi['case_notion_et_id'])
        self.assertEqual(len(pi['selected_event_definition_ids']), 1)
        self.assertEqual([(item['id'], item['status'], item['reason_codes'])
                          for item in pi['activity_requirement_results']],
                         [('R1', 'verified', []), ('R2', 'unresolved', ['event_definition_missing'])])
        self.assertEqual(query['V_q']['unresolved_activity_requirement_ids'], ['R2'])
        self.assertEqual(result['es']['reason_code'], 'explicit_activity_requirements_unresolved')
        self.assertEqual(result['execution'], {})
        self.assertIsNone(result['verification'])

    def test_required_case_role_rejects_the_wrong_leg_and_keeps_direct_case_paths(self):
        """PURPOSE: Check the physical role gate independently of model semantics.
        INPUT: An outbound activity and different case paths. OUTPUT: Only supported paths are kept.
        """
        from src.step2_retrieve_and_interpret.verify_activity_requirements import verify_activity
        requirement = {'id': 'R1', 'span': 'ready', 'meaning': 'Ready to depart', 'qualifiers': ['outbound']}
        review = {'event_definition_ids': ['event'], 'semantic_status': 'matched',
                  'source_attribution_gap': False, 'reason': 'Records the readiness time.'}
        candidate = {'eligible': True, 'binding_policy': {'checks': {}},
                     'attribution': {'status': 'pass', 'paths': []}}
        catalog = {'event': candidate}
        candidate['attribution']['paths'] = [
            {'id': 'inbound', 'role_validation': {'status': 'pass', 'reference': {'role': 'inbound'}},
             'joins': [{'direction': 'parent_to_child'}]}]
        wrong_leg = verify_activity(requirement, review, catalog, ['event'], known_roles={'outbound','inbound'})
        self.assertEqual(wrong_leg['reason_codes'], ['case_attribution_missing'])
        candidate['attribution']['paths'] = [{'id': 'direct', 'joins': [{'direction': 'child_to_parent'}]}]
        direct = verify_activity(requirement, review, catalog, ['event'])
        self.assertEqual(direct['status'], 'verified')
        self.assertEqual(direct['attribution_path_ids'], ['direct'])
        missing = verify_activity(requirement, dict(review, event_definition_ids=[], semantic_status='missing',
                                                    source_attribution_gap=True), catalog, [])
        self.assertEqual(missing['reason_codes'], ['event_definition_missing', 'case_attribution_missing'])

    def test_grouped_activity_keeps_complementary_coded_rules(self):
        """PURPOSE: Distinguish a family of occurrences from alternate labels for the same rows.
        INPUT: One generic clock, two coded definitions and the requirement's coverage intent.
        OUTPUT: Both coded EDs for the group, independent attribution IDs, and ambiguity for a single request.
        """
        from src.step2_retrieve_and_interpret.verify_activity_requirements import verify_activity
        base = {'source_table':'work','occurrence_time_source':{'columns':['finished_at']},
                'source_row_key':['id'],'occurrence_identity_status':'supported'}
        definitions = {'generic':dict(base, source_kind='column_event', row_selection={'kind':'all_rows'})}
        for code in ('a','b'):
            definitions[code] = dict(base, source_kind='row_activity',
                activity_source={'kind':'value','column':'kind','value':code},
                row_selection={'kind':'equals','column':'kind','value':code})
        catalog = {i:{'eligible':True,'binding_policy':{'checks':{}},
                      'attribution':{'status':'pass','paths':[{'id':'path-'+i}]}} for i in definitions}
        req = {'coverage':'all','qualifiers':[],'granularity':'distinct'}
        review = {'event_definition_ids':list(definitions),'semantic_status':'matched',
                  'source_attribution_gap':False,'reason':'Two documented completion codes.'}
        outcome = verify_activity(req,review,catalog,definitions,definitions)
        self.assertEqual(outcome['status'],'verified')
        self.assertEqual(outcome['definition_path_ids'],{'a':['path-a'],'b':['path-b']})
        coarse = verify_activity(dict(req,granularity='coarse'),review,catalog,definitions,definitions)
        self.assertEqual(coarse['definition_path_ids'],{'generic':['path-generic']})
        single = verify_activity(dict(req,coverage='one'),review,catalog,definitions,definitions)
        self.assertEqual(single['reason_codes'],['ambiguous_candidates'])

    def test_mixed_role_activity_family_validates_union_of_member_roles(self):
        """PURPOSE: Resolve distinct inbound/outbound members of a lifecycle family.
        INPUT: Two verified role paths and a grouped request. OUTPUT: Both roles are required across the set.
        """
        from src.step2_retrieve_and_interpret.verify_activity_requirements import verify_activity
        catalog = {role:{'eligible':True,'binding_policy':{'checks':{}},'attribution':{
            'status':'pass','paths':[{'id':role,'role_validation':{'status':'pass','reference':{'role':role}}}]}}
            for role in ('inbound','outbound')}
        requirement = {'coverage':'all','qualifiers':['inbound','outbound']}
        review = {'event_definition_ids':list(catalog),'semantic_status':'matched',
                  'source_attribution_gap':False,'reason':'Both phases match.'}
        complete = verify_activity(requirement,review,catalog,catalog)
        self.assertEqual(complete['definition_path_ids'],{'inbound':['inbound'],'outbound':['outbound']})
        inbound_only = verify_activity(requirement,dict(review,event_definition_ids=['inbound']),catalog,catalog)
        self.assertEqual(inbound_only['reason_codes'],['activity_family_not_fully_attributable'])

    def test_every_active_role_has_an_external_prompt(self):
        """PURPOSE: Keep role schemas and individual prompt files in sync.
        INPUT: Declared active roles. OUTPUT: All prompts resolve with their example delimiter.
        """
        self.assertEqual(set(SCHEMAS), set(PROMPT_FILES))
        for name in PROMPT_FILES.values():
            self.assertIn('\n<!-- examples -->\n', load_prompt('step2_retrieve_and_interpret', name))


if __name__ == '__main__':
    unittest.main()
