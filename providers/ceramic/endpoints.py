"""
providers/ceramic/endpoints.py — Ceramic API schema.

Ceramic (ceramic.ai) exposes a single web-scale search endpoint (verified live
2026-07 against api.ceramic.ai): a JSON POST with an `Authorization: Bearer`
header. Unlike the semantic engines here, Ceramic is keyword search — it matches
distinctive terms rather than interpreting natural language — so it adds a
different retrieval style to Compare.

Response shape: {requestId, result:{results:[{title,url,description}],
searchMetadata:{executionTime}, totalResults}}. `executionTime` (seconds) is the
provider's own processing time, surfaced as the "server" latency pill.
"""

from providers.base import Param, Endpoint

DOCS = "https://docs.ceramic.ai/api-reference/search"

SEARCH = Endpoint(
    "search", "POST /search — web-scale keyword search", "/search",
    compare_query_field="query",
    docs_url=DOCS, params=[
        Param("query", "text", required=True, placeholder="e.g. california rental laws",
              help="Search query, 1–50 words. Ceramic matches keywords (not natural language / synonyms), "
                   "so pick distinctive terms."),
        Param("maxDescriptionLength", "int", min=1000, max=8000, placeholder="3000", advanced=True,
              help="Characters of description text per result (1000–8000, default 3000)."),
    ])

ENDPOINTS = {ep.id: ep for ep in (SEARCH,)}
ENDPOINT_ORDER = ["search"]
