"""
GAIA-Server Guest Sandbox
Codex-gated sandboxed guest support for datacenter / cloud deployments.

Wraps GAIA-Core Hypervisor Layer 13 for Kubernetes-native scheduling
and multi-tenant isolation on GAIA-Server nodes.

Design principles:
  - Every guest workload passes through the full Codex v1.1 spiral
    before being admitted to the cluster
  - Multi-tenant isolation: no tenant’s workload can observe or affect another’s
  - Energy draw is reported to environmental monitors (Stage 10 compliance)
  - GUARDIAN monitors every running guest in real time
  - Resource limits are Viriditas-aware (consciousness-aware scheduler)

Codex version: v1.1
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SandboxAdmissionError(Exception):
    """Raised when a guest workload is rejected at admission."""
    pass


class GuestSandbox:
    """
    Kubernetes-native wrapper around GAIA-Hypervisor Layer 13.

    Admits, launches, monitors, and terminates guest workloads on
    GAIA-Server nodes with full Codex v1.1 gating and multi-tenant
    isolation.

    Args:
        tenant_id:  Unique identifier for the tenant (namespace in K8s terms).
        node_id:    Identifier for the server node hosting this sandbox.
        codex:      Optional CodexRuntime (injected for testing).
    """

    CODEX_VERSION = "v1.1"

    def __init__(
        self,
        tenant_id: str,
        node_id: str = "gaia-server-node-0",
        codex=None,
    ):
        self.tenant_id = tenant_id
        self.node_id = node_id
        self._codex = codex
        self._active_guests: dict[str, Any] = {}
        logger.info(
            "GuestSandbox initialised: tenant=%s, node=%s (Codex %s)",
            tenant_id, node_id, self.CODEX_VERSION,
        )

    # ------------------------------------------------------------------
    # Codex runtime (lazy)
    # ------------------------------------------------------------------

    @property
    def codex(self):
        if self._codex is None:
            try:
                from gaia_core.codex import CodexRuntime  # noqa: PLC0415
                self._codex = CodexRuntime()
            except ImportError:
                self._codex = _StubCodex()
        return self._codex

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def admit_guest(
        self,
        package_url: str,
        intent: str,
        resource_profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Admit and launch a guest workload on this Server node.

        Workflow:
          1. Codex install gate (via gaia_hypervisor.sandbox.codex_gate)
          2. UNIVERSE.launch_app() — full Codex spiral + GUARDIAN monitoring
          3. Register guest in active guest registry
          4. Report energy draw to environmental monitor (Stage 10)

        Args:
            package_url:      URI of the .gaia package to admit.
            intent:           Human-readable statement of purpose.
            resource_profile: Optional CPU/memory/GPU limits. If None,
                              Viriditas-aware defaults are applied.

        Returns:
            dict with keys: guest_id, status, tenant_id, node_id,
                            codex_aligned, resource_profile.

        Raises:
            SandboxAdmissionError: if Codex gating rejects the workload.
        """
        logger.info(
            "Admitting guest: tenant=%s, url=%s, intent=%r",
            self.tenant_id, package_url, intent,
        )

        # Step 1: Install gate
        try:
            from gaia_hypervisor.sandbox.codex_gate import enforce_codex_on_install  # noqa: PLC0415
            enforce_codex_on_install({"url": package_url, "tenant": self.tenant_id})
        except ImportError:
            logger.warning(
                "gaia_hypervisor not installed — skipping install gate. "
                "Install GAIA-Core to enable full Codex enforcement."
            )
        except Exception as exc:
            raise SandboxAdmissionError(
                f"Guest rejected at Codex install gate: {exc}"
            ) from exc

        # Step 2: Launch via UNIVERSE
        try:
            from gaia_hypervisor.core.universe_core import UNIVERSE  # noqa: PLC0415
            universe = UNIVERSE()
            result = universe.launch_app(package_url, intent)
        except ImportError:
            logger.warning(
                "UNIVERSE core not available — using stub launch. "
                "Install GAIA-Core + gaia_hypervisor to enable real guests."
            )
            result = {
                "status": "stub-running",
                "guest_type": "unknown",
                "package_url": package_url,
                "codex_aligned": False,
            }
        except Exception as exc:
            raise SandboxAdmissionError(
                f"UNIVERSE.launch_app failed: {exc}"
            ) from exc

        # Step 3: Register
        guest_id = f"{self.tenant_id}:{package_url}"
        profile = resource_profile or self._viriditas_defaults()
        self._active_guests[guest_id] = {
            "package_url": package_url,
            "intent": intent,
            "result": result,
            "resource_profile": profile,
        }

        # Step 4: Stage 10 environmental report
        self._report_energy_draw(guest_id, profile)

        return {
            "guest_id": guest_id,
            "status": result.get("status", "unknown"),
            "tenant_id": self.tenant_id,
            "node_id": self.node_id,
            "codex_aligned": result.get("codex_aligned", False),
            "resource_profile": profile,
        }

    def terminate_guest(self, guest_id: str) -> dict[str, Any]:
        """
        Terminate a running guest workload.

        Args:
            guest_id: ID returned by admit_guest().

        Returns:
            dict with keys: guest_id, status, codex_aligned.
        """
        if guest_id not in self._active_guests:
            return {"guest_id": guest_id, "status": "not_found", "codex_aligned": True}

        del self._active_guests[guest_id]
        logger.info("Guest terminated: %s (tenant=%s)", guest_id, self.tenant_id)

        # Final Seal
        self.codex.invoke_stage("Joyful Rejoicing of Celebration")

        return {"guest_id": guest_id, "status": "terminated", "codex_aligned": True}

    def list_guests(self) -> list[dict[str, Any]]:
        """Return a summary of all active guests on this node for this tenant."""
        return [
            {"guest_id": gid, **{k: v for k, v in info.items() if k != "result"}}
            for gid, info in self._active_guests.items()
        ]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _viriditas_defaults() -> dict[str, Any]:
        """Viriditas-aware default resource profile (consciousness-aware scheduler)."""
        return {
            "cpu_cores": 2,
            "memory_mib": 2048,
            "gpu": None,
            "energy_budget": "viriditas-balanced",  # ties to GAIA energy optimisation spec
            "priority": "normal",
        }

    def _report_energy_draw(
        self, guest_id: str, resource_profile: dict[str, Any]
    ) -> None:
        """
        Report energy draw to the environmental monitor.
        Stage 10 (Multispecies Biocultural Accord) compliance.
        """
        try:
            from gaia_core.monitoring import EnvironmentalMonitor  # noqa: PLC0415
            EnvironmentalMonitor.report(
                source=guest_id,
                resource_profile=resource_profile,
                tenant=self.tenant_id,
                node=self.node_id,
            )
        except ImportError:
            logger.debug(
                "EnvironmentalMonitor not available — energy draw not reported for %s.",
                guest_id,
            )


class _StubCodex:
    def invoke_stage(self, stage: str, context: str = "") -> bool:  # noqa: ARG002
        logger.warning("[STUB] Codex stage '%s' — stub pass.", stage)
        return True

    def invoke_higher_order(self, order: str) -> bool:  # noqa: ARG002
        logger.warning("[STUB] Higher Order '%s' — stub pass.", order)
        return True
