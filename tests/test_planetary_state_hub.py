"""Tests for PlanetaryStateHub — fleet-level planetary state aggregation.

All 13 tests run without any optional infra (no etcd3, nats, minio required).
"""
from __future__ import annotations

import time
import pytest

from gaia_server.planetary.state_hub import PlanetaryStateHub, PlanetarySnapshot


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def hub() -> PlanetaryStateHub:
    h = PlanetaryStateHub()
    return h


def _snap(node_id: str, love: float = 0.5, obs: int = 3) -> PlanetarySnapshot:
    return PlanetarySnapshot(
        node_id=node_id,
        timestamp=time.time(),
        observations={f"obs_{i}": i for i in range(obs)},
        love_score=love,
    )


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def test_hub_starts_empty(hub):
    assert hub.node_count() == 0


def test_fleet_summary_empty(hub):
    summary = hub.fleet_summary()
    assert summary["node_count"] == 0
    assert summary["fleet_love_score"] == 0.0


# ---------------------------------------------------------------------------
# push() — typed snapshot
# ---------------------------------------------------------------------------

def test_push_single_snapshot(hub):
    hub.push(_snap("node-a"))
    assert hub.node_count() == 1


def test_push_overwrites_same_node(hub):
    hub.push(_snap("node-a", love=0.3))
    hub.push(_snap("node-a", love=0.9))
    assert hub.node_count() == 1
    assert hub.snapshot("node-a").love_score == pytest.approx(0.9)


def test_push_multiple_nodes(hub):
    for i in range(5):
        hub.push(_snap(f"node-{i}"))
    assert hub.node_count() == 5


# ---------------------------------------------------------------------------
# push_dict() — raw gRPC payload path
# ---------------------------------------------------------------------------

def test_push_dict_creates_snapshot(hub):
    snap = hub.push_dict("node-grpc", {"love_score": 0.75, "observations": {"temp": 22.1}})
    assert snap.node_id == "node-grpc"
    assert snap.love_score == pytest.approx(0.75)
    assert hub.node_count() == 1


def test_push_dict_minimal_payload(hub):
    snap = hub.push_dict("node-min", {})
    assert snap.node_id == "node-min"
    assert snap.love_score == 0.0


# ---------------------------------------------------------------------------
# snapshot() — per-node retrieval
# ---------------------------------------------------------------------------

def test_snapshot_returns_none_for_unknown(hub):
    assert hub.snapshot("ghost") is None


def test_snapshot_returns_correct_node(hub):
    hub.push(_snap("node-x", love=0.42))
    hub.push(_snap("node-y", love=0.88))
    assert hub.snapshot("node-x").love_score == pytest.approx(0.42)
    assert hub.snapshot("node-y").love_score == pytest.approx(0.88)


# ---------------------------------------------------------------------------
# fleet_summary()
# ---------------------------------------------------------------------------

def test_fleet_summary_node_count(hub):
    hub.push(_snap("a"))
    hub.push(_snap("b"))
    assert hub.fleet_summary()["node_count"] == 2


def test_fleet_summary_avg_love(hub):
    hub.push(_snap("a", love=0.4))
    hub.push(_snap("b", love=0.6))
    assert hub.fleet_summary()["fleet_love_score"] == pytest.approx(0.5)


def test_fleet_summary_contains_nodes(hub):
    hub.push(_snap("node-1"))
    hub.push(_snap("node-2"))
    summary = hub.fleet_summary()
    assert set(summary["nodes"]) == {"node-1", "node-2"}


# ---------------------------------------------------------------------------
# all_snapshots() and clear()
# ---------------------------------------------------------------------------

def test_all_snapshots_returns_list(hub):
    hub.push(_snap("a"))
    hub.push(_snap("b"))
    assert len(hub.all_snapshots()) == 2


def test_clear_resets_hub(hub):
    hub.push(_snap("a"))
    hub.clear()
    assert hub.node_count() == 0
