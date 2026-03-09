from __future__ import annotations

"""
GAIA Artifact Signer

Signs and verifies high-value GAIA objects with ML-DSA-65.

Mandatory signature targets (per PQC spec section 8.1):
  - consciousness state snapshots
  - core-to-core policy updates
  - emergency override directives
  - deployment manifests
  - model lineage manifests
  - holographic memory compaction manifests
  - backup manifests
  - audit checkpoint digests
  - ADRs that alter security posture
  - root key rotation events

Verification policy for high-risk operations:
  - ML-DSA-65 signature must verify
  - signer identity must be authorized
  - signing key must not be revoked
  - object version and monotonic sequence checks must pass
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from gaia_server.security.pqc_profile import PQCProfile, SignatureResult, VerificationResult

logger = logging.getLogger(__name__)


@dataclass
class SignedArtifact:
    artifact_kind: str
    payload_digest: str          # SHA-256 hex of canonical payload
    payload: Dict[str, Any]
    signature: bytes
    algorithm: str
    signer_id: str
    signed_at: float             # unix timestamp
    manifest_version: int = 1
    sequence: int = 0
    kem_metadata: str = "ML-KEM-768"  # envelope key bootstrap algorithm
    notes: List[str] = field(default_factory=list)


class ArtifactSigner:
    """
    Signs and verifies GAIA artifacts using the PQC profile.

    Every signed artifact carries:
      - payload digest
      - manifest version
      - signer identity
      - ML-DSA-65 signature
      - KEM metadata
    """

    MANDATORY_KINDS = {
        "consciousness_snapshot",
        "policy_update",
        "emergency_override",
        "deployment_manifest",
        "model_lineage",
        "memory_compaction_manifest",
        "backup_manifest",
        "audit_checkpoint",
        "adr_security",
        "root_key_rotation",
    }

    def __init__(self, pqc: PQCProfile, private_key: bytes, public_key: bytes) -> None:
        self.pqc = pqc
        self.private_key = private_key
        self.public_key = public_key
        self._sequence = 0

    def sign(self, artifact_kind: str, payload: Dict[str, Any]) -> SignedArtifact:
        """Sign a GAIA artifact. Logs warning if kind is not in mandatory list."""
        if artifact_kind not in self.MANDATORY_KINDS:
            logger.warning(
                "ArtifactSigner: kind '%s' is not a mandatory signature target.",
                artifact_kind,
            )
        canonical = json.dumps(payload, sort_keys=True, default=str).encode()
        digest = hashlib.sha256(canonical).hexdigest()
        sig_result: SignatureResult = self.pqc.sign_artifact(self.private_key, canonical)
        self._sequence += 1
        artifact = SignedArtifact(
            artifact_kind=artifact_kind,
            payload_digest=digest,
            payload=payload,
            signature=sig_result.signature,
            algorithm=sig_result.algorithm,
            signer_id=sig_result.signer_id or self.pqc.signer_id,
            signed_at=time.time(),
            sequence=self._sequence,
        )
        logger.info(
            "ArtifactSigner.sign kind=%s digest=%s seq=%d",
            artifact_kind, digest[:16], self._sequence,
        )
        return artifact

    def verify(self, artifact: SignedArtifact) -> VerificationResult:
        """Verify a signed GAIA artifact."""
        canonical = json.dumps(artifact.payload, sort_keys=True, default=str).encode()
        recomputed_digest = hashlib.sha256(canonical).hexdigest()
        if recomputed_digest != artifact.payload_digest:
            return VerificationResult(
                verified=False,
                algorithm=artifact.algorithm,
                reason="payload digest mismatch",
            )
        result = self.pqc.verify_artifact(
            self.public_key, canonical, artifact.signature
        )
        if not result.verified:
            logger.warning(
                "ArtifactSigner.verify FAILED kind=%s reason=%s",
                artifact.artifact_kind, result.reason,
            )
        return result

    def sign_consciousness_snapshot(self, snapshot: Dict[str, Any]) -> SignedArtifact:
        """Convenience method: sign a consciousness state snapshot."""
        return self.sign("consciousness_snapshot", snapshot)

    def sign_checkpoint(self, checkpoint: Dict[str, Any]) -> SignedArtifact:
        """Convenience method: sign a checkpoint manifest."""
        return self.sign("audit_checkpoint", checkpoint)
