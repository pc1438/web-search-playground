// playground.js — schema-driven API playground engine (generic renderer).
//
// This file contains NO provider-specific schemas. On load it fetches the
// provider catalog from GET /api/providers (served from the server-side
// `providers/` packages — the single source of truth) and renders a
// request-builder form from the selected endpoint's schema. Assembled requests
// go through POST /api/call, which dispatches to the provider (key injected
// server-side).
//
// To add a provider or endpoint, edit `providers/` on the server — nothing here
// changes. See the About tab for the full architecture.

// Populated from GET /api/providers at init. Shape per provider:
//   { label, baseUrl, authHeader, keyEnv, endpointOrder, endpoints: { id: {label, method, path, categoryCompare, schema:[param]} } }
let PROVIDERS = {};

// ─── DOM helpers ─────────────────────────────────────────────────────────────
function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k === "html") node.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined) node.setAttribute(k, v);
  }
  for (const c of [].concat(children)) if (c) node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  return node;
}

// ─── Help tooltips ───────────────────────────────────────────────────────────
// A single floating bubble (appended to <body>, so the form's overflow can't clip
// it). Shown on hover of any `.pg-info` icon, and toggled on click for touch.
let _pgTip = null;
function pgTipEl() {
  if (!_pgTip) { _pgTip = el("div", { class: "pg-tooltip" }); document.body.appendChild(_pgTip); }
  return _pgTip;
}
function pgShowTip(icon) {
  const text = icon.getAttribute("data-tip");
  if (!text) return;
  const tip = pgTipEl();
  tip.textContent = text;
  tip.classList.add("show");
  const r = icon.getBoundingClientRect(), tr = tip.getBoundingClientRect();
  let left = Math.max(8, Math.min(r.left + r.width / 2 - tr.width / 2, window.innerWidth - tr.width - 8));
  let top = r.top - tr.height - 8;
  if (top < 8) top = r.bottom + 8;
  tip.style.left = left + "px";
  tip.style.top = top + "px";
}
function pgHideTip() { if (_pgTip) _pgTip.classList.remove("show"); }
document.addEventListener("mouseover", e => { const i = e.target.closest?.(".pg-info"); if (i) pgShowTip(i); });
document.addEventListener("mouseout", e => { const i = e.target.closest?.(".pg-info"); if (i) pgHideTip(); });
document.addEventListener("click", e => {
  const i = e.target.closest?.(".pg-info");
  if (i) { e.preventDefault(); e.stopPropagation(); _pgTip?.classList.contains("show") ? pgHideTip() : pgShowTip(i); }
  else pgHideTip();
});

// ─── Field renderer ──────────────────────────────────────────────────────────
// Returns { el, read }. read() returns the value, or undefined to omit the param.
function renderParam(def, depth = 0) {
  if (def.type === "group") return renderGroup(def, depth);

  const row = el("div", { class: "pg-field" });
  const label = el("label", { class: "pg-label", text: def.label || def.name });
  if (def.required) label.appendChild(el("span", { class: "pg-req", text: " *" }));
  if (def.help) label.appendChild(el("span", { class: "pg-info", "data-tip": def.help, text: "i" }));
  row.appendChild(label);

  let control, read;

  switch (def.type) {
    case "text": {
      control = el("textarea", { class: "pg-input pg-textarea", rows: "2", placeholder: def.placeholder || "" });
      read = () => control.value.trim() || undefined;
      break;
    }
    case "string": {
      control = el("input", { type: "text", class: "pg-input", placeholder: def.placeholder || "" });
      if (def.maxlen) control.setAttribute("maxlength", def.maxlen);
      read = () => control.value.trim() || undefined;
      break;
    }
    case "int": {
      control = el("input", { type: "number", class: "pg-input pg-num", placeholder: def.placeholder || "" });
      if (def.min !== undefined) control.setAttribute("min", def.min);
      if (def.max !== undefined) control.setAttribute("max", def.max);
      read = () => { const v = control.value.trim(); return v === "" ? undefined : Number(v); };
      break;
    }
    case "bool": {
      control = el("input", { type: "checkbox", class: "pg-switch-input" });
      row.appendChild(el("label", { class: "pg-switch" }, [control, el("span", { class: "pg-switch-track" })]));
      read = () => (control.checked ? true : undefined);
      break;
    }
    case "enum": {
      control = el("select", { class: "pg-input pg-select" });
      control.appendChild(el("option", { value: "", text: "— none —" }));
      for (const v of def.values) control.appendChild(el("option", { value: v, text: v }));
      read = () => control.value || undefined;
      break;
    }
    case "csv": {
      control = el("input", { type: "text", class: "pg-input", placeholder: def.placeholder || "comma, separated" });
      read = () => {
        const arr = control.value.split(",").map(s => s.trim()).filter(Boolean);
        return arr.length ? arr : undefined;
      };
      break;
    }
    case "date": {
      control = el("input", { type: "date", class: "pg-input pg-date" });
      read = () => { const v = control.value; return v ? new Date(v + "T00:00:00Z").toISOString() : undefined; };
      break;
    }
    case "json": {
      control = el("textarea", { class: "pg-input pg-textarea", rows: "3", placeholder: def.placeholder || '{ "type": "text" }' });
      read = () => { const v = control.value.trim(); if (!v) return undefined; try { return JSON.parse(v); } catch { return v; } };
      break;
    }
    default:
      control = el("input", { type: "text", class: "pg-input" });
      read = () => control.value.trim() || undefined;
  }

  if (def.type !== "bool") row.appendChild(control);
  if (def.deprecated) row.classList.add("pg-deprecated");
  // Roomy fields (multi-line / list) span the full row; short scalars pair up 2-per-row.
  if (["text", "csv", "json"].includes(def.type)) row.classList.add("pg-full");
  return { el: row, read };
}

