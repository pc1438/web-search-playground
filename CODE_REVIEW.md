# Code Review — competitor_search (Search API Playground)

**Reviewer:** Senior staff engineer · full-codebase review
**Scope:** whole repo (~4.3k LoC source): Python `http.server` backend, schema-driven provider layer, vanilla-JS frontend, docs.
**Method:** backend spine, provider contract, and the frontend renderer read line-by-line directly; the inline-JS in `index.html` and the seven provider modules covered by focused parallel passes. Every High-severity item verified against source (grep / config checks) before inclusion.

> **Status:** Complete. The per-provider endpoint-schema pass is **§7** (below). No blockers found there; paths/methods/auth placement are correct for every provider, and the key is never logged or echoed.

---

## Verdict

This is **well-designed, disciplined code**. The schema-driven architecture is the star: providers are declarative packages, the request schema has a single server-side source of truth, and the frontend renders generically from the catalog — so the UI and the request contract genuinely can't drift. Security instincts are good throughout (keys stay server-side, the cURL snippet shows the env-var *name* not the value, the GET query-param key is never echoed, the static-file handler is a strict allowlist so no path traversal, request bodies are size-capped).

The issues are concentrated and mostly **low-severity**, and they cluster around one theme: **the repo was refactored from a narrow "You.com vs Perplexity" comparison tool into a generic multi-provider playground, and vestigial debris from the old identity was left behind** — in `server.py`'s docstrings/banner, the About tab's architecture diagram, ~150 lines of CSS, some dead JS, and the Perplexity runner. Plus one real defense-in-depth gap: no CSP on an app whose whole job is rendering third-party JSON.

