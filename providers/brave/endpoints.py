"""
providers/brave/endpoints.py — Brave Search API schemas.

Brave's API (verified live 2026-07 against api.search.brave.com/res/v1) is unlike
the others: every endpoint is a **GET** with query-string params (not a JSON
body) and an `X-Subscription-Token` header. The base `call()` sends GET params as
a query string (csv-joining lists), so no request-shaping override is needed —
BraveProvider only adds the `Accept: application/json` header.

Endpoints: web/news/image/video search, plus suggest, spellcheck, summarizer, and
local POIs/descriptions. Some (suggest/spellcheck/summarizer) require a paid plan
tier; the playground surfaces Brave's own error faithfully when they're not
subscribed. summarizer + local are two-step: they take a key/ids obtained from a
prior web search.
"""

from providers.base import Param, Endpoint

SAFESEARCH = ["off", "moderate", "strict"]
SAFESEARCH_IMG = ["off", "strict"]
FRESHNESS_HELP = "pd (24h), pw (7d), pm (31d), py (year), or a YYYY-MM-DDtoYYYY-MM-DD range."
RESULT_FILTER = "web, news, videos, discussions, faq, infobox, query, summarizer, locations"
DOCS = "https://api-dashboard.search.brave.com/app/documentation"
LOCAL_DOCS = "https://api-dashboard.search.brave.com/api-reference/web"


def _common(count_max=20):
    # Params shared by the main search endpoints.
    return [
        Param("country", "string", maxlen=2, placeholder="US", help="2-letter country code."),
        Param("search_lang", "string", placeholder="en", help="Search language code."),
        Param("ui_lang", "string", advanced=True, placeholder="en-US", help="UI language (affects some strings)."),
        Param("count", "int", min=1, max=count_max, placeholder="20", help=f"Results to return (max {count_max})."),
        Param("offset", "int", min=0, max=9, advanced=True, help="Pagination offset (0–9)."),
        Param("safesearch", "enum", values=SAFESEARCH, help="Adult-content filtering (default moderate)."),
        Param("spellcheck", "bool", advanced=True, help="Spellcheck the query before searching."),
    ]


WEB = Endpoint(
    "web", "GET /web/search — web results (+ discussions, faq, videos)", "/web/search",
    method="GET", compare_query_field="q", docs_url=f"{DOCS}/web-search/get-started", params=[
        Param("q", "text", required=True, placeholder="e.g. best open-source vector databases",
              help="The search query (max 400 chars / 50 words)."),
        *_common(20),
        Param("freshness", "string", help="Recency filter. " + FRESHNESS_HELP),
        Param("result_filter", "csv", advanced=True, help="Limit result types. Values: " + RESULT_FILTER),
        Param("goggles", "csv", advanced=True, help="Goggle URLs/definitions that re-rank results."),
        Param("units", "enum", values=["metric", "imperial"], advanced=True, help="Measurement units in results."),
        Param("extra_snippets", "bool", advanced=True, help="Return up to 5 extra excerpts per result."),
        Param("summary", "bool", advanced=True, help="Enable a summarizer key in the response (for /summarizer)."),
        Param("text_decorations", "bool", advanced=True, help="Include highlight markup in snippets."),
    ])

NEWS = Endpoint(
    "news", "GET /news/search — news results", "/news/search",
    method="GET", compare_query_field="q", docs_url=f"{DOCS}/news-search/get-started", params=[
        Param("q", "text", required=True, placeholder="e.g. AI chip export controls", help="The search query."),
        *_common(50),
        Param("freshness", "string", help="Recency filter. " + FRESHNESS_HELP),
        Param("extra_snippets", "bool", advanced=True, help="Return extra excerpts per article."),
        Param("goggles", "csv", advanced=True, help="Goggle URLs/definitions that re-rank results."),
    ])

