"""
providers/tavily/endpoints.py — Tavily API schemas.

Tavily's public HTTP surface (verified live 2026-07 against api.tavily.com): four
POST endpoints, all JSON with a `Authorization: Bearer` header:
  /search   — web search (+ optional LLM answer, raw content, images)
  /extract  — pull clean content from known URLs
  /map      — discover a site's URL structure
  /crawl    — crawl a site and return page content
Only /search is answer/result-shaped, so it's the one exposed to Compare.
"""

from providers.base import Param, Endpoint

DEPTH = ["basic", "advanced"]
TOPIC = ["general", "news", "finance"]
TIME_RANGE = ["day", "week", "month", "year"]
FORMAT = ["markdown", "text"]
DOCS = "https://docs.tavily.com/documentation/api-reference/endpoint"

SEARCH = Endpoint(
    "search", "POST /search — web search (+ optional LLM answer)", "/search",
    compare_query_field="query", compare_params=["search_depth", "include_answer"],
    docs_url=f"{DOCS}/search", params=[
        Param("query", "text", required=True, placeholder="e.g. best open-source vector databases",
              help="The search query."),
        Param("search_depth", "enum", values=DEPTH,
              help="basic (1 credit) or advanced (2 credits — deeper retrieval, reranked snippets)."),
        Param("topic", "enum", values=TOPIC, help="Search category. news/finance tune freshness + sources."),
        Param("max_results", "int", min=0, max=20, placeholder="5", help="0–20 results (default 5)."),
        Param("include_answer", "enum", values=DEPTH,
              help="Include an LLM-generated answer: basic (quick) or advanced (thorough)."),
        Param("chunks_per_source", "int", min=1, max=3, advanced=True,
              help="advanced depth only: how many content chunks per source (1–3)."),
        Param("time_range", "enum", values=TIME_RANGE, advanced=True, help="Restrict results to a recent window."),
        Param("days", "int", advanced=True, help="news topic only: results from the past N days."),
        Param("start_date", "date", advanced=True, help="Only results on/after this date."),
        Param("end_date", "date", advanced=True, help="Only results on/before this date."),
        Param("include_raw_content", "enum", values=FORMAT, advanced=True,
              help="Return each result's full page content as markdown or text."),
        Param("include_images", "bool", advanced=True, help="Also return query-related images."),
        Param("include_image_descriptions", "bool", advanced=True, help="Add descriptions to returned images."),
        Param("include_domains", "csv", advanced=True, help="Only return results from these domains."),
        Param("exclude_domains", "csv", advanced=True, help="Never return results from these domains."),
        Param("country", "string", advanced=True, placeholder="united states",
              help="general topic: boost results from this country (full name, lowercase)."),
        Param("auto_parameters", "bool", advanced=True,
              help="Let Tavily auto-tune search_depth/topic/etc. from the query."),
    ])

EXTRACT = Endpoint(
    "extract", "POST /extract — clean content from known URLs", "/extract",
    docs_url=f"{DOCS}/extract", params=[
        Param("urls", "csv", required=True, placeholder="https://example.com/a, https://example.com/b",
              help="One or more URLs to extract content from."),
        Param("extract_depth", "enum", values=DEPTH, help="advanced pulls more (tables, embedded content)."),
        Param("format", "enum", values=FORMAT, help="Content format returned (default markdown)."),
        Param("include_images", "bool", advanced=True, help="Also return images found on each page."),
    ])

MAP = Endpoint(
    "map", "POST /map — discover a site's URL structure", "/map",
    docs_url=f"{DOCS}/map", params=[
        Param("url", "string", required=True, placeholder="https://docs.tavily.com", help="Root URL to map."),
        Param("max_depth", "int", placeholder="1", help="How many link-hops deep to traverse."),
        Param("limit", "int", placeholder="50", help="Max number of URLs to return."),
        Param("max_breadth", "int", advanced=True, help="Max links to follow per page."),
        Param("instructions", "text", advanced=True, help="Natural-language guidance for which pages to include."),
        Param("select_paths", "csv", advanced=True, help="Regex paths to include (e.g. /docs/.*)."),
        Param("select_domains", "csv", advanced=True, help="Regex domains to include."),
        Param("allow_external", "bool", advanced=True, help="Follow links to other domains."),
        Param("categories", "csv", advanced=True, help="Restrict to page categories (e.g. Documentation, Blog)."),
    ])

CRAWL = Endpoint(
    "crawl", "POST /crawl — crawl a site and return page content", "/crawl",
    docs_url=f"{DOCS}/crawl", params=[
        Param("url", "string", required=True, placeholder="https://docs.tavily.com", help="Root URL to crawl."),
        Param("max_depth", "int", placeholder="1", help="How many link-hops deep to crawl."),
        Param("limit", "int", placeholder="10", help="Max number of pages to crawl."),
        Param("instructions", "text", help="Natural-language guidance for which pages to crawl."),
        Param("max_breadth", "int", advanced=True, help="Max links to follow per page."),
        Param("extract_depth", "enum", values=DEPTH, advanced=True, help="How much content to pull per page."),
        Param("format", "enum", values=FORMAT, advanced=True, help="Content format (default markdown)."),
        Param("select_paths", "csv", advanced=True, help="Regex paths to include."),
        Param("select_domains", "csv", advanced=True, help="Regex domains to include."),
        Param("allow_external", "bool", advanced=True, help="Follow links to other domains."),
        Param("include_images", "bool", advanced=True, help="Return images found on each page."),
        Param("categories", "csv", advanced=True, help="Restrict to page categories."),
    ])

ENDPOINTS = {ep.id: ep for ep in (SEARCH, EXTRACT, MAP, CRAWL)}
ENDPOINT_ORDER = ["search", "extract", "map", "crawl"]
