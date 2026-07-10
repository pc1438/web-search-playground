"""
providers/base.py — the provider contract.

Every search provider in this repo is one self-contained package under
`providers/<name>/` that subclasses `Provider`. The base class owns the common
case (a plain JSON POST with an API-key header) so a new provider is usually
just declarative: an id, a base URL, how it authenticates, and a set of
`Endpoint`s whose request bodies are described by `Param`s.

Providers that don't fit the common case (streaming, Bearer auth, an unusual
response envelope) override `call()` — but that override still lives inside
their own package, so working on one provider never means touching another.

Three classes make up the contract:
    Param     — one request-body field (renders to a form control in the UI)
    Endpoint  — one API operation (method, path, and its list of Params)
    Provider  — a provider: identity, auth, endpoints, and how to call them

`catalog()` serializes a provider to the exact JSON shape the frontend
(`app/playground.js`) renders, so the schema has a single source of truth here
on the server rather than being duplicated in JS.
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import requests

log = logging.getLogger("competitor_search.provider")


class ProviderKeyMissing(RuntimeError):
    """Raised when a provider's API key env var is unset or still a placeholder."""


@dataclass
class Param:
    """One request-body field.

    `type` drives how the UI renders it and how the value is read back:
        string | text | int | bool | enum | csv | date | group

    A `group` is a nested object: set `fields` to its child Params. Mark it
    `optional=True` to render an enable checkbox (the param is omitted unless
    enabled), and `boolean_shorthand=True` for Exa's "boolean | object" fields
    (`text`, `highlights`) that send `true` when enabled with no sub-options.
    """
    name: str
    type: str
    label: str = ""
    help: str = ""
    required: bool = False
    values: Optional[list] = None            # enum options
    fields: Optional[list] = None            # child Params, for type="group"
    min: Optional[float] = None
    max: Optional[float] = None
    placeholder: str = ""
    maxlen: Optional[int] = None
    optional: bool = False                   # group: render an enable checkbox
    boolean_shorthand: bool = False          # group: emit `true` if no subfields set
    deprecated: bool = False                 # UI: hidden unless "show deprecated" is on
    advanced: bool = False                   # UI: tucked into the collapsed "Advanced options" group

    def to_dict(self) -> dict:
        """Serialize to the JSON shape the frontend renderer expects.

        Only non-default keys are emitted to keep the catalog compact. Note the
        camelCase `booleanShorthand` — that's the key `playground.js` reads.
        """
        d: dict[str, Any] = {"name": self.name, "type": self.type, "label": self.label or self.name}
        if self.help: d["help"] = self.help
        if self.required: d["required"] = True
        if self.values is not None: d["values"] = self.values
        if self.placeholder: d["placeholder"] = self.placeholder
        if self.maxlen is not None: d["maxlen"] = self.maxlen
        if self.min is not None: d["min"] = self.min
        if self.max is not None: d["max"] = self.max
        if self.optional: d["optional"] = True
        if self.boolean_shorthand: d["booleanShorthand"] = True
        if self.deprecated: d["deprecated"] = True
        if self.advanced: d["advanced"] = True
        if self.fields is not None: d["fields"] = [f.to_dict() for f in self.fields]
        return d


@dataclass
class Endpoint:
    """One API operation of a provider."""
    id: str
    label: str
    path: str
    params: list                              # list[Param]
    method: str = "POST"
    compare_params: list = None               # UI: enum params the user can fan a query across (pick one, then its values)
    extra_headers: dict = None                # extra request headers, e.g. a beta version header
    docs_url: str = ""                        # canonical documentation URL for this endpoint
    base_url: str = ""                        # host override (e.g. a different API host than the provider default)
    compare_query_field: str = ""             # if set, endpoint is selectable in Compare; the query maps into this param

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "method": self.method,
            "path": self.path,
            "compareParams": self.compare_params or [],
            "docsUrl": self.docs_url,
            "comparable": bool(self.compare_query_field),
            "compareQueryField": self.compare_query_field,
            "schema": [p.to_dict() for p in self.params],
        }


class Provider:
    """Base provider. Subclass and set the class attributes; override `call()`
    only if the provider needs non-standard request/response handling."""

    id: str = ""
    label: str = ""
    base_url: str = ""
    auth_header: str = ""                     # header the API key goes in
    auth_prefix: str = ""                     # value prefix, e.g. "Bearer " for Authorization
    key_env: str = ""                         # env var holding the key
    endpoint_order: list = []                 # display order; falls back to dict order
    endpoints: dict = {}                      # id -> Endpoint

    # ── auth ──
    def api_key(self) -> str:
        key = os.environ.get(self.key_env, "")
        if not key or key.startswith("your-"):
            raise ProviderKeyMissing(f"{self.key_env} not configured — add it to env.txt")
        return key

    def headers(self) -> dict:
        return {"Content-Type": "application/json", self.auth_header: self.auth_prefix + self.api_key()}

    # ── invocation ──
    def call(self, endpoint_id: str, params: dict, timeout: int = 120) -> dict:
        """Default: send a single request and return a wrapper the UI understands.
        POST/PUT/… send `params` as a JSON body; GET sends them as query params
        (list values comma-joined, since search APIs expect csv, not repeated
        keys). Returns the upstream status + body even on 4xx/5xx so the
        playground can show the raw error payload.

        Override in a subclass for streaming, async, or response reshaping.
        """
        ep = self.endpoints[endpoint_id]
        url = (ep.base_url or self.base_url).rstrip("/") + ep.path
        headers = {**self.headers(), **(ep.extra_headers or {})}
        method = (ep.method or "POST").upper()
        log.debug("→ %s %s params=%s", method, url, json.dumps(params))
        t0 = time.perf_counter()
        if method == "GET":
            qp = {k: (",".join(map(str, v)) if isinstance(v, list) else v) for k, v in params.items()}
            resp = requests.request(method, url, params=qp, headers=headers, timeout=timeout)
        else:
            resp = requests.request(method, url, json=params, headers=headers, timeout=timeout)
        elapsed_ms = round((time.perf_counter() - t0) * 1000)
        try:
            body = resp.json()
        except ValueError:
            body = {"_raw": resp.text[:8000]}   # e.g. an SSE stream or HTML error page
        log.debug("← %s HTTP %s in %dms body=%.4000s", url, resp.status_code, elapsed_ms, json.dumps(body))
        return {
            "ok": resp.ok,
            "status": resp.status_code,
            "elapsed_ms": elapsed_ms,
            "url": url,
            "request": params,
            "body": body,
        }

    # ── serialization for the frontend ──
    def catalog(self) -> dict:
        """The provider's public shape: identity + endpoint schemas. Exposes the
        key's env-var *name* (for the cURL snippet), never the key itself."""
        order = self.endpoint_order or list(self.endpoints.keys())
        return {
            "label": self.label,
            "baseUrl": self.base_url,
            "authHeader": self.auth_header,
            "authPrefix": self.auth_prefix,
            "keyEnv": self.key_env,
            "comparable": any(self.endpoints[eid].compare_query_field for eid in order),
            "endpointOrder": order,
            "endpoints": {eid: self.endpoints[eid].to_dict() for eid in order},
        }