| # | Severity | Finding | Area |
|---|----------|---------|------|
| 1 | 🟠 Major | No Content-Security-Policy on an app that renders arbitrary third-party JSON | Security |
| 2 | 🟠 Major | Stale identity/architecture docs after the refactor (violates the repo's own self-documenting rule) | Cohesion / docs |
| 3 | 🟡 Minor | `/api/call` doesn't catch generic exceptions → Perplexity agent errors dead-end (unlike `/api/compare`) | Correctness / robustness |
| 4 | 🟡 Minor | No CSRF protection → cross-site POST can burn provider credits | Security |
| 5 | 🟡 Minor | Perplexity agent path ignores the caller's `timeout`; returned `model` is hardcoded | Correctness |
| 6 | 🟡 Minor | Compare loading timers leak on Stop/abort | Correctness / frontend |
| 7 | 🟡 Minor | Refactor debris: vestigial code in `perplexity_runner.py`; duplicate URL sanitizer | Cohesion |
| 8 | 🟡 Minor | Dead code: `MAX_QUERY_LENGTH`, ~40 lines dead JS, ~150 lines dead CSS | Dead code |
| — | ✅ | Notable strengths (see end) | — |

---

## 🟠 Major

### 1. No Content-Security-Policy
`app/index.html` `<head>` has no CSP `<meta>` tag. This app's entire purpose is to render arbitrary JSON from seven third-party search APIs. Today the JS is disciplined (all dynamic data goes through `el()`/`textContent`, URLs through `safe()`), so there's no *active* XSS — but a single future `innerHTML = body.something` regression becomes instant XSS with nothing to contain it. A CSP is the defense-in-depth backstop for exactly this threat model.
**Fix:** Add a CSP meta tag, e.g.
`default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src * data:; connect-src 'self'`
(`img-src *` is needed because result-card favicons load remote images — tighten if acceptable; the app also loads Google Fonts, hence the font/style allowances.)

### 2. Stale identity & architecture docs (self-documenting rule violated)
The app was refactored from a 2-way "You.com vs Perplexity" comparison into a generic 2–4-provider playground, but several canonical descriptions still describe the old design — and `CLAUDE.md` / the About tab explicitly assert a "self-documenting" rule ("If this page looks wrong, the code changed without its docs — that's a bug", `index.html:821`).
- `app/server.py:2` module docstring: "Web server for the You.com vs. Perplexity competitor comparison UI."
- `app/server.py:5`: "POST /api/compare — SSE stream comparing You.com Research API vs. Perplexity SaC" (actual: generic 2–4 side compare).
- `app/server.py:307`: startup banner prints "Competitor Search — You.com vs. Perplexity".
- `app/index.html:736`: "configure *any two comparable* endpoints" — actual is **up to four**.
- `app/index.html:802-806` (About data-flow box): `POST /api/compare {left, right}` → "left.call() + right.call()" → "two raw responses, side by side". Actual contract (`server.py:229-286`, `index.html:1061`) is `{sides:[…]}` (2–4) streamed back over **SSE** — the diagram has both the request shape and the transport wrong.
- Default port is `8081` in code (`server.py:8,293`, and the class-attr `ALLOWED_ORIGIN` fallback at `:81`) vs `8088` everywhere in `README.md`, `CLAUDE.md`, and `.claude/launch.json`.
**Fix:** Update `server.py`'s docstring/banner to the playground identity; update the About data-flow box to `{sides:[…]}` (2–4) + "streamed over SSE, one pane per side"; reconcile the default port to 8088 (or make the docs say 8081).

---

## 🟡 Minor

### 3. `/api/call` doesn't catch generic exceptions (Perplexity agent errors dead-end)
`_handle_call` (`server.py:211-221`) catches `ProviderKeyMissing`, `requests.Timeout`, and `requests.RequestException` — but not a bare `Exception`. `PerplexityProvider.call()`'s agent path delegates to `run_perplexity_sac`, which raises **`RuntimeError`** on a bad key / HTTP error / stream interruption / its own timeout. That `RuntimeError` is uncaught → propagates out of `do_POST` → the client gets a connection reset / non-JSON 500 and the playground shows "Server returned … (non-JSON)". `/api/compare` handles this correctly (`server.py:271`, `except Exception`), so the two paths are inconsistent on a headline endpoint (Perplexity Agent).
**Fix:** Add a trailing `except Exception as e: self._send_json(502, {"error": f"{provider_id}/{endpoint} failed: {e}"})` to `_handle_call`, mirroring the compare handler.

### 4. No CSRF protection → cross-site POST can burn API credits
There's no auth (documented — deploy behind a proxy) and no CSRF token. CORS `Access-Control-Allow-Origin` only gates *reading* the response, not *sending* the request: a page the user visits can issue a CORS-"simple" `POST /api/call` (e.g. a form with `text/plain`, no preflight) and the server will parse the JSON body regardless of `Content-Type` and fire a real, paid provider call — the attacker can't read the result, but the credits are spent. This is consistent with the README's "open access can burn your provider API credits" warning, so it's partly acknowledged, but worth an explicit control.
**Fix:** Require `Content-Type: application/json` on the POST handlers (forces a preflight, which CORS then blocks cross-origin), and/or check the `Origin`/`Referer` header against `ALLOWED_ORIGIN` for state-changing requests.

### 5. Perplexity agent path ignores `timeout`; returned `model` is hardcoded
- `PerplexityProvider.call()` (`providers/perplexity/provider.py:37`) calls `run_perplexity_sac(...)` **without** forwarding `timeout`, so the runner always uses its hardcoded `AGENT_TIMEOUT=300` (`perplexity_runner.py:47`). A playground `/api/call` (which passes `PROXY_TIMEOUT=120`) can therefore hang up to 300s despite the intended 120s cap. **Fix:** thread `timeout` through `run_perplexity_sac`.
- `run_perplexity_sac` sets `stats["model"] = PERPLEXITY_SAC_CONFIG["model"]` (`:96`) even when the caller overrides the model (`provider.py:37` passes `params.get("model")`). The response then reports the wrong model. **Fix:** `stats["model"] = model or PERPLEXITY_SAC_CONFIG["model"]`.

### 6. Compare loading timers leak on Stop/abort
`index.html` — each compare pane's `startLoading` returns a 100ms `setInterval` stored in `_cmpLoad[side]`, cleared only inside the SSE `result` handler (`~:1102`). If the user hits **Stop** (`stopCompare` → `_cmpController.abort()`), any side that hasn't yet produced a `result` keeps its 10Hz timer running forever, updating detached DOM; repeated aborts accumulate them.
**Fix:** In `runCompare`, after the stream ends/aborts (a `finally`), stop all remaining timers: `Object.values(_cmpLoad).forEach(l => l && l.stop())`.

### 7. Refactor debris (cohesion)
- `comparison/perplexity_runner.py:40-41` loads env from a **nonexistent** `../grounding/` sibling directory (`grounding/env.txt`, `grounding/.env`) — leftover from the project this runner was ported from. The `PERPLEXITY_SAC_CONFIG`, `sac_cost_per_call`, `stats["path"]="…SAC…"`, and "SAC comparison module" docstring naming are likewise vestigial ("SAC" is from the old tool). Harmless but confusing. **Fix:** drop the `grounding/` `load_dotenv` calls and rename the SAC-era identifiers to the playground's vocabulary.
- `app/index.html:890` `safeUrl` is a verbatim duplicate of `playground.js`'s `safe()` (`:761`) — two URL sanitizers that can diverge. It's also dead (see §8). **Fix:** delete it; if index.html ever needs it, import/reuse the one in `playground.js`.

### 8. Dead code
- `app/server.py:80` — `MAX_QUERY_LENGTH = 2_000` defined, never referenced.
- `app/index.html:890-926` — `safeUrl`, `escapeHtml`, `renderMarkdown` are unreferenced (grep: `escapeHtml` is called only by the dead `renderMarkdown`; the other two have zero call sites). `renderMarkdown` builds an HTML string from provider text — a "loaded gun" next to a codebase whose safety rests on *not* doing that; delete it (or, if markdown is planned, keep it in one place behind the CSP from §1).
- `app/index.html` — ~150 lines of dead CSS from the removed cost/comparison UI: `.savings-bar`, `.info-btn`, `#codeInfoOverlay`/`#codeInfoModal`, `#costPopup`, `.glossary` (verified: **0** matching HTML elements and **0** JS references each; the live cost drill-down uses `.pg-pop`). Remove them.
- **Nit:** `playground.js:750` adds class `pg-tree-pop`, which has no CSS rule (harmless; the element still gets `.pg-tree`).
- **Nit:** `index.html` SSE reader concatenates multiple `data:` lines without a `\n` separator (spec says join with `\n`) — latent; works only because the server emits single-line JSON per event.

---

## 7. Provider modules (`providers/*/`)

No blockers — every provider's path, method, and auth placement match its real API; the only path interpolation (Parallel's `run_id`) comes from the API response, not user input; and the key is never logged or echoed (base `call()` logs `params` *before* injecting the query-param key). All `compare_query_field`/`compare_params` reference real params, and every `ENDPOINT_ORDER` matches its endpoints. The reuse patterns (`serpapi` engine→param remap, Exa's `_content_fields()`, Brave's `_common()`, You.com's `_source_control()`, Parallel's async-Task `call()`) are sound.