function renderGroup(def, depth) {
  const box = el("div", { class: "pg-group pg-full" + (def.deprecated ? " pg-deprecated" : "") });
  const head = el("div", { class: "pg-group-head" });
  let enabled = { checked: true };

  if (def.optional) {
    enabled = el("input", { type: "checkbox", class: "pg-check" });
    head.appendChild(el("label", { class: "pg-group-toggle" }, [
      enabled, el("span", { text: " " + (def.label || def.name) }),
    ]));
  } else {
    head.appendChild(el("span", { class: "pg-group-title", text: def.label || def.name }));
  }
  if (def.help) head.appendChild(el("span", { class: "pg-info", "data-tip": def.help, text: "i" }));
  box.appendChild(head);

  const body = el("div", { class: "pg-group-body" });
  const children = def.fields.map(f => {
    const r = renderParam(f, depth + 1);
    body.appendChild(r.el);
    return { name: f.name, read: r.read };
  });
  box.appendChild(body);

  const syncEnabled = () => { body.style.display = (def.optional && !enabled.checked) ? "none" : ""; };
  if (def.optional) { enabled.addEventListener("change", syncEnabled); syncEnabled(); }

  const read = () => {
    if (def.optional && !enabled.checked) return undefined;
    const obj = {};
    for (const c of children) { const v = c.read(); if (v !== undefined) obj[c.name] = v; }
    if (def.booleanShorthand && Object.keys(obj).length === 0) return true;
    return obj;
  };
  return { el: box, read };
}

// ─── Playground state ──────────────────────────────────────────────────────
const pg = { provider: null, endpoint: null, readers: [], providerOrder: [] };

// Render an endpoint's schema into `container`: primary fields inline, params
// flagged `advanced` tucked into a collapsed "Advanced options" group (Parallel/
// Exa-style). `skip` (a Set of param names) omits fields — Compare uses it to
// drop the query field, which it drives from its shared query box. Returns the
// readers array. Shared by the playground form and the Compare tab.
function renderSchemaInto(container, schema, skip) {
  skip = skip || new Set();
  const readers = [];
  const addReader = (def, parent) => {
    const r = renderParam(def);
    parent.appendChild(r.el);
    readers.push({ name: def.name, read: r.read, el: r.el, required: !!def.required });
  };
  const fields = schema.filter(d => !skip.has(d.name));
  const advanced = fields.filter(d => d.advanced);
  fields.filter(d => !d.advanced).forEach(def => addReader(def, container));
  if (advanced.length) {
    const box = el("div", { class: "pg-group pg-full pg-collapsible pg-collapsed" });
    const head = el("div", { class: "pg-group-head" });
    head.appendChild(el("span", { class: "pg-group-title", text: "Advanced options" }));
    head.appendChild(el("span", { class: "pg-adv-count", text: advanced.length + "" }));
    head.appendChild(el("span", { class: "pg-chevron" }));
    head.addEventListener("click", () => box.classList.toggle("pg-collapsed"));
    box.appendChild(head);
    const body = el("div", { class: "pg-group-body" });
    advanced.forEach(def => addReader(def, body));
    box.appendChild(body);
    container.appendChild(box);
  }
  return readers;
}

function buildForm() {
  const prov = PROVIDERS[pg.provider];
  const ep = prov.endpoints[pg.endpoint];
  const form = document.getElementById("pgForm");
  form.innerHTML = "";
  pg.readers = renderSchemaInto(form, ep.schema);

  // Compare block — endpoints can offer several fan-out fields (compareParams);
  // the user picks which one (Exa /search → category or type), then its values.
  const cmpWrap = document.getElementById("pgCompareWrap");
  const toggle = document.getElementById("pgCompareToggle");
  const cparams = ep.compareParams || [];
  if (cparams.length) {
    cmpWrap.style.display = "";
    pg.compareParam = cparams[0];
    buildCompareOn(ep);
    buildCompareChecks(ep, pg.compareParam);
    document.getElementById("pgCompareBody").style.display = toggle.checked ? "" : "none";
  } else {
    cmpWrap.style.display = "none";
    toggle.checked = false;
  }

  // Deprecated fields are hidden unless the user opts in. Show the toggle only
  // when this endpoint actually has deprecated fields.
  const depToggle = document.getElementById("pgDepToggle");
  const depCount = countDeprecated(ep.schema);
  depToggle.style.display = depCount ? "" : "none";
  if (depCount) depToggle.querySelector(".pg-dep-count").textContent = "(" + depCount + ")";
  form.classList.toggle("hide-deprecated", !document.getElementById("pgDepCheck").checked);

  updateCompareFieldState();
  updateEndpointMeta();
  updateRequestPreview();
}

// Total count of deprecated fields anywhere in the schema (recursive). Some may
// be nested inside optional groups (e.g. Exa /search's `contents`/`highlights`),
// so they only become visible once the user enables that group — the count is
// the honest total regardless.
function countDeprecated(schema) {
  return (schema || []).reduce((n, p) => n + (p.deprecated ? 1 : 0) + countDeprecated(p.fields), 0);
}

