"""Settings smoke tests — no backends required."""
from __future__ import annotations

import os

from gaia_server.storage.settings import StorageSettings


def test_settings_defaults() -> None:
    """from_env() returns correct defaults when no env vars are set."""
    for key in (
        "NATS_URL", "NATS_CONNECT_TIMEOUT", "NATS_MAX_RECONNECT",
        "MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY",
        "MINIO_BUCKET", "MINIO_SECURE",
        "ETCD_HOST", "ETCD_PORT", "ETCD_NAMESPACE", "ETCD_TIMEOUT",
    ):
        os.environ.pop(key, None)

    s = StorageSettings.from_env()
    assert s.nats_url == "nats://localhost:4222"
    assert s.nats_connect_timeout == 5
    assert s.minio_endpoint == "localhost:9000"
    assert s.minio_secure is False
    assert s.minio_bucket == "gaia-checkpoints"
    assert s.etcd_host == "localhost"
    assert s.etcd_port == 2379
    assert s.etcd_namespace == "gaia"


def test_settings_from_env_overrides(monkeypatch) -> None:
    """from_env() reads overridden env vars correctly."""
    monkeypatch.setenv("NATS_URL", "nats://nats.prod.internal:4222")
    monkeypatch.setenv("MINIO_ENDPOINT", "minio.prod.internal:9000")
    monkeypatch.setenv("MINIO_SECURE", "true")
    monkeypatch.setenv("MINIO_BUCKET", "gaia-prod-checkpoints")
    monkeypatch.setenv("ETCD_HOST", "etcd.prod.internal")
    monkeypatch.setenv("ETCD_PORT", "2380")
    monkeypatch.setenv("ETCD_NAMESPACE", "gaia-prod")

    s = StorageSettings.from_env()
    assert s.nats_url == "nats://nats.prod.internal:4222"
    assert s.minio_endpoint == "minio.prod.internal:9000"
    assert s.minio_secure is True
    assert s.minio_bucket == "gaia-prod-checkpoints"
    assert s.etcd_host == "etcd.prod.internal"
    assert s.etcd_port == 2380
    assert s.etcd_namespace == "gaia-prod"
