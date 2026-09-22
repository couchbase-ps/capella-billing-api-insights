"""Contract checks for every endpoint in docs/api-contract.md against a synced mock store."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import ANALYTICS_EU, APP_SERVICE, FREE_TRIAL, PROD_EU, PROJECT_PROD

SYNC_KEYS = {"id", "startedAt", "finishedAt", "status", "requestsMade", "error"}
CLUSTER_CARD_KEYS = {
    "id",
    "name",
    "projectId",
    "projectName",
    "provider",
    "region",
    "version",
    "supportPlan",
    "availability",
    "state",
    "freeTier",
    "nodes",
    "serviceGroups",
    "appServiceId",
    "credits7d",
    "credits30d",
    "currency7d",
    "currency30d",
}
APP_SERVICE_KEYS = {
    "id",
    "name",
    "clusterId",
    "clusterName",
    "projectId",
    "projectName",
    "provider",
    "nodes",
    "cpu",
    "ram",
    "version",
    "plan",
    "state",
    "endpoints",
    "credits7d",
    "credits30d",
    "currency7d",
    "currency30d",
}
ANALYTICS_KEYS = {
    "id",
    "name",
    "projectId",
    "projectName",
    "provider",
    "region",
    "nodes",
    "cpu",
    "ram",
    "supportPlan",
    "availability",
    "state",
    "credits7d",
    "credits30d",
    "currency7d",
    "currency30d",
}
CONSUMPTION_KEYS = {
    "scope",
    "instanceId",
    "from",
    "to",
    "granularity",
    "currency",
    "series",
    "byCategory",
    "total",
}


def test_health(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["mock"] is True
    assert body["configured"] is True
    assert set(body["lastSync"]) == SYNC_KEYS
    assert body["lastSync"]["status"] == "success"


def test_organization(client: TestClient) -> None:
    body = client.get("/api/organization").json()
    assert body["name"] == "Acme Corp"
    assert body["billingCurrency"] == "USD"
    assert body["billingMode"] == "credits"
    assert body["counts"] == {
        "projects": 2,
        "clusters": 4,
        "appServices": 1,
        "analyticsClusters": 1,
    }
    assert set(body["lastSync"]) == SYNC_KEYS


def test_projects(client: TestClient) -> None:
    body = client.get("/api/projects").json()
    assert body == [
        {"id": "11111111-1111-4111-8111-000000000002", "name": "Development", "clusterCount": 2},
        {"id": PROJECT_PROD, "name": "Production", "clusterCount": 2},
    ]


def test_clusters(client: TestClient) -> None:
    body = client.get("/api/clusters").json()
    assert len(body) == 4
    by_name = {c["name"]: c for c in body}
    prod_eu = by_name["prod-eu"]
    assert set(prod_eu) == CLUSTER_CARD_KEYS
    assert prod_eu["nodes"] == 5
    assert prod_eu["appServiceId"] == APP_SERVICE
    assert prod_eu["serviceGroups"][0] == {
        "services": ["data"],
        "numOfNodes": 3,
        "cpu": 4,
        "ram": 16,
        "diskType": "gp3",
        "diskGb": 100,
        "iops": 3000,
    }
    assert prod_eu["credits7d"] > 0 and prod_eu["credits30d"] > prod_eu["credits7d"]
    assert prod_eu["currency7d"] is None and prod_eu["currency30d"] is None
    free = by_name["free-trial"]
    assert free["freeTier"] is True and free["credits30d"] is None and free["supportPlan"] == "free"
    assert by_name["dev-sandbox"]["state"] == "turnedOff"


def test_cluster_detail(client: TestClient) -> None:
    body = client.get(f"/api/clusters/{PROD_EU}").json()
    assert CLUSTER_CARD_KEYS <= set(body)
    assert body["connectionString"].startswith("couchbases://")
    assert body["createdAt"] == "2024-04-02T08:15:00Z"
    bucket = next(b for b in body["buckets"] if b["name"] == "travel")
    assert bucket == {
        "name": "travel",
        "storageBackend": "magma",
        "memoryAllocationInMb": 2048,
        "replicas": 1,
        "evictionPolicy": "fullEviction",
        "itemCount": 1200000,
        "memoryUsedInMib": 1650,
        "diskUsedInMib": 5200,
        "timeToLiveInSeconds": 0,
    }
    assert set(body["appService"]) == APP_SERVICE_KEYS
    assert {"name": "travel", "bucket": "travel", "state": "online"} in body["appService"][
        "endpoints"
    ]
    assert client.get(f"/api/clusters/{FREE_TRIAL}").json()["appService"] is None


def test_cluster_not_found_envelope(client: TestClient) -> None:
    response = client.get("/api/clusters/nope")
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "cluster 'nope' not found"}
    }


def test_cluster_topology(client: TestClient) -> None:
    body = client.get(f"/api/clusters/{PROD_EU}/topology").json()
    assert {"name", "version", "status", "resources", "serverGroups", "buckets", "mobile"} <= set(
        body
    )
    assert sorted(d["name"] for d in body["mobile"]["databases"]) == ["inventory", "travel"]


def test_cluster_consumption_defaults_and_month(client: TestClient) -> None:
    body = client.get(f"/api/clusters/{PROD_EU}/consumption").json()
    assert set(body) == CONSUMPTION_KEYS
    assert (body["from"], body["to"]) == ("2026-08-23", "2026-09-21")
    assert body["scope"] == "cluster" and body["granularity"] == "day" and body["currency"] == "USD"
    assert set(body["series"][0]) == {"period", "category", "credits", "currency"}
    assert body["series"][0]["period"] == "2026-08-23"
    assert set(body["byCategory"][0]) == {"category", "credits", "currency", "contributionPercent"}
    assert body["byCategory"][0]["category"] == "operationalComputeAndStorage"
    assert body["total"]["credits"] > 0 and body["total"]["currency"] is None
    assert sum(c["contributionPercent"] for c in body["byCategory"]) == pytest_approx(100)

    monthly = client.get(
        f"/api/clusters/{PROD_EU}/consumption",
        params={"from": "2026-08-10", "to": "2026-09-21", "granularity": "month"},
    ).json()
    assert {s["period"] for s in monthly["series"]} == {"2026-08", "2026-09"}
    assert monthly["total"]["credits"] == pytest_approx(
        sum(s["credits"] for s in monthly["series"])
    )


def pytest_approx(value: float):
    import pytest

    return pytest.approx(value, abs=0.05)


def test_invalid_range(client: TestClient) -> None:
    response = client.get(
        f"/api/clusters/{PROD_EU}/consumption", params={"from": "2026-09-10", "to": "2026-09-01"}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_range"
    bad = client.get(f"/api/clusters/{PROD_EU}/consumption", params={"from": "yesterday"})
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "validation_error"


def test_app_services(client: TestClient) -> None:
    body = client.get("/api/appservices").json()
    assert len(body) == 1 and set(body[0]) == APP_SERVICE_KEYS
    assert body[0]["clusterName"] == "prod-eu" and body[0]["projectName"] == "Production"
    assert body[0]["provider"] == "aws" and body[0]["credits7d"] > 0
    consumption = client.get(f"/api/appservices/{APP_SERVICE}/consumption").json()
    assert set(consumption) == CONSUMPTION_KEYS and consumption["scope"] == "appservice"
    assert consumption["byCategory"][0]["category"] == "appServicesComputeAndStorage"
    assert client.get("/api/appservices/nope/consumption").status_code == 404


def test_analytics_clusters(client: TestClient) -> None:
    body = client.get("/api/analyticsclusters").json()
    assert len(body) == 1 and set(body[0]) == ANALYTICS_KEYS
    card = body[0]
    assert (
        card["name"] == "analytics-eu"
        and card["nodes"] == 4
        and card["cpu"] == 8
        and card["ram"] == 32
    )
    assert card["projectName"] == "Production" and card["supportPlan"] == "enterprise"
    assert card["credits7d"] > 0
    detail = client.get(f"/api/analyticsclusters/{ANALYTICS_EU}").json()
    assert set(detail) == ANALYTICS_KEYS | {"createdAt"}
    topology = client.get(f"/api/analyticsclusters/{ANALYTICS_EU}/topology").json()
    assert topology["serverGroups"][0]["name"] == "analytics"
    assert topology["serverGroups"][0]["nodes"][0]["services"] == ["Analytics"]
    consumption = client.get(f"/api/analyticsclusters/{ANALYTICS_EU}/consumption").json()
    assert consumption["scope"] == "analytics"
    assert {c["category"] for c in consumption["byCategory"]} == {
        "analyticsCompute",
        "analyticsStorage",
        "analyticsClusterBackup",
    }
    assert client.get("/api/analyticsclusters/nope").status_code == 404
