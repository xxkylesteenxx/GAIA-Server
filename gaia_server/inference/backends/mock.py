"""MockBackend — deterministic zero-dependency inference backend.

Used for:
- Tests (no model file required)
- Cold-start / degraded mode when no model is loaded
- Contract validation without GPU/CPU overhead

Returns echo-style responses. Never raises on valid input.
"""
from __future__ import annotations

import time
from typing import Any, Mapping

from gaia_core.inference.contracts import InferRequest, InferResponse, RuntimeBackend, TaskType


class MockBackend:
    """Deterministic mock inference backend. No external dependencies."""

    BACKEND = RuntimeBackend.MOCK

    async def generate(self, request: InferRequest) -> InferResponse:
        prompt = str(request.payload.get("prompt", ""))
        return InferResponse(
            request_id=request.request_id,
            accepted=True,
            core_id=request.core_id,
            task_type=TaskType.GENERATE,
            backend=self.BACKEND,
            model_id=request.model_id or "mock",
            result={"text": f"[mock] echo: {prompt[:120]}"},
            usage={"prompt_tokens": len(prompt.split()), "completion_tokens": 8},
            latency_ms=1,
        )

    async def embed(self, request: InferRequest) -> InferResponse:
        text = str(request.payload.get("text", ""))
        # Return a trivial 4-dim unit vector as a stand-in
        return InferResponse(
            request_id=request.request_id,
            accepted=True,
            core_id=request.core_id,
            task_type=TaskType.EMBED,
            backend=self.BACKEND,
            model_id=request.model_id or "mock",
            result={"embedding": [0.25, 0.25, 0.25, 0.25], "dims": 4},
            usage={"tokens": len(text.split())},
            latency_ms=1,
        )

    async def health(self) -> Mapping[str, Any]:
        return {"backend": "mock", "status": "ok", "model": "mock"}
