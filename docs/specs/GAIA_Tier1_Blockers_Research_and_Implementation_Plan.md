# GAIA Tier 1 — Research and Implementation Plan

## Final stack choices
- **Edge inference runtime:** `llama.cpp`
- **Server LLM runtime:** `vLLM`
- **Multi-model serving plane:** `NVIDIA Triton Inference Server`
- **Durable object storage:** `MinIO`
- **Consistent metadata / coordination store:** `etcd`
- **Durable causal log / WAL stream:** `NATS JetStream`
- **TPM userspace / attestation tooling:** `tpm2-tools`, `tpm2-tss`, `tpm2-pytss`
- **Measured boot chain:** `UEFI Secure Boot + UKI + systemd-stub + ukify + systemd-cryptenroll + IMA`
- **Earth-system connectors, wave 1:** `NOAA/NWS`, `USGS Water Data APIs`, `GBIF`, `iNaturalist`

---

## Runtime Mapping

| Node | Runtime |
|------|---------|
| GAIA-Laptop / Desktop | `llama.cpp` |
| GAIA-IoT | tiny classifiers + optional `llama.cpp` gateway |
| GAIA-Server | `vLLM` (generative) + `Triton` (embeddings/classifiers) |
| GAIA-Meta | `vLLM` + `Triton` fleet routing |

---

## Storage Mapping

| Store | Use |
|-------|-----|
| MinIO | checkpoints, artifacts, evidence blobs, snapshots |
| etcd | node registration, routing policy, continuity heads, leases |
| JetStream | causal memory log, WAL, action stream, guardian decisions |

---

## Delivery Sequence

- **Phase 1:** inference abstraction, MinIO/JetStream/etcd integration, observation schema
- **Phase 2:** edge llama.cpp, server vLLM, Triton for embeddings
- **Phase 3:** TPM quote/verify/seal path, quarantine/degraded boot
- **Phase 4:** NOAA/USGS connectors, GBIF/iNaturalist, observation fusion
- **Phase 5:** fleet attestation, cross-node replay/sync hardening
