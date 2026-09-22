"""Inventory sync: org -> projects -> clusters -> buckets -> App Services -> Analytics."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from insights.capella.client import CapellaSource
from insights.capella.models import (
    AnalyticsCluster,
    AppEndpoint,
    AppService,
    Bucket,
    Cluster,
    Organization,
    Project,
)
from insights.config import Settings
from insights.store import repo
from insights.store.db import Database

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Failure:
    """A non-fatal problem with one instance, reported in ``sync_run.detail``."""

    scope: str
    instance_id: str
    message: str

    def as_json(self) -> dict[str, str]:
        return {"scope": self.scope, "instanceId": self.instance_id, "message": self.message}


@dataclass
class Inventory:
    """Everything the billing sync and the store need, as fetched from Capella."""

    org: Organization
    projects: list[Project] = field(default_factory=list)
    clusters: list[tuple[str, Cluster]] = field(default_factory=list)  # (project_id, cluster)
    buckets: dict[str, list[Bucket]] = field(default_factory=dict)
    app_services: list[AppService] = field(default_factory=list)
    endpoints: dict[str, list[AppEndpoint]] = field(default_factory=dict)
    analytics: list[tuple[str, AnalyticsCluster]] = field(default_factory=list)
    failures: list[Failure] = field(default_factory=list)

    @property
    def billable_clusters(self) -> list[tuple[str, Cluster]]:
        return [(pid, c) for pid, c in self.clusters if not c.is_free_tier]

    @property
    def project_of_cluster(self) -> dict[str, str]:
        return {c.id: pid for pid, c in self.clusters}


def _pick_org(orgs: list[Organization], wanted: str | None) -> Organization:
    if wanted:
        for org in orgs:
            if org.id == wanted:
                return org
        return Organization(id=wanted, name=orgs[0].name if len(orgs) == 1 else wanted)
    if not orgs:
        raise RuntimeError("the API key has access to no organization")
    return orgs[0]


async def fetch_inventory(client: CapellaSource, settings: Settings) -> Inventory:
    """Walk the Capella inventory. Per-cluster/App Service problems are recorded, not raised."""
    orgs = await client.list_organizations()
    org = _pick_org(orgs, settings.capella_org_id)
    client.org_id = org.id
    inv = Inventory(org=org)
    inv.projects = await client.list_projects()

    for project in inv.projects:
        clusters = await client.list_clusters(project.id)
        inv.clusters.extend((project.id, c) for c in clusters)
        for cluster in clusters:
            if cluster.is_free_tier:
                continue
            try:
                inv.buckets[cluster.id] = await client.list_buckets(project.id, cluster.id)
            except Exception as exc:
                log.warning("buckets of cluster %s failed: %s", cluster.id, exc)
                inv.failures.append(Failure("cluster", cluster.id, f"buckets: {exc}"))

    inv.app_services = await client.list_app_services()
    project_of = inv.project_of_cluster
    for service in inv.app_services:
        project_id = project_of.get(service.cluster_id)
        if project_id is None:
            inv.failures.append(
                Failure("appservice", service.id, "linked cluster not found in inventory")
            )
            continue
        try:
            inv.endpoints[service.id] = await client.list_app_endpoints(
                project_id, service.cluster_id, service.id
            )
        except Exception as exc:
            log.warning("endpoints of app service %s failed: %s", service.id, exc)
            inv.failures.append(Failure("appservice", service.id, f"endpoints: {exc}"))

    for project in inv.projects:
        try:
            rows = await client.list_analytics_clusters(project.id)
        except Exception as exc:
            log.warning("analytics clusters of project %s failed: %s", project.id, exc)
            inv.failures.append(Failure("analytics", project.id, f"list: {exc}"))
            continue
        inv.analytics.extend((project.id, a) for a in rows)
    return inv


def persist_inventory(db: Database, inv: Inventory, synced_at: str) -> None:
    """Write the inventory in one transaction, pruning resources Capella no longer lists."""
    with db.session() as conn:
        repo.upsert_organization(conn, inv.org, synced_at)
        repo.upsert_projects(conn, inv.org.id, inv.projects)
        repo.prune_projects(conn, [p.id for p in inv.projects])
        by_project: dict[str, list[Cluster]] = {}
        for project_id, cluster in inv.clusters:
            by_project.setdefault(project_id, []).append(cluster)
        for project_id, clusters in by_project.items():
            repo.upsert_clusters(conn, project_id, clusters, synced_at)
        repo.prune_clusters(conn, [c.id for _, c in inv.clusters])
        for cluster_id, buckets in inv.buckets.items():
            repo.replace_buckets(conn, cluster_id, buckets)
        repo.upsert_app_services(conn, inv.app_services)
        repo.prune_app_services(conn, [s.id for s in inv.app_services])
        for service_id, endpoints in inv.endpoints.items():
            repo.replace_app_endpoints(conn, service_id, endpoints)
        analytics_by_project: dict[str, list[AnalyticsCluster]] = {}
        for project_id, cluster in inv.analytics:
            analytics_by_project.setdefault(project_id, []).append(cluster)
        for project_id, rows in analytics_by_project.items():
            repo.upsert_analytics_clusters(conn, project_id, rows, synced_at)
        repo.prune_analytics_clusters(conn, [a.id for _, a in inv.analytics])


async def sync_inventory(
    client: CapellaSource, db: Database, settings: Settings, synced_at: str
) -> Inventory:
    """Fetch and persist the inventory."""
    inv = await fetch_inventory(client, settings)
    await asyncio.to_thread(persist_inventory, db, inv, synced_at)
    log.info(
        "inventory synced: %d projects, %d clusters, %d app services, %d analytics clusters",
        len(inv.projects),
        len(inv.clusters),
        len(inv.app_services),
        len(inv.analytics),
    )
    return inv
