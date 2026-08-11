"""
providers/octen/endpoints.py — Octen API endpoint schemas.

Coverage: /search, /broad-search, /answer, /extract
(docs.octen.ai/api-reference, 2026-07)

Response shape (all endpoints):
  { code, msg, request_id, data: { results: [...] }, meta: { usage, latency } }
Each result: title, url, highlight, full_content, authors, time_published, cover_image
"""

from providers.base import Param, Endpoint

TOPIC = ["general", "news"]
TIME_RANGE = ["day", "week", "month", "year"]
TIME_BASIS = ["auto", "published", "crawled"]
FORMAT = ["text", "markdown"]
SAFESEARCH = ["strict", "off"]

# Shared search config params reused by /search and /broad-search
def _search_options(prefix=""):
    """prefix="" for /search (top-level); prefix="search_options." for /broad-search."""
    return [
        Param("topic", "enum", values=TOPIC, help="Content category filter."),
        Param("count", "int", min=1, max=100, placeholder="5",
              help="Max results per query (1–100)."),
        Param("include_domains", "csv", placeholder="nytimes.com, bbc.com",
              help="Only return results from these domains (max 1200)."),
        Param("exclude_domains", "csv", placeholder="reddit.com",
              help="Never return results from these domains (max 1200)."),
        Param("include_text", "csv", advanced=True,
              help="Phrases that MUST appear in each result (max 5 items, 30 chars each)."),
        Param("exclude_text", "csv", advanced=True,
              help="Phrases that must NOT appear in each result (max 5 items, 30 chars each)."),
        Param("time_range", "enum", values=TIME_RANGE, advanced=True,
              help="Recency filter. Mutually exclusive with start_time/end_time."),
        Param("time_basis", "enum", values=TIME_BASIS, advanced=True,
              help="Whether time filters apply to published or crawled date."),
        Param("language", "csv", advanced=True, placeholder="en, fr",
              help="ISO 639-1 language codes (up to 18 supported)."),
        Param("format", "enum", values=FORMAT, advanced=True,
              help="Content format for highlight and full_content fields."),
        Param("safesearch", "enum", values=SAFESEARCH, advanced=True,
              help="Safe search filter (default: strict)."),
        Param("include_images", "bool", advanced=True,
              help="Include image URLs in each result."),
    ]


SEARCH = Endpoint(
    "search", "POST /search — web search", "/search",
    compare_query_field="query",
    docs_url="https://docs.octen.ai/api-reference/search",
    params=[
        Param("query", "text", required=True, placeholder="e.g. best open-source LLMs 2026",
              help="Search query, max 500 characters."),
        *_search_options(),
        Param("highlight_enable", "bool", advanced=True,
              help="Return highlighted snippets (default: true)."),
        Param("highlight_max_tokens", "int", min=100, max=20000, placeholder="512",
              advanced=True,
              help="Token limit for highlight field. Default: 512 (~2KB text). Max: 20,000 (~80KB). Raise this to get richer snippets — 2,000–5,000 is a good starting point."),
        Param("full_content_enable", "bool", advanced=True,
              help="Return full page content for each result (default: false)."),
        Param("full_content_max_tokens", "int", min=100, max=100000, placeholder="2048",
              advanced=True,
              help="Token limit for full_content field. Default: 2,048 (~8KB text, ~2 pages). Max: 100,000 (~400KB). Set to 20,000–50,000 to get meaningful full-page content comparable to other providers."),
    ])

BROAD_SEARCH = Endpoint(
    "broad-search", "POST /broad-search — multi-angle concurrent search", "/broad-search",
    compare_query_field="query",
    docs_url="https://docs.octen.ai/api-reference/broad-search",
    params=[
        Param("query", "text", required=True, placeholder="e.g. impact of AI on software engineering",
              help="Search query. Octen generates up to max_queries parallel sub-queries internally."),
        Param("max_queries", "int", min=1, max=30, placeholder="5",
              help="Number of concurrent sub-queries to generate (1–30, default 5)."),
        *_search_options(),
        Param("highlight_enable", "bool", advanced=True,
              help="Return highlighted snippets per result (default: true)."),
        Param("highlight_max_tokens", "int", min=100, max=20000, placeholder="512",
              advanced=True,
              help="Token limit for highlight field. Default: 512 (~2KB text). Max: 20,000 (~80KB). Raise this to get richer snippets — 2,000–5,000 is a good starting point."),
        Param("full_content_enable", "bool", advanced=True,
              help="Return full page content per result (default: false)."),
        Param("full_content_max_tokens", "int", min=100, max=100000, placeholder="2048",
              advanced=True,
              help="Token limit for full_content field. Default: 2,048 (~8KB text, ~2 pages). Max: 100,000 (~400KB). Set to 20,000–50,000 to get meaningful full-page content comparable to other providers."),
    ])

ANSWER = Endpoint(
    "answer", "POST /answer — grounded answer with citations", "/answer",
    compare_query_field="messages",
    docs_url="https://docs.octen.ai/api-reference/answer",
    params=[
        Param("messages", "text", required=True,
              placeholder="e.g. What are the latest developments in fusion energy?",
              help="Natural-language question sent as a user message."),
        Param("model", "string", placeholder="anthropic/claude-sonnet-4-6",
              help="LLM for query decomposition and synthesis."),
        Param("mode", "enum", values=["full", "queries_and_search", "queries_only"],
              help="Execution depth (default: full — decompose, search, synthesize)."),
        Param("max_queries", "int", min=1, max=30, placeholder="5",
              help="Max sub-queries to generate (default 30)."),
        Param("stream", "bool", advanced=True,
              help="Stream the answer as SSE chunks (playground shows raw text)."),
    ])

EXTRACT = Endpoint(
    "extract", "POST /extract — crawl and extract content from URLs", "/extract",
    docs_url="https://docs.octen.ai/api-reference/extract",
    params=[
        Param("urls", "csv", required=True,
              placeholder="https://example.com/a, https://example.com/b",
              help="URLs to extract (max 20, 2048 chars each)."),
        Param("query", "string",
              help="Intent keywords — when provided, returns query-relevant highlights per URL."),
        Param("format", "enum", values=FORMAT,
              help="Output format for extracted content (default: markdown)."),
        Param("max_age_seconds", "int", min=300, max=86400, advanced=True,
              help="Max cache age in seconds (300–86400, default 86400)."),
        Param("timeout", "int", min=1, max=60, advanced=True,
              help="Per-URL extraction timeout in seconds (default 30)."),
        Param("include_images", "bool", advanced=True,
              help="Return detected image URLs."),
        Param("include_videos", "bool", advanced=True,
              help="Return detected video URLs."),
    ])

ENDPOINTS = {ep.id: ep for ep in (SEARCH, BROAD_SEARCH, ANSWER, EXTRACT)}
ENDPOINT_ORDER = ["search", "broad-search", "answer", "extract"]
