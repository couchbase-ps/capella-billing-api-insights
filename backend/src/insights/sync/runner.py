"""Sync orchestration: one run at a time, ``sync_run`` bookkeeping, background scheduling."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any

from insights.capella.client import CapellaSource
from insights.config import Settings
from insights.store import repo
from insights.store.db import Database
from insights.sync.billing import ANALYTICS_ATTRIBUTION, sync_billing
from insights.sync.inventory import sync_inventory
from insights.sync.windows import sync_range

log = logging.getLogger(__name__)


class SyncAlreadyRunning(Exception):
    """Raised when a sync is requested while another one holds the lock."""


class SyncNotConfigured(Exception):
    """Raised when neither an API key nor mock mode is configured."""


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class SyncRunner:
    """Runs syncs serially (asyncio.Lock) and records them in ``sync_run``."""

    def __init__(
        self,
        db: Database,
        client: CapellaSource | None,
        settings: Settings,
        *,
        today: Callable[[], date] = lambda: datetime.now(UTC).date(),
    ) -> None:
        self.db = db
        self.client = client
        self.settings = settings
        self._today = today
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None

    @property
    def running(self) -> bool:
        return self._lock.locked()

    def _ensure_configured(self) -> CapellaSource:
        if self.client is None:
            raise SyncNotConfigured(
                "no Capella API key configured (set CAPELLA_API_KEY or CAPELLA_MOCK=true)"
            )
        return self.client

    async def run(self) -> repo.SyncRunRow:
        """Run a full sync now and return the finished ``sync_run`` row."""
        self._ensure_configured()
        if self._lock.locked():
            raise SyncAlreadyRunning("a sync is already running")
        async with self._lock:
            run_id = await asyncio.to_thread(self._create_run)
            await self._execute(run_id)
        return await asyncio.to_thread(self._get_run, run_id)

    async def trigger(self) -> int:
        """Start a sync in the background and return its run id (409 semantics if busy)."""
        self._ensure_configured()
        if self._lock.locked():
            raise SyncAlreadyRunning("a sync is already running")
        await self._lock.acquire()  # cannot suspend: lock is free and has no waiters
        try:
            run_id = await asyncio.to_thread(self._create_run)
        except BaseException:
            self._lock.release()
            raise
        self._task = asyncio.create_task(self._run_locked(run_id))
        return run_id

    async def _run_locked(self, run_id: int) -> None:
        try:
            await self._execute(run_id)
        finally:
            self._lock.release()

    async def wait(self) -> None:
        """Wait for a triggered background run to finish (tests, shutdown)."""
        if self._task is not None:
            await self._task

    def _create_run(self) -> int:
        with self.db.session() as conn:
            return repo.create_sync_run(conn, utc_now_iso())

    def _get_run(self, run_id: int) -> repo.SyncRunRow:
        with self.db.session() as conn:
            runs = [r for r in repo.list_sync_runs(conn, limit=50) if r.id == run_id]
        return runs[0]

    def _finish(
        self, run_id: int, status: str, requests: int, error: str | None, detail: dict[str, Any]
    ) -> None:
        with self.db.session() as conn:
            repo.finish_sync_run(
                conn,
                run_id,
                finished_at=utc_now_iso(),
                status=status,
                requests_made=requests,
                error=error,
                detail=detail,
            )

    def _last_synced_day(self) -> date | None:
        with self.db.session() as conn:
            return repo.last_synced_day(conn, "org")

    async def _execute(self, run_id: int) -> None:
        client = self._ensure_configured()
        before = client.requests_made
        now = utc_now_iso()
        detail = repo.empty_detail()
        status, error = "success", None
        try:
            inventory = await sync_inventory(client, self.db, self.settings, now)
            detail["clustersSynced"] = len(inventory.clusters)
            detail["bucketsSkipped"] = len(inventory.buckets_skipped)
            detail["endpointsSkipped"] = len(inventory.endpoints_skipped)
            detail["analyticsAttribution"] = ANALYTICS_ATTRIBUTION
            detail["appServicesSynced"] = len(inventory.app_services)
            detail["analyticsClustersSynced"] = len(inventory.analytics)
            failures = list(inventory.failures)
            today = self._today()
            last_day = await asyncio.to_thread(self._last_synced_day)
            window = sync_range(
                today, last_day, self.settings.sync_backfill_days, self.settings.sync_refresh_days
            )
            if window is not None:
                outcome = await sync_billing(client, self.db, inventory, window[0], window[1], now)
                detail["billingWindows"] = outcome.windows
                failures.extend(outcome.failures)
            detail["failures"] = [f.as_json() for f in failures]
            if failures:
                status = "partial"
        except Exception as exc:
            log.exception("sync run %d failed", run_id)
            status, error = "failed", f"{type(exc).__name__}: {exc}"
        requests = client.requests_made - before
        await asyncio.to_thread(self._finish, run_id, status, requests, error, detail)
        log.info("sync run %d finished: %s (%d requests)", run_id, status, requests)

    async def background(self) -> None:
        """Startup sync (``SYNC_ON_START``) then periodic resync (``SYNC_INTERVAL_MINUTES``)."""
        if self.client is None:
            log.warning("sync disabled: not configured")
            return
        if self.settings.sync_on_start:
            await self._safe_run()
        interval = self.settings.sync_interval_minutes
        while interval > 0:
            await asyncio.sleep(interval * 60)
            await self._safe_run()

    async def _safe_run(self) -> None:
        try:
            await self.run()
        except SyncAlreadyRunning:
            log.info("background sync skipped: already running")
        except Exception:
            log.exception("background sync crashed")
