"""
providers/firecrawl/endpoints.py — Firecrawl API endpoint schemas.

Coverage: /v2/search (search + optional per-result scrape)

Response shape:
  { success, data: { web: [...], news: [...], images: [...] }, warning, id, creditsUsed }
Each result: title, description, url, markdown (if scrapeOptions requested), metadata

Firecrawl's differentiator: scrapeOptions lets you pull full-page markdown or a
summary in the same call, making it the most LLM-ready search API in the set.
"""

from providers.base import Param, Endpoint

SOURCES    = ["web", "news", "images"]
CATEGORIES = ["github", "research", "pdf"]
FORMATS    = ["markdown", "summary", "html"]

SEARCH = Endpoint(
    "search", "POST /v2/search — web search + optional full-page scrape", "/v2/search",
    compare_query_field="query",
    docs_url="https://docs.firecrawl.dev/api-reference/endpoint/search",
    params=[
        Param("query", "text", required=True, placeholder="e.g. best open-source LLMs 2026",
              help="Search query, max 500 characters."),
        Param("limit", "int", min=1, max=100, placeholder="10",
              help="Number of results to return (1–100, default 10)."),
        Param("sources", "csv", placeholder="web",
              help="Sources to search: web, news, images (default: web)."),
        Param("categories", "csv", advanced=True, placeholder="github, research",
              help="Filter results by category: github, research, pdf."),
        Param("includeDomains", "csv", advanced=True, placeholder="nytimes.com, bbc.com",
              help="Restrict results to these domains only."),
        Param("excludeDomains", "csv", advanced=True, placeholder="reddit.com",
              help="Exclude results from these domains."),
        Param("country", "string", maxlen=2, placeholder="US", advanced=True,
              help="ISO 3166-1 alpha-2 country code for geo-targeting (default US)."),
        Param("tbs", "string", advanced=True, placeholder="qdr:w",
              help="Time-based filter: qdr:h (hour), qdr:d (day), qdr:w (week), qdr:m (month), qdr:y (year)."),
        Param("safe", "bool", advanced=True,
              help="Enable SafeSearch content filtering."),
        Param("highlights", "bool", advanced=True,
              help="Improves description quality with query-relevant highlights. No separate field is returned — the effect appears in the description text only."),
        Param("scrapeFormats", "csv", advanced=True, placeholder="markdown, summary",
              help="Return full-page content per result. Options: markdown, summary, html. "
                   "Adds latency and credits — markdown gives full LLM-ready page text; "
                   "summary gives a short AI-generated summary. Leave blank for title+description only."),
        Param("timeout", "int", min=1000, max=300000, placeholder="60000", advanced=True,
              help="Request timeout in milliseconds (default 60000)."),
    ])

ENDPOINTS = {ep.id: ep for ep in (SEARCH,)}
ENDPOINT_ORDER = ["search"]
