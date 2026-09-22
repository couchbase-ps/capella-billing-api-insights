"""Topology mapper against the fixture clusters."""

from __future__ import annotations

import json

from insights.capella.mock import FIXTURES_DIR
from insights.topology.mapper import absent, analytics_to_topology, cluster_to_topology
from tests.conftest import ANALYTICS_EU, APP_SERVICE, DEV_SANDBOX, PROD_EU, PROJECT_PROD

INVENTORY = json.loads((FIXTURES_DIR / "inventory.json").read_text())


def _cluster(cluster_id: str) -> dict:
    return next(c for rows in INVENTORY["clusters"].values() for c in rows if c["id"] == cluster_id)


def test_prod_eu_with_app_service() -> None:
    doc = cluster_to_topology(
        _cluster(PROD_EU),
        INVENTORY["buckets"][PROD_EU],
        INVENTORY["appServices"][0],
        INVENTORY["appEndpoints"][APP_SERVICE],
    )
    assert doc["name"] == "prod-eu"
    assert doc["version"] == "7.6.4"
    assert doc["status"] == "HEALTHY"
    assert doc["resources"] == {"cpus": 28, "memory": "112 GB"}
    assert [g["name"] for g in doc["serverGroups"]] == ["data", "query/index"]
    data_node = doc["serverGroups"][0]["nodes"][0]
    assert data_node == {
        "name": "100GB gp3",
        "resources": {"cpus": 4, "memory": "16 GB"},
        "services": ["Data"],
        "status": "HEALTHY",
        "total": 3,
    }
    assert doc["serverGroups"][1]["nodes"][0]["services"] == ["Query", "Index"]
    assert doc["serverGroups"][1]["nodes"][0]["total"] == 2
    buckets = {b["name"]: b for b in doc["buckets"]}
    assert buckets["travel"] == {
        "name": "travel",
        "type": "couchbase",
        "quota": "2048 MB",
        "documents": 1200000,
        "replicas": 1,
        "ratio": 0.81,
        "eviction": "fullEviction",
    }
    assert buckets["sessions"]["type"] == "ephemeral"
    mobile = doc["mobile"]
    assert mobile["version"] == "3.2"
    assert mobile["resources"] == {"cpus": 2, "memory": "4 GB"}
    assert mobile["groups"][0]["instances"][0]["total"] == 2
    assert mobile["groups"][0]["instances"][0]["name"] == "prod-eu-app"
    assert mobile["groups"][0]["instances"][0]["nodeIp"] == "prod-eu-app"
    assert mobile["databases"] == [{"name": "travel"}, {"name": "inventory"}]


def test_app_service_instance_node_ip_never_missing() -> None:
    doc = cluster_to_topology(
        _cluster(PROD_EU), [], {"nodes": 1, "compute": {"cpu": 2, "ram": 4}}, []
    )
    instance = doc["mobile"]["groups"][0]["instances"][0]
    assert instance["nodeIp"] == ""
    assert "nodeIp" in instance


def test_turned_off_cluster_without_app_service() -> None:
    doc = cluster_to_topology(_cluster(DEV_SANDBOX), INVENTORY["buckets"][DEV_SANDBOX])
    assert doc["status"] == "TURNEDOFF"
    assert "mobile" not in doc
    assert doc["serverGroups"][0]["name"] == "data/query/index/search"
    assert doc["serverGroups"][0]["nodes"][0]["name"] == "128GB P10"
    assert doc["buckets"][0]["ratio"] == 0.05


def test_absent_figures() -> None:
    doc = cluster_to_topology(
        {
            "name": "bare",
            "currentState": None,
            "serviceGroups": [{"services": ["data"], "node": {}}],
        },
        [{"name": "b"}],
    )
    assert "version" not in doc  # topology-ui would print "v[object Object]" for an absent figure
    assert doc["status"] == "UNKNOWN"
    node = doc["serverGroups"][0]["nodes"][0]
    assert node["resources"] == {"cpus": absent(), "memory": absent()}
    assert node["total"] == absent()
    assert doc["buckets"][0]["quota"] == absent()
    assert doc["buckets"][0]["ratio"] == absent()
    assert doc["buckets"][0]["documents"] == absent()


def test_analytics_topology() -> None:
    raw = INVENTORY["analyticsClusters"][PROJECT_PROD][0]
    assert raw["id"] == ANALYTICS_EU
    doc = analytics_to_topology(raw)
    assert doc["name"] == "analytics-eu"
    assert doc["status"] == "HEALTHY"
    assert doc["resources"] == {"cpus": 32, "memory": "128 GB"}
    assert len(doc["serverGroups"]) == 1
    group = doc["serverGroups"][0]
    assert group["name"] == "analytics"
    assert group["nodes"][0]["services"] == ["Analytics"]
    assert group["nodes"][0]["total"] == 4
    assert group["nodes"][0]["resources"] == {"cpus": 8, "memory": "32 GB"}
    assert "buckets" not in doc and "mobile" not in doc
