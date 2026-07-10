"""
providers/brave/provider.py — the Brave Search provider.

Brave endpoints are GET requests with query-string params and an
`X-Subscription-Token` header. The base `call()` already sends GET params as a
query string, so the only override is `headers()` to add the required
`Accept: application/json` (Brave defaults to a different representation without it).
"""

from providers.base import Provider
from providers.brave.endpoints import ENDPOINTS, ENDPOINT_ORDER


class BraveProvider(Provider):
    id = "brave"
    label = "Brave"
    base_url = "https://api.search.brave.com/res/v1"
    auth_header = "X-Subscription-Token"
    key_env = "BRAVE_API_KEY"
    endpoint_order = ENDPOINT_ORDER
    endpoints = ENDPOINTS

    def headers(self) -> dict:
        return {**super().headers(), "Accept": "application/json"}
