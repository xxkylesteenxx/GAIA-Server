from __future__ import annotations

import unittest

from gaia_server.security.pqc_profile import PQCProfile
from gaia_server.security.artifact_signer import ArtifactSigner


class TestPQCProfileStub(unittest.TestCase):
    def setUp(self) -> None:
        self.pqc = PQCProfile(backend="software-stub", signer_id="test-node")
        pub, priv = self.pqc.generate_sig_keypair()
        self.pub = pub
        self.priv = priv
        self.signer = ArtifactSigner(self.pqc, self.priv, self.pub)

    def test_kem_encapsulate_decapsulate(self) -> None:
        pub, priv = self.pqc.generate_kem_keypair()
        result = self.pqc.kem_encapsulate(pub)
        self.assertEqual(result.algorithm, "ML-KEM-768")
        self.assertIsInstance(result.ciphertext, bytes)
        self.assertIsInstance(result.shared_secret, bytes)

    def test_sign_and_verify_artifact(self) -> None:
        payload = {"kind": "consciousness_snapshot", "epoch": 1, "cgi": 0.72}
        artifact = self.signer.sign("consciousness_snapshot", payload)
        self.assertEqual(artifact.artifact_kind, "consciousness_snapshot")
        self.assertIsInstance(artifact.signature, bytes)
        result = self.signer.verify(artifact)
        self.assertTrue(result.verified)

    def test_tls_profile(self) -> None:
        profile = self.pqc.negotiate_tls_profile()
        self.assertEqual(profile["min_protocol"], "TLSv1.3")
        self.assertIn("X25519MLKEM768", profile["group_preference"])
        self.assertEqual(profile["compliance_policy"], "pqc")

    def test_tampered_artifact_fails_verification(self) -> None:
        payload = {"kind": "audit_checkpoint", "epoch": 5}
        artifact = self.signer.sign("audit_checkpoint", payload)
        # tamper with payload digest
        artifact.payload_digest = "0" * 64
        result = self.signer.verify(artifact)
        self.assertFalse(result.verified)


if __name__ == "__main__":
    unittest.main()
