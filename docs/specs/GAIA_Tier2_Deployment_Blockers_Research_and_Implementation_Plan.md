# GAIA Tier 2 — Deployment Blockers Research and Implementation Plan

## Executive Decisions

- **Restore:** Kubernetes StatefulSet + CSI VolumeSnapshot (default) + CRIU (selective)
- **Approval:** OPA / Rego + Temporal + Next.js + TypeScript + WebAuthn step-up auth
- **Federation:** SPIFFE / SPIRE (identity) + libp2p (transport)
- **Governance:** CRDTs (collaborative workspace) + Raft-backed quorum (authoritative decisions)

---

## Restore Invariants

1. No restore without a signed checkpoint manifest.
2. No continuity claim without causal replay verification.
3. No cross-host promotion to trusted state until attestation and manifest hashes match.
4. CRIU restore is never the only recovery path.

---

## Federation Trust States

`UNTRUSTED` → `IDENTIFIED` → `ATTESTED` → `FEDERATED` → `DEGRADED` → `QUARANTINED`

---

## Immediate ADRs

1. **ADR-005:** hybrid restore architecture
2. **ADR-006:** OPA + Temporal + Next.js + WebAuthn
3. **ADR-007:** SPIFFE/SPIRE + libp2p
4. **ADR-008:** CRDT + quorum governance
