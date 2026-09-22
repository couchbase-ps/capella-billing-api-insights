"""The three custom monthly reports (docs/custom-reports.md) against the mock-synced store."""

from __future__ import annotations

import csv
import io
from datetime import date

import pytest
from fastapi.testclient import TestClient

from insights.reports.custom import credits_by_cluster, credits_by_plan
from insights.reports.labels import CATEGORY_LABELS, humanise, normalise_plan
from insights.reports.registry import ReportContext
from insights.store.db import Database

RANGE = {"from": "2026-07-01", "to": "2026-09-21"}
FIXED_CODES = [code for code, _ in CATEGORY_LABELS]
FIXED_LABELS = [label for _, label in CATEGORY_LABELS]
approx = pytest.approx


def _by_month(rows: list[dict], key: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for r in rows:
        out[r["month"]] = out.get(r["month"], 0.0) + (r[key] or 0.0)
    return out


def _column_sums(rows: list[dict], keys: list[str]) -> dict[str, float | None]:
    sums: dict[str, float | None] = {}
    for k in keys:
        present = [r[k] for r in rows if r.get(k) is not None]
        sums[k] = round(sum(present), 4) if present else None
    return sums


def test_labels_helpers() -> None:
    assert humanise("aiServicesNewThing") == "Ai Services New Thing"
    assert normalise_plan("developer pro") == "Developer Pro"
    assert normalise_plan("Plan: Enterprise") == "Enterprise"
    assert normalise_plan("basic") == "Basic"
    assert normalise_plan(None) is None


def test_reports_are_registered(client: TestClient) -> None:
    keys = [r["key"] for r in client.get("/api/reports").json()]
    assert keys[-3:] == ["credits-by-category", "credits-by-plan", "credits-by-cluster"]


def test_credits_by_category(client: TestClient) -> None:
    body = client.get("/api/reports/credits-by-category", params=RANGE).json()
    assert body["title"] == "Credits split up by categories"
    assert [c["key"] for c in body["columns"]] == ["month", "category", "credits"]
    assert [c["label"] for c in body["columns"]] == [
        "Month",
        "Row Labels",
        "Sum of consumed Credits",
    ]
    assert [c["type"] for c in body["columns"]] == ["month", "string", "credits"]
    months = sorted({r["month"] for r in body["rows"]})
    assert months == ["2026-08", "2026-09"]  # 45-day backfill: data starts 2026-08-08
    august = [r["category"] for r in body["rows"] if r["month"] == "2026-08"]
    assert august == [
        "Backup",
        "Cluster",
        "Data Transfer",
        "Private Endpoints",
        "Columnar Compute",
        "Columnar Storage",
        "Columnar Backup",
        "AppServices Fixed",
    ]
    assert all(r["credits"] is not None for r in body["rows"])
    assert body["totals"]["month"] == "Total" and body["totals"]["category"] is None
    assert body["totals"]["credits"] == approx(sum(r["credits"] for r in body["rows"]), abs=0.01)
    assert body["meta"]["unit"] == "credits"
    assert body["meta"]["categoryOrder"] == FIXED_LABELS
    assert body["meta"]["partialMonths"] == ["2026-09"]


def test_credits_by_plan_reconciles_with_category_report(client: TestClient) -> None:
    body = client.get("/api/reports/credits-by-plan", params=RANGE).json()
    assert body["title"] == "Credits by plan"
    keys = [c["key"] for c in body["columns"]]
    assert keys == ["month", "plan", *FIXED_CODES, "grandTotal"]
    assert (
        body["columns"][1]["label"] == "Credit Plan"
        and body["columns"][-1]["label"] == "Grand Total"
    )
    assert "appServicesVariable" in keys
    assert all(r["appServicesVariable"] is None for r in body["rows"])
    plans_per_month = {
        m: [r["plan"] for r in body["rows"] if r["month"] == m] for m in ("2026-08", "2026-09")
    }
    for plans in plans_per_month.values():
        assert plans == ["Basic", "Developer Pro", "Enterprise", "Unattributed"]
    unattributed = next(
        r for r in body["rows"] if r["plan"] == "Unattributed" and r["month"] == "2026-08"
    )
    assert unattributed["privateEndpointsStandard"] > 0
    assert unattributed["operationalComputeAndStorage"] is None  # fully attributed to instances
    enterprise = next(
        r for r in body["rows"] if r["plan"] == "Enterprise" and r["month"] == "2026-08"
    )
    assert enterprise["analyticsCompute"] > 0 and enterprise["appServicesComputeAndStorage"] > 0
    basic = next(r for r in body["rows"] if r["plan"] == "Basic" and r["month"] == "2026-08")
    assert basic["operationalBucketBackup"] is None  # turned-off sandbox bills storage only
    for row in body["rows"]:
        cells = [row[c] for c in FIXED_CODES if row[c] is not None]
        assert row["grandTotal"] == approx(sum(cells), abs=0.01)

    category = client.get("/api/reports/credits-by-category", params=RANGE).json()
    by_month_plan = _by_month(body["rows"], "grandTotal")
    by_month_category = _by_month(category["rows"], "credits")
    for month, total in by_month_category.items():
        assert by_month_plan[month] == approx(total, abs=0.01)

    expected = _column_sums(body["rows"], [*FIXED_CODES, "grandTotal"])
    assert body["totals"]["month"] == "Total" and body["totals"]["plan"] is None
    for key, value in expected.items():
        assert body["totals"][key] == (approx(value, abs=0.01) if value is not None else None)


def test_credits_by_cluster(client: TestClient) -> None:
    body = client.get("/api/reports/credits-by-cluster", params=RANGE).json()
    assert body["title"] == "Credits by usage per cluster"
    keys = [c["key"] for c in body["columns"]]
    assert keys == [
        "month",
        "instance",
        *FIXED_CODES,
        "totalDevPro",
        "totalEnterprise",
        "totalBasic",
        "onDemand",
    ]
    labels = {c["key"]: c["label"] for c in body["columns"]}
    assert labels["instance"] == "Cluster Instance Name"
    assert (
        labels["totalBasic"] == "Total Plan Basic"
        and labels["onDemand"] == "Total On-demand Credits"
    )
    assert body["meta"]["onDemandMethod"] == "proportional-by-plan"

    august = {r["instance"]: r for r in body["rows"] if r["month"] == "2026-08"}
    assert list(august) == ["analytics-eu", "dev-sandbox", "prod-eu", "prod-us", "Unattributed"]
    prod_eu, prod_us, sandbox = august["prod-eu"], august["prod-us"], august["dev-sandbox"]
    # App Service credits land on the attached cluster's row only
    assert prod_eu["appServicesComputeAndStorage"] > 0
    assert prod_us["appServicesComputeAndStorage"] is None
    assert (
        august["analytics-eu"]["analyticsCompute"] > 0
        and august["analytics-eu"]["operationalComputeAndStorage"] is None
    )
    # plan totals
    row_total = sum(v for k, v in prod_eu.items() if k in FIXED_CODES and v is not None)
    assert prod_eu["totalEnterprise"] == approx(row_total, abs=0.01)
    assert prod_eu["totalDevPro"] is None and prod_eu["totalBasic"] is None
    assert prod_us["totalDevPro"] is not None and prod_us["totalEnterprise"] is None
    assert sandbox["totalBasic"] is not None
    unattributed = august["Unattributed"]
    assert unattributed["privateEndpointsStandard"] > 0
    assert unattributed["totalEnterprise"] is None and unattributed["onDemand"] is None
    # on-demand: payg exists for both months, so every plan row has an estimate <= its total
    for row in body["rows"]:
        if row["instance"] == "Unattributed":
            continue
        total = sum(v for k, v in row.items() if k in FIXED_CODES and v is not None)
        assert row["onDemand"] is not None
        assert 0 <= row["onDemand"] <= total + 1e-6

    expected = _column_sums(
        body["rows"], [*FIXED_CODES, "totalDevPro", "totalEnterprise", "totalBasic", "onDemand"]
    )
    assert body["totals"]["month"] == "Total" and body["totals"]["instance"] is None
    for key, value in expected.items():
        assert body["totals"][key] == (approx(value, abs=0.01) if value is not None else None)

    # Unattributed reconciles with the plan report per month
    plan = client.get("/api/reports/credits-by-plan", params=RANGE).json()
    for month in ("2026-08", "2026-09"):
        cluster_total = sum(
            v
            for r in body["rows"]
            if r["month"] == month
            for k, v in r.items()
            if k in FIXED_CODES and v is not None
        )
        assert cluster_total == approx(_by_month(plan["rows"], "grandTotal")[month], abs=0.01)


def test_on_demand_is_null_without_payg(synced_db: Database) -> None:
    with synced_db.session() as conn:
        conn.execute("DELETE FROM payg_period WHERE day >= '2026-09-01'")
    with synced_db.session() as conn:
        result = credits_by_cluster(ReportContext(conn, date(2026, 8, 1), date(2026, 9, 21)))
    august = [r for r in result.rows if r["month"] == "2026-08" and r["instance"] != "Unattributed"]
    september = [
        r for r in result.rows if r["month"] == "2026-09" and r["instance"] != "Unattributed"
    ]
    assert all(r["onDemand"] is not None for r in august)
    assert all(r["onDemand"] is None for r in september)


def test_plan_report_without_instances_is_all_unattributed(synced_db: Database) -> None:
    with synced_db.session() as conn:
        conn.execute("DELETE FROM credit_usage WHERE scope != 'org'")
    with synced_db.session() as conn:
        result = credits_by_plan(ReportContext(conn, date(2026, 8, 1), date(2026, 9, 21)))
    assert {r["plan"] for r in result.rows} == {"Unattributed"}
    assert result.rows[0]["operationalComputeAndStorage"] > 0


def test_custom_report_csv(client: TestClient) -> None:
    response = client.get("/api/reports/credits-by-plan", params={**RANGE, "format": "csv"})
    assert (
        response.headers["content-disposition"]
        == "attachment; filename=credits-by-plan-2026-07-01_to_2026-09-21.csv"
    )
    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0][:2] == ["Month", "Credit Plan"] and rows[0][-1] == "Grand Total"
    assert rows[-1][0] == "Total" and rows[-1][1] == ""
    assert float(rows[-1][-1]) > 0


def test_empty_range_reports(client: TestClient) -> None:
    body = client.get(
        "/api/reports/credits-by-cluster", params={"from": "2025-01-01", "to": "2025-01-31"}
    ).json()
    assert body["rows"] == []
    assert body["totals"]["month"] == "Total" and body["totals"]["onDemand"] is None
    assert body["meta"]["partialMonths"] == []
