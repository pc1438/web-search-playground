"""
providers/registry.py — the one place that knows which providers exist.

To add a provider: create `providers/<name>/` with a `Provider` subclass, then
register it here. `server.py` and the frontend both go through this registry, so
that single edit surfaces the new provider everywhere (its tab, endpoints, and
request forms) with no other wiring.
"""

from providers.exa import ExaProvider
from providers.youdotcom import YouDotComProvider
from providers.perplexity import PerplexityProvider
from providers.parallel import ParallelProvider
from providers.tavily import TavilyProvider
from providers.brave import BraveProvider
from providers.serpapi import SerpApiProvider

# Instantiate each provider once. Tabs are alpha-sorted in the UI, so this order
# only affects the catalog's providerOrder (used where an explicit order matters).
_INSTANCES = [
    ExaProvider(),
    YouDotComProvider(),
    PerplexityProvider(),
    ParallelProvider(),
    TavilyProvider(),
    BraveProvider(),
    SerpApiProvider(),
]

_PROVIDERS = {p.id: p for p in _INSTANCES}
_ORDER = [p.id for p in _INSTANCES]


def get(provider_id: str):
    """Return the Provider instance, or None if unknown."""
    return _PROVIDERS.get(provider_id)


def catalog() -> dict:
    """Full serialized catalog the frontend renders from."""
    return {
        "providerOrder": _ORDER,
        "providers": {pid: _PROVIDERS[pid].catalog() for pid in _ORDER},
    }
