"""Typed row objects returned by the inventory repositories."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any


def loads(text: str | None) -> dict[str, Any]:
    """Parse a ``raw_json`` column (empty/NULL -> ``{}``)."""
    return json.loads(text) if text else {}


@dataclass(frozen=True)
class ClusterRow:
    id: str
    project_id: str
    project_name: str | None
    name: str
    provider: str | None
    region: str | None
    version: str | None
    support_plan: str | None
    availability: str | None
    state: str | None
    app_service_id: str | None
    free_tier: bool
    raw: dict[str, Any]
    synced_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> ClusterRow:
        keys = row.keys()
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            project_name=row["project_name"] if "project_name" in keys else None,
            name=row["name"],
            provider=row["provider"],
            region=row["region"],
            version=row["version"],
            support_plan=row["support_plan"],
            availability=row["availability"],
            state=row["state"],
            app_service_id=row["app_service_id"],
            free_tier=bool(row["free_tier"]),
            raw=loads(row["raw_json"]),
            synced_at=row["synced_at"],
        )


@dataclass(frozen=True)
class AppServiceRow:
    id: str
    cluster_id: str
    cluster_name: str | None
    project_id: str | None
    project_name: str | None
    provider: str | None
    name: str
    nodes: int | None
    cpu: int | None
    ram: int | None
    version: str | None
    plan: str | None
    state: str | None
    raw: dict[str, Any]

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> AppServiceRow:
        keys = row.keys()
        raw = loads(row["raw_json"])
        return cls(
            id=row["id"],
            cluster_id=row["cluster_id"],
            cluster_name=row["cluster_name"] if "cluster_name" in keys else None,
            project_id=row["project_id"] if "project_id" in keys else None,
            project_name=row["project_name"] if "project_name" in keys else None,
            provider=raw.get("cloudProvider"),
            name=row["name"],
            nodes=row["nodes"],
            cpu=row["cpu"],
            ram=row["ram"],
            version=row["version"],
            plan=row["plan"],
            state=row["state"],
            raw=raw,
        )


@dataclass(frozen=True)
class AnalyticsClusterRow:
    id: str
    project_id: str
    project_name: str | None
    name: str
    provider: str | None
    region: str | None
    nodes: int | None
    cpu: int | None
    ram: int | None
    support_plan: str | None
    availability: str | None
    state: str | None
    raw: dict[str, Any]
    synced_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> AnalyticsClusterRow:
        keys = row.keys()
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            project_name=row["project_name"] if "project_name" in keys else None,
            name=row["name"],
            provider=row["provider"],
            region=row["region"],
            nodes=row["nodes"],
            cpu=row["cpu"],
            ram=row["ram"],
            support_plan=row["support_plan"],
            availability=row["availability"],
            state=row["state"],
            raw=loads(row["raw_json"]),
            synced_at=row["synced_at"],
        )
