"""
providers/ceramic/provider.py — the Ceramic provider.

Ceramic's search endpoint is a plain JSON POST with an `Authorization: Bearer`
header returning JSON, so the base `call()` handles it — no override needed.
"""

from providers.base import Provider
from providers.ceramic.endpoints import ENDPOINTS, ENDPOINT_ORDER


class CeramicProvider(Provider):
    id = "ceramic"
    label = "Ceramic"
    base_url = "https://api.ceramic.ai"
    auth_header = "Authorization"
    auth_prefix = "Bearer "
    key_env = "CERAMIC_API_KEY"
    endpoint_order = ENDPOINT_ORDER
    endpoints = ENDPOINTS
