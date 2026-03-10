"""EtcdMetadataStore — CoordinationBackend implementation via etcd3.

Provides key/value coordination semantics for:
- checkpoint manifests
- trust state
- node registry
- lease-based liveness
- atomic compare-and-swap for split-brain prevention
"""
from __future__ import annotations

from typing import Any, Mapping

import etcd3


class EtcdMetadataStore:
    """Wraps etcd3 to provide CoordinationBackend semantics for GAIA-Server.

    Key namespacing convention:
        /gaia/<namespace>/<key>
    e.g.:
        /gaia/checkpoints/<checkpoint_id>
        /gaia/nodes/<node_id>/trust
        /gaia/manifests/<manifest_id>
    """

    def __init__(self, client: etcd3.Etcd3Client, namespace: str = "gaia") -> None:
        self._client = client
        self._ns = namespace

    def _key(self, key: str) -> str:
        return f"/{self._ns}/{key.lstrip('/')}"

    # -- CoordinationBackend protocol --

    async def get(self, key: str) -> bytes | None:
        value, _ = self._client.get(self._key(key))
        return value  # None if not found

    async def put(
        self,
        key: str,
        value: bytes,
        ttl_seconds: int | None = None,
    ) -> None:
        if ttl_seconds is not None:
            lease = self._client.lease(ttl_seconds)
            self._client.put(self._key(key), value, lease=lease)
        else:
            self._client.put(self._key(key), value)

    async def delete(self, key: str) -> None:
        self._client.delete(self._key(key))

    async def compare_and_swap(
        self,
        key: str,
        expected: bytes,
        value: bytes,
    ) -> bool:
        """Atomically set key=value only if current value == expected.

        Returns True if the swap succeeded, False if the condition failed.
        Used for split-brain token arbitration and trust-state transitions.
        """
        txn_response = self._client.transaction(
            compare=[
                self._client.transactions.value(self._key(key)) == expected,
            ],
            success=[
                self._client.transactions.put(self._key(key), value),
            ],
            failure=[],
        )
        return bool(txn_response[0])

    async def get_prefix(self, prefix: str) -> list[tuple[bytes, str]]:
        """Return all (value, key) pairs under a key prefix."""
        results = []
        for value, meta in self._client.get_prefix(self._key(prefix)):
            results.append((value, meta.key.decode()))
        return results

    async def health(self) -> Mapping[str, Any]:
        try:
            status = self._client.status()
            return {
                "backend": "etcd",
                "status": "ok",
                "leader": status.leader.id,
                "version": status.version,
            }
        except Exception as exc:
            return {"backend": "etcd", "status": "error", "detail": str(exc)}
