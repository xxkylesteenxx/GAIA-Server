# GAIA Post-Quantum Cryptography Specification (condensed)

Source: GAIA Post-Quantum Cryptography Production Deployment Spec v1.0

## Standards basis

- **ML-KEM-768** (FIPS 203) — key encapsulation / envelope key bootstrap
- **ML-DSA-65** (FIPS 204) — digital signatures
- **OpenSSL 3.5+** — production crypto runtime (native ML-KEM, ML-DSA, X25519MLKEM768)
- **Istio 1.29.x** — `COMPLIANCE_POLICY=pqc` (experimental, TLS 1.3 + X25519MLKEM768)

## Three-plane architecture

1. **Transport plane** — hybrid PQ TLS via OpenSSL 3.5+ and Istio PQC enforcement
2. **Artifact authenticity plane** — ML-DSA-65 signatures on high-value objects
3. **Envelope protection plane** — ML-KEM-768 wrapping symmetric data-encryption keys

## Mandatory signature targets (ML-DSA-65)

- consciousness state snapshots
- core-to-core policy updates
- emergency override directives
- deployment manifests
- model lineage manifests
- memory compaction manifests
- backup manifests
- audit checkpoint digests
- ADRs altering security posture
- root key rotation events

## Important limitations

- `COMPLIANCE_POLICY=pqc` alone is NOT sufficient to claim PQC compliance (Istio docs)
- Istio workload certs are RSA/ECDSA by default — not ML-DSA (compatibility boundary)
- oqs-provider is prototyping-grade only — NOT a production dependency
- ML-DSA-65 artifact signatures are the authoritative PQ authenticity layer

## TLS profile (GAIA baseline)

```ini
MinProtocol = TLSv1.3
MaxProtocol = TLSv1.3
Groups = X25519MLKEM768:X25519:SecP256r1MLKEM768
```
