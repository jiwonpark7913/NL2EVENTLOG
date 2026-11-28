"""Public baseline wiring using the frozen Direct SQL contract."""

from contextlib import closing
from importlib.util import module_from_spec, spec_from_file_location
import json
import re
import sqlite3
from time import monotonic

from httpx import HTTPStatusError, TransportError
from openai import APIConnectionError, APIStatusError

from pathlib import Path

from evaluation_harness.contract import digest, read
from src.common.database_io import connect_readonly
from src.common.runtime_input_contract import require_no_oracle_payload, require_public_path, sanitize_dictionary

DIRECT_SOURCE = Path(__file__).with_name('direct_sql_protocol.py')
DIRECT_SOURCE_SHA256 = 'da93fb782ea960e2ece81cbaf31cbe879aace3e646604807d07a712e81797774'
# Direct SQL's seven-column contract is the original scorer boundary, separate from the S0 compiler output.
DIRECT_COLUMNS = frozenset(('case_id', 'activity', 'timestamp', 'source_table', 'source_record_id',
                            'source_timestamp_column', 'occurrence_key'))


def direct_tools():
    """PURPOSE: Load the pinned reusable Direct SQL prompt, schema, snapshot and row checks.
    INPUT: Unmodified companion source. OUTPUT: Direct SQL implementation without loading its scorer.
    """
    source = DIRECT_SOURCE
    if digest(source) != DIRECT_SOURCE_SHA256:
        raise ValueError('The pinned Direct SQL implementation has changed')
    spec = spec_from_file_location('final_direct_sql', source)
    tools = module_from_spec(spec)
    spec.loader.exec_module(tools)
    return tools


def direct_context(database, dictionary, tools):
    """PURPOSE: Prepare identical public base evidence for model SQL comparison arms.
    INPUT: Public DB/DD and frozen snapshot helper. OUTPUT: DDL, three sampled rows per table and sanitized DD.
    """
    safe, _ = sanitize_dictionary(read(require_public_path(dictionary)))
    return {'database': tools.database_snapshot(require_public_path(database), 3), 'data_dictionary': safe}


def direct_result(database, question, context, client, model, tools):
    """PURPOSE: Run one Direct SQL attempt under the pinned public prompt and output contract.
    INPUT: Public context, original request, SQLite snapshot and native/replay client.
    OUTPUT: Raw answer, accepted rows, or actionable provider/contract/execution failure.
    """
    require_no_oracle_payload(context)
    messages = [{'role': 'system', 'content': tools.SYSTEM},
                {'role': 'user', 'content': json.dumps({'question': question, 'runtime_evidence': context},
                                                        ensure_ascii=False, separators=(',', ':'))}]
    result = {'rows': [], 'sql': None, 'attempts': []}
    try:
        answer = tools.call_direct_sql(client, messages, model)
        status = answer['status']
        sql = answer['sql']
        reason = answer['reason']
    except (APIConnectionError, APIStatusError, HTTPStatusError, TransportError, RuntimeError) as error:
        return {**result, 'status': 'provider_error', 'reason': type(error).__name__}
    except (ValueError, TypeError, KeyError) as error:
        return {**result, 'status': 'failed', 'failure_kind': 'output_contract_error', 'reason': type(error).__name__}
    attempt = {'answer': answer, 'shared_response': False}
    result['attempts'].append(attempt)
    if status == 'unsupported':
        return {**result, 'status': 'unsupported', 'reason': reason}
    result['sql'] = sql
    rows = []
    stage = 'execution_error'
    try:
        deadline = monotonic() + 120
        if not isinstance(sql, str) or not re.match(r'\s*(SELECT|WITH)\b', sql, re.I):
            raise ValueError('Direct output must be one read-only SELECT/WITH statement')
        with closing(connect_readonly(database)) as connection:
            connection.execute('PRAGMA query_only=ON')
            connection.row_factory = sqlite3.Row
            connection.set_progress_handler(lambda: int(monotonic() > deadline), 10000)
            cursor = connection.execute(sql)
            names = [field[0] for field in cursor.description or ()]
            rows = [dict(row) for row in cursor]
        stage = 'output_contract_error'
        if not DIRECT_COLUMNS <= set(names) or len(names) != len(set(names)):
            raise ValueError('Direct SQL output is missing required columns or repeats projection aliases')
        if rows:
            tools.validate_occurrence_output_rows(rows)
    except (sqlite3.Error, ValueError, TypeError, TimeoutError, RuntimeError) as error:
        attempt.update(failure_kind=stage, message=str(error)[:1000], raw_rows=rows)
        return {**result, 'status': 'failed', 'reason': str(error)[:1000], 'failure_kind': stage, 'rows': rows}
    attempt.update(status='accepted', row_count=len(rows))
    return {**result, 'status': 'accepted', 'reason': reason, 'rows': rows}
