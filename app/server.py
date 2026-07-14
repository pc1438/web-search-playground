"""
server.py — thin HTTP layer for the Search API Playground.

A small, threaded `http.server` over the `providers/` registry. Endpoints:
    GET  /api/providers  — the provider catalog the frontend renders from
    POST /api/call       — run one endpoint (dispatch to registry.get(...).call(...))
    POST /api/compare    — SSE stream running up to four endpoints side by side

Run:
    python app/server.py                # starts on http://localhost:8088
    python app/server.py --port 9000    # custom port
"""

import json
import logging
import logging.handlers
import os
import sys
import threading
import time
import requests
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path
from dotenv import load_dotenv

# ─── Path setup ────────────────────────────────────────────────────────────
APP_DIR = Path(__file__).parent
REPO_DIR = APP_DIR.parent
LOG_DIR = REPO_DIR / "logs"

load_dotenv(REPO_DIR / "env.txt")
load_dotenv(REPO_DIR / ".env")

logger = logging.getLogger("competitor_search")


def setup_logging():
    """Log to console + a rotating file in logs/. Level from LOG_LEVEL (default
    INFO); set LOG_LEVEL=debug to also record request params, upstream URLs, and
    (truncated) response bodies. Run after load_dotenv so env.txt can set it."""
    LOG_DIR.mkdir(exist_ok=True)
    level = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    root = logging.getLogger()
    root.setLevel(level)
    for h in root.handlers[:]:          # avoid duplicate handlers on re-import
        root.removeHandler(h)
    file_h = logging.handlers.RotatingFileHandler(
        LOG_DIR / "server.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    console_h = logging.StreamHandler()
    for h in (file_h, console_h):
        h.setFormatter(fmt)
        h.setLevel(level)
        root.addHandler(h)
    # Keep DEBUG about *our* requests, not HTTP-library internals.
    for noisy in ("urllib3", "httpx", "httpcore", "openai", "anthropic"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    logger.info("logging at %s → %s", logging.getLevelName(level), LOG_DIR / "server.log")


setup_logging()

sys.path.insert(0, str(REPO_DIR))

from providers import registry
from providers.base import ProviderKeyMissing

THREAD_TIMEOUT = 300
PROXY_TIMEOUT = 120  # per-call timeout for the generic provider proxy

# The playground's providers live in `providers/` — see providers/registry.py.
# server.py is a thin HTTP layer over that: GET /api/providers serves the
# catalog the frontend renders, POST /api/call dispatches to a provider.


# ─── Request handler ───────────────────────────────────────────────────────

class AppHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    MAX_BODY_SIZE = 10_000
    ALLOWED_ORIGIN = "http://localhost:8088"

    def setup(self):
        super().setup()
        self.wfile = self.request.makefile("wb", buffering=0)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._serve_static(APP_DIR / "index.html", "text/html; charset=utf-8")
        elif self.path == "/playground.js":
            self._serve_static(APP_DIR / "playground.js", "application/javascript; charset=utf-8")
        elif self.path == "/api/providers":
            self._send_json(200, registry.catalog())
        else:
            self.send_error(404)

    def _serve_static(self, path, content_type):
        try:
            with open(path, "rb") as f:
                content = f.read()
        except FileNotFoundError:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Access-Control-Allow-Origin", self.ALLOWED_ORIGIN)
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        if self.path == "/api/compare":
            self._handle_compare()
        elif self.path == "/api/call":
            self._handle_call()
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", self.ALLOWED_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        sys.stderr.write(f"[server] {args[0]}\n")

    def _read_json_body(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            self._send_json(411, {"error": "Content-Length required"})
            return None
        if content_length < 0 or content_length > self.MAX_BODY_SIZE:
            self._send_json(400, {"error": "Request body too large"})
            return None
        body = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return None

    def _send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", self.ALLOWED_ORIGIN)
        self.end_headers()
        self.wfile.write(body)

    def _start_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Access-Control-Allow-Origin", self.ALLOWED_ORIGIN)
        self.end_headers()
        self.wfile.flush()

    def _send_sse(self, event, data):
        try:
            payload = f"event: {event}\ndata: {json.dumps(data)}\n\n"
            self.wfile.write(payload.encode("utf-8"))
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _make_sse_sender(self):
        lock = threading.Lock()
        def send_safe(event, data):
            with lock:
                self._send_sse(event, data)
        return send_safe

    # ── /api/call ─────────────────────────────────────────────────────────

    def _handle_call(self):
        """Generic provider API proxy for the playground.

        Body: {"provider": "exa", "endpoint": "search", "params": {...}}

        Resolves the provider in the registry and delegates to `provider.call()`,
        which returns the upstream status + parsed JSON even on 4xx/5xx so the
        playground can display the raw error payload rather than a dead end.
        """
        body = self._read_json_body()
        if body is None:
            return

        provider_id = (body.get("provider") or "").strip()
        endpoint = (body.get("endpoint") or "").strip()
        params = body.get("params")
        if params is None:
            params = {}

        provider = registry.get(provider_id)
        if not provider:
            self._send_json(400, {"error": f"Unknown provider: {provider_id!r}"})
            return
        if endpoint not in provider.endpoints:
            self._send_json(400, {"error": f"Unknown endpoint {endpoint!r} for provider {provider_id!r}"})
            return
        if not isinstance(params, dict):
            self._send_json(400, {"error": "params must be a JSON object"})
            return

        logger.debug("call %s/%s params=%s", provider_id, endpoint, json.dumps(params))
        try:
            result = provider.call(endpoint, params, timeout=PROXY_TIMEOUT)
        except ProviderKeyMissing as e:
            self._send_json(500, {"error": str(e)})
            return
        except requests.Timeout:
            self._send_json(504, {"error": f"{provider_id}/{endpoint} timed out after {PROXY_TIMEOUT}s"})
            return
        except requests.RequestException as e:
            self._send_json(502, {"error": f"Request to {provider_id} failed: {e}"})
            return

        logger.info("proxy %s/%s → HTTP %s in %dms", provider_id, endpoint, result["status"], result["elapsed_ms"])
        logger.debug("call %s/%s response=%.4000s", provider_id, endpoint, json.dumps(result.get("body")))
        self._send_json(200, result)

    # ── /api/compare ──────────────────────────────────────────────────────

    def _handle_compare(self):
        """Stream 2–4 endpoint calls side by side — each side's raw response.

        Body: {sides: [{id, provider, endpoint, params}, …]} (2–4 entries). The
        frontend has already assembled full params (including the shared question
        injected into each endpoint's query field), so each side just runs the
        provider's raw `call()` in its own thread and the {ok,status,elapsed_ms,
        url,request,body} wrapper is streamed back (tagged by `id`) for the UI to
        render exactly like a provider tab. No judging or normalization.
        """
        payload = self._read_json_body()
        if payload is None:
            return

        sides_in = payload.get("sides")
        if not isinstance(sides_in, list) or len(sides_in) < 2:
            self._send_json(400, {"error": "Provide at least two sides."})
            return
        sides_in = sides_in[:4]   # cap at four

        resolved = []   # (id, provider, endpoint, params)
        for s in sides_in:
            sid = (s.get("id") or "").strip()
            prov = registry.get((s.get("provider") or "").strip())
            eid = (s.get("endpoint") or "").strip()
            if prov is None or not eid or eid not in prov.endpoints:
                self._send_json(400, {"error": f"side {sid!r}: unknown provider/endpoint"})
                return
            resolved.append((sid, prov, eid, s.get("params") or {}))

        labels = {sid: f"{p.label} · {e}" for sid, p, e, _ in resolved}
        logger.info("compare %s", " vs ".join(f"{p.id}/{e}" for _, p, e, _ in resolved))

        self._start_sse()
        send = self._make_sse_sender()
        results = {sid: None for sid, *_ in resolved}

        def run(sid, prov, eid, sparams):
            try:
                results[sid] = prov.call(eid, sparams, timeout=THREAD_TIMEOUT)
            except ProviderKeyMissing as e:
                results[sid] = {"error": str(e)}
            except Exception as e:
                logger.error("%s (%s/%s) call failed: %s", sid, prov.id, eid, e, exc_info=True)
                results[sid] = {"error": f"{prov.label} failed. Please try again."}

        threads = [threading.Thread(target=run, args=(sid, p, e, sp)) for sid, p, e, sp in resolved]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=THREAD_TIMEOUT + 10)

        for sid, prov, eid, _ in resolved:
            wrapper = results[sid] or {"error": f"{prov.label} timed out."}
            send("result", {"side": sid, "provider": prov.id, "endpoint": eid,
                            "label": labels[sid], "wrapper": wrapper})

        send("done", {})


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    port = 8088
    for i, arg in enumerate(args):
        if arg == "--port" and i + 1 < len(args):
            try:
                port = int(args[i + 1])
            except ValueError:
                print(f"Error: --port requires an integer, got: {args[i + 1]!r}")
                sys.exit(1)

    class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True

    AppHandler.ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", f"http://localhost:{port}")
    server = ThreadedHTTPServer(("", port), AppHandler)
    print(f"Search API Playground")
    print(f"Server running at http://localhost:{port}")
    print(f"Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
