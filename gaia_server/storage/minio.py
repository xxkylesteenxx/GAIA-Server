"""MinIOCheckpointStore — CheckpointRef and payload persistence via MinIO.

Implements put_checkpoint, get_checkpoint, exists, and health.
Event methods are not implemented here; use JetStreamEventStore for those.
"""
from __future__ import annotations

import io
import json
from typing import Any, Mapping

from minio import Minio
from minio.error import S3Error

from gaia_core.storage import CheckpointRef
from gaia_core.storage.contracts import EventEnvelope
from gaia_core.utils.serialization import from_wire_dict, to_wire_dict


class MinIOCheckpointStore:
    """Persists CheckpointRef metadata and raw payloads in MinIO object storage.

    Object layout:
        checkpoints/<checkpoint_id>/manifest.json   — serialized CheckpointRef
        checkpoints/<checkpoint_id>/payload.bin     — raw checkpoint payload bytes
    """

    MANIFEST_SUFFIX = "manifest.json"
    PAYLOAD_SUFFIX = "payload.bin"

    def __init__(self, client: Minio, bucket: str = "gaia-checkpoints") -> None:
        self._client = client
        self._bucket = bucket

    def _manifest_key(self, checkpoint_id: str) -> str:
        return f"checkpoints/{checkpoint_id}/{self.MANIFEST_SUFFIX}"

    def _payload_key(self, checkpoint_id: str) -> str:
        return f"checkpoints/{checkpoint_id}/{self.PAYLOAD_SUFFIX}"

    # -- StorageBackend protocol --

    async def write_event(self, envelope: EventEnvelope) -> str:
        raise NotImplementedError("Use JetStreamEventStore for event operations")

    async def read_events(self, stream: str, after_sequence: int | None = None, limit: int = 100):
        raise NotImplementedError("Use JetStreamEventStore for event operations")

    async def put_checkpoint(self, ref: CheckpointRef, payload: bytes) -> CheckpointRef:
        """Write manifest JSON and raw payload bytes to MinIO."""
        manifest_bytes = json.dumps(to_wire_dict(ref)).encode()

        self._client.put_object(
            self._bucket,
            self._manifest_key(ref.checkpoint_id),
            io.BytesIO(manifest_bytes),
            length=len(manifest_bytes),
            content_type="application/json",
        )
        self._client.put_object(
            self._bucket,
            self._payload_key(ref.checkpoint_id),
            io.BytesIO(payload),
            length=len(payload),
            content_type="application/octet-stream",
        )
        return ref

    async def get_checkpoint(self, checkpoint_id: str) -> tuple[CheckpointRef, bytes]:
        """Retrieve manifest and payload from MinIO."""
        manifest_resp = self._client.get_object(
            self._bucket, self._manifest_key(checkpoint_id)
        )
        manifest_data = json.loads(manifest_resp.read().decode())
        ref = from_wire_dict(CheckpointRef, manifest_data)

        payload_resp = self._client.get_object(
            self._bucket, self._payload_key(checkpoint_id)
        )
        payload = payload_resp.read()

        return ref, payload

    async def exists(self, uri: str) -> bool:
        """Check whether an object exists in MinIO by URI (bucket/key format)."""
        try:
            parts = uri.lstrip("/").split("/", 1)
            bucket, key = (parts[0], parts[1]) if len(parts) == 2 else (self._bucket, parts[0])
            self._client.stat_object(bucket, key)
            return True
        except S3Error:
            return False

    async def health(self) -> Mapping[str, Any]:
        try:
            self._client.bucket_exists(self._bucket)
            return {"backend": "minio", "status": "ok", "bucket": self._bucket}
        except Exception as exc:
            return {"backend": "minio", "status": "error", "detail": str(exc)}
