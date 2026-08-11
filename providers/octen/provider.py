"""
providers/octen/provider.py — the Octen provider.

Octen uses Bearer auth (Authorization: Bearer <key>) and a nested request shape
for some params (highlight.enable, full_content.enable, search_options.*).
The call() override flattens the playground's flat params into the nested
structure the API expects.
"""

import json
from providers.base import Provider
from providers.octen.endpoints import ENDPOINTS, ENDPOINT_ORDER


class OctenProvider(Provider):
    id = "octen"
    label = "Octen"
    base_url = "https://api.octen.ai"
    auth_header = "Authorization"
    auth_prefix = "Bearer "
    key_env = "OCTEN_API_KEY"
    endpoint_order = ENDPOINT_ORDER
    endpoints = ENDPOINTS

    def _build_params(self, endpoint_id: str, params: dict) -> dict:
        """
        Flatten playground params into Octen's nested request body.

        Playground sends flat keys like `highlight_enable`, `full_content_enable`,
        `full_content_max_tokens`; the API wants nested objects:
          highlight: { enable: true, max_tokens: 512 }
          full_content: { enable: true, max_tokens: 2048 }

        For /broad-search, search-option keys go under `search_options: { ... }`.
        For /answer, the `messages` string is wrapped into the messages array format.
        For /extract, the `urls` CSV string is split into an array.
        """
        p = dict(params)
        out = {}

        # highlight group
        hl = {}
        if "highlight_enable" in p:
            hl["enable"] = p.pop("highlight_enable")
        if "highlight_max_tokens" in p:
            hl["max_tokens"] = p.pop("highlight_max_tokens")
        if hl:
            p["highlight"] = hl

        # full_content group
        fc = {}
        if "full_content_enable" in p:
            fc["enable"] = p.pop("full_content_enable")
        if "full_content_max_tokens" in p:
            fc["max_tokens"] = p.pop("full_content_max_tokens")
        if fc:
            p["full_content"] = fc

        # /broad-search: wrap search option keys under search_options
        if endpoint_id == "broad-search":
            SEARCH_OPTION_KEYS = {
                "topic", "count", "include_domains", "exclude_domains",
                "include_text", "exclude_text", "time_range", "time_basis",
                "language", "format", "safesearch", "include_images",
                "highlight", "full_content",
            }
            so = {}
            remaining = {}
            for k, v in p.items():
                if k in SEARCH_OPTION_KEYS:
                    so[k] = v
                else:
                    remaining[k] = v
            if so:
                remaining["search_options"] = so
            p = remaining

        # CSV fields → arrays
        for csv_key in ("include_domains", "exclude_domains", "include_text",
                        "exclude_text", "language"):
            if csv_key in p and isinstance(p[csv_key], str):
                p[csv_key] = [s.strip() for s in p[csv_key].split(",") if s.strip()]

        # /extract: urls CSV → array
        if endpoint_id == "extract" and "urls" in p and isinstance(p["urls"], str):
            p["urls"] = [u.strip() for u in p["urls"].split(",") if u.strip()]

        # /answer: messages string → messages array
        if endpoint_id == "answer" and "messages" in p and isinstance(p["messages"], str):
            p["messages"] = [{"role": "user", "content": p["messages"]}]

        return p

    def call(self, endpoint_id: str, params: dict, timeout: int = 60) -> dict:
        built = self._build_params(endpoint_id, params)
        return super().call(endpoint_id, built, timeout=timeout)
