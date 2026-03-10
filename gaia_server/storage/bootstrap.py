"""Storage bootstrap — ensure all canonical GAIA JetStream streams exist.

Call ensure_streams(nc) once at startup before any event writes.
All stream creation is idempotent: existing streams are left unchanged.

Canonical GAIA streams:
    gaia-events       — general inference, ATLAS, and core events
    gaia-checkpoints  — checkpoint epoch markers and restore signals
    gaia-federation   — inter-instance federation messages
    gaia-governance   — merge proposals, quorum decisions, dissent records
    gaia-validation   — perturbation traces, metric scores, audit artifacts
"""
from __future__ import annotations

import logging

import nats
import nats.js.api
from nats.aio.client import Client as NATSClient

log = logging.getLogger(__name__)

# Stream definitions: name -> subject filter list
# Retention: limits-based with 7-day max age for all streams.
# Replicas: 1 for dev; override via stream update in production.
_STREAMS: dict[str, list[str]] = {
    "gaia-events": ["gaia.events.>"],
    "gaia-checkpoints": ["gaia.checkpoints.>"],
    "gaia-federation": ["gaia.federation.>"],
    "gaia-governance": ["gaia.governance.>"],
    "gaia-validation": ["gaia.validation.>"],
}

_MAX_AGE_SECONDS = 7 * 24 * 60 * 60  # 7 days


async def ensure_streams(nc: NATSClient) -> None:
    """Idempotently create all canonical GAIA JetStream streams.

    Existing streams are not modified. Missing streams are created with
    limits-based retention and a 7-day max age.
    """
    js = nc.jetstream()

    for stream_name, subjects in _STREAMS.items():
        await _ensure_stream(js, stream_name, subjects)


async def _ensure_stream(
    js: nats.js.JetStreamContext,
    name: str,
    subjects: list[str],
) -> None:
    config = nats.js.api.StreamConfig(
        name=name,
        subjects=subjects,
        retention=nats.js.api.RetentionPolicy.LIMITS,
        max_age=_MAX_AGE_SECONDS,
        storage=nats.js.api.StorageType.FILE,
        num_replicas=1,
        discard=nats.js.api.DiscardPolicy.OLD,
    )
    try:
        await js.find_stream(name)
        log.debug("JetStream stream already exists: %s", name)
    except nats.errors.NotFoundError:
        await js.add_stream(config)
        log.info("Created JetStream stream: %s", name)
