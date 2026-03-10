"""StorageRegistry factory — create_registry() wires all three backends in one call.

Usage:
    from gaia_server.storage.factory import create_registry

    registry = await create_registry()                    # reads from env
    registry = await create_registry(settings=my_cfg)    # explicit settings

The returned StorageRegistry is fully connected and ready. Call
    await registry.health()
to confirm all backends are reachable before accepting traffic.
"""
from __future__ import annotations

import logging

import etcd3
import nats
from minio import Minio

from gaia_server.storage.bootstrap import ensure_streams
from gaia_server.storage.etcd import EtcdMetadataStore
from gaia_server.storage.jetstream import JetStreamEventStore
from gaia_server.storage.minio import MinIOCheckpointStore
from gaia_server.storage.registry import StorageRegistry
from gaia_server.storage.settings import StorageSettings

log = logging.getLogger(__name__)


async def create_registry(
    settings: StorageSettings | None = None,
) -> StorageRegistry:
    """Connect to all three storage backends and return a wired StorageRegistry.

    Steps:
    1. Read settings from env if not provided.
    2. Connect NATS client.
    3. Ensure canonical JetStream streams exist (idempotent).
    4. Create MinIO client and ensure bucket exists.
    5. Create etcd3 client.
    6. Wrap all three in backend classes.
    7. Return StorageRegistry.
    """
    cfg = settings or StorageSettings.from_env()

    # --- NATS / JetStream ---
    log.info("Connecting to NATS at %s", cfg.nats_url)
    nc = await nats.connect(
        cfg.nats_url,
        connect_timeout=cfg.nats_connect_timeout,
        max_reconnect_attempts=cfg.nats_max_reconnect,
    )
    await ensure_streams(nc)
    event_store = JetStreamEventStore(nc)

    # --- MinIO ---
    log.info("Connecting to MinIO at %s (secure=%s)", cfg.minio_endpoint, cfg.minio_secure)
    minio_client = Minio(
        cfg.minio_endpoint,
        access_key=cfg.minio_access_key,
        secret_key=cfg.minio_secret_key,
        secure=cfg.minio_secure,
    )
    _ensure_bucket(minio_client, cfg.minio_bucket)
    checkpoint_store = MinIOCheckpointStore(minio_client, bucket=cfg.minio_bucket)

    # --- etcd ---
    log.info("Connecting to etcd at %s:%s", cfg.etcd_host, cfg.etcd_port)
    etcd_client = etcd3.client(
        host=cfg.etcd_host,
        port=cfg.etcd_port,
        timeout=cfg.etcd_timeout,
    )
    metadata_store = EtcdMetadataStore(etcd_client, namespace=cfg.etcd_namespace)

    registry = StorageRegistry(
        events=event_store,
        checkpoints=checkpoint_store,
        metadata=metadata_store,
    )

    log.info("StorageRegistry created successfully")
    return registry


def _ensure_bucket(client: Minio, bucket: str) -> None:
    """Create the MinIO bucket if it does not already exist."""
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
        log.info("Created MinIO bucket: %s", bucket)
    else:
        log.debug("MinIO bucket already exists: %s", bucket)
