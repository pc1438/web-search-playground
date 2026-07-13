# Search API Playground

A schema-driven playground to **try, inspect, and compare web-search APIs** side by
side — Exa, You.com, Perplexity, Parallel, Tavily, Brave, and SerpApi — from one UI.

Two modes:

- **Playground** — pick a provider tab, choose an endpoint, fill a request form
  generated from that endpoint's schema, and inspect the **raw response** (an
  interactive JSON tree + a copyable raw view, plus parsed result cards).
- **Compare** — configure any two comparable endpoints, ask one question, and see
  each endpoint's raw response head-to-head.

No SDKs, no per-provider UI code: every form and view is rendered generically from
a server-side catalog, so the request schema and the UI can't drift apart.

## Providers & endpoints

| Provider | Endpoints | Auth |
|---|---|---|
| **Exa** | `/search`, `/contents`, `/answer` | `x-api-key` |
| **You.com** | `/v1/search`, `/v1/contents`, `/v1/research`, `/v1/finance_research` | `X-API-Key` |
| **Perplexity** | `/search`, `/v1/agent` (BYOLLM, streaming) | Bearer |
| **Parallel** | `/v1/search` (`mode`: turbo / basic / advanced — turbo = Search Turbo), `/v1beta/search`, `/v1/tasks/runs` (Task API), `/v1beta/findall/entity-search` | `x-api-key` |
| **Tavily** | `/search`, `/extract`, `/map`, `/crawl` | Bearer |
| **Brave** | web / news / images / videos search, suggest, spellcheck, summarizer, local POIs & descriptions | `X-Subscription-Token` (GET) |
| **SerpApi** | `/search` across engines (Google, Bing, DuckDuckGo, YouTube, …) via an `engine` selector | `api_key` query param (GET) |

Any endpoint that accepts a query is selectable in **Compare**. Some Brave
endpoints require a higher plan tier; the playground surfaces the provider's own
error faithfully when they aren't subscribed.

## Quickstart

```bash
# 1. install deps (Python 3.10+)
pip install -r requirements.txt

# 2. add your keys
cp .env.example env.txt        # then edit env.txt — env.txt is git-ignored
#    (you only need keys for the providers you want to use)

# 3. run
python3 app/server.py --port 8088
#    open http://localhost:8088
```

## Deploy

The server is Python's built-in `http.server` (threaded, single-process) — great
for local use and small internal deployments, but **not hardened for the open
internet**. To run it beyond localhost:

- **Bind to localhost and put it behind a reverse proxy** (nginx, Caddy) that
  terminates **TLS** and adds **authentication** — the app has no auth of its own,
  and open access can burn your provider API credits.
- **Set `ALLOWED_ORIGIN`** to your domain (CORS) in `env.txt`.
- **Keep `env.txt` on the server only** — inject keys at runtime; never bake them
  into an image or commit them.
- Run under a process manager (systemd, pm2, Docker) so it restarts on failure.

```bash
python3 app/server.py --port 8088   # front this with your proxy
```

## Project layout

```
providers/     # one self-contained package per provider (the core of the app)
  base.py      # the contract: Param · Endpoint · Provider
  registry.py  # the one list of which providers exist
  <name>/      # __init__.py · provider.py · endpoints.py  (same 3 files each)
app/
  server.py      # thin HTTP: GET /api/providers · POST /api/call · POST /api/compare
  index.html     # tabs, form shell, Compare, About tab, all styles
  playground.js  # generic renderer — fetches the catalog, no per-provider code
comparison/    # perplexity_runner.py — the SSE Agent-API runner used by call()
```

Adding a provider is one folder + one line in `registry.py`; it then appears as a
tab, with endpoints and forms, automatically. See
[providers/index.md](providers/index.md) and the in-app **About** tab.

## Docs

- **[CLAUDE.md](CLAUDE.md)** — architecture, data flow, and conventions.
- **[providers/index.md](providers/index.md)** — per-provider notes.
- **[UX_STYLEGUIDE.md](UX_STYLEGUIDE.md)** — design tokens, components, and
  interaction patterns (shareable across apps).

## Notes

- **Keys never leave the server** — the frontend calls `/api/call`, which injects
  the key server-side. `env.txt` is git-ignored.
- **Latency** shown in the UI is full round-trip (browser → server → provider →
  back), not the provider's own processing time.
- **Deploying beyond localhost?** See [Deploy](#deploy) above.
