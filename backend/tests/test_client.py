"""Limiter, retry/backoff and page walking of ``CapellaClient`` (respx-mocked HTTP)."""

from __future__ import annotations

import asyncio
import json
from datetime import date

import httpx
import pytest
import respx

from insights.capella.client import CapellaAPIError, CapellaClient
from insights.capella.limiter import RetryPolicy, TokenBucket, parse_retry_after

BASE = "https://capella.test"
ORG = "0f6d2a1e-7c3b-4c8a-9e1d-000000000001"


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def make_client(clock: FakeClock) -> CapellaClient:
    limiter = TokenBucket(600, burst=100, clock=clock, sleep=clock.sleep)
    retry = RetryPolicy(base_delay=0.5, jitter=0.0, rng=lambda: 0.0)
    return CapellaClient(
        "secret-key", BASE, limiter=limiter, retry=retry, sleep=clock.sleep, org_id=ORG
    )


# --- token bucket -----------------------------------------------------------------------


async def test_token_bucket_sleeps_exact_refill_time() -> None:
    clock = FakeClock()
    bucket = TokenBucket(60, burst=2, clock=clock, sleep=clock.sleep)  # 1 token/second
    await bucket.acquire()
    await bucket.acquire()
    assert clock.sleeps == []
    await bucket.acquire()  # bucket empty: must wait one second, once
    assert clock.sleeps == [1.0]


async def test_token_bucket_refills_over_time() -> None:
    clock = FakeClock()
    bucket = TokenBucket(60, burst=1, clock=clock, sleep=clock.sleep)
    await bucket.acquire()
    clock.now += 5
    assert bucket.available == pytest.approx(1.0)  # capped at burst
    await bucket.acquire()
    assert clock.sleeps == []


async def test_token_bucket_serialises_concurrent_waiters() -> None:
    clock = FakeClock()
    bucket = TokenBucket(60, burst=1, clock=clock, sleep=clock.sleep)
    await asyncio.gather(*(bucket.acquire() for _ in range(4)))
    assert sum(clock.sleeps) >= 3.0


def test_default_burst_keeps_under_capella_limit() -> None:
    bucket = TokenBucket(80)
    assert bucket.available == 16


def test_parse_retry_after() -> None:
    assert parse_retry_after("7") == 7.0
    assert parse_retry_after(None) is None
    assert parse_retry_after("not a date") is None


# --- retries ----------------------------------------------------------------------------


async def test_429_then_200_honours_retry_after() -> None:
    clock = FakeClock()
    with respx.mock(base_url=BASE) as router:
        route = router.get("/v4/organizations").mock(
            side_effect=[
                httpx.Response(
                    429, headers={"Retry-After": "3"}, json={"code": 1004, "message": "slow"}
                ),
                httpx.Response(200, json={"data": [{"id": ORG, "name": "Acme"}]}),
            ]
        )
        async with make_client(clock) as client:
            orgs = await client.list_organizations()
    assert [o.name for o in orgs] == ["Acme"]
    assert route.call_count == 2
    assert client.requests_made == 2
    assert 3.0 in clock.sleeps


async def test_5xx_is_retried_with_backoff() -> None:
    clock = FakeClock()
    with respx.mock(base_url=BASE) as router:
        router.get("/v4/organizations").mock(
            side_effect=[
                httpx.Response(503),
                httpx.Response(502),
                httpx.Response(200, json={"data": [{"id": ORG, "name": "Acme"}]}),
            ]
        )
        async with make_client(clock) as client:
            await client.list_organizations()
    assert clock.sleeps == [0.5, 1.0]
    assert client.requests_made == 3


async def test_5xx_gives_up_after_three_attempts() -> None:
    clock = FakeClock()
    with respx.mock(base_url=BASE) as router:
        route = router.get("/v4/organizations").mock(
            return_value=httpx.Response(500, json={"message": "boom"})
        )
        async with make_client(clock) as client:
            with pytest.raises(CapellaAPIError) as info:
                await client.list_organizations()
    assert info.value.http_status == 500
    assert route.call_count == 3


