"""InferenceRouter factory — create_router() wires the correct backend in one call.

Usage:
    from gaia_server.inference.factory import create_router

    router = await create_router()               # reads from env
    router = await create_router(settings=cfg)   # explicit settings

If LLAMA_MODEL_PATH is set, loads LlamaCppBackend and registers it.
Otherwise falls back to MockBackend only (safe for dev and test).
"""
from __future__ import annotations

import logging

from gaia_core.inference.contracts import RuntimeBackend
from gaia_server.inference.router import InferenceRouter
from gaia_server.inference.settings import InferenceSettings

log = logging.getLogger(__name__)


async def create_router(
    settings: InferenceSettings | None = None,
) -> InferenceRouter:
    """Build and return a wired InferenceRouter.

    Steps:
    1. Read settings from env if not provided.
    2. If LLAMA_MODEL_PATH is set, load LlamaCppBackend and register it.
    3. Register MockBackend (always present as fallback).
    4. Set default backend per settings.inference_default_backend.
    5. Return wired InferenceRouter.
    """
    cfg = settings or InferenceSettings.from_env()

    router = InferenceRouter(
        default_backend_name=cfg.inference_default_backend,
        timeout_ms=cfg.inference_timeout_ms,
    )

    if cfg.llama_model_path:
        try:
            from gaia_server.inference.backends.llamacpp import LlamaCppBackend
            llama = LlamaCppBackend.load(cfg)
            router.register(RuntimeBackend.LLAMA_CPP, llama)
            log.info("LlamaCppBackend registered from %s", cfg.llama_model_path)
        except Exception as exc:
            log.warning("Failed to load LlamaCppBackend: %s — falling back to mock", exc)
    else:
        log.info("LLAMA_MODEL_PATH not set — running inference in mock mode")

    return router
