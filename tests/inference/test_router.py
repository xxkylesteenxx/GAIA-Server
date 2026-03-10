"""InferenceRouter unit tests — MockBackend only, no model file required."""
from __future__ import annotations

import asyncio

import pytest

from gaia_core.inference.contracts import InferRequest, RuntimeBackend, TaskType
from gaia_server.inference.router import InferenceRouter


def _router(timeout_ms: int = 5_000) -> InferenceRouter:
    return InferenceRouter(default_backend_name="mock", timeout_ms=timeout_ms)


async def test_generate_returns_accepted_response() -> None:
    router = _router()
    req = InferRequest(
        request_id="req-001",
        core_id="core-nexus",
        task_type=TaskType.GENERATE,
        backend=RuntimeBackend.MOCK,
        payload={"prompt": "Hello GAIA"},
    )
    resp = await router.infer(req)
    assert resp.accepted is True
    assert resp.request_id == "req-001"
    assert "text" in resp.result
    assert resp.error_code is None


async def test_embed_returns_embedding() -> None:
    router = _router()
    req = InferRequest(
        request_id="req-002",
        core_id="core-nexus",
        task_type=TaskType.EMBED,
        backend=RuntimeBackend.MOCK,
        payload={"text": "embed this"},
    )
    resp = await router.infer(req)
    assert resp.accepted is True
    assert "embedding" in resp.result
    assert isinstance(resp.result["embedding"], list)


async def test_unknown_backend_falls_back_to_mock() -> None:
    router = _router()
    req = InferRequest(
        request_id="req-003",
        core_id="core-nexus",
        task_type=TaskType.GENERATE,
        backend=RuntimeBackend.VLLM,   # not registered
        payload={"prompt": "test"},
    )
    # vllm not registered — router falls back to mock
    resp = await router.infer(req)
    assert resp.accepted is True


async def test_timeout_returns_error_response() -> None:
    router = InferenceRouter(default_backend_name="mock", timeout_ms=1)

    class SlowBackend:
        async def generate(self, request):
            await asyncio.sleep(10)

        async def embed(self, request):
            await asyncio.sleep(10)

        async def health(self):
            return {"status": "ok"}

    router.register(RuntimeBackend.MOCK, SlowBackend())

    req = InferRequest(
        request_id="req-004",
        core_id="core-nexus",
        task_type=TaskType.GENERATE,
        backend=RuntimeBackend.MOCK,
        payload={"prompt": "slow"},
    )
    resp = await router.infer(req)
    assert resp.accepted is False
    assert resp.error_code == "TIMEOUT"


async def test_backend_exception_returns_error_response() -> None:
    router = _router()

    class BrokenBackend:
        async def generate(self, request):
            raise RuntimeError("model exploded")

        async def embed(self, request):
            raise RuntimeError("model exploded")

        async def health(self):
            return {"status": "error"}

    router.register(RuntimeBackend.MOCK, BrokenBackend())

    req = InferRequest(
        request_id="req-005",
        core_id="core-nexus",
        task_type=TaskType.GENERATE,
        backend=RuntimeBackend.MOCK,
        payload={"prompt": "break"},
    )
    resp = await router.infer(req)
    assert resp.accepted is False
    assert resp.error_code == "BACKEND_ERROR"
    assert "exploded" in (resp.error_message or "")


async def test_router_health_aggregates_backends() -> None:
    router = _router()
    health = await router.health()
    assert health["status"] == "ok"
    assert "mock" in health["backends"]
