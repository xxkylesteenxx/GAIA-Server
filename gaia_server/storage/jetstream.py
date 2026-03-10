"""JetStreamEventStore — EventEnvelope persistence via NATS JetStream.

Implements the StorageBackend protocol (write_event, read_events, exists, health).
Checkpoint methods are not implemented here; use MinIOCheckpointStore for those.
"""
from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

import nats
import nats.js
from nats.aio.client import Client as NATSClient

from gaia_core.storage import EventEnvelope
from gaia_core.storage.contracts import CheckpointRef
from gaia_core.utils.serialization import from_wire_dict, to_wire_dict


class JetStreamEventStore:
    """Stores and replays EventEnvelope objects via NATS JetStream.

    Stream names map to EventEnvelope.stream.
    Subject format: <stream>.<topic>
    """

    def __init__(self, nc: NATSClient) -> None:
        self._nc = nc
        self._js = nc.jetstream()

    # -- StorageBackend protocol --

    async def write_event(self, envelope: EventEnvelope) -> str:
        """Publish envelope to JetStream. Returns the NATS sequence as string."""
        subject = f"{envelope.stream}.{envelope.topic}"
        payload = json.dumps(to_wire_dict(envelope)).encode()
        ack = await self._js.publish(subject, payload)
        return str(ack.seq)

    async def read_events(
        self,
        stream: str,
        after_sequence: int | None = None,
        limit: int = 100,
    ) -> Sequence[EventEnvelope]:
        """Fetch up to `limit` messages from a JetStream stream."""
        deliver_policy = nats.js.api.DeliverPolicy.ALL
        start_seq: int | None = None

        if after_sequence is not None:
            deliver_policy = nats.js.api.DeliverPolicy.BY_START_SEQUENCE
            start_seq = after_sequence + 1

        config = nats.js.api.ConsumerConfig(
            filter_subject=f"{stream}.>",
            deliver_policy=deliver_policy,
            opt_start_seq=start_seq,
            max_deliver=1,
            ack_policy=nats.js.api.AckPolicy.NONE,
        )

        results: list[EventEnvelope] = []
        sub = await self._js.subscribe(
            f"{stream}.>",
            config=config,
            manual_ack=True,
        )
        try:
            for _ in range(limit):
                try:
                    msg = await sub.next_msg(timeout=0.5)
                    data = json.loads(msg.data.decode())
                    results.append(from_wire_dict(EventEnvelope, data))
                except nats.errors.TimeoutError:
                    break
        finally:
            await sub.unsubscribe()

        return results

    async def put_checkpoint(self, ref: CheckpointRef, payload: bytes) -> CheckpointRef:
        raise NotImplementedError("Use MinIOCheckpointStore for checkpoint operations")

    async def get_checkpoint(self, checkpoint_id: str) -> tuple[CheckpointRef, bytes]:
        raise NotImplementedError("Use MinIOCheckpointStore for checkpoint operations")

    async def exists(self, uri: str) -> bool:
        """Check whether a subject has any messages in the stream."""
        try:
            js_info = await self._js.stream_info(uri.split(".")[0])
            return js_info.state.messages > 0
        except Exception:
            return False

    async def health(self) -> Mapping[str, Any]:
        try:
            await self._nc.flush(timeout=2)
            return {"backend": "jetstream", "status": "ok", "connected": self._nc.is_connected}
        except Exception as exc:
            return {"backend": "jetstream", "status": "error", "detail": str(exc)}
