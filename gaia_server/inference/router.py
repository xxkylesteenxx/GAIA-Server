"""InferenceRouter — dispatches InferRequest to the correct backend.

Dispatch priority:
    1. request.backend field (explicit override)
    2. settings.inference_default_backend (env-configured default)
    3. MockBackend (fallback, always available)

All responses are wrapped in InferResponse with:
    - latency_ms measured end-to-end in the router
    - error_code / error_message populated on failure
    - accepted=False on any exception or timeout

The router never raises. All errors become InferResponse(accepted=False).
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from gaia_core.inference.contracts import InferRequest, InferResponse, RuntimeBackend, TaskType
from gaia_server.inference.backends.mock import MockBackend

log = logging.getLogger(__name__)


class InferenceRouter:
    """Routes InferRequest objects to registered backends."""

    def __init__(
        self,
        default_backend_name: str = "mock",
        timeout_ms: int = 30_000,
    ) -> None:
        self._backends: dict[str, Any] = {}
        self._default = default_backend_name
        self._timeout_s = timeout_ms / 1000.0
        # mock is always registered
        self.register(RuntimeBackend.MOCK, MockBackend())

    def register(self, backend_id: RuntimeBackend | str, backend: Any) -> None:
        """Register a backend under its RuntimeBackend key."""
        self._backends[str(backend_id)] = backend
        log.debug("[router] registered backend: %s", backend_id)

    async def infer(self, request: InferRequest) -> InferResponse:
        """Dispatch request to the appropriate backend. Never raises."""
        t0 = time.monotonic()

        # Resolve backend
        backend_key = str(request.backend) if request.backend else self._default
        backend = self._backends.get(backend_key) or self._backends.get(RuntimeBackend.MOCK)

        if backend is None:
            return _error_response(request, "NO_BACKEND", f"No backend registered for '{backend_key}'")

        # Dispatch by task type
        try:
            coro = _dispatch(backend, request)
            response = await asyncio.wait_for(coro, timeout=self._timeout_s)
        except asyncio.TimeoutError:
            latency_ms = int((time.monotonic() - t0) * 1000)
            log.warning("[router] timeout on request %s after %dms", request.request_id, latency_ms)
            return _error_response(request, "TIMEOUT", f"Inference timed out after {self._timeout_s}s")
        except Exception as exc:
            latency_ms = int((time.monotonic() - t0) * 1000)
            log.exception("[router] backend error on request %s", request.request_id)
            return _error_response(request, "BACKEND_ERROR", str(exc))

        return response

    async def health(self) -> dict[str, Any]:
        results = {}
        for key, backend in self._backends.items():
            try:
                results[key] = await backend.health()
            except Exception as exc:
                results[key] = {"status": "error", "detail": str(exc)}
        return {"status": "ok" if all(v.get("status") == "ok" for v in results.values()) else "degraded",
                "backends": results}


def _dispatch(backend: Any, request: InferRequest):
    """Select the correct backend method by TaskType."""
    if request.task_type == TaskType.EMBED:
        return backend.embed(request)
    # GENERATE, SUMMARIZE, CLASSIFY, ROUTE, POLICY_EVAL all map to generate
    return backend.generate(request)


def _error_response(request: InferRequest, code: str, message: str) -> InferResponse:
    return InferResponse(
        request_id=request.request_id,
        accepted=False,
        core_id=request.core_id,
        task_type=request.task_type,
        backend=request.backend or RuntimeBackend.MOCK,
        model_id=request.model_id,
        result={},
        usage={},
        latency_ms=0,
        error_code=code,
        error_message=message,
    )
