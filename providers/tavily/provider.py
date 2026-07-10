"""
providers/tavily/provider.py — the Tavily provider.

Every Tavily endpoint is a plain JSON POST with an `Authorization: Bearer` header
returning JSON, so the base `call()` handles them all — no override needed.
"""

from providers.base import Provider
from providers.tavily.endpoints import ENDPOINTS, ENDPOINT_ORDER


class TavilyProvider(Provider):
    id = "tavily"
    label = "Tavily"
    base_url = "https://api.tavily.com"
    auth_header = "Authorization"
    auth_prefix = "Bearer "
    key_env = "TAVILY_API_KEY"
    endpoint_order = ENDPOINT_ORDER
    endpoints = ENDPOINTS
