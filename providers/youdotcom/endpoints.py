"""
providers/youdotcom/endpoints.py — You.com API schemas.

You.com exposes four endpoints across two hosts (verified against
you.com/docs, 2026-07):
  Search  — GET/POST ydc-index.io/v1/search   (LLM-ready web results)
  Contents— POST     ydc-index.io/v1/contents (crawl/extract known URLs)
  Research— POST     api.you.com/v1/research   (multi-step research + synthesis)
  Finance — POST     api.you.com/v1/finance_research (finance/company research)
All use the `X-API-Key` header. The provider's default host is api.you.com;
Search/Contents override it to ydc-index.io via Endpoint.base_url.
"""

from providers.base import Param, Endpoint

YDC_INDEX = "https://ydc-index.io"
EFFORTS = ["lite", "standard", "deep", "exhaustive"]
SAFESEARCH = ["off", "moderate", "strict"]
LIVECRAWL = ["web", "news", "all"]
FRESHNESS_HELP = "day, week, month, year, or a YYYY-MM-DDtoYYYY-MM-DD range."
COUNTRIES = ["AR", "AU", "AT", "BE", "BR", "CA", "CL", "DK", "FI", "FR", "DE", "HK", "IN", "ID",
             "IT", "JP", "KR", "MY", "MX", "NL", "NZ", "NO", "CN", "PL", "PT", "PH", "RU", "SA",
             "ZA", "ES", "SE", "CH", "TW", "TR", "GB", "US"]

DOCS = "https://you.com/docs/api-reference"


def _source_control():
    return Param("source_control", "group", optional=True, advanced=True, help="Restrict/steer which sources are used.", fields=[
        Param("include_domains", "csv", help="Only these domains (max 500; not with exclude_domains)."),
        Param("exclude_domains", "csv", help="Block these domains (max 500)."),
        Param("boost_domains", "csv", help="Boost these domains' ranking (max 500; not with include_domains)."),
        Param("freshness", "string", help="Recency filter. " + FRESHNESS_HELP),
        Param("country", "enum", values=COUNTRIES, help="Two-letter country code."),
    ])


SEARCH = Endpoint("search", "POST /v1/search — LLM-ready web + news results", "/v1/search",
    base_url=YDC_INDEX, compare_query_field="query", docs_url=f"{DOCS}/search/v1-search", params=[
    Param("query", "text", required=True, placeholder="e.g. best open-source vector databases",
          help="Search query (may include operators like site:, filetype:)."),
    Param("count", "int", min=1, max=50, placeholder="10", help="Results per section (web/news)."),
    Param("country", "enum", values=COUNTRIES, help="Geographic focus."),
    Param("safesearch", "enum", values=SAFESEARCH, help="Content filtering (default moderate)."),
    Param("freshness", "string", help="Recency filter. " + FRESHNESS_HELP),
    Param("offset", "int", advanced=True, min=0, max=9, help="Pagination offset, in multiples of count (0–9)."),
    Param("language", "string", advanced=True, placeholder="en", help="Result language (BCP 47)."),
    Param("include_domains", "csv", advanced=True, help="Allowlist (comma-separated; not with exclude_domains)."),
    Param("exclude_domains", "csv", advanced=True, help="Blocklist (comma-separated)."),
    Param("boost_domains", "csv", advanced=True, help="Boost these domains' ranking (up to 500)."),
    Param("livecrawl", "enum", advanced=True, values=LIVECRAWL, help="Return full page content (adds latency + cost)."),
    Param("livecrawl_formats", "csv", advanced=True, help="Crawled content formats: html, markdown."),
    Param("crawl_timeout", "int", advanced=True, min=1, max=60, help="Seconds to wait for page content (default 10)."),
])

CONTENTS = Endpoint("contents", "POST /v1/contents — crawl/extract known URLs", "/v1/contents",
    base_url=YDC_INDEX, docs_url=f"{DOCS}/contents/contents", params=[
    Param("urls", "csv", required=True, placeholder="https://example.com/a, https://example.com/b",
          help="URLs to crawl and extract."),
    Param("formats", "csv", required=True, placeholder="markdown, html",
          help="Content formats to return: html, markdown."),
    Param("crawl_timeout", "int", min=1, max=60, help="Seconds to wait per page (default 10)."),
])

RESEARCH = Endpoint("research", "POST /v1/research — deep research answer + sources", "/v1/research",
    compare_query_field="input", docs_url=f"{DOCS}/research/v1-research", params=[
    Param("input", "text", required=True, placeholder="e.g. who won the 2026 Olympic hockey gold?",
          help="The research question (max 40,000 chars). Multi-step search + synthesis."),
    Param("research_effort", "enum", values=EFFORTS,
          help="Depth: lite (fast) → exhaustive (most thorough). Default standard."),
    _source_control(),
    Param("output_schema", "json", advanced=True, help="JSON Schema for structured output (standard/deep/exhaustive only)."),
])

FINANCE = Endpoint("finance_research", "POST /v1/finance_research — finance/company research", "/v1/finance_research",
    compare_query_field="input", docs_url=f"{DOCS}/research/v1-research", params=[
    Param("input", "text", required=True, placeholder="e.g. NVIDIA latest earnings and guidance",
          help="Finance/company research question."),
    Param("research_effort", "enum", values=EFFORTS, help="Depth: lite → exhaustive. Default standard."),
    _source_control(),
    Param("output_schema", "json", advanced=True, help="JSON Schema for structured output."),
])

ENDPOINTS = {ep.id: ep for ep in (SEARCH, CONTENTS, RESEARCH, FINANCE)}
ENDPOINT_ORDER = ["search", "contents", "research", "finance_research"]
