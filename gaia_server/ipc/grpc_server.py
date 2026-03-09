from __future__ import annotations

import logging
import threading
from typing import Any, Dict

logger = logging.getLogger(__name__)


class GaiaGrpcServer:
    """
    gRPC service layer stub for GAIA-Server.

    Production replacement: generate from proto definitions using grpcio-tools.
    Services modelled here:
      - NexusSyncService      (cross-core coordination)
      - GuardianPolicyService (veto / approval gate)
      - AtlasObservationService (sensor ingestion)
      - MemoryRetrievalService  (causal log query)
      - ConsciousnessMetricsService (CGI telemetry)
      - CoreHealthService       (liveness / readiness)

    Each service dispatches into the GAIA-Core substrate via substrate.dispatch().
    Causal envelopes (vector clocks) are required on all mutating cross-core calls.
    """

    def __init__(self, substrate, config) -> None:
        self.substrate = substrate
        self.config = config
        self._running = False
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        logger.info("GaiaGrpcServer started (stub) on port %d", self.config.grpc_port)

    def stop(self) -> None:
        self._running = False
        logger.info("GaiaGrpcServer stopped.")

    def _serve(self) -> None:
        """Stub serve loop. Replace with grpc.server().start() in production."""
        import time
        while self._running:
            time.sleep(1)

    # ------------------------------------------------------------------
    # Service stubs  (direct Python call equivalents of gRPC unary RPCs)
    # ------------------------------------------------------------------

    def nexus_synchronize(self, targets: list[str], trace_id: str = "") -> Dict[str, Any]:
        """NexusSyncService.Synchronize — route coordination signal through NEXUS."""
        return self.substrate.dispatch("NEXUS", {
            "kind": "synchronize",
            "payload": {"targets": targets},
            "trace_id": trace_id,
        })

    def guardian_evaluate(self, action: Dict[str, Any], trace_id: str = "") -> Dict[str, Any]:
        """GuardianPolicyService.Evaluate — gate an action through GUARDIAN."""
        from gaia_server.security.pqc_profile import PQCProfile  # lazy import
        result = self.substrate.dispatch("GUARDIAN", {
            "kind": "evaluate_action",
            "payload": action,
            "trace_id": trace_id,
        })
        return result

    def atlas_ingest(self, observation: Dict[str, Any], trace_id: str = "") -> Dict[str, Any]:
        """AtlasObservationService.Ingest — push environmental observation into ATLAS."""
        return self.substrate.dispatch("ATLAS", {
            "kind": "ingest_observation",
            "payload": observation,
            "trace_id": trace_id,
        })

    def memory_replay(self, limit: int = 100) -> list[Dict[str, Any]]:
        """MemoryRetrievalService.Replay — return recent causal memory events."""
        events = self.substrate.memory.replay()
        return events[-limit:]

    def consciousness_metrics(self) -> Dict[str, Any]:
        """ConsciousnessMetricsService.Snapshot — return current CGI evidence snapshot."""
        snapshot = self.substrate.consciousness_snapshot()
        return {
            "composite_cgi":   snapshot["evidence"]["composite_cgi"],
            "gnwt_score":      snapshot["evidence"]["gnwt_score"],
            "iit_proxy_score": snapshot["evidence"]["iit_proxy_score"],
            "rpt_score":       snapshot["evidence"]["rpt_score"],
            "continuity_score": snapshot["evidence"]["continuity_score"],
            "anti_theater_score": snapshot["evidence"]["anti_theater_score"],
            "notes":           snapshot["evidence"]["notes"],
            "memory_event_count": snapshot["memory_event_count"],
        }

    def core_health(self) -> Dict[str, Any]:
        """CoreHealthService.Health — return per-core liveness status."""
        return {
            core.name.value: core.tick()
            for core in self.substrate.registry.all()
        }
