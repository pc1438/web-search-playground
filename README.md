# Search API Playground

A schema-driven playground to **try, inspect, and compare web-search APIs** side by
side — Exa, You.com, Perplexity, Parallel, Tavily, Brave, SerpApi, and Ceramic — from one UI.

Two modes:

- **Playground** — pick a provider tab, choose an endpoint, fill a request form
  generated from that endpoint's schema, and inspect the **raw response** (an
  interactive JSON tree + a copyable raw view, plus parsed result cards).
- **Compare** — configure up to **four** comparable endpoints (any side can be
  "None"), ask one question, and see each endpoint's raw response side by side.

No SDKs, no per-provider UI code: every form and view is rendered generically from
a server-side catalog, so the request schema and the UI can't drift apart.

## Providers & endpoints

| Provider | Endpoints | Auth |
|---|---|---|
| **Exa** | `/search`, `/contents`, `/answer` | `x-api-key` |
| **You.com** | `/v1/search`, `/v1/contents`, `/v1/research`, `/v1/finance_research` | `X-API-Key` |
| **Perplexity** | `/search`, `/v1/agent` (BYOLLM, streaming) | Bearer |
| **Parallel** | `/v1/search` (`mode`: turbo / fast / basic / advanced), `/v1beta/search`, `/v1/tasks/runs` (Task API), `/v1beta/findall/entity-search` | `x-api-key` |
| **Tavily** | `/search`, `/extract`, `/map`, `/crawl` | Bearer |
| **Brave** | web / news / images / videos search, suggest, spellcheck, summarizer, local POIs & descriptions | `X-Subscription-Token` (GET) |
| **SerpApi** | `/search` across engines (Google, Bing, DuckDuckGo, YouTube, …) via an `engine` selector | `api_key` query param (GET) |
| **Ceramic** | `/search` (web-scale keyword search built for LLMs) | Bearer |

Any endpoint that accepts a query is selectable in **Compare**. Some Brave
endpoints require a higher plan tier; the playground surfaces the provider's own
error faithfully when they aren't subscribed.

## API keys

Keys can be supplied two ways — they work together:

**Admin keys (server-configured)** — set in `env.txt` (local) or as environment
variables (hosted). These apply to everyone using the deployment and are never
exposed to the browser.

**User keys (browser-supplied)** — open the **⛭ Keys** tab in the UI, paste a
key for any provider, and click Save. Keys are stored in your browser's
`localStorage` and sent per-request in the request body. The server uses them only
for that call and never stores them. If an admin key is configured for the same
provider, it takes precedence.

This means you can run the playground with no server-side keys at all and let each
user supply their own, or pre-configure shared keys for providers your team uses.

## Quickstart (local)

```bash
# 1. install deps (Python 3.10+)
pip install -r requirements.txt

# 2. add your keys (only the providers you want to use)
cp .env.example env.txt   # env.txt is git-ignored — edit it, never commit it
```

`env.txt` format:
```
EXA_API_KEY=your-key-here
YDC_API_KEY=your-key-here
PERPLEXITY_API_KEY=your-key-here
PARALLEL_API_KEY=your-key-here
TAVILY_API_KEY=your-key-here
BRAVE_API_KEY=your-key-here
SERPAPI_API_KEY=your-key-here
CERAMIC_API_KEY=your-key-here
```

```bash
# 3. run
python3 app/server.py
#    open http://localhost:8088
```

Alternatively, skip `env.txt` entirely and supply keys per-session via the **⛭ Keys**
tab in the UI.

## Deploy

### Local / internal network

For personal or team use on a trusted network, the Quickstart above is sufficient.
To tighten security when others on the network can reach the port:

```bash
BIND_HOST=127.0.0.1 python3 app/server.py   # localhost only; put a proxy in front
```

Or set `BIND_HOST=127.0.0.1` in `env.txt` and run normally. Then front it with
nginx or Caddy that terminates TLS and adds auth — the app has no auth of its own.

### Railway (and similar PaaS platforms)

Railway routes traffic to your container from outside, so the server must listen on
all interfaces (the default). Set your keys as **Railway environment variables** —
not in a file.

1. Connect the repo in Railway and create a new service.
2. Add your provider keys under **Variables** in the Railway dashboard (same names
   as in `env.txt`, e.g. `EXA_API_KEY`, `YDC_API_KEY`, …).
3. Optionally set `ALLOWED_ORIGIN` to your Railway public URL (CORS):
   ```
   ALLOWED_ORIGIN=https://your-app.up.railway.app
   ```
4. Railway sets `PORT` automatically — the server reads it:
   ```bash
   python3 app/server.py --port $PORT
   ```
   Add that as the **Start command** in Railway settings.

Users who need a provider key not configured in Railway can supply it themselves
via the **⛭ Keys** tab — it's stored in their browser and sent per-request.

### General hardening (any public deployment)

- **Add authentication at the proxy** — open access lets anyone burn your API credits.
- **Set `ALLOWED_ORIGIN`** to your domain to restrict cross-origin requests.
- **Never commit `env.txt`** — it's git-ignored; inject keys at runtime only.
- **Content-Security-Policy** at the proxy is a worthwhile XSS backstop (`img-src *`
  is required for result-card favicons):

  ```
  Content-Security-Policy:
    default-src 'self';
    script-src 'self' 'unsafe-inline';
    style-src  'self' 'unsafe-inline';
    img-src    * data:;
    connect-src 'self';
    object-src 'none';
    base-uri 'self';
    frame-ancestors 'none'
  ```

## Project layout

```
providers/     # one self-contained package per provider (the core of the app)
  base.py      # the contract: Param · Endpoint · Provider
  registry.py  # the one list of which providers exist
  <name>/      # __init__.py · provider.py · endpoints.py  (same 3 files each)
app/
  server.py      # thin HTTP: GET /api/providers · POST /api/call · POST /api/compare
  index.html     # tabs, form shell, Compare, About tab, ⛭ Keys tab, all styles
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

- **User-supplied keys** are stored in the browser (localStorage) and sent
  per-request in the request body — they are never stored on the server.
  Admin keys (env vars / `env.txt`) always take precedence and are never
  exposed to the browser.
- **Latency** shown in the UI is full round-trip (browser → server → provider →
  back), not the provider's own processing time.
