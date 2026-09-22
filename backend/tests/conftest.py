"""Shared fixtures: pinned "today", mock client, temp SQLite store, synced app + TestClient."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from insights.api.app import create_app
from insights.capella.mock import MockCapellaClient
from insights.config import Settings
from insights.store.db import Database
from insights.sync.runner import SyncRunner

TODAY = date(2026, 9, 22)

PROD_EU = "22222222-2222-4222-8222-000000000001"
PROD_US = "22222222-2222-4222-8222-000000000002"
DEV_SANDBOX = "22222222-2222-4222-8222-000000000003"
FREE_TRIAL = "22222222-2222-4222-8222-000000000004"
APP_SERVICE = "33333333-3333-4333-8333-000000000001"
ANALYTICS_EU = "44444444-4444-4444-8444-000000000001"
PROJECT_PROD = "11111111-1111-4111-8111-000000000001"


@pytest.fixture
def today() -> date:
    return TODAY


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        capella_mock=True,
        db_path=str(tmp_path / "insights.db"),
        sync_on_start=False,
        sync_interval_minutes=0,
        sync_backfill_days=45,
        sync_refresh_days=7,
    )


@pytest.fixture
def mock_client(today: date) -> MockCapellaClient:
    return MockCapellaClient(today=today)


@pytest.fixture
def db(settings: Settings) -> Database:
    database = Database(settings.db_path)
    database.init_schema()
    return database


@pytest.fixture
def runner(db: Database, mock_client: MockCapellaClient, settings: Settings, today: date) -> SyncRunner:
    return SyncRunner(db, mock_client, settings, today=lambda: today)


@pytest.fixture
async def synced_db(db: Database, runner: SyncRunner) -> Database:
    """A store populated by one full mock sync."""
    row = await runner.run()
    assert row.status == "success", row
    return db


@pytest.fixture
def client(settings: Settings, mock_client: MockCapellaClient, synced_db: Database, today: date) -> Iterator[TestClient]:
    app = create_app(settings, client=mock_client, db=synced_db, background_sync=False)
    app.state.today = lambda: today
    with TestClient(app) as test_client:
        yield test_client
