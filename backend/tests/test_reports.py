"""Built-in reports as JSON and CSV, plus the registry extension point."""

from __future__ import annotations

import csv
import io
from datetime import date

from fastapi.testclient import TestClient

from insights.reports.registry import (
    ReportColumn,
    ReportContext,
    ReportDefinition,
    ReportRegistry,
    ReportResult,
    result_to_csv,
)
from tests.conftest import ANALYTICS_EU, PROD_EU


def test_consumption_summary_json(client: TestClient) -> None:
    body = client.get(
        "/api/reports/consumption-summary", params={"from": "2026-09-01", "to": "2026-09-21"}
    ).json()
    assert set(body) == {"key", "title", "from", "to", "columns", "rows", "totals"}
    assert body["key"] == "consumption-summary"
    assert (body["from"], body["to"]) == ("2026-09-01", "2026-09-21")
    assert [c["key"] for c in body["columns"]] == [
        "scope",
        "instanceId",
        "name",
        "project",
        "category",
        "credits",
        "currency",
    ]
    assert {c["type"] for c in body["columns"]} == {"string", "credits", "currency"}
    scopes = {r["scope"] for r in body["rows"]}
    assert scopes == {"cluster", "appservice", "analytics"}
    analytics_rows = [r for r in body["rows"] if r["scope"] == "analytics"]
    assert {r["category"] for r in analytics_rows} == {
        "analyticsCompute",
        "analyticsStorage",
        "analyticsClusterBackup",
    }
    assert analytics_rows[0]["project"] == "Production"
    assert body["totals"]["credits"] > 0 and body["totals"]["currency"] is None
    assert body["rows"][0]["credits"] >= body["rows"][1]["credits"]


def test_cluster_daily_json_and_csv(client: TestClient) -> None:
    params = {"from": "2026-09-01", "to": "2026-09-03", "clusterId": PROD_EU}
    body = client.get("/api/reports/cluster-daily", params=params).json()
    assert len(body["rows"]) == 9  # 3 days x 3 categories
    assert body["rows"][0]["day"] == "2026-09-01" and body["rows"][0]["cluster"] == "prod-eu"
    assert body["rows"][0]["scope"] == "cluster"

    response = client.get("/api/reports/cluster-daily", params={**params, "format": "csv"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert (
        response.headers["content-disposition"]
        == "attachment; filename=cluster-daily-2026-09-01_to_2026-09-03.csv"
    )
    reader = list(csv.reader(io.StringIO(response.text)))
    assert reader[0] == ["Day", "Cluster", "Scope", "Category", "Credits", "Currency"]
    assert len(reader) == 1 + 9 + 1
    assert reader[-1][0] == "TOTAL" and reader[-1][5] == ""


def test_cluster_daily_resolves_analytics_id(client: TestClient) -> None:
    body = client.get(
        "/api/reports/cluster-daily",
        params={"from": "2026-09-01", "to": "2026-09-01", "clusterId": ANALYTICS_EU},
    ).json()
    assert body["rows"][0]["scope"] == "analytics"
    assert body["rows"][0]["cluster"] == "analytics-eu"
    assert len(body["rows"]) == 3


def test_report_errors(client: TestClient) -> None:
    missing = client.get("/api/reports/cluster-daily")
    assert missing.status_code == 400
    assert missing.json()["error"]["code"] == "invalid_params"
    unknown = client.get("/api/reports/cluster-daily", params={"clusterId": "nope"})
    assert unknown.status_code == 400
    assert client.get("/api/reports/does-not-exist").status_code == 404


def test_registry_extension_point() -> None:
    registry = ReportRegistry()

    def run(ctx: ReportContext) -> ReportResult:
        return ReportResult(
            columns=[ReportColumn("a", "A", "string"), ReportColumn("n", "N", "number")],
            rows=[{"a": "x, y", "n": 1.5}],
            totals={"n": 1.5},
        )

    registry.register(ReportDefinition("custom", "Custom", "d", (), run))
    assert [d.key for d in registry.list()] == ["custom"]
    definition = registry.get("custom")
    assert definition is not None
    result = definition.run(
        ReportContext(conn=None, date_from=date(2026, 1, 1), date_to=date(2026, 1, 2))
    )  # type: ignore[arg-type]
    assert result_to_csv(result) == 'A,N\n"x, y",1.5\nTOTAL,1.5\n'
    assert registry.get("missing") is None
