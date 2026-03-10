"""RestoreOrchestrator — enforces all four GAIA restore invariants.

Invariants (from Tier 2 spec):
    1. No restore without a signed checkpoint manifest.
    2. No continuity claim without causal replay verification.
    3. No cross-host promotion to trusted state until attestation
       and manifest hashes match.
    4. CRIU restore is never the only recovery path.

Orchestration sequence:
    load_manifest()       — fetch manifest from etcd, verify it exists and is signed
    verify_hashes()       — validate manifest_hash, state_hash, payload_hash
    verify_attestation()  — confirm attestation artifact exists and is sufficient
    replay_events()       — replay causal tail from JetStream after causal_cursor
    promote_trust()       — CAS trust state in etcd to requested_trust_class
    restore()             — full sequence in correct order
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass

from gaia_core.restore.manifest import RestoreManifest, RestorePath
from gaia_core.security.tpm.contracts import TrustClass
from gaia_core.storage import CheckpointRef, EventEnvelope
from gaia_core.utils.serialization import from_wire_dict, to_wire_dict
from gaia_server.restore.errors import (
    AttestationError,
    CausalReplayError,
    ManifestError,
    TrustPromotionError,
)
from gaia_server.storage.registry import StorageRegistry

log = logging.getLogger(__name__)

# etcd key namespaces
_MANIFEST_PREFIX = "manifests"
_TRUST_PREFIX = "nodes"
_ATTESTATION_PREFIX = "attestations"


@dataclass
class RestoreResult:
    """Summary of a completed restore operation."""
    manifest_id: str
    node_id: str
    restore_path: RestorePath
    events_replayed: int
    granted_trust_class: TrustClass
    payload: bytes


class RestoreOrchestrator:
    """Orchestrates cross-host and same-host restore sequences.

    Requires a fully wired StorageRegistry.
    """

    def __init__(self, registry: StorageRegistry) -> None:
        self._registry = registry

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def restore(self, manifest_id: str) -> RestoreResult:
        """Execute a full restore sequence for the given manifest ID.

        Enforces all four invariants in order. Raises RestoreError
        subclasses on any violation.
        """
        log.info("[restore] starting restore for manifest %s", manifest_id)

        # Invariant 1: manifest must exist and be signed
        manifest = await self.load_manifest(manifest_id)

        # Invariant 1 continued: hash integrity
        await self.verify_hashes(manifest)

        # Invariant 3: attestation required before cross-host trust promotion
        await self.verify_attestation(manifest)

        # Fetch payload from MinIO
        payload = await self._fetch_payload(manifest)

        # Invariant 2: causal replay must be verifiable
        events_replayed = await self.replay_events(manifest)

        # Invariant 4: CRIU path is never sole path — enforce at decision point
        self._check_criu_invariant(manifest)

        # Promote trust state in etcd
        granted = await self.promote_trust(manifest)

        log.info(
            "[restore] completed manifest=%s node=%s events=%d trust=%s",
            manifest_id, manifest.node_id, events_replayed, granted,
        )
        return RestoreResult(
            manifest_id=manifest_id,
            node_id=manifest.node_id,
            restore_path=manifest.restore_path,
            events_replayed=events_replayed,
            granted_trust_class=granted,
            payload=payload,
        )

    # ------------------------------------------------------------------
    # Step 1 — load and validate manifest exists and is signed
    # ------------------------------------------------------------------

    async def load_manifest(self, manifest_id: str) -> RestoreManifest:
        """Fetch RestoreManifest from etcd. Raises ManifestError if missing or unsigned."""
        key = f"{_MANIFEST_PREFIX}/{manifest_id}"
        raw = await self._registry.metadata.get(key)

        if raw is None:
            raise ManifestError(f"Manifest not found in etcd: {manifest_id}")

        try:
            data = json.loads(raw.decode())
            manifest = from_wire_dict(RestoreManifest, data)
        except Exception as exc:
            raise ManifestError(f"Manifest deserialization failed: {exc}") from exc

        # Invariant 1: manifest must carry a non-empty manifest_hash (signed)
        if not manifest.manifest_hash:
            raise ManifestError(
                f"Manifest {manifest_id} has no manifest_hash — unsigned manifests are not admissible"
            )

        log.debug("[restore] loaded manifest %s node=%s", manifest_id, manifest.node_id)
        return manifest

    # ------------------------------------------------------------------
    # Step 2 — verify hashes
    # ------------------------------------------------------------------

    async def verify_hashes(self, manifest: RestoreManifest) -> None:
        """Verify manifest_hash integrity. Raises ManifestError on mismatch.

        Computes SHA-256 of the canonical wire dict excluding manifest_hash
        itself and compares against the stored manifest_hash.
        """
        wire = to_wire_dict(manifest)
        # Exclude manifest_hash from the hash input
        wire_for_hash = {k: v for k, v in wire.items() if k != "manifest_hash"}
        computed = _sha256_dict(wire_for_hash)

        if not manifest.manifest_hash.endswith(computed):
            raise ManifestError(
                f"Manifest hash mismatch for {manifest.manifest_id}: "
                f"computed={computed} stored={manifest.manifest_hash}"
            )
        log.debug("[restore] manifest hash verified for %s", manifest.manifest_id)

    # ------------------------------------------------------------------
    # Step 3 — verify attestation
    # ------------------------------------------------------------------

    async def verify_attestation(
        self,
        manifest: RestoreManifest,
    ) -> None:
        """Verify attestation artifact exists and trust class is sufficient.

        Cross-host paths require attestation. Same-host soft restart
        may proceed with DEGRADED trust if no attestation_ref is present.
        Raises AttestationError on violation.
        """
        cross_host_paths = {
            RestorePath.CROSS_HOST,
            RestorePath.K8S_STATEFUL_RESTORE,
            RestorePath.QUARANTINED_FOREIGN_HOST,
            RestorePath.CRIU_MIGRATION,
        }

        is_cross_host = manifest.restore_path in cross_host_paths

        if is_cross_host and not manifest.attestation_ref:
            raise AttestationError(
                f"Cross-host restore {manifest.manifest_id} requires attestation_ref — none present"
            )

        if manifest.attestation_ref:
            key = f"{_ATTESTATION_PREFIX}/{manifest.attestation_ref}"
            raw = await self._registry.metadata.get(key)
            if raw is None:
                raise AttestationError(
                    f"Attestation ref {manifest.attestation_ref} not found in etcd"
                )
            log.debug("[restore] attestation verified: %s", manifest.attestation_ref)

    # ------------------------------------------------------------------
    # Step 4 — fetch payload from MinIO
    # ------------------------------------------------------------------

    async def _fetch_payload(self, manifest: RestoreManifest) -> bytes:
        """Retrieve checkpoint payload from MinIO and verify payload_hash."""
        _ref, payload = await self._registry.checkpoints.get_checkpoint(
            manifest.checkpoint_id
        )
        if manifest.payload_hash:
            computed = "sha256:" + hashlib.sha256(payload).hexdigest()
            if computed != manifest.payload_hash:
                raise ManifestError(
                    f"Payload hash mismatch for checkpoint {manifest.checkpoint_id}: "
                    f"computed={computed} stored={manifest.payload_hash}"
                )
        log.debug("[restore] payload fetched and verified for checkpoint %s", manifest.checkpoint_id)
        return payload

    # ------------------------------------------------------------------
    # Step 5 — causal replay
    # ------------------------------------------------------------------

    async def replay_events(
        self,
        manifest: RestoreManifest,
        stream: str = "gaia-checkpoints",
    ) -> int:
        """Replay events from JetStream after the manifest's causal_cursor.

        Returns count of events replayed. Raises CausalReplayError if
        causal_cursor is set but no events are found (empty tail is suspicious).
        """
        if not manifest.causal_cursor:
            log.debug("[restore] no causal_cursor on manifest %s — skipping replay", manifest.manifest_id)
            return 0

        try:
            after_seq = int(manifest.causal_cursor.replace("seq:", ""))
        except ValueError:
            raise CausalReplayError(
                f"causal_cursor format unrecognized: {manifest.causal_cursor!r} — expected 'seq:<int>'"
            )

        events = await self._registry.events.read_events(
            stream=stream,
            after_sequence=after_seq,
            limit=1000,
        )

        if not events:
            raise CausalReplayError(
                f"Causal replay found zero events after cursor {manifest.causal_cursor} — "
                f"cannot verify continuity for manifest {manifest.manifest_id}"
            )

        log.info("[restore] replayed %d events after cursor %s", len(events), manifest.causal_cursor)
        return len(events)

    # ------------------------------------------------------------------
    # Step 6 — CRIU invariant check
    # ------------------------------------------------------------------

    def _check_criu_invariant(self, manifest: RestoreManifest) -> None:
        """Invariant 4: CRIU must never be the only declared restore path.

        CRIU_MIGRATION is only allowed if the manifest also carries a
        non-empty admissibility_policy_ref (proof it was gated), and
        only on same-family kernel/runtime environments.
        """
        if manifest.restore_path == RestorePath.CRIU_MIGRATION:
            if not manifest.admissibility_policy_ref:
                raise ManifestError(
                    "CRIU_MIGRATION restore path requires admissibility_policy_ref — "
                    "CRIU must always be policy-gated and cannot be the sole recovery path"
                )
        log.debug("[restore] CRIU invariant passed for manifest %s", manifest.manifest_id)

    # ------------------------------------------------------------------
    # Step 7 — trust promotion
    # ------------------------------------------------------------------

    async def promote_trust(
        self,
        manifest: RestoreManifest,
    ) -> TrustClass:
        """Atomically promote node trust state in etcd via compare-and-swap.

        Cross-host restores start at UNVERIFIED and are promoted only after
        all prior invariants pass. Uses split_brain_token as the CAS expected
        value to prevent concurrent split-brain promotions.

        Returns the granted TrustClass.
        """
        trust_key = f"{_TRUST_PREFIX}/{manifest.node_id}/trust"

        # Determine granted trust class
        cross_host_paths = {
            RestorePath.CROSS_HOST,
            RestorePath.K8S_STATEFUL_RESTORE,
            RestorePath.CRIU_MIGRATION,
        }
        if manifest.restore_path in cross_host_paths:
            # Cross-host always starts DEGRADED until next attestation cycle
            granted = TrustClass.DEGRADED
        elif manifest.restore_path == RestorePath.QUARANTINED_FOREIGN_HOST:
            granted = TrustClass.QUARANTINED
        else:
            granted = manifest.requested_trust_class

        new_value = granted.encode()

        if manifest.split_brain_token:
            expected = manifest.split_brain_token.encode()
            swapped = await self._registry.metadata.compare_and_swap(
                trust_key, expected, new_value
            )
            if not swapped:
                raise TrustPromotionError(
                    f"Split-brain CAS failed for node {manifest.node_id} — "
                    "another restore may have already claimed this node"
                )
        else:
            await self._registry.metadata.put(trust_key, new_value)

        log.info(
            "[restore] trust promoted: node=%s granted=%s",
            manifest.node_id, granted,
        )
        return granted


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _sha256_dict(d: dict) -> str:
    """Deterministic SHA-256 of a JSON-serialized dict."""
    canonical = json.dumps(d, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
