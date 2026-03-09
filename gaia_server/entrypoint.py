from __future__ import annotations

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from gaia_core.bootstrap import build_default_gaia
from gaia_server.config import ServerConfig, DEFAULT_SERVER_CONFIG
from gaia_server.ipc.grpc_server import GaiaGrpcServer
from gaia_server.observability.telemetry import TelemetryCollector
from gaia_server.tenancy.tenant_registry import TenantRegistry

logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    """Minimal HTTP health/readiness handler for Kubernetes probes."""

    substrate = None

    def do_GET(self):
        if self.path in ("/healthz", "/readyz"):
            body = json.dumps({"status": "ok", "node": self.server.node_id}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):  # suppress default HTTP logging
        pass


class GaiaServer:
    def __init__(self, config: ServerConfig = DEFAULT_SERVER_CONFIG) -> None:
        self.config = config
        self.substrate = None
        self.grpc = None
        self.telemetry = None
        self.tenants = None

    def boot(self) -> None:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
        logger.info("GAIA-Server booting. node=%s cluster=%s",
                    self.config.node_id, self.config.cluster_id)

        # 1. Bootstrap GAIA-Core substrate
        logger.info("Bootstrapping GAIA-Core substrate...")
        self.substrate = build_default_gaia(Path(self.config.state_root))
        logger.info("Substrate ready. cores=%s", self.substrate.registry.names())

        # 2. Start gRPC layer
        logger.info("Starting gRPC server on port %d...", self.config.grpc_port)
        self.grpc = GaiaGrpcServer(self.substrate, self.config)
        self.grpc.start()

        # 3. Register tenants
        logger.info("Initializing tenant registry...")
        self.tenants = TenantRegistry(self.config)
        for tenant in self.config.allowed_tenants:
            self.tenants.register(tenant)
        logger.info("Tenants registered: %s", self.tenants.list_tenants())

        # 4. Start observability
        logger.info("Starting telemetry collector...")
        self.telemetry = TelemetryCollector(self.substrate, self.config)
        self.telemetry.start()

        # 5. Health server
        logger.info("Starting health server on port %d...", self.config.health_port)
        self._start_health_server()

        logger.info("GAIA-Server ready. identity=%s",
                    self.substrate.identity.public_fingerprint)

    def _start_health_server(self) -> None:
        server = HTTPServer(("", self.config.health_port), HealthHandler)
        server.node_id = self.config.node_id
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()

    def shutdown(self) -> None:
        logger.info("GAIA-Server shutting down...")
        if self.grpc:
            self.grpc.stop()
        if self.telemetry:
            self.telemetry.stop()
        logger.info("GAIA-Server shutdown complete.")


def main() -> None:
    server = GaiaServer()
    server.boot()
    try:
        import signal, time
        def _handler(sig, frame):
            server.shutdown()
        signal.signal(signal.SIGTERM, _handler)
        signal.signal(signal.SIGINT, _handler)
        while True:
            time.sleep(5)
    except SystemExit:
        pass


if __name__ == "__main__":
    main()