// In compare mode the fan-out field is driven by the compare panel, not the
// form — dim it (and it's excluded from required-field validation) so that's clear.
function updateCompareFieldState() {
  const compareOn = document.getElementById("pgCompareToggle").checked &&
                    document.getElementById("pgCompareWrap").style.display !== "none";
  (pg.readers || []).forEach(r => r.el && r.el.classList.toggle("pg-overridden", compareOn && r.name === pg.compareParam));
}

function pluralize(param) {
  const w = (param || "").replace(/_/g, " ");
  if (w.endsWith("s")) return w;                               // already plural (e.g. "tools")
  return w.endsWith("y") ? w.slice(0, -1) + "ies" : w + "s";   // category→categories, entity type→entity types
}

// "Compare on:" selector — pills to choose which field to fan out over.
// Hidden (shown as a label) when the endpoint offers only one field.
function buildCompareOn(ep) {
  const wrap = document.getElementById("pgCompareOn");
  wrap.innerHTML = "";
  const params = ep.compareParams || [];
  if (params.length <= 1) {
    wrap.appendChild(el("span", { class: "pg-compare-on-label", text: "Comparing across " + pluralize(params[0]) }));
    return;
  }
  wrap.appendChild(el("span", { class: "pg-compare-on-label", text: "Compare on:" }));
  for (const p of params) {
    wrap.appendChild(el("button", {
      type: "button", class: "pg-onpill" + (p === pg.compareParam ? " active" : ""), text: p,
      onclick: () => { pg.compareParam = p; buildCompareOn(ep); buildCompareChecks(ep, p); updateCompareFieldState(); updateRequestPreview(); },
    }));
  }
}

// (Re)build the value checkboxes for the chosen compare field. "(none)" only
// when the param is optional. Default-check the first few values.
function buildCompareChecks(ep, paramName) {
  const wrap = document.getElementById("pgCatChecks");
  wrap.innerHTML = "";
  const param = (ep.schema || []).find(p => p.name === paramName) || {};
  const opts = (param.values || []).slice();
  if (!param.required) opts.push("__none__");
  opts.forEach((c, i) => {
    const cb = el("input", { type: "checkbox", class: "pg-cat-cb", value: c });
    // Default selection: for Exa's `category` fan-out, pre-pick company + people
    // (the two entity-shaped categories); otherwise pre-pick the first few values.
    const on = c !== "__none__" && (paramName === "category" ? (c === "company" || c === "people") : i < 3);
    if (on) cb.checked = true;
    wrap.appendChild(el("label", { class: "pg-cat" }, [cb, el("span", { text: " " + (c === "__none__" ? "(none)" : c) })]));
  });
}

function updateEndpointMeta() {
  const ep = PROVIDERS[pg.provider].endpoints[pg.endpoint];
  // The dropdown already shows METHOD + path, so here we show only the human
  // description (the label text after the "METHOD /path — " prefix).
  document.getElementById("pgEndpointMeta").textContent = (ep.label || "").split(" — ").slice(1).join(" — ");
  const link = document.getElementById("pgDocsLink");
  if (ep.docsUrl) { link.href = ep.docsUrl; link.style.display = ""; }
  else { link.style.display = "none"; }
}

function readParams() {
  const params = {};
  for (const r of pg.readers) { const v = r.read(); if (v !== undefined) params[r.name] = v; }
  return params;
}

// ─── Send ────────────────────────────────────────────────────────────────
async function pgCall(params) {
  const t0 = performance.now();
  const resp = await fetch("/api/call", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider: pg.provider, endpoint: pg.endpoint, params }),
  });
  const clientMs = Math.round(performance.now() - t0);
  let data;
  try { data = await resp.json(); }
  catch { data = { error: `Server returned ${resp.status} (non-JSON)` }; }
  return { httpOk: resp.ok, clientMs, data };
}

// Live-render the request body + cURL from the current form + compare state.
// Called on every form change (and on Send). Non-compare → one runnable request.
// Compare → N concrete, runnable requests (one per selected value), so anything
// shown can be copy-pasted and actually works.
function updateRequestPreview() {
  if (!pg.provider) return;
  (pg.readers || []).forEach(r => r.el && r.el.classList.remove("pg-invalid"));  // clear required-field errors on edit
  const ep = PROVIDERS[pg.provider].endpoints[pg.endpoint];
  const base = readParams();
  const preEl = document.getElementById("pgRequestPreview");
  const curlEl = document.getElementById("pgCurl");
  const compareOn = document.getElementById("pgCompareToggle").checked && (ep.compareParams || []).length > 0;

  if (!compareOn) {
    preEl.textContent = JSON.stringify(base, null, 2);
    curlEl.textContent = toCurl(base);
    return;
  }

  const field = pg.compareParam;
  const bodies = Array.from(document.querySelectorAll(".pg-cat-cb:checked")).map(c => {
    const p = { ...base };
    if (c.value === "__none__") delete p[field]; else p[field] = c.value;
    return { label: c.value === "__none__" ? "(omitted)" : c.value, p };
  });
  if (!bodies.length) {
    preEl.textContent = JSON.stringify(base, null, 2);
    curlEl.textContent = "# select at least one " + field + " value to compare";
    return;
  }
  // Body preview: one concrete body per selected value (labeled), matching the cURLs
  preEl.textContent = `// Compare mode — ${bodies.length} request bod${bodies.length > 1 ? "ies" : "y"}, one per ${field}:\n\n` +
    bodies.map(b => `// ${field} = ${b.label}\n` + JSON.stringify(b.p, null, 2)).join("\n\n");
  // cURL: one real, runnable command per selected value
  curlEl.textContent = `# Compare mode — ${bodies.length} request(s), one per ${field}:\n\n` +
    bodies.map(b => `# ${field} = ${b.label}\n` + toCurl(b.p)).join("\n\n");
}

