"""``sync_run`` bookkeeping."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SyncRunRow:
    id: int
    started_at: str
    finished_at: str | None
    status: str
    requests_made: int | None
    error: str | None
    detail: dict[str, Any] | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> SyncRunRow:
        return cls(
            id=row["id"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            status=row["status"],
            requests_made=row["requests_made"],
            error=row["error"],
            detail=json.loads(row["detail_json"]) if row["detail_json"] else None,
        )

    def as_json(self, include_detail: bool = False) -> dict[str, Any]:
        """Contract shape for ``lastSync`` (and sync status when ``include_detail``)."""
        payload: dict[str, Any] = {
            "id": self.id,
            "startedAt": self.started_at,
            "finishedAt": self.finished_at,
            "status": self.status,
            "requestsMade": self.requests_made,
            "error": self.error,
        }
        if include_detail:
            payload["detail"] = self.detail or empty_detail()
        return payload


def empty_detail() -> dict[str, Any]:
    return {
        "clustersSynced": 0,
        "appServicesSynced": 0,
        "analyticsClustersSynced": 0,
        "billingWindows": 0,
        "failures": [],
    }


def create_sync_run(conn: sqlite3.Connection, started_at: str) -> int:
    """Insert a ``running`` row and return its id."""
    cur = conn.execute(
        "INSERT INTO sync_run (started_at, status, requests_made) VALUES (?, 'running', 0)",
        (started_at,),
    )
    return int(cur.lastrowid or 0)


def finish_sync_run(
    conn: sqlite3.Connection,
    run_id: int,
    *,
    finished_at: str,
    status: str,
    requests_made: int,
    error: str | None,
    detail: dict[str, Any],
) -> None:
    conn.execute(
        "UPDATE sync_run SET finished_at = ?, status = ?, requests_made = ?, error = ?,"
        " detail_json = ? WHERE id = ?",
        (finished_at, status, requests_made, error, json.dumps(detail), run_id),
    )


def list_sync_runs(conn: sqlite3.Connection, limit: int = 10) -> list[SyncRunRow]:
    rows = conn.execute("SELECT * FROM sync_run ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [SyncRunRow.from_row(r) for r in rows]


def last_sync_run(conn: sqlite3.Connection) -> SyncRunRow | None:
    runs = list_sync_runs(conn, limit=1)
    return runs[0] if runs else None


def mark_stale_runs_failed(conn: sqlite3.Connection, finished_at: str) -> None:
    """On startup, runs left ``running`` by a crashed process are marked failed."""
    conn.execute(
        "UPDATE sync_run SET status = 'failed', finished_at = ?, error = ?"
        " WHERE status = 'running'",
        (finished_at, "interrupted: process restarted while the sync was running"),
    )
