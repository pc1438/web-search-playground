"""
providers/serpapi/endpoints.py — SerpApi schema.

SerpApi (verified live 2026-07 against serpapi.com) is a single GET endpoint,
`/search`, parameterized by an `engine` — it scrapes real SERPs (Google, Bing,
DuckDuckGo, YouTube, …) and returns structured JSON. Auth is a `?api_key=` query
param (not a header). Exposed as one endpoint with an engine selector, which also
makes `engine` a natural Compare fan-out dimension (e.g. Google vs Bing vs DDG).
"""

from providers.base import Param, Endpoint

# Common engines (SerpApi supports many more). `q` is the query param for all of
# these; google-family params (location/gl/hl/…) are ignored by engines that
# don't use them.
ENGINES = [
    "google", "google_light", "google_news", "google_images", "google_videos",
    "google_scholar", "google_maps", "google_shopping", "bing", "duckduckgo",
    "yahoo", "yandex", "baidu", "youtube",
]

SEARCH = Endpoint(
    "search", "GET /search — real SERP results via a chosen engine", "/search",
    method="GET", compare_query_field="q", compare_params=["engine"],
    docs_url="https://serpapi.com/search-api", params=[
        Param("engine", "enum", required=True, values=ENGINES,
              help="Which search engine to scrape. Changes the per-result shape (organic_results, "
                   "news_results, images_results, …)."),
        Param("q", "text", required=True, placeholder="e.g. best open-source vector databases",
              help="The search query. Sent as the engine's query param automatically "
                   "(most use `q`; Yandex uses `text`, Yahoo `p`, YouTube `search_query`)."),
        Param("location", "string", placeholder="Austin, Texas, United States",
              help="Canonical location to search from (google-family engines)."),
        Param("google_domain", "string", placeholder="google.com", help="Google domain to use."),
        Param("gl", "string", maxlen=2, placeholder="us", help="Two-letter country code (geolocation)."),
        Param("hl", "string", placeholder="en", help="Two-letter UI/host language code."),
        Param("num", "int", min=1, max=100, placeholder="10", help="Number of results to return."),
        Param("start", "int", advanced=True, min=0, help="Result offset for pagination."),
        Param("safe", "enum", advanced=True, values=["active", "off"], help="SafeSearch filtering."),
        Param("device", "enum", advanced=True, values=["desktop", "tablet", "mobile"],
              help="Device to emulate for the SERP."),
        Param("tbs", "string", advanced=True, help="Advanced search params (engine-specific, e.g. time filters)."),
        Param("no_cache", "bool", advanced=True,
              help="Force a fresh scrape instead of a cached result (slower; may cost more)."),
    ])

ENDPOINTS = {ep.id: ep for ep in (SEARCH,)}
ENDPOINT_ORDER = ["search"]
