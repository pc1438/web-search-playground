# competitor_search — Search API Playground

A schema-driven playground for search endpoints across providers, with two modes:
- **Playground**: pick a provider (tab: Brave · Exa · Parallel · Perplexity ·
  SerpApi · Tavily · You.com), an endpoint (dropdown), fill a request-builder form
  generated from that endpoint's schema, inspect the raw response.
- **Compare**: configure any two comparable endpoints (provider + endpoint +
  their parameters), ask one question, and see each endpoint's **raw response**
  side by side — the same view the provider tabs use. No scoring/judging.

Tab order: **About** first, then provider tabs (alpha-sorted), then **Compare** last.
An endpoint is comparable iff it sets `compare_query_field`; those endpoints are
selectable per side in the Compare picker, and the shared question is injected
into that field (the rest of the params come from each side's own form).

## Always: self-documenting

**After any change that alters behavior, config, commands, APIs, or project
structure, follow the `self-documenting` skill and update the relevant docs in
the same change.** This is always on (the equivalent of a Cursor
`alwaysApply: true` rule). The skill lives at
`.claude/skills/self-documenting/SKILL.md`. For this repo that means: when the
architecture changes, update the **About tab** in `app/index.html` (the arch
tree + core-classes section) and this file; when an endpoint/param changes,
update the provider package's docstrings; keep `providers/index.md` current. UI
work should follow [UX_STYLEGUIDE.md](UX_STYLEGUIDE.md) — the app's design tokens,
components, and interaction patterns (shareable across apps).

## Architecture (where a provider's code lives)

One provider = one self-contained package under `providers/`. See
[providers/index.md](providers/index.md) and the in-app **About** tab for detail.

```
providers/
  base.py         # Provider · Endpoint · Param — the contract every provider implements
  registry.py     # the one place that lists which providers exist
  exa/            # ExaProvider — /search /contents /answer; base call() fits (x-api-key)
  youdotcom/      # YouDotComProvider — /v1/search /contents /research /finance_research; base call() fits
  perplexity/     # PerplexityProvider — /search (Search API, base call()) + /v1/agent (Bearer, streaming
                  # call() via runner; `tools` selector: web_search/fetch_url/people_search/finance_search).
                  # Note: Perplexity has no contents/people/company ENDPOINTS — those are agent tools.
  parallel/       # ParallelProvider — /v1/search (mode: turbo=Search Turbo / basic / advanced) + /v1beta/search (beta, processor/limits;
                  # uses Endpoint.extra_headers for the beta version header) + /v1/tasks/runs (Task API:
                  # async create→poll→result via a custom call(); synthesized cited answer)
                  # + /v1beta/findall/entity-search (results-only).
  tavily/         # TavilyProvider — /search /extract /map /crawl; base call() fits (Bearer)
  brave/          # BraveProvider — GET web/news/images/videos search + suggest/spellcheck/summarizer/
                  # local; query-param API (X-Subscription-Token); headers() adds Accept: application/json
  serpapi/        # SerpApiProvider — one GET /search across engines (google/bing/ddg/youtube/…) via an
                  # `engine` selector; auth is a ?api_key= query param (auth_query_param), not a header
app/
  server.py       # thin HTTP: GET /api/providers · POST /api/call · POST /api/compare
  index.html      # provider tabs, form shell, Compare picker, About tab
  playground.js   # generic renderer — fetches the catalog, no per-provider code
comparison/       # perplexity_runner.py — the SSE Agent-API runner used by
                  # PerplexityProvider.call() for /v1/agent
```

**Data flow (playground):** frontend fetches `GET /api/providers` → renders
tabs/forms from the catalog → `POST /api/call {provider, endpoint, params}` →
`registry.get(...).call(...)` → upstream API (key injected server-side) → raw
response.

**Response viewer (`renderResponse` in `playground.js`, shared by playground +
Compare):** summary pills (HTTP status, latency, result count, and a **cost pill**
when the body reports one — `extractCost()` returns `{value, detail}` from Exa
`costDollars`, Perplexity `usage.cost` / agent `actual_cost`, or a plain `cost`;
the pill is clickable to drill into the breakdown when a `detail` object exists), then
the response object with a **Tree | Raw** toggle (interactive collapsible JSON
tree — deep nodes auto-collapse, URL values become links; Raw is the wrapped
`JSON.stringify`) and a **Copy** button, then a parsed answer/result-cards view.
Each result card's content badges (highlights/summary/entities/…) are **clickable
pills** that open the field's full value in a popover (text, list, or JSON tree).

**Form rendering (`playground.js`):** one generic renderer builds every form
from the catalog — no per-provider code. Layout: short scalars (int/enum/bool/
date/string) pair up two-per-row; roomy fields (text/csv/json) and groups span
the full row. Each field's `help` is a hover **ⓘ tooltip** beside its label (not
an always-on line); `bool` renders a **toggle switch**. Param flags drive
placement: `required` (asterisk + validated), `optional` (group enable toggle),
`deprecated` (hidden until "show deprecated" is on), and `advanced` (tucked into
a collapsed **"Advanced options"** group at the bottom, Parallel/Exa-style). Keep
each endpoint's primary view to its few common knobs; flag the rest `advanced=True`.

**Data flow (compare):** `POST /api/compare {left, right}`, each side
`{provider, endpoint, params}` (the frontend injects the shared question into the
endpoint's `compare_query_field`). Each side runs the provider's raw `call()` in a
thread; the `{ok,status,elapsed_ms,url,request,body}` wrapper is streamed back as
SSE and rendered exactly like a provider tab. No normalization or judging.

**To add a provider:** create `providers/<name>/` with a `Provider` subclass +
its endpoint schemas, register it in `providers/registry.py`, add its key to
`env.txt`. It appears as a playground tab automatically, and any endpoint with a
`compare_query_field` is automatically selectable in the Compare picker. The base
`call()` handles POST-JSON and **GET** (query-string) endpoints out of the box —
set `Endpoint.method="GET"` for query-param APIs (e.g. Brave). Auth is a header by
default (`auth_header`/`auth_prefix`); set `auth_query_param` instead for key-in-URL
APIs (e.g. SerpApi `?api_key=`) — the key is injected at request time and never
echoed in the response. Override `Provider.call()` only for streaming / async /
non-standard flows, and `Provider.headers()` for extra required headers (Brave's `Accept`).

## Run

```bash
python3 app/server.py --port 8088   # http://localhost:8088
```

Keys live in `env.txt` (git-ignored), one per provider: `EXA_API_KEY`,
`PARALLEL_API_KEY`, `YDC_API_KEY`, `PERPLEXITY_API_KEY`, `TAVILY_API_KEY`,
`BRAVE_API_KEY`, `SERPAPI_API_KEY`. A provider tab only works if its key is present.

## Logging

`server.py` logs to the console **and** a rotating file at `logs/server.log`
(git-ignored; 5MB × 5 backups). Level is `LOG_LEVEL` in `env.txt` — default
`INFO` (per-request one-liners). Set `LOG_LEVEL=DEBUG` to also record request
params, upstream URLs, and truncated response bodies (in `Provider.call` and the
`/api/call` + `/api/compare` handlers). `setup_logging()` runs after `load_dotenv`.