async function pgSend() {
  const base = readParams();
  const btn = document.getElementById("pgSendBtn");
  const results = document.getElementById("pgResults");
  const compareParam = pg.compareParam;   // the field the user chose to fan out over
  const compareOn = document.getElementById("pgCompareToggle").checked &&
                    document.getElementById("pgCompareWrap").style.display !== "none";

  updateRequestPreview();

  // Client-side guard: don't fire if a required field is empty (avoids opaque
  // upstream 400s like "expected string, received undefined at query").
  // In compare mode the fan-out field is supplied per-pane, so don't require it.
  pg.readers.forEach(r => r.el && r.el.classList.remove("pg-invalid"));
  const missing = pg.readers.filter(r => r.required && !(compareOn && r.name === compareParam)
                                       && (base[r.name] === undefined || base[r.name] === ""));
  if (missing.length) {
    missing.forEach(r => r.el && r.el.classList.add("pg-invalid"));
    results.className = "pg-results";
    results.innerHTML = "";
    results.appendChild(el("div", { class: "pg-error",
      text: "Fill required field" + (missing.length > 1 ? "s" : "") + ": " + missing.map(r => r.name).join(", ") }));
    const ctrl = missing[0].el && missing[0].el.querySelector("input, textarea, select");
    if (ctrl) ctrl.focus();
    return;
  }

  btn.disabled = true; btn.textContent = "Sending…";
  results.innerHTML = "";

  try {
    if (compareOn) {
      const vals = Array.from(document.querySelectorAll(".pg-cat-cb:checked")).map(c => c.value);
      if (!vals.length) { results.appendChild(el("div", { class: "pg-empty", text: "Select at least one value to compare." })); return; }
      results.className = "pg-results pg-grid";
      const panes = vals.map(v => { const p = makePane(v === "__none__" ? "(none)" : v); results.appendChild(p.el); return { v, ...p }; });
      await Promise.all(panes.map(async pane => {
        const params = { ...base };
        if (pane.v === "__none__") delete params[compareParam]; else params[compareParam] = pane.v;
        try { const r = await pgCall(params); pane.load.stop(); renderResponse(pane.body, r); }
        catch (e) { pane.load.stop(); pane.body.innerHTML = ""; pane.body.appendChild(el("div", { class: "pg-error", text: String(e) })); }
      }));
    } else {
      results.className = "pg-results";
      const pane = makePane(null);
      results.appendChild(pane.el);
      try { const r = await pgCall(base); pane.load.stop(); renderResponse(pane.body, r); }
      catch (e) { pane.load.stop(); pane.body.innerHTML = ""; pane.body.appendChild(el("div", { class: "pg-error", text: String(e) })); }
    }
  } finally {
    btn.disabled = false; btn.textContent = "Send request";
  }
}

// ─── Response rendering ────────────────────────────────────────────────────
// A clear "waiting on the server" indicator: spinner + label + a live elapsed
// timer (reassuring for slow deep-research calls) + an indeterminate bar.
// Returns { stop } to cancel the timer before the real response replaces it.
// Shared by the playground panes and the Compare panes.
function startLoading(container, label) {
  container.innerHTML = "";
  const sub = el("div", { class: "pg-loading-sub" });
  const box = el("div", { class: "pg-loading" }, [
    el("div", { class: "pg-loading-spin" }),
    el("div", { class: "pg-loading-text", text: label || "Querying…" }),
    sub,
    el("div", { class: "pg-loading-bar" }),
  ]);
  container.appendChild(box);
  const t0 = performance.now();
  const tick = () => { sub.textContent = ((performance.now() - t0) / 1000).toFixed(1) + "s · waiting for the server…"; };
  tick();
  const iv = setInterval(tick, 100);
  return { stop: () => clearInterval(iv) };
}

function makePane(title) {
  const pane = el("div", { class: "pg-pane" });
  if (title) pane.appendChild(el("div", { class: "pg-pane-title", text: title }));
  const body = el("div", { class: "pg-pane-body" });
  pane.appendChild(body);
  const who = PROVIDERS[pg.provider] ? `${PROVIDERS[pg.provider].label} · ${pg.endpoint}` : "endpoint";
  const load = startLoading(body, `Querying ${who}${title ? ` · ${title}` : ""}…`);
  return { el: pane, body, load };
}

