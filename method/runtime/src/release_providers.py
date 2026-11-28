"""Reuse the measured provider clients and guarded receipt accounting."""

from contextlib import ExitStack, closing, contextmanager
from decimal import Decimal
import os

from cross_model_evaluation.providers import SETTINGS, GeminiSpendGuard, gemini_client, haiku_guard
from src.common.claude_client import ClaudeChatClient


@contextmanager
def release_clients(output, *, models, maximum, gemini_billing='paid_cap_permitted'):
    """PURPOSE: Open only the required native clients with an explicit shared USD limit.
    INPUT: Ledger directory, registered model IDs, monetary cap and Gemini billing mode.
    OUTPUT: Model-to-client and model-to-guard maps, with deterministic cleanup.
    """
    caps = Decimal(str(maximum))
    if not caps.is_finite() or caps <= 0:
        raise ValueError('A finite positive USD cap is required')
    haiku, gemini = (SETTINGS[name]['id'] for name in ('haiku', 'gemini'))
    if set(models) - {haiku, gemini}:
        raise ValueError('Use a registered release provider')
    paths = {haiku: output/'claude.json', gemini: output/'gemini.json'}
    guards = {haiku: haiku_guard(paths[haiku], paths[gemini], caps),
              gemini: GeminiSpendGuard(paths[gemini], caps, paths[haiku], gemini_billing)}
    with ExitStack() as stack:
        clients = {}
        if haiku in models:
            clients[haiku] = stack.enter_context(closing(ClaudeChatClient(
                os.environ['ANTHROPIC_API_KEY'], effort='medium', transport=guards[haiku], max_requests=400)))
        if gemini in models:
            clients[gemini] = stack.enter_context(closing(gemini_client(
                os.environ['GEMINI_API_KEY'], guards[gemini])))
        yield clients, guards


def check_limit(guards, clients):
    """PURPOSE: Stop before starting another condition after the shared cost guard blocks.
    INPUT: Active guards and native clients. OUTPUT: None, or an exception retaining the receipt ledger.
    """
    states = [*guards.values(), *clients.values()]
    failure = next((state.blocked for state in states if getattr(state, 'blocked', None)), None)
    if failure:
        raise RuntimeError(failure)
