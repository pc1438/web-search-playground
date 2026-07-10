"""
providers/exa/provider.py — the Exa provider.

Exa fits the base contract exactly: a plain JSON POST with an `x-api-key` header,
so there's no `call()` override — every endpoint (including Compare) runs through
the base `call()`.
"""

from providers.base import Provider
from providers.exa.endpoints import ENDPOINTS, ENDPOINT_ORDER


class ExaProvider(Provider):
    id = "exa"
    label = "Exa"
    base_url = "https://api.exa.ai"
    auth_header = "x-api-key"
    key_env = "EXA_API_KEY"
    endpoint_order = ENDPOINT_ORDER
    endpoints = ENDPOINTS
