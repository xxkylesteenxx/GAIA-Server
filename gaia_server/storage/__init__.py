"""Storage backend implementations for GAIA-Server.

Imports are lazy to avoid triggering optional infra dependencies
(etcd3, minio, nats) when only config or contracts are needed.
Use explicit imports in application code:

    from gaia_server.storage.registry import StorageRegistry
    from gaia_server.storage.etcd import EtcdMetadataStore
    ...
"""


def __getattr__(name: str):
    """Lazy attribute loader — only imports the backend module on first access."""
    _map = {
        "EtcdMetadataStore":    "gaia_server.storage.etcd",
        "JetStreamEventStore":  "gaia_server.storage.jetstream",
        "MinIOCheckpointStore": "gaia_server.storage.minio",
        "StorageRegistry":      "gaia_server.storage.registry",
    }
    if name in _map:
        import importlib
        mod = importlib.import_module(_map[name])
        return getattr(mod, name)
    raise AttributeError(f"module 'gaia_server.storage' has no attribute {name!r}")


__all__ = [
    "EtcdMetadataStore",
    "JetStreamEventStore",
    "MinIOCheckpointStore",
    "StorageRegistry",
]
