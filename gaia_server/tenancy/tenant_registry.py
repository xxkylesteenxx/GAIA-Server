from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TenantRecord:
    tenant_id: str
    namespace: str
    isolation_mode: str        # namespace | cgroup | vm
    active: bool = True
    metadata: Dict[str, str] = field(default_factory=dict)


class TenantRegistry:
    """
    Multi-tenant isolation registry for GAIA-Server.

    Isolation modes (per ServerConfig.tenant_isolation):
      namespace  - Kubernetes namespace-level isolation (default)
      cgroup     - cgroup v2 CPU/memory reservation per tenant
      vm         - full VM-level isolation (future)

    Rules:
      - max_tenants enforced at registration time
      - tenant IDs must be unique
      - deregistered tenants are marked inactive, not deleted (audit trail)
    """

    def __init__(self, config) -> None:
        self.config = config
        self._tenants: Dict[str, TenantRecord] = {}
        self._lock = threading.Lock()

    def register(self, tenant_id: str, metadata: Optional[Dict[str, str]] = None) -> TenantRecord:
        with self._lock:
            active_count = sum(1 for t in self._tenants.values() if t.active)
            if active_count >= self.config.max_tenants:
                raise RuntimeError(
                    f"Max tenants ({self.config.max_tenants}) reached. "
                    f"Cannot register '{tenant_id}'."
                )
            if tenant_id in self._tenants:
                logger.warning("Tenant '%s' already registered. Skipping.", tenant_id)
                return self._tenants[tenant_id]
            record = TenantRecord(
                tenant_id=tenant_id,
                namespace=f"gaia-{tenant_id}",
                isolation_mode=self.config.tenant_isolation,
                metadata=metadata or {},
            )
            self._tenants[tenant_id] = record
            logger.info("Tenant registered: id=%s namespace=%s mode=%s",
                        tenant_id, record.namespace, record.isolation_mode)
            return record

    def deregister(self, tenant_id: str) -> None:
        with self._lock:
            if tenant_id not in self._tenants:
                raise KeyError(f"Unknown tenant: {tenant_id}")
            self._tenants[tenant_id].active = False
            logger.info("Tenant deregistered: id=%s", tenant_id)

    def get(self, tenant_id: str) -> TenantRecord:
        with self._lock:
            if tenant_id not in self._tenants:
                raise KeyError(f"Unknown tenant: {tenant_id}")
            return self._tenants[tenant_id]

    def list_tenants(self) -> List[str]:
        with self._lock:
            return [tid for tid, t in self._tenants.items() if t.active]

    def snapshot(self) -> List[Dict]:
        with self._lock:
            return [
                {
                    "tenant_id":      t.tenant_id,
                    "namespace":      t.namespace,
                    "isolation_mode": t.isolation_mode,
                    "active":         t.active,
                }
                for t in self._tenants.values()
            ]
