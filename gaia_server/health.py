"""HealthAggregator — collects and reports health across all GAIA-Server subsystems.

Usage:
    agg = HealthAggregator()
    agg.register("storage", registry.health)
    agg.register("inference", router.health)
    report = await agg.check()
    print(report.status)   # ok | degraded | down
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Mapping


@dataclass
class HealthReport:
    status: str                              # ok | degraded | down
    subsystems: dict[str, Mapping[str, Any]]
    checked_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def is_ok(self) -> bool:
        return self.status == "ok"


class HealthAggregator:
    """Runs health checks across registered subsystems concurrently."""

    def __init__(self) -> None:
        self._checks: dict[str, Callable[[], Coroutine[Any, Any, Mapping[str, Any]]]] = {}

    def register(
        self,
        name: str,
        check_fn: Callable[[], Coroutine[Any, Any, Mapping[str, Any]]],
    ) -> None:
        self._checks[name] = check_fn

    async def check(self) -> HealthReport:
        """Run all registered health checks concurrently."""
        if not self._checks:
            return HealthReport(status="ok", subsystems={})

        names = list(self._checks.keys())
        coros = [self._checks[n]() for n in names]
        results = await asyncio.gather(*coros, return_exceptions=True)

        subsystems: dict[str, Mapping[str, Any]] = {}
        for name, result in zip(names, results):
            if isinstance(result, Exception):
                subsystems[name] = {"status": "down", "detail": str(result)}
            else:
                subsystems[name] = result  # type: ignore[assignment]

        statuses = {v.get("status", "unknown") for v in subsystems.values()}
        if statuses == {"ok"}:
            overall = "ok"
        elif "down" in statuses:
            overall = "down"
        else:
            overall = "degraded"

        return HealthReport(status=overall, subsystems=subsystems)
