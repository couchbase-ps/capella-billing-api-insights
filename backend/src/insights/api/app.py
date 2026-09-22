"""FastAPI application factory with lifespan-managed store, client and background sync."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from insights import __version__
from insights.api.errors import install_error_handlers
from insights.api.routes import billing, health, inventory, reports, sync
from insights.capella.client import CapellaClient, CapellaSource
from insights.capella.mock import MockCapellaClient
from insights.config import Settings, load_settings
from insights.reports.builtin import register_builtin
from insights.reports.custom import register_custom
from insights.store import repo
from insights.store.db import Database
from insights.sync.runner import SyncRunner, utc_now_iso

log = logging.getLogger(__name__)


def build_client(settings: Settings) -> CapellaSource | None:
    """Mock client, real client, or ``None`` when nothing is configured."""
    if settings.capella_mock:
        return MockCapellaClient(org_id=settings.capella_org_id)
    key = settings.api_key_value
    if key is None:
        return None
    return CapellaClient(
        api_key=key,
        base_url=settings.capella_base_url,
        rate_limit_per_minute=settings.rate_limit_per_minute,
        org_id=settings.capella_org_id,
    )


def create_app(
    settings: Settings | None = None,
    *,
    client: CapellaSource | None = None,
    db: Database | None = None,
    background_sync: bool = True,
) -> FastAPI:
    """Create the application. ``client``/``db`` overrides are for tests."""
    cfg = settings or load_settings()
    register_builtin()
    register_custom()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        database = db or Database(cfg.effective_db_path)
        database.init_schema()
        with database.session() as conn:
            repo.mark_stale_runs_failed(conn, utc_now_iso())
        source = client if client is not None else build_client(cfg)
        runner = SyncRunner(database, source, cfg)
        app.state.settings = cfg
        app.state.db = database
        app.state.client = source
        app.state.runner = runner
        task: asyncio.Task[None] | None = None
        if (
            background_sync
            and source is not None
            and (cfg.sync_on_start or cfg.sync_interval_minutes > 0)
        ):
            task = asyncio.create_task(runner.background(), name="insights-sync")
        log.info(
            "insights %s started (mock=%s, configured=%s)",
            __version__,
            cfg.capella_mock,
            cfg.configured,
        )
        try:
            yield
        finally:
            if task is not None:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            if source is not None:
                await source.aclose()

    app = FastAPI(title="Capella Billing API Insights", version=__version__, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )
    install_error_handlers(app)
    for module in (health, inventory, billing, reports, sync):
        app.include_router(module.router)
    return app