**Correctness**
- 🟡 **Brave `goggles` is `csv` but Brave expects a *repeatable* query param** — `providers/brave/endpoints.py:48` (web), `:62` (news). The base GET path comma-joins list values (`base.py:161`), so two goggles are sent as `goggles=url1,url2`, which Brave reads as one malformed value. Single-goggle (the common case) works, hence easy to miss. (`result_filter` on the same endpoints is correctly `csv` — Brave documents *it* as comma-separated.) *Verify against Brave's current Goggles docs;* fix by limiting `goggles` to one value or teaching the base GET path to emit repeated keys for flagged params.
- 🟡 **Perplexity `/search` may carry chat-only params** — `providers/perplexity/endpoints.py:22,25,28`: `search_context_size`, `max_tokens`, `search_language_filter` read like Sonar *chat-completions* options (`web_search_options.*`) rather than fields of the standalone Search API. If so they're ignored/rejected. *Low confidence — verify against the Search API reference.*
- Nit — **You.com `/v1/search` defaults to POST** (`youdotcom/endpoints.py:38`) while the docstring hedges "GET/POST"; if the endpoint is GET-only this 405s. *Verify.*

**Cohesion / docs**
- 🟡 **Parallel docstring contradicts the code on `mode`** — `parallel/endpoints.py:6-7` says `mode` is "deliberately NOT exposed," but `SEARCH` exposes it (`:23,29`) and `index.md:14` documents it as a Compare dimension. Stale comment that could get `mode` wrongly deleted. Fix the docstring.
- 🟡 **You.com Finance uses the Research docs URL** — `youdotcom/endpoints.py:76` sets `docs_url={DOCS}/research/v1-research`, identical to `RESEARCH` (`:66`), so the Finance tab's "Docs" link goes to the wrong page. Point it at the finance_research reference.
- 🟡 **`"json"` param type is undocumented in the base contract** — `base.py:44-46` lists types as `string | text | int | bool | enum | csv | date | group`, but `"json"` is used in 6 places (exa/youdotcom/parallel). It *is* handled by `playground.js` (`case "json"`), so this is a doc gap, not a render bug — add `json` to the `Param` docstring's type list.

