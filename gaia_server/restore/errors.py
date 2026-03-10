"""Typed restore error hierarchy.

All restore failures raise a subclass of RestoreError so callers
can catch the entire family or specific failure modes.
"""
from __future__ import annotations


class RestoreError(Exception):
    """Base class for all restore failures."""


class ManifestError(RestoreError):
    """Raised when a manifest is missing, unsigned, or hash-invalid."""


class CausalReplayError(RestoreError):
    """Raised when causal replay cannot be verified from the event log."""


class AttestationError(RestoreError):
    """Raised when attestation is missing, expired, or trust class is insufficient."""


class TrustPromotionError(RestoreError):
    """Raised when trust-state promotion fails (e.g. split-brain CAS conflict)."""
