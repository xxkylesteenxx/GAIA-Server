"""Unit tests for RestoreOrchestrator — all four invariants.

No running backends required. All storage calls are mocked.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from gaia_core.restore.manifest import RestoreManifest, RestorePath
from gaia_core.security.tpm.contracts import TrustClass
from gaia_core.utils.serialization import to_wire_dict
from gaia_server.restore.errors import (
    AttestationError,
    CausalReplayError,
    ManifestError,
    TrustPromotionError,
)
from gaia_server.restore.orchestrator import RestoreOrchestrator


def _make_registry(
    manifest: RestoreManifest | None = None,
    attestation_exists: bool = True,
    events: list | None = None,
    cas_result: bool = True,
) -> MagicMock:
    """Build a minimal mock StorageRegistry."""
    registry = MagicMock()

    # etcd metadata mock
    async def mock_get(key: str) -> bytes | None:
        if "manifests/" in key and manifest is not None:
            return json.dumps(to_wire_dict(manifest)).encode()
        if "attestations/" in key:
            return b"present" if attestation_exists else None
        if "/trust" in key:
            return b"unverified"
        return None

    registry.metadata.get = mock_get
    registry.metadata.put = AsyncMock()
    registry.metadata.compare_and_swap = AsyncMock(return_value=cas_result)

    # MinIO checkpoint mock
    registry.checkpoints.get_checkpoint = AsyncMock(
        return_value=(MagicMock(), b"payload-bytes")
    )

    # JetStream events mock
    registry.events.read_events = AsyncMock(return_value=events or [MagicMock()])

    return registry


def _valid_manifest(**overrides) -> RestoreManifest:
    """Return a minimal valid RestoreManifest for testing."""
    defaults = dict(
        manifest_id="mfst-001",
        checkpoint_id="ckpt-001",
        node_id="node-alpha",
        restore_path=RestorePath.SOFT_RESTART,
        requested_trust_class=TrustClass.TRUSTED,
        manifest_hash="sha256:placeholder",  # orchestrator checks endswith computed
        state_hash="sha256:statehash",
        payload_hash="",  # skip payload hash check in most tests
        causal_cursor="seq:100",
        attestation_ref=None,
    )
    defaults.update(overrides)
    return RestoreManifest(**defaults)


# ------------------------------------------------------------------
# Invariant 1 — No restore without a signed manifest
# ------------------------------------------------------------------

async def test_invariant1_missing_manifest_raises() -> None:
    registry = _make_registry(manifest=None)
    orch = RestoreOrchestrator(registry)
    with pytest.raises(ManifestError, match="not found"):
        await orch.load_manifest("mfst-missing")


async def test_invariant1_unsigned_manifest_raises() -> None:
    manifest = _valid_manifest(manifest_hash="")
    registry = _make_registry(manifest=manifest)
    orch = RestoreOrchestrator(registry)
    with pytest.raises(ManifestError, match="no manifest_hash"):
        await orch.load_manifest("mfst-001")


# ------------------------------------------------------------------
# Invariant 2 — No continuity claim without causal replay
# ------------------------------------------------------------------

async def test_invariant2_empty_replay_raises() -> None:
    manifest = _valid_manifest(causal_cursor="seq:100")
    registry = _make_registry(manifest=manifest, events=[])
    orch = RestoreOrchestrator(registry)
    with pytest.raises(CausalReplayError, match="zero events"):
        await orch.replay_events(manifest)


async def test_invariant2_no_cursor_skips_replay() -> None:
    manifest = _valid_manifest(causal_cursor=None)
    registry = _make_registry(manifest=manifest)
    orch = RestoreOrchestrator(registry)
    count = await orch.replay_events(manifest)
    assert count == 0


# ------------------------------------------------------------------
# Invariant 3 — No cross-host promotion without attestation
# ------------------------------------------------------------------

async def test_invariant3_cross_host_without_attestation_raises() -> None:
    manifest = _valid_manifest(
        restore_path=RestorePath.CROSS_HOST,
        attestation_ref=None,
    )
    registry = _make_registry(manifest=manifest)
    orch = RestoreOrchestrator(registry)
    with pytest.raises(AttestationError, match="requires attestation_ref"):
        await orch.verify_attestation(manifest)


async def test_invariant3_cross_host_missing_attestation_artifact_raises() -> None:
    manifest = _valid_manifest(
        restore_path=RestorePath.CROSS_HOST,
        attestation_ref="attest-xyz",
    )
    registry = _make_registry(manifest=manifest, attestation_exists=False)
    orch = RestoreOrchestrator(registry)
    with pytest.raises(AttestationError, match="not found"):
        await orch.verify_attestation(manifest)


async def test_invariant3_same_host_no_attestation_passes() -> None:
    manifest = _valid_manifest(
        restore_path=RestorePath.SOFT_RESTART,
        attestation_ref=None,
    )
    registry = _make_registry(manifest=manifest)
    orch = RestoreOrchestrator(registry)
    await orch.verify_attestation(manifest)  # should not raise


# ------------------------------------------------------------------
# Invariant 4 — CRIU never sole recovery path
# ------------------------------------------------------------------

async def test_invariant4_criu_without_policy_ref_raises() -> None:
    manifest = _valid_manifest(
        restore_path=RestorePath.CRIU_MIGRATION,
        admissibility_policy_ref=None,
    )
    registry = _make_registry(manifest=manifest)
    orch = RestoreOrchestrator(registry)
    with pytest.raises(ManifestError, match="admissibility_policy_ref"):
        orch._check_criu_invariant(manifest)


async def test_invariant4_criu_with_policy_ref_passes() -> None:
    manifest = _valid_manifest(
        restore_path=RestorePath.CRIU_MIGRATION,
        admissibility_policy_ref="policy://criu-gate-v1",
    )
    registry = _make_registry(manifest=manifest)
    orch = RestoreOrchestrator(registry)
    orch._check_criu_invariant(manifest)  # should not raise


# ------------------------------------------------------------------
# Trust promotion — split-brain CAS
# ------------------------------------------------------------------

async def test_split_brain_cas_failure_raises() -> None:
    manifest = _valid_manifest(
        restore_path=RestorePath.CROSS_HOST,
        attestation_ref="attest-xyz",
        split_brain_token="token-abc",
    )
    registry = _make_registry(manifest=manifest, cas_result=False)
    orch = RestoreOrchestrator(registry)
    with pytest.raises(TrustPromotionError, match="Split-brain"):
        await orch.promote_trust(manifest)


async def test_cross_host_restore_grants_degraded_trust() -> None:
    manifest = _valid_manifest(
        restore_path=RestorePath.CROSS_HOST,
        attestation_ref="attest-xyz",
        requested_trust_class=TrustClass.TRUSTED,
    )
    registry = _make_registry(manifest=manifest)
    orch = RestoreOrchestrator(registry)
    granted = await orch.promote_trust(manifest)
    assert granted == TrustClass.DEGRADED


async def test_quarantined_path_grants_quarantined_trust() -> None:
    manifest = _valid_manifest(
        restore_path=RestorePath.QUARANTINED_FOREIGN_HOST,
        attestation_ref="attest-xyz",
        requested_trust_class=TrustClass.TRUSTED,
    )
    registry = _make_registry(manifest=manifest)
    orch = RestoreOrchestrator(registry)
    granted = await orch.promote_trust(manifest)
    assert granted == TrustClass.QUARANTINED