// Pull the USD cost out of a response body when the provider reports one. Cost
// lives in a different place per API, so check the known shapes. Returns
// { value, detail } — `detail` is the richer cost object (e.g. Exa's
// costDollars breakdown) for the drill-down popover, or null if cost is a bare
// number. Returns null overall if no cost is present.
function extractCost(body) {
  if (!body || typeof body !== "object") return null;
  const cd = body.costDollars;
  const uc = body.usage && body.usage.cost;             // Perplexity usage.cost{...}
  let value = null, detail = null;
  if (cd && typeof cd === "object" && cd.total != null) { value = Number(cd.total); detail = cd; }
  else if (typeof cd === "number") value = cd;
  else if (uc && typeof uc === "object" && (uc.total_cost ?? uc.total) != null) { value = Number(uc.total_cost ?? uc.total); detail = uc; }
  else if (typeof body.actual_cost === "number") value = body.actual_cost;   // Perplexity agent runner
  else if (typeof body.cost === "number") value = body.cost;
  if (value === null || Number.isNaN(Number(value))) return null;
  // No dollar breakdown? Fall back to a usage detail (tokens / calls) so the pill
  // still drills — e.g. Perplexity reports usage but a single cost number.
  if (!detail) {
    const u = {};
    for (const k of ["actual_cost", "input_tokens", "output_tokens", "search_context_tokens",
                     "total_tokens", "api_calls", "search_calls"])
      if (typeof body[k] === "number") u[k] = body[k];
    if (Object.keys(u).length > 1) detail = u;   // >1 so a lone cost number isn't a trivial popover
  }
  return { value: Number(value), detail };
}

// Format a dollar amount without showing "$0.0000" for tiny-but-nonzero costs.
function fmtCost(n) {
  if (n === 0) return "0";
  if (n < 0.0001) return n.toExponential(2);
  return n.toFixed(4);
}

function renderResponse(container, { httpOk, clientMs, data }) {
  container.innerHTML = "";

  // data = proxy wrapper {ok,status,elapsed_ms,url,request,body} or {error}
  if (data.error) {
    container.appendChild(el("div", { class: "pg-error", text: "Proxy error: " + data.error }));
    return;
  }
  const body = data.body || {};
  const results = Array.isArray(body.results) ? body.results
                 : Array.isArray(body.citations) ? body.citations
                 : Array.isArray(body.entities) ? body.entities
                 : (body.web && Array.isArray(body.web.results)) ? body.web.results          // Brave web nests here
                 : (body.results && Array.isArray(body.results.web)) ? body.results.web      // You.com search nests here
                 : Array.isArray(body.organic_results) ? body.organic_results                // SerpApi (google/bing/ddg/…)
                 : Array.isArray(body.news_results) ? body.news_results                      // SerpApi news engines
                 : Array.isArray(body.images_results) ? body.images_results                  // SerpApi image engines
                 : Array.isArray(body.video_results) ? body.video_results                    // SerpApi video engines
                 : Array.isArray(body.local_results) ? body.local_results                    // SerpApi maps/local
                 : null;
  // Synthesized answer: Exa/Perplexity use `answer`; You.com research/finance and
  // Parallel Task put it under `output.content`.
  const answerText = typeof body.answer === "string" ? body.answer
                   : (body.output && typeof body.output.content === "string" ? body.output.content : null);
  const cost = extractCost(body);

  // Summary bar
  const bar = el("div", { class: "pg-summary" });
  bar.appendChild(el("span", { class: "pg-pill " + (data.ok ? "pg-ok" : "pg-bad"), text: "HTTP " + data.status }));
  // Latency pill is self-labeling ("round-trip") with an ⓘ explaining it's the
  // full client→server→provider→back time, not the API's own processing time.
  const msPill = el("span", { class: "pg-pill", text: data.elapsed_ms + " ms round-trip" });
  msPill.appendChild(el("span", { class: "pg-info", "data-tip":
    "Round-trip measured by the playground: browser → this server → the provider API → back (includes network + our proxy hop). It's larger than the provider's own processing time, which — when the API reports it — appears in the response body.", text: "i" }));
  bar.appendChild(msPill);
  if (results) bar.appendChild(el("span", { class: "pg-pill", text: results.length + " result" + (results.length === 1 ? "" : "s") }));
  if (cost) {
    const costPill = el("span", { class: "pg-pill pg-cost", text: "$" + fmtCost(cost.value) });
    if (cost.detail && typeof cost.detail === "object") {   // drill into the breakdown
      costPill.classList.add("pg-pill-click");
      costPill.title = "Click for the cost / usage detail";
      costPill.addEventListener("click", (e) => { e.stopPropagation(); openFieldPopover(costPill, "cost detail", cost.detail); });
    }
    bar.appendChild(costPill);
  }
  if (body.requestId) bar.appendChild(el("span", { class: "pg-pill pg-muted", text: body.requestId }));
  container.appendChild(bar);

  // Response object — the guaranteed-faithful view. Shown right under the summary
  // so it's obvious the parsed cards below are just a rendering of this. Collapsed
  // by default; offers an interactive Tree view + a Raw text view, and a Copy button.
  container.appendChild(renderRawObject(body));

  // Parsed / formatted view
  if (!data.ok) {
    const msg = body.error || body.message || (body._raw ? body._raw.slice(0, 400) : "Request failed");
    container.appendChild(el("div", { class: "pg-error", text: String(msg) }));
  } else if (answerText) {
    container.appendChild(el("div", { class: "pg-answer", text: answerText }));
    // Some answer endpoints (You.com research/finance) return sources alongside.
    const srcs = (body.output && Array.isArray(body.output.sources)) ? body.output.sources : [];
    if (srcs.length) {
      const line = el("div", { class: "pg-help", style: "margin-top:8px" }, ["Sources: "]);
      srcs.slice(0, 25).forEach((s, i) => {
        const u = typeof s === "string" ? s : (s && (s.url || s.link));
        if (u) { const a = el("a", { href: safe(u), target: "_blank", text: "[" + (i + 1) + "]" }); a.style.marginRight = "6px"; line.appendChild(a); }
      });
      container.appendChild(line);
    }
  } else if (results) {
    const list = el("div", { class: "pg-cards" });
    const shown = results.slice(0, 12);
    for (const r of shown) list.appendChild(renderResultCard(r));
    container.appendChild(list);
    if (results.length > shown.length)
      container.appendChild(el("div", { class: "pg-help", text: `+ ${results.length - shown.length} more — expand the raw response object above to see all` }));
  }
}

