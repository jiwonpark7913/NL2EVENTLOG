"""Measure indexed PI against the full-card control using independently generated public SQLite."""

from collections import Counter
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
import tracemalloc
from types import SimpleNamespace

import tiktoken

from src.eeg.eeg_store import EEGStore, write_index
from src.common.graph_identifiers import event_definition_id, path_id
from src.pipeline import run_pipeline
from src.step1_understand.pipeline import build_evidence_graph
from src.step1_understand.eeg_configuration import DbuConfig
from src.step1_understand.project_runtime_evidence_graph import to_runtime_graph

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
from test_pipeline_runtime import ScriptedClient  # noqa: E402
from test_v2_index_and_recovery import event_contract  # noqa: E402
from validation.knowledge_accounting import knowledge_counts


class TokenCountingClient(ScriptedClient):
    """Offline reply double with local estimates for complete provider inputs."""

    def create(self, **kwargs):
        """PURPOSE: Count actual serialized role inputs without a remote provider.
        INPUT: Normal role messages and JSON schema. OUTPUT: Scripted response with locally estimated usage.
        """
        role = kwargs['response_format']['json_schema']['name']
        if role == 'pi_unified':
            self.calls.append(kwargs)
            wrapped = kwargs['messages'][1]['content']
            payload = json.loads(wrapped.split('\n', 1)[1].rsplit('\n', 1)[0])
            from test_v2_final_architecture import unified_reply
            response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                content=json.dumps(unified_reply(payload)), refusal=None), finish_reason='stop')])
        elif role == 'pi_cases':
            self.calls.append(kwargs)
            wrapped = kwargs['messages'][1]['content']
            payload = json.loads(wrapped.split('\n', 1)[1].rsplit('\n', 1)[0])
            case = next(e for e in payload['entity_types'] if e['name'].casefold() == 'order')
            mode = 'explicit' if 'Approved' in payload['original_request'] else 'implicit'
            reply = {'candidates': [{'et': case['id'], 'mode': mode, 'focus': ''}]}
            response = SimpleNamespace(choices=[SimpleNamespace(
                message=SimpleNamespace(content=json.dumps(reply), refusal=None), finish_reason='stop')])
        else:
            response = super().create(**kwargs)
        encoding = tiktoken.get_encoding('o200k_base')
        text = ''.join(message['content'] for message in kwargs['messages'])
        text += json.dumps(kwargs['response_format']['json_schema']['schema'], ensure_ascii=False)
        input_tokens = len(encoding.encode(text)) + 4 * len(kwargs['messages'])
        output_tokens = len(encoding.encode(response.choices[0].message.content))
        response.usage = SimpleNamespace(prompt_tokens=input_tokens, completion_tokens=output_tokens,
                                         total_tokens=input_tokens + output_tokens)
        return response


def create_fixture(path, unrelated, related):
    """PURPOSE: Vary irrelevant schema and genuine activity scope independently.
    INPUT: Local temporary directory, counts of unrelated tables and related occurrence clocks.
    OUTPUT: Synthetic SQLite, public DD, and expected count for the requested activity.
    """
    database = path / 'source.sqlite'
    dictionary = {'name': 'Synthetic public benchmark', 'timezone': 'UTC', 'tables': []}
    with closing(sqlite3.connect(database)) as conn, conn:
        extra = [f'milestone_{n}_at' for n in range(related)]
        conn.execute('CREATE TABLE orders (id INTEGER PRIMARY KEY, approved_at TEXT' +
                     ''.join(f', {clock} TEXT' for clock in extra) + ')')
        rows = [(i, f'2025-02-0{i}T00:00:00Z', *[f'2025-02-0{i}T01:00:00Z' for _ in extra])
                for i in (1, 2)]
        conn.executemany('INSERT INTO orders VALUES (' + ','.join('?' for _ in rows[0]) + ')', rows)
        dictionary['tables'].append({'table': 'orders', 'readable_name': 'Order',
            'definition': 'One order business entity.',
            'columns': [{'name': 'id', 'type': 'INTEGER', 'definition': 'Order identifier.'},
                        {'name': 'approved_at', 'type': 'TEXT', 'event_activity': 'Approved',
                         'definition': 'Actual Approved occurrence time.'},
                        *[{'name': clock, 'type': 'TEXT', 'event_activity': f'Order milestone {n}',
                           'definition': f'Actual time of order milestone {n}.'} for n, clock in enumerate(extra)]]})
        for n in range(unrelated):
            table = f'archive_{n}'
            conn.execute(f'CREATE TABLE {table} (id INTEGER PRIMARY KEY, archived_at TEXT)')
            conn.execute(f'INSERT INTO {table} VALUES (?,?)', (1, '2025-03-01T00:00:00Z'))
            dictionary['tables'].append({'table': table, 'readable_name': f'Archive {n}',
                'definition': f'One independent archive {n} entity.',
                'columns': [{'name': 'id', 'type': 'INTEGER', 'definition': 'Archive identifier.'},
                            {'name': 'archived_at', 'type': 'TEXT', 'event_activity': f'Archive {n} recorded',
                             'definition': f'Actual time of archive {n} registration.'}]})
    path_dd = path / 'dictionary.json'
    path_dd.write_text(json.dumps(dictionary))
    return database, path_dd, dictionary



