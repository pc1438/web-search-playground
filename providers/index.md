# Providers

Each provider is one self-contained package. Working on a provider means
touching only its folder — never another provider's, and rarely the shared base.

- [base.py](base.py) — the contract: `Param` (one request-body field), `Endpoint` (one API operation), `Provider` (identity, auth, endpoints). Key methods:
  - `call(endpoint, params)` — the request behind both the playground and Compare. Default = plain JSON POST with the API-key header; override for streaming / async / non-standard auth.
  - `catalog()` — serializes the provider for the frontend renderer.
- [registry.py](registry.py) — the single list of which providers exist. `get(id)` and `catalog()`. Adding a provider = one edit here.
- [exa/](exa/) — Exa. `/search` `/contents` `/answer`; `x-api-key` auth. No `call()` override.
- [youdotcom/](youdotcom/) — You.com. `/v1/search`, `/v1/contents` (host `ydc-index.io`), `/v1/research`, `/v1/finance_research`; `X-API-Key` auth; base `call()` fits all (each returns JSON).
- [perplexity/](perplexity/) — Perplexity, two endpoints. `/search` (Search API — plain JSON, base `call()`) and `/v1/agent` (`Bearer` auth via `auth_prefix`; `call()` routes to the streaming runner `comparison/perplexity_runner.py`; exposes a `tools` selector — web_search/fetch_url/people_search/finance_search). Note: Perplexity's "contents"/"people"/"company" are agent **tools**, not standalone endpoints.
- [parallel/](parallel/) — Parallel Search + Task + FindAll APIs, four endpoints (both search variants exposed so their differing optionality is visible):
  - `/v1/search` — `search_queries` **required**, `objective` optional, plus **`mode`** (`turbo` = Parallel's Search Turbo ~200ms · `basic` · `advanced` default ~3s). `mode` is a Compare fan-out dimension.
  - `/v1beta/search` (beta) — `objective` and/or `search_queries`, plus `processor`/`max_results`/`max_chars_per_result`; sends the beta version header via `Endpoint.extra_headers`.
  - `/v1/tasks/runs` (Task API) — deep research: `input` + `processor` (lite/base/core/pro/ultra) + optional `task_spec.output_schema`. **Asynchronous** — the provider overrides `call()` to create the run, poll `GET /v1/tasks/runs/{id}` until terminal, then fetch `…/result`. Returns a synthesized answer (`output.content`) with citations (`output.basis[].citations[].url`).
  - `/v1beta/findall/entity-search` — ranked entities (`entity_type` + `objective`); results-only.
  `x-api-key`. Base `call()` fits Search/FindAll; Task needs the custom create→poll→result `call()`. Search, Search-beta, and Task all set `compare_query_field`, so they're selectable in Compare; FindAll entity-search is playground-only.
- [tavily/](tavily/) — Tavily. `/search` (comparable) + `/extract` + `/map` + `/crawl`; `Authorization: Bearer` auth; base `call()` fits (plain JSON POST). `/search` can return an LLM `answer` alongside results.
- [serpapi/](serpapi/) — SerpApi. One **GET** `/search` across engines (google, google_news, google_images, bing, duckduckgo, youtube, …) via an `engine` selector; `engine` is a Compare fan-out dimension. Auth is a `?api_key=` **query param** (`auth_query_param`), so there's no auth header and the key is never echoed in the response. Results live under engine-specific arrays (`organic_results`, `news_results`, …); the renderer maps those + the `link` field to result cards.
- [brave/](brave/) — Brave Search. **GET** query-param API (`X-Subscription-Token` header, `Accept: application/json` added in `headers()`): `web`/`news`/`images`/`videos` search (comparable) + `suggest`, `spellcheck`, `summarizer`, `local_pois`, `local_descriptions`. No `call()` override — the base handles GET (params → query string, lists comma-joined). Web results nest under `body.web.results`. Some endpoints (suggest/spellcheck/summarizer) need a higher plan tier; the playground shows Brave's own error when they aren't subscribed. `summarizer`/`local_*` are two-step (they take a key/ids from a prior web search).

## Adding a provider

1. Create `providers/<name>/provider.py` with a `Provider` subclass (+ `endpoints.py` for its schemas).
2. Register it in `registry.py`.
3. Add its API key to `env.txt`.

It surfaces automatically as a playground tab (catalog → tab → endpoint dropdown → form). Any endpoint that sets `compare_query_field` is automatically selectable in the **Compare** picker — no extra code. Override `Provider.call()` only if the API streams, is async, or authenticates unusually (see `perplexity/`, `parallel/`).
