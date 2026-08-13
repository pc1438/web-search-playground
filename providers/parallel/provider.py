"""
providers/parallel/provider.py — the Parallel provider.

Most endpoints are plain JSON POSTs with an `x-api-key` header, so the base
`call()` handles them:
  /v1/search, /v1beta/search        — ranked results + excerpts (results-only)
  /v1beta/findall/entity-search     — ranked entities (results-only)

The Task API (/v1/tasks/runs) is different: it's asynchronous. You create a run,
then poll until it completes and fetch the result. `call()` is overridden to run
that create → poll → result flow and return the final result as the raw body
(a synthesized, cited answer) — the same path the Compare tab uses.
"""

import time

import requests

from providers.base import Provider
from providers.parallel.endpoints import ENDPOINTS, ENDPOINT_ORDER

# Run states that mean "keep waiting"; anything else is terminal.
_ACTIVE = {"queued", "running", "action_required"}


class ParallelProvider(Provider):
    id = "parallel"
    label = "Parallel"
    base_url = "https://api.parallel.ai"
    auth_header = "x-api-key"
    key_env = "PARALLEL_API_KEY"
    key_docs_url = "https://app.parallel.ai/"
    endpoint_order = ENDPOINT_ORDER
    endpoints = ENDPOINTS

    def call(self, endpoint_id: str, params: dict, timeout: int = 180,
             request_keys: dict = None) -> dict:
        # Search/FindAll are single POSTs → base call(). Task is create + poll.
        if endpoint_id != "task":
            return super().call(endpoint_id, params, timeout, request_keys=request_keys)
        return self._run_task(params, timeout=timeout, request_keys=request_keys)

    # ── Task API create → poll → result ──
    def _run_task(self, params: dict, timeout: int = 180, on_progress=None,
                  request_keys: dict = None) -> dict:
        base = self.base_url.rstrip("/")
        headers = self.headers(request_keys)
        runs_url = f"{base}/v1/tasks/runs"
        t0 = time.perf_counter()
        elapsed = lambda: round((time.perf_counter() - t0) * 1000)

        create = requests.post(runs_url, json=params, headers=headers, timeout=30)
        if not create.ok:
            return self._wrap(create, runs_url, params, elapsed())
        run = create.json()
        run_id = run.get("run_id")
        status = run.get("status")
        status_url = f"{base}/v1/tasks/runs/{run_id}"
        if on_progress:
            on_progress(f"Task run {run_id} created ({run.get('processor')}) — {status}…")

        deadline = t0 + timeout
        while status in _ACTIVE and time.perf_counter() < deadline:
            time.sleep(2)
            r = requests.get(status_url, headers=headers, timeout=30)
            if r.ok:
                run = r.json()
                status = run.get("status")
                if on_progress:
                    on_progress(f"…{status}")

        if status != "completed":
            return {
                "ok": False, "status": 504, "elapsed_ms": elapsed(), "url": status_url,
                "request": params,
                "body": {"error": f"Run {run_id} status '{status}' — not completed within {timeout}s. "
                                  f"Fetch {status_url}/result to retrieve it when ready."},
            }

        result = requests.get(f"{status_url}/result", headers=headers, timeout=timeout)
        return self._wrap(result, f"{status_url}/result", params, elapsed())

    @staticmethod
    def _wrap(resp, url: str, params: dict, elapsed_ms: int) -> dict:
        try:
            body = resp.json()
        except ValueError:
            body = {"_raw": resp.text[:8000]}
        return {"ok": resp.ok, "status": resp.status_code, "elapsed_ms": elapsed_ms,
                "url": url, "request": params, "body": body}