IMAGES = Endpoint(
    "images", "GET /images/search — image results", "/images/search",
    method="GET", compare_query_field="q", docs_url=f"{DOCS}/image-search/get-started", params=[
        Param("q", "text", required=True, placeholder="e.g. northern lights", help="The search query."),
        Param("country", "string", maxlen=2, placeholder="US", help="2-letter country code."),
        Param("search_lang", "string", placeholder="en", help="Search language code."),
        Param("count", "int", min=1, max=100, placeholder="50", help="Images to return (max 100)."),
        Param("safesearch", "enum", values=SAFESEARCH_IMG, help="Adult-content filtering (off or strict)."),
        Param("spellcheck", "bool", advanced=True, help="Spellcheck the query before searching."),
    ])

VIDEOS = Endpoint(
    "videos", "GET /videos/search — video results", "/videos/search",
    method="GET", compare_query_field="q", docs_url=f"{DOCS}/video-search/get-started", params=[
        Param("q", "text", required=True, placeholder="e.g. how vector databases work", help="The search query."),
        *_common(50),
        Param("freshness", "string", help="Recency filter. " + FRESHNESS_HELP),
    ])

SUGGEST = Endpoint(
    "suggest", "GET /suggest/search — autocomplete suggestions", "/suggest/search",
    method="GET", docs_url=f"{DOCS}/suggest/get-started", params=[
        Param("q", "text", required=True, placeholder="e.g. vector dat", help="Partial query to autocomplete."),
        Param("country", "string", maxlen=2, placeholder="US", help="2-letter country code."),
        Param("count", "int", min=1, max=20, advanced=True, help="Number of suggestions."),
        Param("rich", "bool", advanced=True, help="Return richer suggestion entities where available."),
    ])

SPELLCHECK = Endpoint(
    "spellcheck", "GET /spellcheck/search — spelling correction", "/spellcheck/search",
    method="GET", docs_url=f"{DOCS}/spellcheck/get-started", params=[
        Param("q", "text", required=True, placeholder="e.g. vetcor databse", help="Query to spellcheck."),
        Param("country", "string", maxlen=2, advanced=True, placeholder="US", help="2-letter country code."),
    ])

SUMMARIZER = Endpoint(
    "summarizer", "GET /summarizer/search — AI summary (needs a summary key)", "/summarizer/search",
    method="GET", docs_url=f"{DOCS}/summarizer-search/get-started", params=[
        Param("key", "string", required=True,
              help="The summarizer key from a Web Search run with summary=true (summarizer.key in that response)."),
        Param("entity_info", "bool", advanced=True, help="Include entity metadata in the summary."),
    ])

LOCAL_POIS = Endpoint(
    "local_pois", "GET /local/pois — local point-of-interest details", "/local/pois",
    method="GET", docs_url=f"{LOCAL_DOCS}/local_pois", params=[
        Param("ids", "csv", required=True,
              help="Location IDs from a Web Search 'locations' result (max 20)."),
        Param("search_lang", "string", advanced=True, placeholder="en", help="Search language code."),
        Param("ui_lang", "string", advanced=True, placeholder="en-US", help="UI language code."),
        Param("units", "enum", values=["metric", "imperial"], advanced=True, help="Measurement units."),
    ])

LOCAL_DESC = Endpoint(
    "local_descriptions", "GET /local/descriptions — AI descriptions for locations", "/local/descriptions",
    method="GET", docs_url=f"{LOCAL_DOCS}/local_pois", params=[   # local API docs (pois page covers descriptions too)
        Param("ids", "csv", required=True, help="Location IDs from a Web Search 'locations' result (max 20)."),
        Param("search_lang", "string", advanced=True, placeholder="en", help="Search language code."),
        Param("ui_lang", "string", advanced=True, placeholder="en-US", help="UI language code."),
    ])

ENDPOINTS = {ep.id: ep for ep in (WEB, NEWS, IMAGES, VIDEOS, SUGGEST, SPELLCHECK, SUMMARIZER, LOCAL_POIS, LOCAL_DESC)}
ENDPOINT_ORDER = ["web", "news", "images", "videos", "suggest", "spellcheck", "summarizer", "local_pois", "local_descriptions"]
