"""Sanity of the fixture-backed mock client and its synthetic billing."""

from __future__ import annotations

from datetime import date

from insights.capella.client import CapellaSource
from insights.capella.mock import MockCapellaClient
from tests.conftest import ANALYTICS_EU, APP_SERVICE, DEV_SANDBOX, FREE_TRIAL, PROD_EU, PROJECT_PROD


def test_mock_satisfies_protocol(mock_client: MockCapellaClient) -> None:
    assert isinstance(mock_client, CapellaSource)


async def test_inventory_fixture(mock_client: MockCapellaClient) -> None:
    orgs = await mock_client.list_organizations()
    assert orgs[0].name == "Acme Corp"
    projects = await mock_client.list_projects()
    assert [p.name for p in projects] == ["Production", "Development"]
    clusters = [c for p in projects for c in await mock_client.list_clusters(p.id)]
    assert {c.name for c in clusters} == {"prod-eu", "prod-us", "dev-sandbox", "free-trial"}
    free = next(c for c in clusters if c.id == FREE_TRIAL)
    assert free.is_free_tier
    prod_eu = next(c for c in clusters if c.id == PROD_EU)
    assert prod_eu.node_count == 5
    assert prod_eu.app_service_id == APP_SERVICE
    assert len(await mock_client.list_buckets(PROJECT_PROD, PROD_EU)) == 3
    services = await mock_client.list_app_services()
    assert services[0].name == "prod-eu-app"
    endpoints = await mock_client.list_app_endpoints(PROJECT_PROD, PROD_EU, APP_SERVICE)
    assert [e.name for e in endpoints] == ["travel", "inventory"]
    analytics = await mock_client.list_analytics_clusters(PROJECT_PROD)
    assert analytics[0].id == ANALYTICS_EU and analytics[0].nodes == 4


async def test_daily_periods_inside_one_month(mock_client: MockCapellaClient) -> None:
    billing = await mock_client.categorized_billing(
        date(2026, 8, 1), date(2026, 8, 31), instance_ids=[PROD_EU]
    )
    assert len(billing.periods) == 31
    assert all(p.start_date == p.end_date for p in billing.periods)
    categories = {c.category for c in billing.periods[0].categories}
    assert categories == {
        "operationalComputeAndStorage",
        "operationalBucketBackup",
        "dataTransferStandard",
    }
    assert billing.periods[0].categories[0].currency_spend is None
    assert billing.billing_currency == "USD"


async def test_monthly_periods_when_range_spans_months(mock_client: MockCapellaClient) -> None:
    billing = await mock_client.categorized_billing(
        date(2026, 7, 15), date(2026, 9, 3), instance_ids=[PROD_EU]
    )
    assert [(p.start_date, p.end_date) for p in billing.periods] == [
        (date(2026, 7, 15), date(2026, 7, 31)),
        (date(2026, 8, 1), date(2026, 8, 31)),
        (date(2026, 9, 1), date(2026, 9, 3)),
    ]


async def test_billing_is_deterministic(mock_client: MockCapellaClient) -> None:
    a = await mock_client.categorized_billing(
        date(2026, 8, 1), date(2026, 8, 10), instance_ids=[PROD_EU]
    )
    b = await MockCapellaClient(today=date(2026, 9, 22)).categorized_billing(
        date(2026, 8, 1), date(2026, 8, 10), instance_ids=[PROD_EU]
    )
    assert a.model_dump() == b.model_dump()


async def test_org_total_exceeds_sum_of_instances(mock_client: MockCapellaClient) -> None:
    lo, hi = date(2026, 8, 1), date(2026, 8, 31)
    org = await mock_client.categorized_billing(lo, hi)
    parts = 0.0
    for instance in (
        PROD_EU,
        DEV_SANDBOX,
        APP_SERVICE,
        ANALYTICS_EU,
        "22222222-2222-4222-8222-000000000002",
    ):
        parts += (
            await mock_client.categorized_billing(lo, hi, instance_ids=[instance])
        ).total.total_credit_spend or 0
    assert org.total.total_credit_spend is not None
    assert org.total.total_credit_spend > parts
    assert "privateEndpointsStandard" in {c.category for c in org.total.categories}


async def test_turned_off_cluster_bills_only_storage(mock_client: MockCapellaClient) -> None:
    billing = await mock_client.categorized_billing(
        date(2026, 8, 1), date(2026, 8, 5), instance_ids=[DEV_SANDBOX]
    )
    categories = {c.category for p in billing.periods for c in p.categories}
    assert categories == {"operationalComputeAndStorage"}
    assert (billing.total.total_credit_spend or 0) < 5


async def test_free_tier_has_no_billing(mock_client: MockCapellaClient) -> None:
    billing = await mock_client.categorized_billing(
        date(2026, 8, 1), date(2026, 8, 5), instance_ids=[FREE_TRIAL]
    )
    assert billing.periods == []


async def test_app_service_and_analytics_categories(mock_client: MockCapellaClient) -> None:
    app = await mock_client.categorized_billing(
        date(2026, 8, 1), date(2026, 8, 2), instance_ids=[APP_SERVICE]
    )
    assert {c.category for c in app.periods[0].categories} == {"appServicesComputeAndStorage"}
    analytics = await mock_client.categorized_billing(
        date(2026, 8, 1), date(2026, 8, 2), instance_ids=[ANALYTICS_EU]
    )
    by_cat = {c.category: c.credit_spend or 0 for c in analytics.periods[0].categories}
    assert set(by_cat) == {"analyticsCompute", "analyticsStorage", "analyticsClusterBackup"}
    assert (
        by_cat["analyticsCompute"] > by_cat["analyticsStorage"] > by_cat["analyticsClusterBackup"]
    )


async def test_prepaid_and_payg(mock_client: MockCapellaClient) -> None:
    credits = await mock_client.prepaid_credits()
    assert [c.total for c in credits] == [50000.0, 5000.0]
    assert credits[1].remaining_percent == 10.0
    assert credits[1].expiration_date.startswith("2027-01-20")
    payg = await mock_client.pay_as_you_go(date(2026, 7, 1), date(2026, 8, 31))
    assert [p.start_date for p in payg.periods] == [date(2026, 7, 1), date(2026, 8, 1)]
    assert payg.total.total > 0


async def test_itemized_billing(mock_client: MockCapellaClient) -> None:
    itemized = await mock_client.itemized_billing(
        PROJECT_PROD, PROD_EU, date(2026, 8, 1), date(2026, 8, 3)
    )
    assert itemized.cluster_name == "prod-eu"
    assert itemized.support_plan == "Enterprise"
    assert len(itemized.periods) == 3


async def test_requests_are_counted(mock_client: MockCapellaClient) -> None:
    await mock_client.list_organizations()
    await mock_client.list_projects()
    assert mock_client.requests_made == 2
