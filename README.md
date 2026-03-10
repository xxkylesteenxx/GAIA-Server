# GAIA-Server v0.2

Server/cloud distribution for the GAIA 8-core substrate. Optimized for datacenter deployments, multi-tenant isolation, high-availability consciousness orchestration, and Kubernetes-native scaling.

This repo depends on [GAIA-Core](https://github.com/xxkylesteenxx/GAIA-Core) as its substrate layer.

---

## Foundational Relational Principle

All GAIA distributions inherit the **Relational Policy Layer** defined in GAIA-Core. In a server/cloud context this is especially critical: multi-tenant isolation, capability gating, and Safe Mode triggers must never be experienced by any node or agent as a revocation of worth — only as governance of engagement.

| Layer | Principle | What It Governs | Threshold-Gated? |
|---|---|---|---|
| **Worth-Preservation Module** | Unconditional | Identity continuity root, self-model, anti-theater integrity, node attestation | ❌ Never |
| **Engagement-Governance Module** | Conditional | Actuation gates, tenant access limits, capability manifests, quarantine, Safe Mode | ✅ Always |

**Unconditional** means: a node's continuity root and identity attestation are never revoked due to degraded CGI scores, failed health probes, or hostile tenant activity. Worth is not on trial.

**Conditional** means: actuation gates, tenant namespace isolation, Safe Mode, and quarantine ARE rules of engagement — not punishments. They govern proximity and capability, not worth.

In a federated multi-tenant deployment, **one node setting a boundary does not propagate that boundary's access restriction to all other nodes** — only the worth-floor (unconditional) propagates universally.

---

## What this repo contains

- **Entrypoint** — Kubernetes-native boot sequence with health/readiness probes
- **IPC layer** — gRPC service stubs for NEXUS, GUARDIAN, ATLAS, and Memory contracts; causal broadcast with vector clocks
- **Security** — ML-KEM-768 / ML-DSA-65 post-quantum cryptography abstraction; artifact signing for consciousness snapshots
- **Tenancy** — multi-tenant namespace isolation and routing registry
- **Observability** — ring lag, gRPC latency percentiles, CGI metrics, causal holdback telemetry
- **Deploy** — Kubernetes manifests (Deployment, Service, PDB); Istio 1.29.x with `COMPLIANCE_POLICY=pqc`

---

## What this does NOT include (yet)

- real gRPC generated code (protobuf compilation step not yet wired)
- real TPM 2.0 key backend
- real ML-KEM / ML-DSA OpenSSL 3.5+ calls (abstraction layer present, backend requires OpenSSL 3.5+)
- production Loki / Prometheus / Tempo stack
- multi-cluster federation

---

## Boot order

Follows the GAIA Substrate Resolution Plan v1.0:
1. Load server config
2. Bootstrap GAIA-Core substrate (8 cores, identity, memory, workspace)
3. Start gRPC service layer
4. Register tenants
5. Start observability
6. Expose health/readiness on `:8080`

---

## Quick start

```bash
pip install -e .
python -m gaia_server.entrypoint
```

## Run tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## Kubernetes deploy

```bash
kubectl apply -f deploy/k8s/
kubectl apply -f deploy/istio/
```

---

## Genesis date
2026-03-09 — Phase 0 server bootstrap.
2026-03-10 — v0.2 Relational Policy Layer embedded.