// ─── Raw response viewer: collapsible Tree | Raw text + Copy ─────────────────
function renderRawObject(body) {
  const text = JSON.stringify(body, null, 2);
  const details = el("details", { class: "pg-raw" });
  details.appendChild(el("summary", { text: "Response object (as returned by the API)" }));

  const tools = el("div", { class: "pg-raw-tools" });
  const seg = el("div", { class: "pg-seg" });
  const treeBtn = el("button", { type: "button", class: "pg-seg-btn active", text: "Tree" });
  const rawBtn = el("button", { type: "button", class: "pg-seg-btn", text: "Raw" });
  seg.append(treeBtn, rawBtn);
  const copyBtn = el("button", { type: "button", class: "pg-copy", text: "Copy" });
  copyBtn.addEventListener("click", async (e) => {
    e.preventDefault();
    try { await navigator.clipboard.writeText(text); }
    catch { const ta = el("textarea"); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove(); }
    copyBtn.textContent = "Copied!"; copyBtn.classList.add("copied");
    setTimeout(() => { copyBtn.textContent = "Copy"; copyBtn.classList.remove("copied"); }, 1200);
  });
  tools.append(seg, copyBtn);
  details.appendChild(tools);

  const tree = el("div", { class: "pg-tree" }, [jsonNode(null, body, 0)]);
  const pre = el("pre", { class: "pg-json", hidden: "" });
  pre.textContent = text;
  details.append(tree, pre);

  const show = (v) => {
    const isTree = v === "tree";
    treeBtn.classList.toggle("active", isTree);
    rawBtn.classList.toggle("active", !isTree);
    tree.hidden = !isTree; pre.hidden = isTree;
  };
  treeBtn.addEventListener("click", (e) => { e.preventDefault(); show("tree"); });
  rawBtn.addEventListener("click", (e) => { e.preventDefault(); show("raw"); });
  return details;
}

// One node of the JSON tree. Objects/arrays are collapsible; leaves are colored.
// Containers auto-collapse below depth 1 so large payloads stay scannable.
function jsonNode(key, value, depth) {
  const keyEl = (k) => k === null ? null
    : el("span", { class: "jt-key", text: (typeof k === "number" ? k : JSON.stringify(k)) + ": " });

  if (value === null || typeof value !== "object") {
    const row = el("div", { class: "jt-row" });
    const ke = keyEl(key); if (ke) row.appendChild(ke);
    row.appendChild(leafValue(value));
    return row;
  }

  const isArr = Array.isArray(value);
  const entries = isArr ? value.map((v, i) => [i, v]) : Object.entries(value);
  const node = el("div", { class: "jt-node" });
  const head = el("div", { class: "jt-head" });
  head.appendChild(el("span", { class: "jt-tri" }));
  const ke = keyEl(key); if (ke) head.appendChild(ke);
  const count = entries.length + (isArr ? " items" : " keys");
  head.appendChild(el("span", { class: "jt-summary", text: (isArr ? "[" : "{") + " " + count + " " + (isArr ? "]" : "}") }));
  node.appendChild(head);

  const kids = el("div", { class: "jt-children" });
  for (const [k, v] of entries) kids.appendChild(jsonNode(k, v, depth + 1));
  node.appendChild(kids);

  if (entries.length && depth >= 1) node.classList.add("collapsed");
  head.addEventListener("click", () => node.classList.toggle("collapsed"));
  if (!entries.length) head.querySelector(".jt-tri").classList.add("jt-empty");
  return node;
}