def request_scores(result, expected, required_ed, required_paths):
    """PURPOSE: Score delivered knowledge and extracted rows against synthetic fixture facts.
    INPUT: One retrieval arm and independent source keys, clock columns and dependency IDs.
    OUTPUT: Recall, completeness, exact match, event F1 and diagnostics.
    """
    delivered = result['graph']
    ids = {event['id'] for event in delivered['event_definitions']}
    rules = {rule['id'] for rule in delivered['attribution_paths']}
    extracted = Counter(
        (str(json.loads(row['case_id'])[2][0][1]), str(json.loads(row['source_record_id'])[0]),
         row['timestamp_raw_column'], row['timestamp'])
        for row in result['execution'].get('event_log', []))
    reference = Counter(expected)
    measurements = result['manifest']['measurements']
    budget = os.environ.get('NL2EL_EVAL_INPUT_TOKEN_LIMIT')
    fits = budget is None or measurements['provider_usage']['maximum_input_tokens'] <= int(budget)
    return {
        'ed_recall': len(ids & required_ed) / len(required_ed),
        'attribution_recall': len(rules & required_paths) / len(required_paths),
        'knowledge_complete': required_ed <= ids and required_paths <= rules,
        'exact': extracted == reference if fits else None,
        'event_f1': 2 * sum((reference & extracted).values()) / (sum(reference.values()) + sum(extracted.values())) if fits else None,
        'status': result['es']['status'] if fits else 'context_limit_exceeded',
        'measurements': measurements,
    }

