"""Contract-layer smoke tests for storage types.

These tests require no running backends — only gaia-core installed.
They verify: instantiation, to_wire_dict roundtrip, from_wire_dict roundtrip.
"""
from __future__ import annotations

from datetime import datetime, timezone

from gaia_core.storage import CheckpointRef, EventEnvelope
from gaia_core.utils.serialization import from_wire_dict, to_wire_dict


def test_event_envelope_defaults() -> None:
    env = EventEnvelope()
    assert env.schema_version == "1.0"
    assert env.sequence == 0
    assert env.payload == {}


def test_event_envelope_roundtrip() -> None:
    now = datetime(2026, 3, 10, 9, 0, 0, tzinfo=timezone.utc)
    env = EventEnvelope(
        event_id="evt-001",
        stream="gaia.core",
        topic="inference.request",
        sequence=42,
        entity_id="core-nexus",
        occurred_at=now,
        correlation_id="corr-abc",
        causation_id="cause-xyz",
        payload={"prompt": "hello"},
        payload_hash="sha256:abc123",
    )
    wire = to_wire_dict(env)
    assert wire["event_id"] == "evt-001"
    assert wire["occurred_at"] == "2026-03-10T09:00:00+00:00"
    assert wire["payload"] == {"prompt": "hello"}

    restored = from_wire_dict(EventEnvelope, wire)
    assert restored.event_id == env.event_id
    assert restored.stream == env.stream
    assert restored.occurred_at == env.occurred_at
    assert restored.payload_hash == env.payload_hash


def test_checkpoint_ref_roundtrip() -> None:
    now = datetime(2026, 3, 10, 9, 0, 0, tzinfo=timezone.utc)
    ref = CheckpointRef(
        checkpoint_id="ckpt-001",
        node_id="node-alpha",
        epoch=7,
        manifest_uri="minio://gaia-checkpoints/checkpoints/ckpt-001/manifest.json",
        payload_uri="minio://gaia-checkpoints/checkpoints/ckpt-001/payload.bin",
        state_hash="sha256:def456",
        causal_cursor="seq:1042",
        created_at=now,
    )
    wire = to_wire_dict(ref)
    assert wire["epoch"] == 7
    assert wire["state_hash"] == "sha256:def456"

    restored = from_wire_dict(CheckpointRef, wire)
    assert restored.checkpoint_id == ref.checkpoint_id
    assert restored.epoch == ref.epoch
    assert restored.causal_cursor == ref.causal_cursor
    assert restored.created_at == ref.created_at
