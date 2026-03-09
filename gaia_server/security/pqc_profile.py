from __future__ import annotations

"""
GAIA Post-Quantum Cryptography Profile

Abstraction layer for ML-KEM-768 (key encapsulation) and ML-DSA-65
(digital signatures) per the GAIA PQC Production Deployment Spec v1.0.

Backend requirements:
  - OpenSSL 3.5+ with native ML-KEM / ML-DSA support
  - OR oqs-provider for research/lab environments only
    (NOT production per spec: oqs-provider is prototyping-grade)

This module defines the interface contract. Concrete backends are
swapped in at instantiation time via the `backend` parameter.

Current backends:
  'software-stub'  - safe no-op stub for testing without OpenSSL 3.5+
  'openssl35'      - production backend (requires OpenSSL 3.5+ bindings)

Cryptographic control matrix (per spec):
  Service-to-service TLS  : X25519MLKEM768 hybrid group via Istio PQC enforcement
  Artifact signing        : ML-DSA-65
  Envelope key bootstrap  : ML-KEM-768
  Data at rest            : AES-256-GCM, keys wrapped via ML-KEM-768
  Mesh workload certs     : RSA/ECDSA (transitional - Istio limitation)

Mandatory first-wave signature targets:
  - consciousness state snapshots
  - core-to-core policy updates
  - emergency override directives
  - deployment manifests
  - audit checkpoint digests
  - memory checkpoint / holographic memory manifests
"""

import hashlib
import hmac
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class KEMResult:
    """Result of ML-KEM-768 encapsulation."""
    ciphertext: bytes
    shared_secret: bytes
    algorithm: str = "ML-KEM-768"


@dataclass
class SignatureResult:
    """Result of ML-DSA-65 signing."""
    signature: bytes
    algorithm: str = "ML-DSA-65"
    signer_id: str = ""


@dataclass
class VerificationResult:
    verified: bool
    algorithm: str
    reason: str = ""


class PQCProfile:
    """
    Post-quantum cryptography profile for GAIA-Server.

    Interface contract (backends must implement all methods):
      kem_encapsulate(peer_public_key) -> KEMResult
      kem_decapsulate(private_key, ciphertext) -> bytes  (shared secret)
      sign_artifact(private_key, payload) -> SignatureResult
      verify_artifact(public_key, payload, signature) -> VerificationResult
      generate_kem_keypair() -> (public_key, private_key)
      generate_sig_keypair() -> (public_key, private_key)
    """

    def __init__(self, backend: str = "software-stub", signer_id: str = "") -> None:
        self.backend = backend
        self.signer_id = signer_id
        if backend == "software-stub":
            logger.warning(
                "PQCProfile using software-stub backend. "
                "NOT production-grade. Requires OpenSSL 3.5+ for real PQC."
            )
        elif backend == "openssl35":
            self._init_openssl35()
        else:
            raise ValueError(f"Unknown PQC backend: {backend}")

    def _init_openssl35(self) -> None:
        """Validate OpenSSL 3.5+ availability. Raises if not present."""
        try:
            import ssl
            version = ssl.OPENSSL_VERSION
            # OpenSSL 3.5+ required for native ML-KEM / ML-DSA
            parts = version.split(" ")[1].split(".")
            major, minor = int(parts[0]), int(parts[1])
            if (major, minor) < (3, 5):
                raise RuntimeError(
                    f"OpenSSL 3.5+ required for production PQC. Found: {version}"
                )
            logger.info("PQCProfile: OpenSSL %s detected.", version)
        except Exception as exc:
            raise RuntimeError(f"PQCProfile openssl35 init failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Key encapsulation: ML-KEM-768
    # ------------------------------------------------------------------

    def generate_kem_keypair(self) -> Tuple[bytes, bytes]:
        """Generate ML-KEM-768 key pair. Returns (public_key, private_key)."""
        if self.backend == "software-stub":
            pub = os.urandom(32)
            priv = os.urandom(32)
            return pub, priv
        raise NotImplementedError("openssl35 KEM keygen not yet wired - use EVP_PKEY_keygen with ML-KEM-768")

    def kem_encapsulate(self, peer_public_key: bytes) -> KEMResult:
        """ML-KEM-768 encapsulate: derive shared secret + ciphertext."""
        if self.backend == "software-stub":
            shared_secret = hashlib.sha256(peer_public_key + os.urandom(16)).digest()
            ciphertext = os.urandom(48)
            return KEMResult(ciphertext=ciphertext, shared_secret=shared_secret)
        raise NotImplementedError("openssl35 KEM encapsulate not yet wired")

    def kem_decapsulate(self, private_key: bytes, ciphertext: bytes) -> bytes:
        """ML-KEM-768 decapsulate: recover shared secret from ciphertext."""
        if self.backend == "software-stub":
            return hashlib.sha256(private_key + ciphertext).digest()
        raise NotImplementedError("openssl35 KEM decapsulate not yet wired")

    # ------------------------------------------------------------------
    # Digital signatures: ML-DSA-65
    # ------------------------------------------------------------------

    def generate_sig_keypair(self) -> Tuple[bytes, bytes]:
        """Generate ML-DSA-65 key pair. Returns (public_key, private_key)."""
        if self.backend == "software-stub":
            pub = os.urandom(32)
            priv = os.urandom(64)
            return pub, priv
        raise NotImplementedError("openssl35 DSA keygen not yet wired")

    def sign_artifact(self, private_key: bytes, payload: bytes) -> SignatureResult:
        """ML-DSA-65 sign an artifact payload."""
        if self.backend == "software-stub":
            sig = hmac.new(private_key, payload, hashlib.sha256).digest()
            return SignatureResult(signature=sig, signer_id=self.signer_id)
        raise NotImplementedError("openssl35 DSA signing not yet wired")

    def verify_artifact(
        self, public_key: bytes, payload: bytes, signature: bytes
    ) -> VerificationResult:
        """ML-DSA-65 verify an artifact signature."""
        if self.backend == "software-stub":
            # stub: re-derive from public_key as proxy (not real verification)
            expected = hmac.new(public_key, payload, hashlib.sha256).digest()
            verified = hmac.compare_digest(signature, expected)
            return VerificationResult(
                verified=verified,
                algorithm="ML-DSA-65-stub",
                reason="" if verified else "signature mismatch (stub)",
            )
        raise NotImplementedError("openssl35 DSA verification not yet wired")

    # ------------------------------------------------------------------
    # TLS profile descriptor
    # ------------------------------------------------------------------

    def negotiate_tls_profile(self) -> Dict[str, Any]:
        """
        Return the required TLS profile for GAIA-Server connections.
        Enforced by Istio COMPLIANCE_POLICY=pqc in production.
        """
        return {
            "min_protocol": "TLSv1.3",
            "max_protocol": "TLSv1.3",
            "group_preference": "X25519MLKEM768:X25519:SecP256r1MLKEM768",
            "cipher_suites": [
                "TLS_AES_256_GCM_SHA384",
                "TLS_AES_128_GCM_SHA256",
            ],
            "compliance_policy": "pqc",
            "istio_min_version": "1.29.x",
        }