def measure(unrelated, related):
    """PURPOSE: Compare fixed-policy full and indexed delivery without model API calls.
    INPUT: Controlled fixture workload counts. OUTPUT: Artifact with scope and execution checks and measurements.
    """
    with TemporaryDirectory(prefix='nl2eventlog-v2-public-') as directory:
        path = Path(directory)
        database, path_dd, dd = create_fixture(path, unrelated, related)
        config = DbuConfig(repair=False, semantic_signatures=False, global_ot_review=False,
                           pairwise_identity_llm=False)
        started = perf_counter()
        graph = to_runtime_graph(build_evidence_graph(database, path_dd, config, llm=TokenCountingClient()), database)
        build_seconds = perf_counter() - started
        index_path = path / 'index.sqlite'
        built = write_index(index_path, graph, 'benchmark')
        index = EEGStore(index_path, 'benchmark', {'index': built})
        question = 'Extract Approved for each order.'
        full = run_pipeline(database, dd, question, graph=graph, client=TokenCountingClient(),
                            config=config, evidence_retrieval=False, recovery_enabled=False)
        start = perf_counter()
        indexed = run_pipeline(database, dd, question, graph=index, client=TokenCountingClient(),
                               config=config, evidence_retrieval=False, recovery_enabled=False)
        first = perf_counter() - start
        unified = run_pipeline(database, dd, question, graph=index, client=TokenCountingClient(),
                               config=config, evidence_retrieval=False, recovery_enabled=False,
                               pi_mode='unified')
        assert event_contract(unified) == event_contract(indexed) and unified['es']['status'] == 'accepted'
        warm = []
        for _ in range(3):
            with index.open(database) as lookup:
                start = perf_counter()
                lookup.request_graph(question)
                warm.append(perf_counter() - start)
        tracemalloc.start()
        try:
            with index.open(database) as lookup:
                lookup.request_graph(question)
            _, peak_lookup_bytes = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        assert full['es']['status'] == indexed['es']['status'] == 'accepted', (
            full['es']['status'], indexed['es']['status'], full['query']['status'], indexed['query']['status'])
        assert event_contract(full) == event_contract(indexed) and len(event_contract(full)) == 2
        rows = indexed['execution']['event_log']
        observed = sorted((str(json.loads(r['source_record_id'])[0]), r['timestamp_raw_column']) for r in rows)
        assert observed == [('1', 'approved_at'), ('2', 'approved_at')], observed
        assert full['execution']['sql'] == indexed['execution']['sql']
        semantic = run_pipeline(database, dd, question, graph=index, client=TokenCountingClient(),
                                config=config, evidence_retrieval=False, recovery_enabled=False,
                                retrieval_mode='semantic', semantic_top_k=3)
        case = next(e['id'] for e in graph['entity_types'] if e['name'] == 'Order')
        approved = event_definition_id('orders', {'kind': 'column'}, 'TS:orders.approved_at')
        approved_rows = [(str(i), str(i), 'approved_at', f'2025-02-0{i}T00:00:00Z') for i in (1, 2)]
        arms = {mode: request_scores(result, approved_rows, {approved}, {path_id(approved, case, ['O:orders'])})
                for mode, result in (('full', full), ('semantic', semantic), ('graph', indexed))}
        fact = {'kind': 'column_event', 'source': {'table': 'orders', 'timestamp_unit_id': 'TS:orders.approved_at'},
                'case': case}
        knowledge = knowledge_counts([fact], graph['candidate_ledger'], graph, indexed['graph'],
                                     indexed['query']['process_information'])
        assert not knowledge['first_losses'], knowledge
        assert not graph['candidate_ledger']['audit']['missing_decisions']
        assert not graph['candidate_ledger']['audit']['missing_projections']
        history_request = 'Extract history for each order.'
        history_graph = {}
        for mode, snapshot in (('full', graph), ('semantic', index), ('graph', index)):
            history_graph[mode] = run_pipeline(database, dd, history_request, graph=snapshot,
                client=TokenCountingClient(), config=config, evidence_retrieval=False,
                recovery_enabled=False, retrieval_mode=mode, semantic_top_k=3)
        history = history_graph['graph']
        assert history['es']['status'] == 'accepted'
        events = history['execution']['event_log']
        clocks = {'approved_at', *(f'milestone_{n}_at' for n in range(related))}
        assert len(events) == 2 * len(clocks)
        assert not any('Archive' in event['activity'] for event in events)
        required_history = {event_definition_id('orders', {'kind': 'column'}, f'TS:orders.{clock}')
                            for clock in clocks}
        expected_history = [*approved_rows,
            *((str(i), str(i), f'milestone_{n}_at', f'2025-02-0{i}T01:00:00Z')
              for n in range(related) for i in (1, 2))]
        history_arms = {mode: request_scores(result, expected_history, required_history,
            {path_id(ed, case, ['O:orders']) for ed in required_history})
                        for mode, result in history_graph.items()}
        return {
            'unrelated_tables': unrelated, 'related_clocks': related,
            'canonical_eeg_json_bytes': len(json.dumps(graph, ensure_ascii=False, separators=(',', ':')).encode()),
            'native_build_seconds': build_seconds, 'index': built,
            'global_ed_count': len(graph['event_definitions']),
            'ledger': graph['candidate_ledger']['audit'],
            'reference_knowledge': knowledge,
            'fixture_extraction': {'expected': 2, 'extracted': len(rows), 'exact': True, 'f1': 1.0},
            'retrieval_arms': arms, 'history_retrieval_arms': history_arms,
            'source_coverage': graph['source_coverage'],
            'parser_ablation': {
                mode: {'status': result['es']['status'], 'exact': event_contract(result) == event_contract(indexed),
                       'measurements': result['manifest']['measurements'],
                       'semantic_graph_counts': result['manifest']['step2']['semantic_graph_counts'],
                       'executable_graph_counts': result['manifest']['step3']['executable_graph_counts'],
                       'execution_fidelity': result['execution'].get('sql') == indexed['execution'].get('sql')}
                for mode, result in (('sequential', indexed), ('unified', unified))},
            'full': full['manifest']['measurements'],
            'indexed': indexed['manifest']['measurements'],
            'indexed_first_wall_seconds': first,
            'warm_retrieval_seconds': sorted(warm)[1],
            'peak_lookup_python_bytes': peak_lookup_bytes,
            'execution_equivalent': True,
            'history': {'event_rows': len(events), 'selected_ed_count': 1 + related,
                        'measurements': history['manifest']['measurements']},
        }


