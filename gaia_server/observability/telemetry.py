from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class TelemetrySnapshot:
    timestamp: float
    node_id: str
    composite_cgi: float
    memory_event_count: int
    core_statuses: Dict[str, str]
    grpc_latency_ms: Dict[str, float]   # method -> p99 latency stub
    causal_holdback_depth: int
    checkpoint_epoch: int
    active_tenants: int
    warnings: List[str] = field(default_factory=list)


class TelemetryCollector:
    """
    Observability collector for GAIA-Server.

    Collects per-interval snapshots of:
      - CGI evidence scores (composite + per-theory)
      - per-core liveness and last summary
      - causal broadcast holdback queue depth
      - gRPC latency percentile stubs (p50, p99)
      - memory event count
      - workspace epoch / checkpoint epoch
      - active tenant count
      - ring occupancy (stub - requires real io_uring ring metrics)

    Required metrics (per IPC spec section 9):
      - ring occupancy
      - writer/reader lag
      - dropped message count by class
      - io_uring SQ/CQ depth
      - gRPC latency percentiles by method
      - causal holdback queue size
      - out-of-order arrival count
      - vector-clock conflict count
      - fallback path activation count

    Stub values are emitted for ring/io_uring metrics until real
    infrastructure (PREEMPT_RT, dedicated rings) is in place.
    """

    COLLECTION_INTERVAL_SECONDS = 30

    def __init__(self, substrate, config) -> None:
        self.substrate = substrate
        self.config = config
        self._running = False
        self._thread: threading.Thread | None = None
        self._history: List[TelemetrySnapshot] = []
        self._lock = threading.Lock()

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._thread.start()
        logger.info("TelemetryCollector started. interval=%ds",
                    self.COLLECTION_INTERVAL_SECONDS)

    def stop(self) -> None:
        self._running = False
        logger.info("TelemetryCollector stopped.")

    def _collect_loop(self) -> None:
        while self._running:
            try:
                snap = self._collect()
                with self._lock:
                    self._history.append(snap)
                    if len(self._history) > 1000:
                        self._history = self._history[-1000:]
                self._log_snapshot(snap)
            except Exception as exc:
                logger.error("TelemetryCollector error: %s", exc)
            time.sleep(self.COLLECTION_INTERVAL_SECONDS)

    def _collect(self) -> TelemetrySnapshot:
        snapshot = self.substrate.consciousness_snapshot()
        core_statuses = {
            name: state.get("last_summary", "unknown")
            for name, state in snapshot["core_states"].items()
        }
        workspace = snapshot.get("workspace", {})
        return TelemetrySnapshot(
            timestamp=time.time(),
            node_id=self.config.node_id,
            composite_cgi=snapshot["evidence"]["composite_cgi"],
            memory_event_count=snapshot["memory_event_count"],
            core_statuses=core_statuses,
            grpc_latency_ms={
                # stubs — replace with real gRPC interceptor metrics
                "NexusSyncService/Synchronize":       0.0,
                "GuardianPolicyService/Evaluate":     0.0,
                "AtlasObservationService/Ingest":     0.0,
                "MemoryRetrievalService/Replay":      0.0,
                "ConsciousnessMetricsService/Snapshot": 0.0,
                "CoreHealthService/Health":            0.0,
            },
            causal_holdback_depth=0,   # stub — wire to CausalBroadcast.hold_queue_depth()
            checkpoint_epoch=workspace.get("epoch", 0),
            active_tenants=0,          # wire to TenantRegistry.list_tenants()
        )

    def _log_snapshot(self, snap: TelemetrySnapshot) -> None:
        logger.info(
            "[telemetry] node=%s cgi=%.3f events=%d epoch=%d tenants=%d holdback=%d",
            snap.node_id,
            snap.composite_cgi,
            snap.memory_event_count,
            snap.checkpoint_epoch,
            snap.active_tenants,
            snap.causal_holdback_depth,
        )
        if snap.warnings:
            for w in snap.warnings:
                logger.warning("[telemetry] %s", w)

    def latest(self) -> TelemetrySnapshot | None:
        with self._lock:
            return self._history[-1] if self._history else None

    def history(self, limit: int = 100) -> List[TelemetrySnapshot]:
        with self._lock:
            return list(self._history[-limit:])
