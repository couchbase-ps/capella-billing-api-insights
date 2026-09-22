"""Inventory repositories: organization, projects, clusters, buckets, App Services, Analytics."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from insights.capella.models import (
    AnalyticsCluster,
    AppEndpoint,
    AppService,
    Bucket,
    Cluster,
    Organization,
    Project,
)


def _loads(text: str | None) -> dict[str, Any]:
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
            raw=_loads(row["raw_json"]),
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
        raw = _loads(row["raw_json"])
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
            raw=_loads(row["raw_json"]),
            synced_at=row["synced_at"],
        )


# --- organization / projects ------------------------------------------------------------


def upsert_organization(conn: sqlite3.Connection, org: Organization, synced_at: str) -> None:
    """Insert or replace the single organization row."""
    conn.execute(
        "INSERT INTO organization (id, name, raw_json, synced_at) VALUES (?, ?, ?, ?)"
        " ON CONFLICT(id) DO UPDATE SET name=excluded.name, raw_json=excluded.raw_json,"
        " synced_at=excluded.synced_at",
        (org.id, org.name, json.dumps(org.raw()), synced_at),
    )


def get_organization(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM organization ORDER BY synced_at DESC LIMIT 1").fetchone()


def upsert_projects(conn: sqlite3.Connection, org_id: str, projects: Iterable[Project]) -> None:
    conn.executemany(
        "INSERT INTO project (id, org_id, name, raw_json) VALUES (?, ?, ?, ?)"
        " ON CONFLICT(id) DO UPDATE SET org_id=excluded.org_id, name=excluded.name,"
        " raw_json=excluded.raw_json",
        [(p.id, org_id, p.name, json.dumps(p.raw())) for p in projects],
    )


def prune_projects(conn: sqlite3.Connection, keep_ids: Iterable[str]) -> None:
    """Delete projects that no longer exist in Capella."""
    _prune(conn, "project", "id", keep_ids)


def list_projects_with_counts(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT p.id, p.name, (SELECT COUNT(*) FROM cluster c WHERE c.project_id = p.id)"
        " AS cluster_count FROM project p ORDER BY p.name"
    ).fetchall()
    return [{"id": r["id"], "name": r["name"], "clusterCount": r["cluster_count"]} for r in rows]


def count_inventory(conn: sqlite3.Connection) -> dict[str, int]:
    """Counts used by ``GET /api/organization``."""
    return {
        "projects": conn.execute("SELECT COUNT(*) FROM project").fetchone()[0],
        "clusters": conn.execute("SELECT COUNT(*) FROM cluster").fetchone()[0],
        "appServices": conn.execute("SELECT COUNT(*) FROM app_service").fetchone()[0],
        "analyticsClusters": conn.execute("SELECT COUNT(*) FROM analytics_cluster").fetchone()[0],
    }


# --- clusters ---------------------------------------------------------------------------


def upsert_clusters(
    conn: sqlite3.Connection, project_id: str, clusters: Iterable[Cluster], synced_at: str
) -> None:
    conn.executemany(
        "INSERT INTO cluster (id, project_id, name, provider, region, version, support_plan,"
        " availability, state, app_service_id, free_tier, raw_json, synced_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT(id) DO UPDATE SET project_id=excluded.project_id, name=excluded.name,"
        " provider=excluded.provider, region=excluded.region, version=excluded.version,"
        " support_plan=excluded.support_plan, availability=excluded.availability,"
        " state=excluded.state, app_service_id=excluded.app_service_id,"
        " free_tier=excluded.free_tier, raw_json=excluded.raw_json, synced_at=excluded.synced_at",
        [
            (
                c.id,
                project_id,
                c.name,
                c.cloud_provider.type,
                c.cloud_provider.region,
                c.couchbase_server.version if c.couchbase_server else None,
                c.support.plan if c.support else None,
                c.availability.type if c.availability else None,
                c.current_state,
                c.app_service_id,
                1 if c.is_free_tier else 0,
                json.dumps(c.raw()),
                synced_at,
            )
            for c in clusters
        ],
    )


def prune_clusters(conn: sqlite3.Connection, keep_ids: Iterable[str]) -> None:
    ids = list(keep_ids)
    _prune(conn, "cluster", "id", ids)
    _prune(conn, "bucket", "cluster_id", ids)


_CLUSTER_SELECT = (
    "SELECT c.*, p.name AS project_name FROM cluster c LEFT JOIN project p ON p.id = c.project_id"
)


def list_clusters(conn: sqlite3.Connection) -> list[ClusterRow]:
    rows = conn.execute(f"{_CLUSTER_SELECT} ORDER BY p.name, c.name").fetchall()
    return [ClusterRow.from_row(r) for r in rows]


def get_cluster(conn: sqlite3.Connection, cluster_id: str) -> ClusterRow | None:
    row = conn.execute(f"{_CLUSTER_SELECT} WHERE c.id = ?", (cluster_id,)).fetchone()
    return ClusterRow.from_row(row) if row else None


# --- buckets ----------------------------------------------------------------------------


def replace_buckets(conn: sqlite3.Connection, cluster_id: str, buckets: Iterable[Bucket]) -> None:
    """Replace the bucket set of one cluster."""
    conn.execute("DELETE FROM bucket WHERE cluster_id = ?", (cluster_id,))
    conn.executemany(
        "INSERT INTO bucket (cluster_id, name, raw_json) VALUES (?, ?, ?)",
        [(cluster_id, b.name, json.dumps(b.raw())) for b in buckets],
    )


def list_buckets(conn: sqlite3.Connection, cluster_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT raw_json FROM bucket WHERE cluster_id = ? ORDER BY name", (cluster_id,)
    ).fetchall()
    return [_loads(r["raw_json"]) for r in rows]


# --- app services -----------------------------------------------------------------------


def upsert_app_services(conn: sqlite3.Connection, services: Iterable[AppService]) -> None:
    conn.executemany(
        "INSERT INTO app_service (id, cluster_id, name, nodes, cpu, ram, version, plan, state,"
        " raw_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT(id) DO UPDATE SET cluster_id=excluded.cluster_id, name=excluded.name,"
        " nodes=excluded.nodes, cpu=excluded.cpu, ram=excluded.ram, version=excluded.version,"
        " plan=excluded.plan, state=excluded.state, raw_json=excluded.raw_json",
        [
            (
                s.id,
                s.cluster_id,
                s.name,
                s.nodes,
                s.compute.cpu if s.compute else None,
                s.compute.ram if s.compute else None,
                s.version,
                s.plan,
                s.current_state,
                json.dumps(s.raw()),
            )
            for s in services
        ],
    )


def prune_app_services(conn: sqlite3.Connection, keep_ids: Iterable[str]) -> None:
    ids = list(keep_ids)
    _prune(conn, "app_service", "id", ids)
    _prune(conn, "app_endpoint", "app_service_id", ids)


_APP_SERVICE_SELECT = (
    "SELECT a.*, c.name AS cluster_name, c.project_id AS project_id, p.name AS project_name"
    " FROM app_service a LEFT JOIN cluster c ON c.id = a.cluster_id"
    " LEFT JOIN project p ON p.id = c.project_id"
)


def list_app_services(conn: sqlite3.Connection) -> list[AppServiceRow]:
    rows = conn.execute(f"{_APP_SERVICE_SELECT} ORDER BY a.name").fetchall()
    return [AppServiceRow.from_row(r) for r in rows]


def get_app_service(conn: sqlite3.Connection, app_service_id: str) -> AppServiceRow | None:
    row = conn.execute(f"{_APP_SERVICE_SELECT} WHERE a.id = ?", (app_service_id,)).fetchone()
    return AppServiceRow.from_row(row) if row else None


def get_app_service_for_cluster(conn: sqlite3.Connection, cluster_id: str) -> AppServiceRow | None:
    row = conn.execute(f"{_APP_SERVICE_SELECT} WHERE a.cluster_id = ?", (cluster_id,)).fetchone()
    return AppServiceRow.from_row(row) if row else None


def replace_app_endpoints(
    conn: sqlite3.Connection, app_service_id: str, endpoints: Iterable[AppEndpoint]
) -> None:
    conn.execute("DELETE FROM app_endpoint WHERE app_service_id = ?", (app_service_id,))
    conn.executemany(
        "INSERT INTO app_endpoint (app_service_id, name, bucket, raw_json) VALUES (?, ?, ?, ?)",
        [(app_service_id, e.name, e.bucket, json.dumps(e.raw())) for e in endpoints],
    )


def list_app_endpoints(conn: sqlite3.Connection, app_service_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT raw_json FROM app_endpoint WHERE app_service_id = ? ORDER BY name",
        (app_service_id,),
    ).fetchall()
    return [_loads(r["raw_json"]) for r in rows]


# --- analytics clusters -----------------------------------------------------------------


def upsert_analytics_clusters(
    conn: sqlite3.Connection,
    project_id: str,
    clusters: Iterable[AnalyticsCluster],
    synced_at: str,
) -> None:
    conn.executemany(
        "INSERT INTO analytics_cluster (id, project_id, name, provider, region, nodes, cpu, ram,"
        " support_plan, availability, state, raw_json, synced_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT(id) DO UPDATE SET project_id=excluded.project_id, name=excluded.name,"
        " provider=excluded.provider, region=excluded.region, nodes=excluded.nodes,"
        " cpu=excluded.cpu, ram=excluded.ram, support_plan=excluded.support_plan,"
        " availability=excluded.availability, state=excluded.state, raw_json=excluded.raw_json,"
        " synced_at=excluded.synced_at",
        [
            (
                a.id,
                project_id,
                a.name,
                a.cloud_provider,
                a.region,
                a.nodes,
                a.compute.cpu,
                a.compute.ram,
                a.support.plan if a.support else None,
                a.availability.type if a.availability else None,
                a.current_state,
                json.dumps(a.raw()),
                synced_at,
            )
            for a in clusters
        ],
    )


def prune_analytics_clusters(conn: sqlite3.Connection, keep_ids: Iterable[str]) -> None:
    _prune(conn, "analytics_cluster", "id", keep_ids)


_ANALYTICS_SELECT = (
    "SELECT a.*, p.name AS project_name FROM analytics_cluster a"
    " LEFT JOIN project p ON p.id = a.project_id"
)


def list_analytics_clusters(conn: sqlite3.Connection) -> list[AnalyticsClusterRow]:
    rows = conn.execute(f"{_ANALYTICS_SELECT} ORDER BY p.name, a.name").fetchall()
    return [AnalyticsClusterRow.from_row(r) for r in rows]


def get_analytics_cluster(conn: sqlite3.Connection, cluster_id: str) -> AnalyticsClusterRow | None:
    row = conn.execute(f"{_ANALYTICS_SELECT} WHERE a.id = ?", (cluster_id,)).fetchone()
    return AnalyticsClusterRow.from_row(row) if row else None


def instance_names(conn: sqlite3.Connection) -> dict[tuple[str, str], tuple[str, str | None]]:
    """``(scope, instance_id) -> (name, project_name)`` for every known billable instance."""
    out: dict[tuple[str, str], tuple[str, str | None]] = {}
    for c in list_clusters(conn):
        out[("cluster", c.id)] = (c.name, c.project_name)
    for a in list_app_services(conn):
        out[("appservice", a.id)] = (a.name, a.project_name)
    for x in list_analytics_clusters(conn):
        out[("analytics", x.id)] = (x.name, x.project_name)
    return out


def _prune(conn: sqlite3.Connection, table: str, column: str, keep_ids: Iterable[str]) -> None:
    ids = list(keep_ids)
    if not ids:
        conn.execute(f"DELETE FROM {table}")
        return
    placeholders = ",".join("?" for _ in ids)
    conn.execute(f"DELETE FROM {table} WHERE {column} NOT IN ({placeholders})", ids)
