"""
providers/parallel/endpoints.py — Parallel Search + FindAll API schemas.

Coverage verified against the live API (2026-07) since Parallel's public docs
don't fully enumerate the search bodies. Accepted fields probed directly:
  /v1/search (stable): objective, search_queries, session_id  (+ an undocumented
      internal `mode` enum, deliberately NOT exposed — internal engine names).
  /v1beta/search (beta): objective, search_queries, processor, max_results,
      max_chars_per_result, source_policy{include_domains, exclude_domains}, session_id.
  /v1beta/findall/entity-search: entity_type, objective, match_limit (complete).
"""

from providers.base import Param, Endpoint

ENTITY_TYPES = ["people", "companies"]
PROCESSORS = ["base", "pro"]
TASK_PROCESSORS = ["lite", "base", "core", "pro", "ultra"]

SEARCH = Endpoint(
    "search", "POST /v1/search — ranked results + excerpts (stable)",
    "/v1/search", compare_query_field="search_queries",
    docs_url="https://docs.parallel.ai/api-reference/search/search", params=[
        Param("search_queries", "csv", required=True, placeholder="best vector databases 2026",
              help="Keyword queries to execute (comma-separated). At least one required."),
        Param("objective", "text", placeholder="e.g. best open-source vector databases",
              help="Optional natural-language description of what you're searching for."),
        Param("session_id", "string", advanced=True, help="Optional ID to group related calls (up to 1000 chars)."),
    ])

SEARCH_BETA = Endpoint(
    "search-beta", "POST /v1beta/search — adds processor + result limits (beta)",
    "/v1beta/search", extra_headers={"parallel-beta": "search-extract-2025-10-10"},
    compare_query_field="objective",
    docs_url="https://docs.parallel.ai/api-reference/legacy/search-beta/search", params=[
        Param("objective", "text", placeholder="e.g. best open-source vector databases",
              help="Natural-language search intent. Provide objective and/or search_queries."),
        Param("search_queries", "csv", placeholder="best vector databases 2026",
              help="Keyword queries to guide the search (comma-separated)."),
        Param("processor", "enum", values=PROCESSORS,
              help="Search mode. base is cheaper/faster; pro is more thorough."),
        Param("max_results", "int", advanced=True, min=1, max=100, placeholder="10", help="Max results to return."),
        Param("max_chars_per_result", "int", advanced=True, min=100, max=30000,
              help="Character limit per result excerpt."),
        Param("source_policy", "group", optional=True, advanced=True,
              help="Restrict which sources are used.", fields=[
            Param("include_domains", "csv", help="Only use results from these domains."),
            Param("exclude_domains", "csv", help="Never use results from these domains."),
        ]),
        Param("session_id", "string", advanced=True, help="Optional ID to group related calls."),
    ])

TASK = Endpoint(
    "task", "POST /v1/tasks/runs — deep research task (synthesized, cited answer)",
    "/v1/tasks/runs", compare_query_field="input",
    docs_url="https://docs.parallel.ai/api-reference/tasks/create-task-run", params=[
        Param("input", "text", required=True,
              placeholder="e.g. What year was Stripe founded and who are its co-founders?",
              help="The task / research question. Parallel researches the web and returns a "
                   "synthesized answer with citations. (The playground creates the run and polls "
                   "for the result — higher processors can take a while.)"),
        Param("processor", "enum", required=True, values=TASK_PROCESSORS,
              help="Compute tier: lite/base (fast enrichments) → core (reliable, up to ~10 output "
                   "fields) → pro/ultra (deep reasoning). Higher = slower and more expensive."),
        Param("task_spec", "group", optional=True,
              help="Optional output specification. Omit for auto-formatted output.", fields=[
            Param("output_schema", "text",
                  placeholder="e.g. The founding year and a list of co-founder names",
                  help="Natural-language description of the desired output (the API also accepts a "
                       "full JSON Schema object for structured output)."),
        ]),
        Param("metadata", "json", advanced=True,
              help="Arbitrary key/value metadata echoed back on the run object."),
    ])

ENTITY_SEARCH = Endpoint(
    "entity-search", "POST /v1beta/findall/entity-search — find people or companies",
    "/v1beta/findall/entity-search", compare_params=["entity_type"],
    docs_url="https://docs.parallel.ai/findall-api/entity-search", params=[
        Param("entity_type", "enum", required=True, values=ENTITY_TYPES,
              help="The kind of entity to search for."),
        Param("objective", "text", required=True,
              placeholder="e.g. Series A robotics startups in Europe",
              help="Natural-language description of the people or companies you're looking for."),
        Param("match_limit", "int", min=5, max=1000, placeholder="100",
              help="Max results to return (5–1000; may yield fewer). No pagination."),
    ])

ENDPOINTS = {ep.id: ep for ep in (SEARCH, SEARCH_BETA, TASK, ENTITY_SEARCH)}
ENDPOINT_ORDER = ["search", "search-beta", "task", "entity-search"]
