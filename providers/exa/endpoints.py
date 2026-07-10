"""
providers/exa/endpoints.py — Exa's request-body schemas.

Single source of truth for what each Exa endpoint accepts. The frontend renders
its request-builder form directly from these Params (via the catalog), so this
file is the one place to change when Exa's API surface changes.

Coverage: enumerated against Exa's OpenAPI reference (docs.exa.ai/reference,
2026-07) — every documented request-body field, including nested `contents.*`
sub-fields and deprecated ones (marked in help text). Deprecated: startCrawlDate,
endCrawlDate, contents.livecrawl, contents.context, highlights.numSentences,
highlights.highlightsPerUrl.
"""

from providers.base import Param, Endpoint

EXA_TYPES = ["auto", "fast", "instant", "deep-lite", "deep", "deep-reasoning"]
EXA_CATEGORIES = ["company", "research paper", "news", "personal site", "financial report", "people"]
VERBOSITY = ["compact", "standard", "full"]
LIVECRAWL = ["never", "always", "fallback", "preferred"]
SECTIONS = "header, navigation, banner, body, sidebar, footer, metadata"

DOCS = "https://docs.exa.ai/reference"


# Content-extraction fields, shared by /search (nested under `contents`) and
# /contents (top-level). Factory so each endpoint gets its own Param instances.
def _content_fields():
    return [
        Param("text", "group", optional=True, boolean_shorthand=True,
              help="Full page text. Enable alone to send `true`, or set options for an object.", fields=[
            Param("maxCharacters", "int", min=1, max=10000),
            Param("includeHtmlTags", "bool"),
            Param("verbosity", "enum", values=VERBOSITY),
            Param("includeSections", "csv", help="Keep only these page sections. Values: " + SECTIONS),
            Param("excludeSections", "csv", help="Drop these page sections. Values: " + SECTIONS),
        ]),
        Param("highlights", "group", optional=True, boolean_shorthand=True,
              help="LLM-selected relevant snippets.", fields=[
            Param("query", "string", help="Guides which snippets are chosen."),
            Param("maxCharacters", "int", min=1, max=10000),
            Param("numSentences", "int", min=1, max=20, help="Deprecated.", deprecated=True),
            Param("highlightsPerUrl", "int", min=1, max=20, help="Deprecated.", deprecated=True),
        ]),
        Param("summary", "group", optional=True, help="LLM-generated summary of each result.", fields=[
            Param("query", "string", help="Optional focus for the summary."),
            Param("schema", "json", help="Optional JSON Schema for a structured summary object."),
        ]),
        Param("extras", "group", optional=True, help="Extra extractions from each page.", fields=[
            Param("links", "int", min=0, max=1000),
            Param("imageLinks", "int", min=0, max=1000),
            Param("richImageLinks", "int", min=0, max=1000),
            Param("richLinks", "int", min=0, max=1000),
            Param("codeBlocks", "int", min=0, max=1000),
        ]),
        Param("maxAgeHours", "int", min=-1, max=720,
              help="Freshness: 0 = fetch fresh, -1 = cache only, N = use cache if < N hours old."),
        Param("livecrawl", "enum", values=LIVECRAWL, help="Deprecated — prefer maxAgeHours.", deprecated=True),
        Param("livecrawlTimeout", "int", min=1, max=90000, help="Livecrawl timeout in ms (default 10000)."),
        Param("subpages", "int", min=0, max=100, help="Crawl N related subpages per result."),
        Param("subpageTarget", "csv", help="Keyword(s) to pick which subpages to crawl."),
        Param("context", "group", optional=True, deprecated=True,
              help="Deprecated — combined context string; use text/highlights instead.", fields=[
            Param("maxCharacters", "int", min=1, max=10000),
        ]),
    ]


SEARCH = Endpoint("search", "POST /search — web search + content extraction", "/search",
    compare_params=["category", "type"], compare_query_field="query", docs_url=f"{DOCS}/search", params=[
    Param("query", "text", required=True, placeholder="e.g. best open-source vector databases",
          help="The search query string."),
    Param("type", "enum", values=EXA_TYPES, help="Search mode. auto balances quality and speed."),
    Param("category", "enum", values=EXA_CATEGORIES,
          help="Focus on a data category. This is what changes the per-result shape (entities)."),
    Param("numResults", "int", min=1, max=100, placeholder="10", help="1–100 results."),
    Param("includeDomains", "csv", placeholder="nytimes.com, bbc.com",
          help="Only return results from these domains (comma-separated, max 1200)."),
    Param("excludeDomains", "csv", placeholder="reddit.com", help="Never return results from these domains (max 1200)."),
    Param("startPublishedDate", "date", help="Only results published on/after this date."),
    Param("endPublishedDate", "date", help="Only results published on/before this date."),
    Param("startCrawlDate", "date", help="Deprecated — only links crawled on/after this date.", deprecated=True),
    Param("endCrawlDate", "date", help="Deprecated — only links crawled on/before this date.", deprecated=True),
    Param("includeText", "csv", advanced=True, help="Phrase(s) that must appear on the result page."),
    Param("excludeText", "csv", advanced=True, help="Phrase(s) that must NOT appear on the result page."),
    Param("userLocation", "string", advanced=True, placeholder="US", maxlen=2,
          help="Two-letter ISO country code for localized results."),
    Param("moderation", "bool", advanced=True, help="Filter unsafe results."),
    Param("compliance", "enum", advanced=True, values=["hipaa"], help="Enterprise-only HIPAA-safe processing mode."),
    Param("additionalQueries", "csv", advanced=True, help="1–10 query variations (deep-search modes only)."),
    Param("systemPrompt", "text", advanced=True, help="Guidance for output generation / agent behavior."),
    Param("outputSchema", "json", advanced=True, help="JSON Schema for synthesized structured output (adds ~2s latency)."),
    Param("stream", "bool", advanced=True, help="Stream synthesized output as SSE (playground shows it as raw text)."),
    Param("contents", "group", optional=True,
          help="Extract page content for each result (text, highlights, summary, …).", fields=_content_fields()),
])

CONTENTS = Endpoint("contents", "POST /contents — crawl/extract known URLs or IDs", "/contents",
    docs_url=f"{DOCS}/get-contents", params=[
    Param("urls", "csv", placeholder="https://example.com/a, https://example.com/b",
          help="URLs to crawl (or use ids from a prior search). Max 100."),
    Param("ids", "csv", help="Document IDs obtained from a search response. Max 100."),
    Param("compliance", "enum", advanced=True, values=["hipaa"], help="Enterprise-only HIPAA-safe processing mode."),
    *_content_fields(),
])

ANSWER = Endpoint("answer", "POST /answer — grounded answer with citations", "/answer",
    compare_query_field="query", docs_url=f"{DOCS}/answer", params=[
    Param("query", "text", required=True, placeholder="e.g. what is the latest on the EU AI Act?",
          help="Natural-language question."),
    Param("text", "bool", help="Include full page text of each citation."),
    Param("outputSchema", "json", advanced=True, help="JSON Schema (Draft 7) for structured output."),
    Param("stream", "bool", advanced=True, help="Stream the answer as SSE (playground shows it as raw text)."),
])

ENDPOINTS = {ep.id: ep for ep in (SEARCH, CONTENTS, ANSWER)}
ENDPOINT_ORDER = ["search", "contents", "answer"]
