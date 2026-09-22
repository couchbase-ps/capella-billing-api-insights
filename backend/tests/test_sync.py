"""Full sync of the mock client into SQLite, plus runner concurrency and failure handling."""

from __future__ import annotations

import asyncio
from datetime import date

import pytest

from insights.capella.client import CapellaAPIError
from insights.capella.mock import MockCapellaClient
from insights.config import Settings
from insights.store import repo
from insights.store.db import Database
from insights.sync.runner import SyncAlreadyRunning, SyncNotConfigured, SyncRunner
from tests.conftest import ANALYTICS_EU, APP_SERVICE, FREE_TRIAL, PROD_EU


async def test_full_sync_populates_store(
    synced_db: Database, mock_client: MockCapellaClient, today: date
) -> None:
    with synced_db.session() as conn:
        assert repo.count_inventory(conn) == {
            "projects": 2,
            "clusters": 4,
            "appServices": 1,
            "analyticsClusters": 1,
        }
        assert len(repo.list_buckets(conn, PROD_EU)) == 3
        assert repo.list_buckets(conn, FREE_TRIAL) == []
        assert repo.get_cluster(conn, FREE_TRIAL).free_tier is True
        assert [e["name"] for e in repo.list_app_endpoints(conn, APP_SERVICE)] == [
            "inventory",
            "travel",
        ]
        # billing: 45-day backfill ending yesterday, daily rows for every scope
        assert repo.last_synced_day(conn, "org") == date(2026, 9, 21)
        first = min(r.day for r in repo.query_usage(conn, "org", "", date(2000, 1, 1), today))
        assert first == date(2026, 8, 8)
        assert repo.query_usage(conn, "cluster", FREE_TRIAL, date(2000, 1, 1), today) == []
        assert repo.query_usage(
            conn, "analytics", ANALYTICS_EU, date(2026, 9, 1), date(2026, 9, 21)
        )
        assert len(repo.list_prepaid(conn)) == 2
        assert [r["day"] for r in repo.list_payg(conn, date(2026, 1, 1), today)] == [
            "2026-08-08",
            "2026-09-01",
        ]
        run = repo.last_sync_run(conn)
    assert run is not None and run.status == "success"
    assert run.detail == {
        "clustersSynced": 4,
        "appServicesSynced": 1,
        "analyticsClustersSynced": 1,
        "billingWindows": 2,
        "failures": [],
    }
    assert run.requests_made == mock_client.requests_made


async def test_second_sync_only_refreshes_trailing_window(
    synced_db: Database, runner: SyncRunner, mock_client: MockCapellaClient
) -> None:
    before = mock_client.requests_made
    run = await runner.run()
    assert run.status == "success"
    # inventory: orgs + projects + 2 cluster lists + 3 bucket lists + app services + endpoints
    # + 2 analytics lists = 11; one September window: org + 3 clusters + app service + analytics
    # + payg = 7; prepaid = 1
    assert mock_client.requests_made - before == 11 + 7 + 1
    with synced_db.session() as conn:
        assert repo.last_synced_day(conn, "org") == date(2026, 9, 21)
        assert len(repo.list_sync_runs(conn)) == 2


class FailingClient(MockCapellaClient):
    async def categorized_billing(
        self, start, end, instance_ids=None, project_ids=None, categories=None
    ):  # type: ignore[override]
        if instance_ids and instance_ids[0] == PROD_EU:
            raise CapellaAPIError(422, 2000, "instance not billable", "")
        return await super().categorized_billing(start, end, instance_ids, project_ids, categories)


async def test_instance_failure_is_partial_not_fatal(
    db: Database, settings: Settings, today: date
) -> None:
    client = FailingClient(today=today)
    runner = SyncRunner(db, client, settings, today=lambda: today)
    run = await runner.run()
    assert run.status == "partial"
    assert run.error is None
    failures = run.detail["failures"]
    assert len(failures) == 2  # one per month window
    assert failures[0]["scope"] == "cluster" and failures[0]["instanceId"] == PROD_EU
    assert "instance not billable" in failures[0]["message"]
    with db.session() as conn:
        assert repo.query_usage(conn, "cluster", PROD_EU, date(2000, 1, 1), today) == []
        assert repo.query_usage(conn, "org", "", date(2026, 9, 1), today)


class BrokenClient(MockCapellaClient):
    async def list_organizations(self):  # type: ignore[override]
        raise CapellaAPIError(401, 1001, "invalid api key", "")


async def test_top_level_failure_is_recorded(db: Database, settings: Settings, today: date) -> None:
    runner = SyncRunner(db, BrokenClient(today=today), settings, today=lambda: today)
    run = await runner.run()
    assert run.status == "failed"
    assert "invalid api key" in (run.error or "")
    assert run.finished_at is not None


async def test_runner_refuses_concurrent_runs(runner: SyncRunner) -> None:
    run_id = await runner.trigger()
    assert runner.running
    with pytest.raises(SyncAlreadyRunning):
        await runner.trigger()
    with pytest.raises(SyncAlreadyRunning):
        await runner.run()
    await runner.wait()
    assert not runner.running
    with runner.db.session() as conn:
        assert repo.last_sync_run(conn).id == run_id
        assert repo.last_sync_run(conn).status == "success"


async def test_runner_not_configured(db: Database, settings: Settings) -> None:
    runner = SyncRunner(db, None, settings)
    with pytest.raises(SyncNotConfigured):
        await runner.run()
    await asyncio.wait_for(runner.background(), timeout=1)  # returns immediately
