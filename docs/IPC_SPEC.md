# GAIA IPC Specification (condensed)

Source: GAIA Inter-Process Communication Specification v1.0

## Three-tier fabric

| Layer | Mechanism | Use |
|-------|-----------|-----|
| L0 | in-process lock-free queues | same-goroutine/thread |
| L1 | memfd shared rings + eventfd | same-host hot path |
| L2 | Unix domain sockets + io_uring | same-host async service |
| L3 | gRPC + Protobuf over mTLS/PQC | cross-host control/data |
| L4 | causal broadcast + vector clocks | distributed state propagation |

## Data classes

- **Class A** (coherence critical): NEXUS barrier, GUARDIAN veto, coherence updates, health beacons → memfd locally, gRPC remotely, causal envelope required
- **Class B** (sensor/memory streaming): env observations, retrieval, fused state → memfd locally or io_uring UDS/TCP, gRPC streams remotely
- **Class C** (bulk/archival): replay logs, training exports, forensic captures → io_uring file/socket pipelines

## gRPC services

- `NexusSyncService` — cross-core coordination
- `GuardianPolicyService` — veto / approval gate
- `AtlasObservationService` — sensor ingestion
- `MemoryRetrievalService` — causal log query
- `ConsciousnessMetricsService` — CGI telemetry
- `CoreHealthService` — liveness / readiness

## Causal ordering rules

- A message is **deliverable** only when its sender counter is the next expected and all other dimensions are ≤ local knowledge.
- High-volume telemetry is NOT causally ordered — eventually ordered only.
- Causal ordering is mandatory for: NEXUS barrier state, GUARDIAN veto, memory consolidation snapshots, cross-core policy updates.

## Required observability metrics

- ring occupancy and writer/reader lag
- dropped message count by class
- io_uring SQ/CQ depth
- gRPC latency percentiles by method
- causal holdback queue size
- out-of-order arrival count
- vector-clock conflict count
- fallback path activation count