function leafValue(v) {
  if (v === null) return el("span", { class: "jt-null", text: "null" });
  if (typeof v === "number") return el("span", { class: "jt-num", text: String(v) });
  if (typeof v === "boolean") return el("span", { class: "jt-bool", text: String(v) });
  // string — link if it looks like a URL, otherwise a wrapped quoted string
  if (/^https?:\/\//i.test(v))
    return el("a", { class: "jt-str jt-link", href: safe(v), target: "_blank", text: JSON.stringify(v) });
  return el("span", { class: "jt-str", text: JSON.stringify(v) });
}

// Standard result fields; anything else on a result is "extra" (category-specific).
const STD_KEYS = new Set(["title", "name", "url", "link", "id", "publishedDate", "publish_date", "date", "last_updated",
  "author", "image", "favicon", "text", "highlights", "highlightScores", "summary", "description", "snippet",
  "excerpts", "subpages", "score",
  // SerpApi-common fields (keep cards clean; full data is in the raw tree)
  "position", "displayed_link", "redirect_link", "source", "thumbnail", "snippet_highlighted_words"]);

function renderResultCard(r) {
  const url = r.url || r.link;   // SerpApi results use `link` rather than `url`
  const card = el("div", { class: "pg-card" });
  const head = el("div", { class: "pg-card-head" });
  if (r.favicon) head.appendChild(el("img", { class: "pg-favicon", src: r.favicon, alt: "" }));
  const title = el("a", { class: "pg-card-title", href: safe(url), target: "_blank", text: r.title || r.name || url || "(untitled)" });
  head.appendChild(title);
  card.appendChild(head);

  const meta = [];
  if (url) { try { meta.push(new URL(url).hostname); } catch { meta.push(url); } }
  const pub = r.publishedDate || r.publish_date || r.date;
  if (pub) meta.push(String(pub).slice(0, 10));
  if (r.author) meta.push(r.author);
  if (meta.length) card.appendChild(el("div", { class: "pg-card-meta", text: meta.join(" · ") }));

  // Badges: which content fields came back. Each is a clickable pill that opens
  // the field's full content in a popover (see openFieldPopover).
  const badges = el("div", { class: "pg-badges" });
  const addPill = (name, value, hot) => {
    const b = el("span", { class: "pg-badge pg-badge-click" + (hot ? " pg-badge-hot" : ""), text: name, title: "Click to view " + name });
    b.addEventListener("click", () => openFieldPopover(b, name, value));
    badges.appendChild(b);
  };
  for (const [k, present, val] of [
    ["text", r.text, r.text],
    ["highlights", r.highlights && r.highlights.length, r.highlights],
    ["summary", r.summary, r.summary],
    ["subpages", r.subpages && r.subpages.length, r.subpages],
    ["extras", r.extras, r.extras],
  ]) if (present) addPill(k, val, false);
  // Category-specific structured keys (e.g. entities, meta_url, thumbnail) get a
  // clickable pill. Only objects/arrays — bare scalars need no popover and would
  // just add noise (e.g. Brave's many per-result flags), and stay in the raw view.
  const extraKeys = Object.keys(r).filter(k => !STD_KEYS.has(k) && k !== "extras");
  for (const k of extraKeys) if (r[k] && typeof r[k] === "object") addPill(k, r[k], true);
  if (badges.children.length) card.appendChild(badges);

  if (r.summary) card.appendChild(el("div", { class: "pg-snippet", text: clip(r.summary, 240) }));
  else if (r.highlights && r.highlights.length) card.appendChild(el("div", { class: "pg-snippet", text: clip(r.highlights[0], 240) }));
  else if (r.description) card.appendChild(el("div", { class: "pg-snippet", text: clip(r.description, 240) }));
  else if (r.excerpts && r.excerpts.length) card.appendChild(el("div", { class: "pg-snippet", text: clip(r.excerpts[0], 240) }));
  else if (r.snippet) card.appendChild(el("div", { class: "pg-snippet", text: clip(r.snippet, 240) }));
  return card;
}

// ─── Field popover — click a content pill to view its full value ─────────────
// One reusable popover appended to <body> (so card overflow can't clip it).
let _pop = null;
function popEl() {
  if (_pop) return _pop;
  _pop = el("div", { class: "pg-pop" }, [
    el("div", { class: "pg-pop-head" }, [
      el("span", { class: "pg-pop-title" }),
      el("button", { type: "button", class: "pg-pop-x", text: "×", onclick: closeFieldPopover }),
    ]),
    el("div", { class: "pg-pop-body" }),
  ]);
  document.body.appendChild(_pop);
  return _pop;
}
function closeFieldPopover() { if (_pop) _pop.classList.remove("show"); }

function openFieldPopover(anchor, name, value) {
  const p = popEl();
  p.querySelector(".pg-pop-title").textContent = name;
  const body = p.querySelector(".pg-pop-body");
  body.innerHTML = "";
  body.appendChild(fieldContent(value));
  p.classList.add("show");
  // Position under the pill, clamped to the viewport; flip above if no room below.
  const r = anchor.getBoundingClientRect(), pr = p.getBoundingClientRect();
  const left = Math.max(12, Math.min(r.left, window.innerWidth - pr.width - 12));
  let top = r.bottom + 6;
  if (top + pr.height > window.innerHeight - 12) top = Math.max(12, r.top - pr.height - 6);
  p.style.left = left + "px";
  p.style.top = top + "px";
}

// String → wrapped text; array of strings → list; anything structured → JSON tree.
function fieldContent(value) {
  if (value === null || value === undefined) return el("div", { class: "pg-pop-text", text: String(value) });
  if (typeof value === "string") {
    return /^https?:\/\//i.test(value)
      ? el("a", { class: "pg-pop-text jt-link", href: safe(value), target: "_blank", text: value })
      : el("div", { class: "pg-pop-text", text: value });
  }
  if (typeof value === "number" || typeof value === "boolean") return el("div", { class: "pg-pop-text", text: String(value) });
  if (Array.isArray(value) && value.every(v => typeof v === "string"))
    return el("ul", { class: "pg-pop-list" }, value.map(v => el("li", { text: v })));
  return el("div", { class: "pg-tree pg-tree-pop" }, [jsonNode(null, value, 0)]);
}

// Dismiss the popover on outside-click or Escape (opening click is on a pill).
document.addEventListener("click", (e) => {
  if (_pop && _pop.classList.contains("show") && !_pop.contains(e.target) && !e.target.closest(".pg-badge-click"))
    closeFieldPopover();
});
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeFieldPopover(); });

// ─── Misc helpers ────────────────────────────────────────────────────────
function safe(u) { try { const p = new URL(u); return (p.protocol === "https:" || p.protocol === "http:") ? u : "#"; } catch { return "#"; } }
function clip(s, n) { s = String(s); return s.length > n ? s.slice(0, n) + "…" : s; }

