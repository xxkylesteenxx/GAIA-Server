"""LlamaCppBackend — llama-cpp-python adapter implementing InferenceBackend.

Loaded only when LLAMA_MODEL_PATH is set. Import is deferred so that
gaia-server starts cleanly without a model file in mock/dev mode.

Supported task types:
    GENERATE   — text completion via Llama.__call__
    EMBED      — embedding via Llama.embed

All other task types return an error InferResponse without raising.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Mapping

from gaia_core.inference.contracts import InferRequest, InferResponse, RuntimeBackend, TaskType

log = logging.getLogger(__name__)


class LlamaCppBackend:
    """Wraps a loaded llama-cpp-python Llama model."""

    BACKEND = RuntimeBackend.LLAMA_CPP

    def __init__(self, model: Any) -> None:
        # model is a llama_cpp.Llama instance; typed as Any to avoid
        # hard import at module level so mock mode works without llama-cpp-python
        self._model = model

    @classmethod
    def load(cls, settings: Any) -> LlamaCppBackend:
        """Load a Llama model from settings.llama_model_path."""
        try:
            from llama_cpp import Llama  # deferred import
        except ImportError as exc:
            raise RuntimeError(
                "llama-cpp-python is not installed. "
                "Install gaia-server with the 'llama' extra or set INFERENCE_DEFAULT_BACKEND=mock."
            ) from exc

        log.info(
            "Loading llama.cpp model from %s (n_ctx=%d, gpu_layers=%d)",
            settings.llama_model_path,
            settings.llama_n_ctx,
            settings.llama_n_gpu_layers,
        )
        model = Llama(
            model_path=settings.llama_model_path,
            n_ctx=settings.llama_n_ctx,
            n_gpu_layers=settings.llama_n_gpu_layers,
            n_threads=settings.llama_n_threads,
            verbose=settings.llama_verbose,
            embedding=True,
        )
        return cls(model)

    async def generate(self, request: InferRequest) -> InferResponse:
        prompt = str(request.payload.get("prompt", ""))
        max_tokens = request.max_tokens or 512
        temperature = request.temperature if request.temperature is not None else 0.7

        t0 = time.monotonic()
        output = self._model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=request.payload.get("stop", []),
            echo=False,
        )
        latency_ms = int((time.monotonic() - t0) * 1000)

        choice = output["choices"][0] if output.get("choices") else {}
        usage = output.get("usage", {})

        return InferResponse(
            request_id=request.request_id,
            accepted=True,
            core_id=request.core_id,
            task_type=TaskType.GENERATE,
            backend=self.BACKEND,
            model_id=request.model_id or "llama.cpp",
            result={"text": choice.get("text", ""), "finish_reason": choice.get("finish_reason")},
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            },
            latency_ms=latency_ms,
        )

    async def embed(self, request: InferRequest) -> InferResponse:
        text = str(request.payload.get("text", ""))

        t0 = time.monotonic()
        embedding = self._model.embed(text)
        latency_ms = int((time.monotonic() - t0) * 1000)

        return InferResponse(
            request_id=request.request_id,
            accepted=True,
            core_id=request.core_id,
            task_type=TaskType.EMBED,
            backend=self.BACKEND,
            model_id=request.model_id or "llama.cpp",
            result={"embedding": embedding, "dims": len(embedding)},
            usage={"tokens": len(text.split())},
            latency_ms=latency_ms,
        )

    async def health(self) -> Mapping[str, Any]:
        try:
            model_path = getattr(self._model, "model_path", "unknown")
            return {"backend": "llama.cpp", "status": "ok", "model": str(model_path)}
        except Exception as exc:
            return {"backend": "llama.cpp", "status": "error", "detail": str(exc)}
