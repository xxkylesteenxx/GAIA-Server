"""StorageSettings — all storage backend configuration via environment variables.

Env vars and defaults:
    NATS_URL                nats://localhost:4222
    NATS_CONNECT_TIMEOUT    5          (seconds)
    NATS_MAX_RECONNECT      10

    MINIO_ENDPOINT          localhost:9000
    MINIO_ACCESS_KEY        minioadmin
    MINIO_SECRET_KEY        minioadmin
    MINIO_BUCKET            gaia-checkpoints
    MINIO_SECURE            false

    ETCD_HOST               localhost
    ETCD_PORT               2379
    ETCD_NAMESPACE          gaia
    ETCD_TIMEOUT            5          (seconds)
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class StorageSettings:
    # NATS / JetStream
    nats_url: str
    nats_connect_timeout: int
    nats_max_reconnect: int

    # MinIO
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_secure: bool

    # etcd
    etcd_host: str
    etcd_port: int
    etcd_namespace: str
    etcd_timeout: int

    @classmethod
    def from_env(cls) -> StorageSettings:
        """Read all storage settings from environment variables with defaults."""
        return cls(
            nats_url=os.environ.get("NATS_URL", "nats://localhost:4222"),
            nats_connect_timeout=int(os.environ.get("NATS_CONNECT_TIMEOUT", "5")),
            nats_max_reconnect=int(os.environ.get("NATS_MAX_RECONNECT", "10")),

            minio_endpoint=os.environ.get("MINIO_ENDPOINT", "localhost:9000"),
            minio_access_key=os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
            minio_secret_key=os.environ.get("MINIO_SECRET_KEY", "minioadmin"),
            minio_bucket=os.environ.get("MINIO_BUCKET", "gaia-checkpoints"),
            minio_secure=os.environ.get("MINIO_SECURE", "false").lower() == "true",

            etcd_host=os.environ.get("ETCD_HOST", "localhost"),
            etcd_port=int(os.environ.get("ETCD_PORT", "2379")),
            etcd_namespace=os.environ.get("ETCD_NAMESPACE", "gaia"),
            etcd_timeout=int(os.environ.get("ETCD_TIMEOUT", "5")),
        )
