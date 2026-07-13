"""
providers/serpapi/provider.py — the SerpApi provider.

A single GET `/search` endpoint. Auth is a `?api_key=` query param, so the
provider sets `auth_query_param` (no auth header) — the base `call()` injects the
key into the query string at request time and never echoes it in the response
wrapper. No override needed.
"""

from providers.base import Provider
from providers.serpapi.endpoints import ENDPOINTS, ENDPOINT_ORDER


class SerpApiProvider(Provider):
    id = "serpapi"
    label = "SerpApi"
    base_url = "https://serpapi.com"
    auth_query_param = "api_key"   # key goes in the query string, not a header
    key_env = "SERPAPI_API_KEY"
    endpoint_order = ENDPOINT_ORDER
    endpoints = ENDPOINTS
