"""SQLite connection handling and schema (design spec §3.3)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS organization (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    synced_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS project (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    name TEXT NOT NULL,
    raw_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cluster (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    provider TEXT,
    region TEXT,
    version TEXT,
    support_plan TEXT,
    availability TEXT,
    state TEXT,
    app_service_id TEXT,
    free_tier INTEGER NOT NULL DEFAULT 0,
    raw_json TEXT NOT NULL,
    synced_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bucket (
    cluster_id TEXT NOT NULL,
    name TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    PRIMARY KEY (cluster_id, name)
);
CREATE TABLE IF NOT EXISTS app_service (
    id TEXT PRIMARY KEY,
    cluster_id TEXT NOT NULL,
    name TEXT NOT NULL,
    nodes INTEGER,
    cpu INTEGER,
    ram INTEGER,
    version TEXT,
    plan TEXT,
    state TEXT,
    raw_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS app_endpoint (
    app_service_id TEXT NOT NULL,
    name TEXT NOT NULL,
    bucket TEXT,
    raw_json TEXT NOT NULL,
    PRIMARY KEY (app_service_id, name)
);
CREATE TABLE IF NOT EXISTS analytics_cluster (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    provider TEXT,
    region TEXT,
    nodes INTEGER,
    cpu INTEGER,
    ram INTEGER,
    support_plan TEXT,
    availability TEXT,
    state TEXT,
    raw_json TEXT NOT NULL,
    synced_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS credit_usage (
    day DATE NOT NULL,
    scope TEXT NOT NULL,
    instance_id TEXT NOT NULL,
    category TEXT NOT NULL,
    credit_spend REAL,
    currency_spend REAL,
    currency TEXT,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (day, scope, instance_id, category)
);
CREATE INDEX IF NOT EXISTS idx_credit_usage_scope_instance_day
    ON credit_usage (scope, instance_id, day);
CREATE TABLE IF NOT EXISTS prepaid_credit (
    id TEXT PRIMARY KEY,
    credit_name TEXT,
    support_plan TEXT,
    start_date TEXT,
    expiration_date TEXT,
    total REAL,
    used REAL,
    remaining REAL,
    remaining_percent REAL,
    fetched_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS payg_period (
    day DATE PRIMARY KEY,
    basic REAL,
    dev_pro REAL,
    enterprise REAL,
    total REAL,
    currency TEXT,
    fetched_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sync_run (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    requests_made INTEGER,
    error TEXT,
    detail_json TEXT
);
"""


class Database:
    """Opens short-lived SQLite connections (WAL mode) against one file.

    A fresh connection per unit of work keeps the store safe to use from FastAPI's
    threadpool and from ``asyncio.to_thread`` without sharing connections across threads.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        """Open a connection with WAL journaling and ``sqlite3.Row`` rows."""
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=30, isolation_level="DEFERRED")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    @contextmanager
    def session(self) -> Iterator[sqlite3.Connection]:
        """Connection context manager: commit on success, rollback on error, always close."""
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_schema(self) -> None:
        """Create all tables and indexes; safe to call repeatedly."""
        with self.session() as conn:
            conn.executescript(SCHEMA)