def measure_recovery():
    """PURPOSE: Measure native and recovered outcomes with independent source evidence.
    INPUT: Synthetic public order fixture, intact and with its required ED removed.
    OUTPUT: Recovery trigger/success rates and additional estimated tokens and time.
    """
    with TemporaryDirectory(prefix='nl2eventlog-v2-recovery-') as directory:
        path = Path(directory)
        database, path_dd, dd = create_fixture(path, 0, 0)
        config = DbuConfig(repair=False, semantic_signatures=False, global_ot_review=False, pairwise_identity_llm=False)
        native = build_evidence_graph(database, path_dd, config, llm=TokenCountingClient())
        graph = to_runtime_graph(native, database)
        broken = dict(graph, event_definitions=[], attribution_paths=[], event_families=[],
                      event_definition_pair_relationships=[], unresolved_event_evidence={'pairs': []})
        results = []
        for name, snapshot in (('native', graph), ('required_rule_absent', broken)):
            location = path / (name + '.sqlite')
            write_index(location, snapshot, name)
            results.append(run_pipeline(database, dd, 'Extract Approved for each order.', client=TokenCountingClient(),
                graph=EEGStore(location, name), config=config, evidence_retrieval=False))
        assert results[1]['es']['status'] == 'accepted', (results[1]['manifest']['recovery'], results[1]['query']['status'])
        assert event_contract(results[0]) == event_contract(results[1])
        outcomes = [result['manifest']['recovery'] for result in results]
        triggers = sum(r['triggered'] for r in outcomes)
        return {
            'native_resolution_rate': sum(r['native_resolved'] for r in outcomes) / len(outcomes),
            'recovery_trigger_rate': triggers / len(outcomes),
            'recovery_success_rate': sum(r['succeeded'] for r in outcomes) / triggers,
            'completion_rate': sum(r['es']['status'] == 'accepted' for r in results) / len(results),
            'records': outcomes,
            'basis': 'one intact and one deliberately incomplete fixture; rates are not dataset estimates',
        }


def main():
    """PURPOSE: Write repeatable controlled measurements and method-integrity checks.
    INPUT: Optional path for the JSON result. OUTPUT: Aggregate printed report and optional artifact.
    """
    os.environ.setdefault('NL2EL_SEMANTIC_MODEL', 'off')
    results = {'basis': 'offline local token estimate with scripted selection; no provider calls',
               'network_calls': 0, 'external_cost_usd': 0, 'input_token_limit': os.environ.get('NL2EL_EVAL_INPUT_TOKEN_LIMIT'),
               'recovery': measure_recovery(),
               'cold_meaning': 'first lookup on a newly written index; OS page cache not flushed',
               'comparisons': [measure(count, 0) for count in (0, 8, 32)] +
                              [measure(8, clocks) for clocks in (2, 6)]}
    payload = json.dumps(results, indent=2) + '\n'
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(payload)
    print(payload)


if __name__ == '__main__':
    main()
