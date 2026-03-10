"""GAIA-Server entrypoint — async main() wires all subsystems and holds the process alive.

Startup sequence:
    1. configure_logging()
    2. create_registry()     — NATS + MinIO + etcd
    3. create_router()       — inference backend
    4. HealthAggregator.check()  — verify all backends reachable
    5. Install SIGINT / SIGTERM handlers
    6. Log startup complete
    7. asyncio.Event().wait()  — hold alive until signal

Shutdown sequence:
    1. Signal received — set stop event
    2. Log shutdown initiated
    3. Drain NATS connection
    4. Log shutdown complete
    5. Exit 0
"""
from __future__ import annotations

import asyncio
import logging
import signal
import sys

from gaia_server.health import HealthAggregator
from gaia_server.inference.factory import create_router
from gaia_server.logging_config import configure_logging
from gaia_server.storage.factory import create_registry

log = logging.getLogger("gaia_server")


async def main() -> None:
    configure_logging()
    log.info("GAIA-Server starting")

    # --- Wire storage ---
    log.info("Initializing storage registry")
    registry = await create_registry()

    # --- Wire inference ---
    log.info("Initializing inference router")
    router = await create_router()

    # --- Health check ---
    agg = HealthAggregator()
    agg.register("storage", registry.health)
    agg.register("inference", router.health)

    report = await agg.check()
    if report.is_ok():
        log.info("Startup health check passed: %s", report.subsystems)
    else:
        log.warning(
            "Startup health check status=%s subsystems=%s",
            report.status,
            report.subsystems,
        )
        if report.status == "down":
            log.error("One or more critical subsystems are DOWN — aborting startup")
            sys.exit(1)

    # --- Signal handling ---
    stop = asyncio.Event()

    def _handle_signal(sig: signal.Signals) -> None:
        log.info("Received signal %s — initiating graceful shutdown", sig.name)
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal, sig)

    log.info("GAIA-Server ready")

    # --- Hold alive ---
    await stop.wait()

    # --- Graceful shutdown ---
    log.info("GAIA-Server shutting down")
    await _shutdown(registry)
    log.info("GAIA-Server stopped")


async def _shutdown(registry: object) -> None:
    """Drain connections gracefully."""
    try:
        # Drain NATS if the event store exposes the connection
        nc = getattr(getattr(registry, "events", None), "_nc", None)
        if nc is not None and hasattr(nc, "drain"):
            await nc.drain()
            log.debug("NATS connection drained")
    except Exception as exc:
        log.warning("Error during shutdown drain: %s", exc)
