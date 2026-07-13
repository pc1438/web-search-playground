"""
providers/serpapi/provider.py — the SerpApi provider.

A single GET `/search` endpoint. Auth is a `?api_key=` query param, so the
provider sets `auth_query_param` (no auth header) — the base `call()` injects the
key into the query string at request time and never echoes it in the response
wrapper. No override needed.
"""

from providers.base import Provider
from providers.serpapi.endpoints import ENDPOINTS, ENDPOINT_ORDER

# Most SerpApi engines take the query in `q`, but a few use a different param.
# The playground uses a single `q` field; we remap it per engine at call time.
_QUERY_PARAM = {"yandex": "text", "yahoo": "p", "youtube": "search_query"}


class SerpApiProvider(Provider):
    id = "serpapi"
    label = "SerpApi"
    base_url = "https://serpapi.com"
    auth_query_param = "api_key"   # key goes in the query string, not a header
    key_env = "SERPAPI_API_KEY"
    endpoint_order = ENDPOINT_ORDER
    endpoints = ENDPOINTS

    def call(self, endpoint_id: str, params: dict, timeout: int = 60) -> dict:
        # Rename the query field to the selected engine's expected param (e.g.
        # yandex → text). Everything else is a standard GET (base call()).
        params = dict(params)
        qp = _QUERY_PARAM.get(params.get("engine"))
        if qp and "q" in params:
            params[qp] = params.pop("q")
        return super().call(endpoint_id, params, timeout)