**Dead config / nits**
- 🟡 **Parallel `entity-search` sets `compare_params=["entity_type"]` but has no `compare_query_field`** (`parallel/endpoints.py:82`), so it's never comparable (`comparable=False`) and the `compare_params` is dead. `index.md:18` confirms FindAll is playground-only. Drop the `compare_params`.
- Nit — Perplexity `agent` fans Compare across `tools` (a multi-select `csv`), which is semantically odd for the single-pick `compare_params` mechanism (each cell gets one tool). Confirm intended.
- Nit — Missing constraints: Exa `/contents` marks neither `urls` nor `ids` required though Exa needs at least one (not schema-expressible, but no help text signals it); Perplexity `max_tokens*` have no `min`/`max` despite help citing limits.
- Not-an-issue (noted for completeness): `SAFESEARCH` and `include_domains`/`exclude_domains` recur across providers, but field names/help differ per each real API (camelCase for Exa, snake_case elsewhere), so keeping them provider-local is the right call — not worth forcing a shared abstraction.

---

## ✅ Notable strengths (keep doing this)
- **Schema-driven, single-source-of-truth architecture** — providers are declarative (`base.py` `Param`/`Endpoint`/`Provider`); `catalog()` serializes the exact shape the frontend renders, so UI and request contract can't drift. Adding a provider is one folder + one registry line. This is genuinely good design.
- **Key hygiene** — keys are injected server-side and never sent to the browser; the cURL snippet uses the env-var *name* (`$EXA_API_KEY`); the SerpApi query-param key is added at request time and never echoed in the returned `request`.
- **Frontend XSS discipline** — `el()` renders via `textContent`; every link href passes through `safe()` (non-http(s) schemes → `#`); `innerHTML` is only ever assigned static templates, with dynamic data set separately via `textContent`. Compare reuses the playground renderer rather than reimplementing it.
- **Backend hardening basics** — `do_GET` is a strict path allowlist so `SimpleHTTPRequestHandler`'s default file-serving/traversal is never reached; request bodies are size-capped (`MAX_BODY_SIZE`); providers return the raw upstream status+body even on 4xx/5xx so errors are shown faithfully instead of dead-ending.
- **Secrets hygiene** — `env.txt` and `logs/` are gitignored and untracked; `.env.example` lists exactly the seven provider keys and is accurate.
