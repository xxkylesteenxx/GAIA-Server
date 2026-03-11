---
v1 Boundary Compliance: IN SCOPE
Relevant v1 Sections: 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
Post-v1 Tag: NO
Post-v1 Milestone: NA
Scope Matrix Tier: MUST SHIP
---

# GAIA v1 Product Boundary Spec v1.1

**Status:** Canonical — Governs all GAIA v1 scope decisions

> See canonical source: `GAIA-Core/docs/governance/GAIA-v1-Product-Boundary-Spec-v1.1.md`

**GAIA v1 in one sentence:** GAIA v1 is a bootable, secure, AI-native operating system for desktop, laptop, and server, with one integrated Gaian experience and one scoped ATLAS Earth-aware service layer.

**Priority order for all future work:**
1. Bootable, trustworthy GAIA OS
2. Integrated Gaian experience
3. Scoped ATLAS capability
4. Platform hardening and interoperability
5. Expanded domains, devices, and ecosystem

**v1 Failure conditions** — GAIA v1 is off-boundary if it:
- Tries to become a full planetary platform before the OS is real
- Tries to become a phone OS before desktop/laptop/server are stable
- Multiplies personas, products, and modules without one coherent flagship experience
- Makes claims larger than the implemented evidence supports

**Trust success criterion:** The system boots with a verifiable signed image, the local AI runtime is issued a SPIRE workload identity from an attested node, and LUKS2 state volumes are sealed to approved PCR policy.

Full spec: `GAIA-Core/docs/governance/GAIA-v1-Product-Boundary-Spec-v1.1.md`
