from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ServerConfig:
    # identity
    node_id: str = "gaia-server-node-01"
    cluster_id: str = "gaia-cluster-main"

    # runtime
    grpc_port: int = 50051
    health_port: int = 8080
    worker_threads: int = 8
    coordination_target_ms: float = 10.0
    checkpoint_interval_seconds: int = 300

    # tenancy
    max_tenants: int = 64
    tenant_isolation: str = "namespace"  # namespace | cgroup | vm

    # security
    pqc_enabled: bool = True
    pqc_kem_algorithm: str = "ML-KEM-768"
    pqc_sig_algorithm: str = "ML-DSA-65"
    tls_min_version: str = "TLSv1.3"
    tls_group_preference: str = "X25519MLKEM768"

    # observability
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    audit_log_path: str = ".gaia_server_state/audit.jsonl"

    # state paths
    state_root: str = ".gaia_server_state"

    # RT
    preempt_rt_required: bool = False   # set True in production
    cgroup_isolation: bool = False       # set True in production
    sched_ext_enabled: bool = False      # experimental, not default

    # allowed tenant namespaces
    allowed_tenants: List[str] = field(default_factory=lambda: ["default"])


DEFAULT_SERVER_CONFIG = ServerConfig()