function toCurl(params) {
  const p = PROVIDERS[pg.provider];
  const ep = p.endpoints[pg.endpoint];
  const authHeaderLine = p.authHeader ? `-H "${p.authHeader}: ${p.authPrefix || ""}$${p.keyEnv}"` : "";
  // GET endpoints (Brave, SerpApi) send params as a query string, not a JSON body.
  if ((ep.method || "POST").toUpperCase() === "GET") {
    const parts = Object.entries(params).map(([k, v]) =>
      `${encodeURIComponent(k)}=${encodeURIComponent(Array.isArray(v) ? v.join(",") : v)}`);
    if (p.authQueryParam) parts.push(`${p.authQueryParam}=$${p.keyEnv}`);   // key as a query param (SerpApi)
    const qs = parts.length ? "?" + parts.join("&") : "";
    const lines = [`curl "${p.baseUrl}${ep.path}${qs}"${authHeaderLine ? " \\" : ""}`];
    if (authHeaderLine) lines.push(`  ${authHeaderLine}`);
    return lines.join("\n");
  }
  return [
    `curl -X ${ep.method} ${p.baseUrl}${ep.path} \\`,
    `  ${authHeaderLine} \\`,
    `  -H "Content-Type: application/json" \\`,
    `  -d '${JSON.stringify(params)}'`,
  ].join("\n");
}

function copyText(id, btn) {
  const t = document.getElementById(id).textContent;
  navigator.clipboard.writeText(t).then(() => {
    const old = btn.textContent; btn.textContent = "Copied!";
    setTimeout(() => { btn.textContent = old; }, 1200);
  });
}

// ─── Tabs + switching ────────────────────────────────────────────────────────
// About is the first tab (static, in index.html). Provider tabs come next
// (alpha-sorted), and Compare sits last.
function buildTabs() {
  const bar = document.getElementById("tabBar");
  const providers = pg.providerOrder
    .map(pid => ({ label: PROVIDERS[pid].label, provider: pid,
                   onclick: (e) => switchProvider(pid, e.currentTarget) }))
    .sort((a, b) => a.label.localeCompare(b.label));
  const entries = [
    ...providers,
    { label: "Compare", onclick: (e) => switchTab("tab-compare", e.currentTarget) },
  ];
  for (const en of entries) {
    const attrs = { class: "tab-btn", text: en.label, onclick: en.onclick,
      "data-tab": en.provider ? "tab-playground" : "tab-compare" };
    if (en.provider) attrs["data-provider"] = en.provider;
    bar.appendChild(el("button", attrs));
  }
}

function switchProvider(providerId, btn) {
  pg.provider = providerId;
  pg.endpoint = PROVIDERS[providerId].endpointOrder[0];
  switchTab("tab-playground", btn);   // shared panel; switchTab handles active state
  buildEndpointDropdown();
  buildForm();
  const results = document.getElementById("pgResults");
  results.className = "pg-results";
  results.innerHTML = '<div class="pg-empty">Build a request and hit <strong>Send</strong> to see the response.</div>';
}

function buildEndpointDropdown() {
  const prov = PROVIDERS[pg.provider];
  const sel = document.getElementById("pgEndpoint");
  sel.innerHTML = "";
  // The dropdown is just the switcher — show the compact method + path; the full
  // description shows in the prominent header below (see updateEndpointMeta).
  for (const id of prov.endpointOrder) {
    const ep = prov.endpoints[id];
    sel.appendChild(el("option", { value: id, text: `${ep.method} ${ep.path}` }));
  }
  sel.value = pg.endpoint;
}

// ─── Init ──────────────────────────────────────────────────────────────────
async function initPlayground() {
  // Fetch the provider catalog (single source of truth, server-side).
  try {
    const catalog = await (await fetch("/api/providers")).json();
    PROVIDERS = catalog.providers || {};
    pg.providerOrder = catalog.providerOrder || Object.keys(PROVIDERS);
  } catch (e) {
    document.getElementById("pgForm").innerHTML =
      '<div class="pg-error">Could not load provider catalog from /api/providers.</div>';
    return;
  }
  if (!pg.providerOrder.length) return;

  buildTabs();

  // Wire shell controls once
  document.getElementById("pgEndpoint").addEventListener("change", (e) => { pg.endpoint = e.target.value; buildForm(); });
  const toggle = document.getElementById("pgCompareToggle");
  toggle.addEventListener("change", () => { document.getElementById("pgCompareBody").style.display = toggle.checked ? "" : "none"; updateCompareFieldState(); });
  document.getElementById("pgDepCheck").addEventListener("change", (e) => {
    document.getElementById("pgForm").classList.toggle("hide-deprecated", !e.target.checked);
  });
  document.getElementById("pgSendBtn").addEventListener("click", pgSend);
  // Keep the request body + cURL live: any form / compare change re-renders it.
  const left = document.querySelector(".pg-left");
  left.addEventListener("input", updateRequestPreview);
  left.addEventListener("change", updateRequestPreview);

  // Pre-build the playground for the first provider so the panel is ready when a
  // provider tab is clicked. About is the landing tab, so we don't switch to it.
  pg.provider = pg.providerOrder[0];
  pg.endpoint = PROVIDERS[pg.provider].endpointOrder[0];
  buildEndpointDropdown();
  buildForm();

  // Expose for the comparison picker (built in index.html)
  window.PG_CATALOG = { providers: PROVIDERS, order: pg.providerOrder };
  if (window.initComparePicker) window.initComparePicker();
}

// Script is loaded at end of <body>; if the DOM is already parsed, run now.
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initPlayground);
else initPlayground();
