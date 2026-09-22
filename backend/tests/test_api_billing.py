"""Contract checks: billing, reports listing, sync and CORS (see docs/api-contract.md)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.test_api import SYNC_KEYS


def pytest_approx(value: float):
    return pytest.approx(value, abs=0.05)


def test_billing_summary(client: TestClient) -> None:
    body = client.get(
        "/api/billing/summary", params={"from": "2026-09-01", "to": "2026-09-21"}
    ).json()
    assert set(body) == {
        "from",
        "to",
        "currency",
        "org",
        "attributed",
        "unattributed",
        "byCategory",
        "byInstance",
    }
    assert body["org"]["credits"] > body["attributed"]["credits"] > 0
    assert body["unattributed"]["credits"] == pytest_approx(
        body["org"]["credits"] - body["attributed"]["credits"]
    )
    assert body["org"]["currency"] is None and body["unattributed"]["currency"] is None
    assert {c["category"] for c in body["byCategory"]} >= {
        "privateEndpointsStandard",
        "analyticsCompute",
    }
    instances = {(i["scope"], i["name"]): i for i in body["byInstance"]}
    assert set(instances) == {
        ("cluster", "prod-eu"),
        ("cluster", "prod-us"),
        ("cluster", "dev-sandbox"),
        ("appservice", "prod-eu-app"),
        ("analytics", "analytics-eu"),
    }
    assert set(body["byInstance"][0]) == {
        "scope",
        "instanceId",
        "name",
        "projectName",
        "credits",
        "currency",
        "sharePercent",
    }
    assert instances[("cluster", "prod-eu")]["projectName"] == "Production"
    assert body["byInstance"][0]["sharePercent"] > 0


def test_billing_consumption_groupings(client: TestClient) -> None:
    day = client.get(
        "/api/billing/consumption", params={"from": "2026-09-01", "to": "2026-09-03"}
    ).json()
    assert day["groupBy"] == "day"
    assert set(day["rows"][0]) == {"period", "category", "credits", "currency"}
    assert {r["period"] for r in day["rows"]} == {"2026-09-01", "2026-09-02", "2026-09-03"}

    cat = client.get("/api/billing/consumption", params={"groupBy": "category"}).json()
    assert set(cat["rows"][0]) == {"key", "credits", "currency"}

    inst = client.get("/api/billing/consumption", params={"groupBy": "instance"}).json()
    assert {"key", "credits", "currency"} <= set(inst["rows"][0])
    assert len(inst["rows"]) == 5

    cluster_days = client.get(
        "/api/billing/consumption",
        params={"groupBy": "day", "scope": "cluster", "from": "2026-09-01", "to": "2026-09-02"},
    ).json()
    assert [r["key"] for r in cluster_days["rows"]] == ["2026-09-01", "2026-09-02"]
    assert set(cluster_days["rows"][0]) == {"key", "credits", "currency"}

    assert client.get("/api/billing/consumption", params={"groupBy": "week"}).status_code == 422


def test_billing_prepaid(client: TestClient) -> None:
    body = client.get("/api/billing/prepaid").json()
    assert set(body) == {"credits", "aggregate", "fetchedAt"}
    assert set(body["credits"][0]) == {
        "id",
        "creditName",
        "supportPlan",
        "startDate",
        "expirationDate",
        "total",
        "used",
        "remaining",
        "remainingPercent",
    }
    assert body["aggregate"] == {
        "total": 55000.0,
        "used": 24625.5,
        "remaining": 30374.5,
        "remainingPercent": 55.23,
    }
    assert body["fetchedAt"]


def test_billing_payg(client: TestClient) -> None:
    body = client.get("/api/billing/payg", params={"from": "2026-08-01", "to": "2026-09-21"}).json()
    assert body["currency"] == "USD"
    assert [p["period"] for p in body["periods"]] == ["2026-08-08", "2026-09-01"]
    assert set(body["periods"][0]) == {"period", "basic", "devPro", "enterprise", "total"}
    assert set(body["total"]) == {"basic", "devPro", "enterprise", "total"}
    assert body["total"]["total"] == pytest_approx(sum(p["total"] for p in body["periods"]))


def test_reports_list(client: TestClient) -> None:
    body = client.get("/api/reports").json()
    assert [r["key"] for r in body] == [
        "consumption-summary",
        "cluster-daily",
        "credits-by-category",
        "credits-by-plan",
        "credits-by-cluster",
    ]
    assert {"key", "title", "description", "params"} <= set(body[0])
    assert body[0]["params"][0] == {
        "name": "from",
        "type": "date",
        "required": True,
        "description": "First day (inclusive)",
    }
    assert body[1]["params"][2]["name"] == "clusterId"


def test_sync_status_and_trigger(client: TestClient) -> None:
    status = client.get("/api/sync/status").json()
    assert status["running"] is False
    assert len(status["runs"]) == 1
    run = status["runs"][0]
    assert set(run) == SYNC_KEYS | {"detail"}
    assert set(run["detail"]) == {
        "clustersSynced",
        "bucketsSkipped",
        "appServicesSynced",
        "analyticsClustersSynced",
        "billingWindows",
        "failures",
    }

    response = client.post("/api/sync")
    assert response.status_code == 202
    assert set(response.json()) == {"runId", "status"}
    assert response.json()["status"] == "running"
    runner = client.app.state.runner
    # TestClient drives the loop from a portal thread; wait for the background run there.
    client.portal.call(runner.wait)  # type: ignore[attr-defined]
    after = client.get("/api/sync/status").json()
    assert after["running"] is False
    assert len(after["runs"]) == 2 and after["runs"][0]["id"] == response.json()["runId"]
    assert after["runs"][0]["status"] == "success"


def test_sync_conflict_returns_409(client: TestClient) -> None:
    runner = client.app.state.runner
    client.portal.call(runner._lock.acquire)  # type: ignore[attr-defined]
    try:
        response = client.post("/api/sync")
    finally:
        client.portal.call(runner._lock.release)  # type: ignore[attr-defined]
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "sync_running"


def test_cors_headers(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "*"
