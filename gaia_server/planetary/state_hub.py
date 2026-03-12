"""PlanetaryStateHub — fleet-level aggregator for node-published PlanetaryState snapshots.

Each GAIA node (IoT, Desktop, Laptop, Server) can push a partial or full
PlanetaryState snapshot. The hub merges snapshots by node_id, maintains a
latest-per-node registry, and exposes a fleet summary.

This is the server-side counterpart to gaia_iot.planetary.publisher.
Production path: IoT nodes push via gRPC planetary_state_push(); this hub
holds the in-memory state until a durable propagation layer is wired.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class PlanetarySnapshot:
    """A node-local partial planetary-state snapshot."""
    node_id: str
    timestamp: float = field(default_factory=time.time)
    observations: dict[str, Any] = field(default_factory=dict)
    energy: dict[str, Any] = field(default_factory=dict)
    climate: dict[str, Any] = field(default_factory=dict)
    biosphere: dict[str, Any] = field(default_factory=dict)
    network: dict[str, Any] = field(default_factory=dict)
    integrity: dict[str, Any] = field(default_factory=dict)
    love_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class PlanetaryStateHub:
    """Fleet-level registry and aggregator for PlanetaryState snapshots.

    Thread-safety: single-threaded async model assumed (asyncio). If
    multi-threaded access is needed, wrap mutation methods with asyncio.Lock.
    """

    def __init__(self) -> None:
        self._snapshots: dict[str, PlanetarySnapshot] = {}
        log.info("[PlanetaryStateHub] initialised")

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def push(self, snapshot: PlanetarySnapshot) -> None:
        """Accept a node snapshot and update the registry."""
        self._snapshots[snapshot.node_id] = snapshot
        log.debug(
            "[PlanetaryStateHub] snapshot received from node=%s ts=%.3f obs=%d",
            snapshot.node_id,
            snapshot.timestamp,
            len(snapshot.observations),
        )

    def push_dict(self, node_id: str, payload: dict[str, Any]) -> PlanetarySnapshot:
        """Accept a raw dict payload from a gRPC push and upsert."""
        snapshot = PlanetarySnapshot(
            node_id=node_id,
            timestamp=payload.get("timestamp", time.time()),
            observations=payload.get("observations", {}),
            energy=payload.get("energy", {}),
            climate=payload.get("climate", {}),
            biosphere=payload.get("biosphere", {}),
            network=payload.get("network", {}),
            integrity=payload.get("integrity", {}),
            love_score=float(payload.get("love_score", 0.0)),
            metadata=payload.get("metadata", {}),
        )
        self.push(snapshot)
        return snapshot

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def snapshot(self, node_id: str) -> PlanetarySnapshot | None:
        """Return the latest snapshot for a specific node, or None."""
        return self._snapshots.get(node_id)

    def fleet_summary(self) -> dict[str, Any]:
        """Return a summary dict aggregated across all known nodes."""
        if not self._snapshots:
            return {"node_count": 0, "nodes": [], "fleet_love_score": 0.0}

        nodes = list(self._snapshots.keys())
        avg_love = sum(s.love_score for s in self._snapshots.values()) / len(self._snapshots)
        latest_ts = max(s.timestamp for s in self._snapshots.values())

        return {
            "node_count": len(nodes),
            "nodes": nodes,
            "fleet_love_score": round(avg_love, 4),
            "latest_snapshot_ts": latest_ts,
            "snapshots": {
                nid: {
                    "timestamp": s.timestamp,
                    "love_score": s.love_score,
                    "observation_count": len(s.observations),
                }
                for nid, s in self._snapshots.items()
            },
        }

    def all_snapshots(self) -> list[PlanetarySnapshot]:
        """Return all current snapshots as a list."""
        return list(self._snapshots.values())

    def node_count(self) -> int:
        return len(self._snapshots)

    def clear(self) -> None:
        """Reset hub state (testing / safe-mode use only)."""
        self._snapshots.clear()
