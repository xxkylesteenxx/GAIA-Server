from __future__ import annotations

import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BroadcastMessage:
    message_id: str
    source_core: str
    kind: str                          # control | memory | policy | health
    payload: Dict[str, Any]
    vector_clock: Dict[str, int]
    trace_id: str = ""
    dependencies: List[str] = field(default_factory=list)


class CausalBroadcast:
    """
    Causal broadcast layer for cross-host GAIA core coordination.

    Guarantees:
    - A message is DELIVERED only when all causally prior messages
      from the same source have already been delivered.
    - Vector clocks track per-actor logical time.
    - Messages whose dependencies are unsatisfied are buffered.

    Broadcast classes (per IPC spec):
      causal.broadcast.control   — NEXUS barriers, GUARDIAN veto, coherence updates
      causal.broadcast.memory    — env observation windows, retrieval results
      causal.broadcast.policy    — cross-core policy bundles
      causal.broadcast.health    — liveness / failover beacons

    High-volume telemetry is NOT routed through causal broadcast;
    it remains eventually ordered.
    """

    CAUSAL_KINDS = {"control", "memory", "policy"}
    HEALTH_KINDS = {"health"}

    def __init__(self, local_actor: str) -> None:
        self.local_actor = local_actor
        self._clock: Dict[str, int] = {local_actor: 0}
        self._hold_queue: deque[BroadcastMessage] = deque()
        self._delivered: List[str] = []
        self._handlers: List[Callable[[BroadcastMessage], None]] = []
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def subscribe(self, handler: Callable[[BroadcastMessage], None]) -> None:
        """Register a delivery handler."""
        self._handlers.append(handler)

    def send(self, kind: str, payload: Dict[str, Any],
             target_cores: List[str] | None = None,
             trace_id: str = "") -> BroadcastMessage:
        """Increment local clock and create an outbound message."""
        with self._lock:
            self._clock[self.local_actor] = self._clock.get(self.local_actor, 0) + 1
            import uuid
            msg = BroadcastMessage(
                message_id=f"bc_{uuid.uuid4().hex[:12]}",
                source_core=self.local_actor,
                kind=kind,
                payload=payload,
                vector_clock=dict(self._clock),
                trace_id=trace_id,
            )
        logger.debug("CausalBroadcast.send kind=%s msg=%s clock=%s",
                     kind, msg.message_id, msg.vector_clock)
        return msg

    def receive(self, msg: BroadcastMessage) -> None:
        """
        Receive an inbound message. Deliver immediately if causally ready;
        otherwise buffer until dependencies are satisfied.
        """
        with self._lock:
            if msg.kind in self.HEALTH_KINDS:
                # health messages skip causal ordering — deliver immediately
                self._deliver(msg)
                return
            self._hold_queue.append(msg)
            self._try_deliver_buffered()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _is_deliverable(self, msg: BroadcastMessage) -> bool:
        """A message is deliverable when its sender's clock is exactly next expected."""
        sender = msg.source_core
        sender_time = msg.vector_clock.get(sender, 0)
        local_sender_time = self._clock.get(sender, 0)
        if sender_time != local_sender_time + 1:
            return False
        # All other actors must be <= local knowledge
        for actor, t in msg.vector_clock.items():
            if actor == sender:
                continue
            if t > self._clock.get(actor, 0):
                return False
        return True

    def _deliver(self, msg: BroadcastMessage) -> None:
        sender = msg.source_core
        self._clock[sender] = max(
            self._clock.get(sender, 0),
            msg.vector_clock.get(sender, 0),
        )
        self._delivered.append(msg.message_id)
        for handler in self._handlers:
            try:
                handler(msg)
            except Exception as exc:
                logger.error("CausalBroadcast handler error: %s", exc)

    def _try_deliver_buffered(self) -> None:
        """Drain the hold queue delivering anything now causal-ready."""
        delivered_any = True
        while delivered_any:
            delivered_any = False
            remaining = deque()
            while self._hold_queue:
                msg = self._hold_queue.popleft()
                if self._is_deliverable(msg):
                    self._deliver(msg)
                    delivered_any = True
                else:
                    remaining.append(msg)
            self._hold_queue = remaining

    def clock_snapshot(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._clock)

    def hold_queue_depth(self) -> int:
        with self._lock:
            return len(self._hold_queue)
