from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gaia_server.config import ServerConfig
from gaia_server.entrypoint import GaiaServer


class TestGaiaServerBoot(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="gaia-server-test-")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _config(self) -> ServerConfig:
        return ServerConfig(
            node_id="test-node",
            state_root=self.tmpdir,
            health_port=0,    # disable real HTTP server in tests
            grpc_port=0,
            allowed_tenants=["default", "test-tenant"],
        )

    def test_substrate_boots_with_eight_cores(self) -> None:
        cfg = self._config()
        server = GaiaServer(cfg)
        with patch.object(server, '_start_health_server'):
            server.boot()
        self.assertIsNotNone(server.substrate)
        self.assertEqual(len(server.substrate.registry.names()), 8)
        self.assertIn("NEXUS", server.substrate.registry.names())
        self.assertIn("GUARDIAN", server.substrate.registry.names())
        server.shutdown()

    def test_tenants_registered(self) -> None:
        cfg = self._config()
        server = GaiaServer(cfg)
        with patch.object(server, '_start_health_server'):
            server.boot()
        tenants = server.tenants.list_tenants()
        self.assertIn("default", tenants)
        self.assertIn("test-tenant", tenants)
        server.shutdown()

    def test_grpc_server_starts(self) -> None:
        cfg = self._config()
        server = GaiaServer(cfg)
        with patch.object(server, '_start_health_server'):
            server.boot()
        self.assertIsNotNone(server.grpc)
        server.shutdown()


if __name__ == "__main__":
    unittest.main()
