"""
providers/perplexity/provider.py — the Perplexity provider.

Bearer auth (auth_prefix) on api.perplexity.ai. The Search API (/search) is a
plain JSON POST → handled by the base `call()`. The Agent API (/v1/agent) is an
SSE stream with required tool/instruction fields → routed through the proven
`run_perplexity_agent` runner in `comparison/`.
"""

import time

from providers.base import Provider
from providers.perplexity.endpoints import ENDPOINTS, ENDPOINT_ORDER
from comparison.perplexity_runner import run_perplexity_agent


class PerplexityProvider(Provider):
    id = "perplexity"
    label = "Perplexity"
    base_url = "https://api.perplexity.ai"
    auth_header = "Authorization"
    auth_prefix = "Bearer "
    key_env = "PERPLEXITY_API_KEY"
    key_docs_url = "https://www.perplexity.ai/settings/api"
    endpoint_order = ENDPOINT_ORDER
    endpoints = ENDPOINTS

    def call(self, endpoint_id: str, params: dict, timeout: int = 120,
             request_keys: dict = None) -> dict:
        # Search API (and any future plain-JSON endpoint) → base POST.
        if endpoint_id != "agent":
            return super().call(endpoint_id, params, timeout, request_keys=request_keys)
        # Agent API needs tools + instructions + streaming → delegate to the runner.
        question = params.get("input") or params.get("query") or ""
        tools = params.get("tools")
        if isinstance(tools, str):   # fan-out compare mode sends a single tool name
            tools = [tools]
        t0 = time.perf_counter()
        stats = run_perplexity_agent(question, self.api_key(request_keys), tools=tools, model=params.get("model"), timeout=timeout)
        return {
            "ok": True,
            "status": 200,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000),
            "url": self.base_url + "/v1/agent",
            "request": params,
            "body": stats,
        }