async def test_401_raises_api_error_without_retry() -> None:
    clock = FakeClock()
    with respx.mock(base_url=BASE) as router:
        route = router.get("/v4/organizations").mock(
            return_value=httpx.Response(
                401,
                json={
                    "httpStatusCode": 401,
                    "code": 1001,
                    "message": "bad key",
                    "hint": "check it",
                },
            )
        )
        async with make_client(clock) as client:
            with pytest.raises(CapellaAPIError) as info:
                await client.list_organizations()
    assert (info.value.http_status, info.value.code) == (401, 1001)
    assert info.value.message == "bad key"
    assert info.value.hint == "check it"
    assert route.call_count == 1
    assert clock.sleeps == []


async def test_bearer_header_is_sent() -> None:
    clock = FakeClock()
    with respx.mock(base_url=BASE) as router:
        route = router.get("/v4/organizations").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        async with make_client(clock) as client:
            await client.list_organizations()
    assert route.calls.last.request.headers["Authorization"] == "Bearer secret-key"


# --- pagination + billing bodies --------------------------------------------------------


async def test_walk_pages_follows_cursor() -> None:
    clock = FakeClock()

    def respond(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        if page == 1:
            return httpx.Response(
                200,
                json={
                    "data": [{"id": "p1", "name": "one"}],
                    "cursor": {"pages": {"page": 1, "next": 2, "last": 2}},
                },
            )
        return httpx.Response(
            200,
            json={
                "data": [{"id": "p2", "name": "two"}],
                "cursor": {"pages": {"page": 2, "last": 2}},
            },
        )

    with respx.mock(base_url=BASE) as router:
        route = router.get(f"/v4/organizations/{ORG}/projects").mock(side_effect=respond)
        async with make_client(clock) as client:
            projects = await client.list_projects()
    assert [p.id for p in projects] == ["p1", "p2"]
    assert route.call_count == 2


async def test_categorized_billing_request_body() -> None:
    clock = FakeClock()
    payload = {
        "data": {
            "billingCurrency": "USD",
            "periods": [
                {
                    "startDate": "2026-08-01",
                    "endDate": "2026-08-01",
                    "categories": [
                        {
                            "category": "operationalComputeAndStorage",
                            "creditSpend": 1.5,
                            "currencySpend": None,
                            "contributionPercent": 100,
                        }
                    ],
                    "totalCreditSpend": 1.5,
                    "totalCurrencySpend": None,
                }
            ],
            "total": {
                "startDate": "2026-08-01",
                "endDate": "2026-08-01",
                "categories": [],
                "totalCreditSpend": 1.5,
            },
        }
    }
    with respx.mock(base_url=BASE) as router:
        route = router.post(f"/v4/organizations/{ORG}/billing").mock(
            return_value=httpx.Response(200, json=payload)
        )
        async with make_client(clock) as client:
            billing = await client.categorized_billing(
                date(2026, 8, 1), date(2026, 8, 1), instance_ids=["c1"]
            )
    body = json.loads(route.calls.last.request.content)
    assert body == {
        "startDate": "2026-08-01",
        "endDate": "2026-08-01",
        "filters": {"instanceIds": ["c1"]},
    }
    assert billing.periods[0].categories[0].credit_spend == 1.5
    assert billing.periods[0].categories[0].currency_spend is None
    assert billing.periods[0].start_date == date(2026, 8, 1)


async def test_analytics_clusters_path() -> None:
    clock = FakeClock()
    with respx.mock(base_url=BASE) as router:
        route = router.get(f"/v4/organizations/{ORG}/projects/p1/analyticsClusters").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "a1",
                            "name": "analytics",
                            "cloudProvider": "aws",
                            "region": "eu-west-1",
                            "nodes": 2,
                            "compute": {"cpu": 4, "ram": 16},
                            "currentState": "healthy",
                            "support": {"plan": "enterprise", "timezone": "GMT"},
                            "availability": {"type": "single"},
                        }
                    ],
                    "cursor": {"pages": {"page": 1, "last": 1}},
                },
            )
        )
        async with make_client(clock) as client:
            rows = await client.list_analytics_clusters("p1")
    assert route.call_count == 1
    assert rows[0].compute.ram == 16 and rows[0].support.plan == "enterprise"  # type: ignore[union-attr]
