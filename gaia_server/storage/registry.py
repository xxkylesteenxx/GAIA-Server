"""StorageRegistry — single wiring point for all GAIA-Server storage backends.

Holds references to JetStreamEventStore, MinIOCheckpointStore, and EtcdMetadataStore.
Exposes aggregate health check across all three backends.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from gaia_server.storage.etcd import EtcdMetadataStore
from gaia_server.storage.jetstream import JetStreamEventStore
from gaia_server.storage.minio import MinIOCheckpointStore


@dataclass
class StorageRegistry:
    """Wires the three storage backends together and exposes aggregate health."""

    events: JetStreamEventStore
    checkpoints: MinIOCheckpointStore
    metadata: EtcdMetadataStore

    async def health(self) -> Mapping[str, Any]:
        """Aggregate health across all three backends."""
        results = await _gather_health(
            self.events.health(),
            self.checkpoints.health(),
            self.metadata.health(),
        )
        overall = "ok" if all(r.get("status") == "ok" for r in results) else "degraded"
        return {
            "status": overall,
            "backends": results,
        }


async def _gather_health(*coros) -> list[Mapping[str, Any]]:
    import asyncio
    return list(await asyncio.gather(*coros, return_exceptions=False))
