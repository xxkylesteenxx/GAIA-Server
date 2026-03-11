# GAIA Inter-Process Communication Specification v1.0

**Status:** Repo-ready architecture specification  
**Scope:** zero-copy local IPC, asynchronous I/O, gRPC/Protobuf contracts, causal broadcast ordering

---

## 1. Executive Position

GAIA should use a **three-tier IPC fabric**:

1. **Local fast path:** `memfd` + shared memory rings + eventfd/futex
2. **Host async transport:** `io_uring` for file, socket, and queue operations
3. **Networked contract plane:** gRPC with Protobuf schemas, wrapped in causal metadata for cross-core ordering

---

## 2. Transport layers

```text
L0  In-process: lock-free queues / channels
L1  Same-host hot path: memfd shared rings + eventfd/futex
L2  Same-host async service path: Unix domain sockets + io_uring
L3  Cross-host control/data path: gRPC + Protobuf over mTLS / PQC transport
L4  Distributed state propagation: causal broadcast envelope with vector clocks
```

---

## 3. Base gRPC envelope

```proto
message GaiaEnvelope {
  string message_id = 1;
  string source_core = 2;
  string target_core = 3;
  uint64 monotonic_ns = 4;
  string trace_id = 5;
  bytes causal_clock = 6;
  string contract_version = 7;
  bytes auth_context = 8;
}
```

---

## 4. Bottom line

GAIA should use **`memfd` for same-host zero-copy exchange, `io_uring` for async I/O execution, and gRPC/Protobuf for typed cross-core contracts**, with **causal broadcast and vector clocks** on any distributed state path that must preserve dependency order.
