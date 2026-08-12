"""
providers/youdotcom/provider.py — the You.com provider.

Every You.com endpoint is a plain JSON POST/GET with an `X-API-Key` header, so
the base `call()` handles them all. The one override here translates the flat
`extraction_preset` compare-shim param into the nested extraction object the
API actually expects.
"""

from providers.base import Provider
from providers.youdotcom.endpoints import ENDPOINTS, ENDPOINT_ORDER


class YouDotComProvider(Provider):
    id = "youdotcom"
    label = "You.com"
    base_url = "https://api.you.com"
    auth_header = "X-API-Key"
    key_env = "YDC_API_KEY"
    endpoint_order = ENDPOINT_ORDER
    endpoints = ENDPOINTS

    def call(self, endpoint_id: str, params: dict, timeout: int = 120) -> dict:
        if endpoint_id == "search" and "extraction_preset" in params:
            params = dict(params)
            preset = params.pop("extraction_preset", "")
            if preset and preset != "(none)":
                params["extraction"] = {"extraction_mode": preset}
        return super().call(endpoint_id, params, timeout)
