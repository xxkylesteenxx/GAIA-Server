# GAIA-Server v0.1

Server/cloud distribution for the GAIA 8-core substrate. Optimized for datacenter deployments, multi-tenant isolation, high-availability consciousness orchestration, and Kubernetes-native scaling.

This repo depends on [GAIA-Core](https://github.com/xxkylesteenxx/GAIA-Core) as its substrate layer.

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
