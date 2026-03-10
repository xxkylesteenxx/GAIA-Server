"""InferenceSettings — all inference backend configuration via environment variables.

Env vars and defaults:
    LLAMA_MODEL_PATH            (required for llama.cpp backend)
    LLAMA_N_CTX                 4096
    LLAMA_N_GPU_LAYERS          0          (CPU-only by default)
    LLAMA_N_THREADS             4
    LLAMA_VERBOSE               false

    INFERENCE_TIMEOUT_MS        30000
    INFERENCE_MAX_TOKENS        512
    INFERENCE_DEFAULT_BACKEND   mock       (mock | llama.cpp)
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class InferenceSettings:
    # llama.cpp model
    llama_model_path: str | None
    llama_n_ctx: int
    llama_n_gpu_layers: int
    llama_n_threads: int
    llama_verbose: bool

    # runtime
    inference_timeout_ms: int
    inference_max_tokens: int
    inference_default_backend: str

    @classmethod
    def from_env(cls) -> InferenceSettings:
        return cls(
            llama_model_path=os.environ.get("LLAMA_MODEL_PATH") or None,
            llama_n_ctx=int(os.environ.get("LLAMA_N_CTX", "4096")),
            llama_n_gpu_layers=int(os.environ.get("LLAMA_N_GPU_LAYERS", "0")),
            llama_n_threads=int(os.environ.get("LLAMA_N_THREADS", "4")),
            llama_verbose=os.environ.get("LLAMA_VERBOSE", "false").lower() == "true",

            inference_timeout_ms=int(os.environ.get("INFERENCE_TIMEOUT_MS", "30000")),
            inference_max_tokens=int(os.environ.get("INFERENCE_MAX_TOKENS", "512")),
            inference_default_backend=os.environ.get("INFERENCE_DEFAULT_BACKEND", "mock"),
        )
