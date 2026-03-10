"""Entrypoint smoke test — verifies startup and clean shutdown under mocked backends."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gaia_server.health import HealthAggregator, HealthReport


# --- HealthAggregator unit tests (no backend required) ---

async def test_health_aggregator_all_ok() -> None:
    agg = HealthAggregator()
    agg.register("storage", AsyncMock(return_value={"status": "ok"}))
    agg.register("inference", AsyncMock(return_value={"status": "ok"}))
    report = await agg.check()
    assert report.status == "ok"
    assert report.is_ok()
    assert "storage" in report.subsystems
    assert "inference" in report.subsystems


async def test_health_aggregator_one_degraded() -> None:
    agg = HealthAggregator()
    agg.register("storage", AsyncMock(return_value={"status": "ok"}))
    agg.register("inference", AsyncMock(return_value={"status": "degraded"}))
    report = await agg.check()
    assert report.status == "degraded"
    assert not report.is_ok()


async def test_health_aggregator_one_down() -> None:
    agg = HealthAggregator()
    agg.register("storage", AsyncMock(return_value={"status": "ok"}))
    agg.register("inference", AsyncMock(side_effect=RuntimeError("backend down")))
    report = await agg.check()
    assert report.status == "down"
    assert report.subsystems["inference"]["status"] == "down"
    assert "backend down" in report.subsystems["inference"]["detail"]


async def test_health_aggregator_empty() -> None:
    agg = HealthAggregator()
    report = await agg.check()
    assert report.status == "ok"
    assert report.subsystems == {}


# --- Entrypoint wiring smoke test ---

async def test_main_starts_and_shuts_down_cleanly() -> None:
    """Simulate a full startup+shutdown cycle with mocked backends."""
    mock_registry = MagicMock()
    mock_registry.health = AsyncMock(return_value={"status": "ok", "backends": {}})
    mock_registry.events._nc = None  # no NATS drain

    mock_router = MagicMock()
    mock_router.health = AsyncMock(return_value={"status": "ok", "backends": {}})

    with (
        patch("gaia_server.entrypoint.create_registry", AsyncMock(return_value=mock_registry)),
        patch("gaia_server.entrypoint.create_router", AsyncMock(return_value=mock_router)),
    ):
        from gaia_server.entrypoint import main

        # Run main but cancel it immediately after health check passes
        # by injecting a stop signal via the event loop
        async def _run_with_auto_stop() -> None:
            task = asyncio.create_task(main())
            await asyncio.sleep(0.1)   # let startup complete
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass  # expected — clean cancellation is correct shutdown behavior

        await _run_with_auto_stop()
