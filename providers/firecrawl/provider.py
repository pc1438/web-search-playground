"""
providers/firecrawl/provider.py — the Firecrawl provider.

Auth: Bearer token (Authorization: Bearer <key>).
The call() override translates the playground's flat `scrapeFormats` CSV param
into the nested scrapeOptions.formats object the API expects.
"""

from providers.base import Provider
from providers.firecrawl.endpoints import ENDPOINTS, ENDPOINT_ORDER


class FirecrawlProvider(Provider):
    id = "firecrawl"
    label = "Firecrawl"
    base_url = "https://api.firecrawl.dev"
    auth_header = "Authorization"
    auth_prefix = "Bearer "
    key_env = "FIRECRAWL_API_KEY"
    key_docs_url = "https://www.firecrawl.dev/app/api-keys"
    endpoint_order = ENDPOINT_ORDER
    endpoints = ENDPOINTS

    def _build_params(self, endpoint_id: str, params: dict) -> dict:
        p = dict(params)

        # scrapeFormats CSV → scrapeOptions: { formats: [...] }
        if "scrapeFormats" in p:
            raw = p.pop("scrapeFormats")
            if isinstance(raw, str):
                formats = [s.strip() for s in raw.split(",") if s.strip()]
            else:
                formats = raw
            if formats:
                p["scrapeOptions"] = {"formats": formats}

        # sources / categories CSV → arrays
        for key in ("sources", "categories", "includeDomains", "excludeDomains"):
            if key in p and isinstance(p[key], str):
                p[key] = [s.strip() for s in p[key].split(",") if s.strip()]

        return p

    def call(self, endpoint_id: str, params: dict, timeout: int = 60,
             request_keys: dict = None) -> dict:
        built = self._build_params(endpoint_id, params)
        return super().call(endpoint_id, built, timeout=timeout, request_keys=request_keys)
