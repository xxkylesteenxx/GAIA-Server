> See canonical source: `GAIA-Core/docs/governance/GAIA-v1-Scope-Matrix-v1.0.md`

# GAIA v1 Scope Matrix v1.0 (Mirror)

**Status:** Canonical mirror — authoritative copy lives in GAIA-Core.

**Governing rule:** Anything in the Deferred tier cannot appear in a v1 milestone plan without an explicit exception note signed off by the boundary spec owner.

For the full Must Ship / Should Ship / May Ship / Deferred tables, see: `GAIA-Core/docs/governance/GAIA-v1-Scope-Matrix-v1.0.md`

## GAIA-Server Relevant Must Ship Items

| Item | Notes |
|------|-------|
| GAIA-Server headless admin edition | Should Ship — only if Server edition reaches boot/update parity |
| mTLS between all GAIA platform services | No plaintext inter-service |
| SPIRE SVID issued to NEXUS, GUARDIAN, ATLAS | Workload identity baseline |
| Vault-based secrets management | Namespaced by service account |
| Hash-chained audit ledger | Mandatory for compliance path |
| Local inference runtime (llama.cpp baseline) | vLLM/JetStream as Should Ship upgrade |
| Prometheus/Grafana/OpenTelemetry observability | Should Ship |
