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

## Verification notes

Findings from probing the live APIs (so they're not re-investigated):
- **Perplexity `/search` params are valid.** `search_context_size`, `max_tokens`, `max_tokens_per_page`, `search_language_filter`, `search_domain_filter`, `country` each return 200 individually. There's a **Perplexity-side** quirk: `search_context_size` + `max_tokens` **together** reproducibly return `500 internal_error` (each alone is fine). Not our bug; the playground surfaces the raw 500. Schema left as-is.
- **Brave `goggles` is single-value here.** Brave's `goggles` is a *repeatable* query param; our base GET path csv-joins lists (`a,b`), which Brave treats as one (invalid) goggle and silently drops (no error). So `goggles` is modeled as a `string` (one goggle) rather than `csv`. Single-goggle — the common case — works.

## Evaluated but not added

Notes on search sources we looked at but chose not to integrate (yet), so the reasoning is on record.

### Amazon Bedrock AgentCore — Web Search Tool  *(evaluated 2026-07; held off)*
Amazon's fully-managed web search, backed by Amazon's own web index (tens of billions of docs, continuously refreshed, knowledge graph + semantic snippet extraction). Returns `title / url / snippet (text) / publishedDate`; `us-east-1` only. Docs: <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-target-connector-web-search-tool.html>.

**Why it doesn't fit the current contract** — every provider here is "public base URL + API-key (header/query) + one REST call → JSON." Bedrock differs on all three axes:
- **Endpoint:** not a public `/search`; you must **provision an AgentCore Gateway** in your own AWS account and add a Web Search target (`connectorId: "web-search"`), which yields a per-account, region-locked Gateway URL.
- **Auth:** AWS **SigV4 / IAM** (`bedrock-agentcore:InvokeGateway` on the Gateway ARN) or the Gateway's OAuth/JWT — not an API key.
- **Protocol:** **MCP** over HTTP — `tools/list` to discover, then `tools/call` (JSON-RPC), not a single plain request.

**Invocation shape** (for whenever we revisit):
- `tools/call` input: `query` (string, ≤200 chars, required), `maxResults` (int 1–25, default 10).
- Response (MCP): `content[0].text` is a JSON string → `{ id, results: [{ text, url, title, publishedDate }] }`. Maps cleanly to our result cards (`text` → snippet).

**What adding it would require** — a new `auth: sigv4` mode (pulls in `boto3`/`botocore`, the first heavyweight dep) or an OAuth-JWT flow; a custom `call()` that performs the MCP `tools/call` against the Gateway; and config for the Gateway URL/ARN + AWS creds/region. It also can't be verified without a provisioned Gateway. **Decision:** revisit only if we're actively on AWS and can stand up a Gateway; the response shape is a fine fit, but the integration is far heavier than a key-based REST provider.

**Two ways a third-party search API (like the providers here) plugs into Bedrock** — reference for "how would a REST search API work with Bedrock?":
- **Converse `tool_use` (client-side).** The model runs on Bedrock; the app calls the Bedrock Runtime **`Converse`** API — an HTTPS POST to `bedrock-runtime.<region>.amazonaws.com`, **SigV4-signed** (usually via an AWS SDK) — with a `toolConfig` declaring e.g. a `web_search` tool. The model returns a `toolUse` block; **the app's own code** makes an ordinary HTTPS call to the search API (plain API key) and returns the hits as a `toolResult` on the next turn. No AWS provisioning; the search call happens in the app (leaves AWS). This is the common, low-friction path.
- **AgentCore Gateway target (MCP).** Register the search API as a Gateway target (an OpenAPI spec or a Lambda); the Gateway exposes it as an MCP tool discoverable via `tools/list` — the same mechanism as the bundled `web-search` connector, just pointed at a third-party API. Requires standing up a Gateway.

Neither path is wired into this playground today; the providers here are plain REST endpoints that either of the above could call.
