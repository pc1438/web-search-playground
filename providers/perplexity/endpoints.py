"""
providers/perplexity/endpoints.py — Perplexity Search + Agent API schemas.

Perplexity's public HTTP surface (verified 2026-07 against docs.perplexity.ai +
live probing): the Search API (POST /search) and the Agent API (POST /v1/agent),
plus Sonar chat/embeddings (not search-shaped, omitted). Notably, "contents",
"people", and "company/finance" are NOT standalone endpoints — they are Agent
*tools* (fetch_url, people_search, finance_search), selectable on the agent below.
"""

from providers.base import Param, Endpoint

CONTEXT_SIZE = ["low", "medium", "high"]
AGENT_TOOLS = "web_search, fetch_url, people_search, finance_search"

SEARCH = Endpoint(
    "search", "POST /search — ranked web results (Search API)", "/search",
    compare_query_field="query", docs_url="https://docs.perplexity.ai/api-reference/search-post", params=[
        Param("query", "csv", required=True, placeholder="best vector databases 2026",
              help="One search term, or 2–5 comma-separated queries (multi-query bundling)."),
        Param("max_results", "int", min=1, max=20, placeholder="10", help="1–20 results."),
        Param("search_context_size", "enum", values=CONTEXT_SIZE, help="Retrieval depth (default high)."),
        Param("search_domain_filter", "csv", placeholder="github.com, -reddit.com",
              help="Up to 20 domains; prefix a domain with '-' to exclude it."),
        Param("max_tokens", "int", advanced=True, help="Overall token cap for returned content (up to 1,000,000)."),
        Param("max_tokens_per_page", "int", advanced=True, help="Per-result content token limit."),
        Param("country", "string", advanced=True, placeholder="US", maxlen=2, help="ISO 3166-1 alpha-2 country code."),
        Param("search_language_filter", "csv", advanced=True, placeholder="en, fr",
              help="ISO 639-1 language codes; max 10."),
    ])

AGENT = Endpoint(
    "agent", "POST /v1/agent — Claude runs inside Perplexity (BYOLLM)", "/v1/agent",
    compare_query_field="input", compare_params=["tools"],
    docs_url="https://docs.perplexity.ai/api-reference/agent-post", params=[
        Param("input", "text", required=True, placeholder="e.g. what happened in tech news today?",
              help="The question. Claude uses the selected tools and synthesizes an answer."),
        Param("model", "string", placeholder="anthropic/claude-sonnet-4-6",
              help="BYOLLM model (defaults to claude-sonnet-4-6)."),
        Param("tools", "csv", placeholder=AGENT_TOOLS,
              values=["web_search", "fetch_url", "people_search", "finance_search"],
              help="Tools Claude may use: web_search, fetch_url (page contents), people_search (people), "
                   "finance_search (company/finance). Comma-separated; defaults to web_search + fetch_url."),
    ])

ENDPOINTS = {ep.id: ep for ep in (SEARCH, AGENT)}
ENDPOINT_ORDER = ["search", "agent"]
