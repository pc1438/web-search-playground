"""
providers/youdotcom/provider.py — the You.com provider.

Every You.com endpoint (Search, Contents, Research, Finance Research) is a plain
JSON POST with an `X-API-Key` header returning JSON, so the base `call()` handles
them all — no override needed. Search/Contents live on a different host, which the
endpoints set via `Endpoint.base_url`.
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
