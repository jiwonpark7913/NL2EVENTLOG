"""Report request usage and retrieval work without changing extraction behavior."""

from pathlib import Path
from math import isfinite


def process_io():
    """PURPOSE: Capture Linux process I/O for offline measurement.
    INPUT: Current process counters, if provided by the operating system.
    OUTPUT: Byte counters or an empty result when unavailable.
    """
    try:
        fields = dict(line.split(': ', 1) for line in Path('/proc/self/io').read_text().splitlines())
        return {key: int(fields[key]) for key in ('rchar', 'read_bytes')}
    except (OSError, KeyError, ValueError):
        return {}


def summarize_usage(requests, rates=None):
    """PURPOSE: Aggregate actual provider calls, including retries and non-PI stages.
    INPUT: MeteredClient request records (no credentials or prompt text).
    OUTPUT: Input peak and total, output and cached token totals, and completion/failure counts.
    """
    inputs = [r.get('input_tokens', 0) for r in requests]
    cost = None
    if rates is not None and all(r.get('input_tokens') and r.get('model') in rates for r in requests):
        total = 0.0
        for request in requests:
            price = rates[request['model']]
            cached = request.get('cached_input_tokens', 0)
            values = [price['input'], price['output'], price.get('cached_input', price['input'])]
            if any(not isfinite(item) or item < 0 for item in values):
                raise ValueError('token rates must be finite, nonnegative USD per million tokens')
            total += ((request['input_tokens'] - cached) * values[0]
                      + request.get('output_tokens', 0) * values[1] + cached * values[2])
        cost = total / 1_000_000
    return {
        'estimated_provider_cost_usd': cost,
        'calls': len(requests), 'completed_calls': sum(r['status'] == 'completed' for r in requests),
        'failed_calls': sum(r['status'] == 'failed' for r in requests),
        'maximum_input_tokens': max(inputs, default=0), 'cumulative_input_tokens': sum(inputs),
        'cumulative_cached_input_tokens': sum(r.get('cached_input_tokens', 0) for r in requests),
        'cumulative_output_tokens': sum(r.get('output_tokens', 0) for r in requests),
        'usage_incomplete': any(not r.get('input_tokens') for r in requests),
    }
