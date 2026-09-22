"""Store rows -> contract JSON (cards, details, consumption payloads)."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any, Literal

from insights.store import repo


def _credit_fields(c7: repo.Money | None, c30: repo.Money | None) -> dict[str, float | None]:
    return {
        "credits7d": c7.credits if c7 else None,
        "credits30d": c30.credits if c30 else None,
        "currency7d": c7.currency if c7 else None,
        "currency30d": c30.currency if c30 else None,
    }


class CreditWindows:
    """Per-instance 7-day and 30-day totals for one scope, computed once per request."""

    def __init__(self, conn: sqlite3.Connection, scope: str, now: date) -> None:
        yesterday = now - timedelta(days=1)
        self.last7 = repo.credits_per_instance(conn, scope, now - timedelta(days=7), yesterday)
        self.last30 = repo.credits_per_instance(conn, scope, now - timedelta(days=30), yesterday)

    def fields(self, instance_id: str) -> dict[str, float | None]:
        return _credit_fields(self.last7.get(instance_id), self.last30.get(instance_id))


def service_groups(raw: dict[str, Any]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for group in raw.get("serviceGroups") or []:
        node = group.get("node") or {}
        compute = node.get("compute") or {}
        disk = node.get("disk") or {}
        groups.append(
            {
                "services": list(group.get("services") or []),
                "numOfNodes": group.get("numOfNodes"),
                "cpu": compute.get("cpu"),
                "ram": compute.get("ram"),
                "diskType": disk.get("type"),
                "diskGb": disk.get("storage"),
                "iops": disk.get("iops"),
            }
        )
    return groups


def cluster_card(row: repo.ClusterRow, credits: CreditWindows) -> dict[str, Any]:
    groups = service_groups(row.raw)
    return {
        "id": row.id,
        "name": row.name,
        "projectId": row.project_id,
        "projectName": row.project_name,
        "provider": row.provider,
        "region": row.region,
        "version": row.version,
        "supportPlan": row.support_plan,
        "availability": row.availability,
        "state": row.state,
        "freeTier": row.free_tier,
        "nodes": sum(g["numOfNodes"] or 0 for g in groups),
        "serviceGroups": groups,
        "appServiceId": row.app_service_id,
        **credits.fields(row.id),
    }


def bucket_json(raw: dict[str, Any]) -> dict[str, Any]:
    stats = raw.get("stats") or {}
    return {
        "name": raw.get("name"),
        "storageBackend": raw.get("storageBackend"),
        "memoryAllocationInMb": raw.get("memoryAllocationInMb"),
        "replicas": raw.get("replicas"),
        "evictionPolicy": raw.get("evictionPolicy"),
        "itemCount": stats.get("itemCount"),
        "memoryUsedInMib": stats.get("memoryUsedInMib"),
        "diskUsedInMib": stats.get("diskUsedInMib"),
        "timeToLiveInSeconds": raw.get("timeToLiveInSeconds"),
    }


def app_service_card(
    row: repo.AppServiceRow, endpoints: list[dict[str, Any]], credits: CreditWindows
) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "clusterId": row.cluster_id,
        "clusterName": row.cluster_name,
        "projectId": row.project_id,
        "projectName": row.project_name,
        "provider": row.provider,
        "nodes": row.nodes,
        "cpu": row.cpu,
        "ram": row.ram,
        "version": row.version,
        "plan": row.plan,
        "state": row.state,
        "endpoints": [
            {
                "name": e.get("name"),
                "bucket": e.get("bucket"),
                "state": (e.get("state") or "").lower() or None,
            }
            for e in endpoints
        ],
        **credits.fields(row.id),
    }


def analytics_card(row: repo.AnalyticsClusterRow, credits: CreditWindows) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "projectId": row.project_id,
        "projectName": row.project_name,
        "provider": row.provider,
        "region": row.region,
        "nodes": row.nodes,
        "cpu": row.cpu,
        "ram": row.ram,
        "supportPlan": row.support_plan,
        "availability": row.availability,
        "state": row.state,
        **credits.fields(row.id),
    }


def created_at(raw: dict[str, Any]) -> str | None:
    return (raw.get("audit") or {}).get("createdAt")


def consumption_payload(
    conn: sqlite3.Connection,
    scope: str,
    instance_id: str,
    lo: date,
    hi: date,
    granularity: Literal["day", "month"],
) -> dict[str, Any]:
    """Contract shape shared by cluster / App Service / Analytics consumption endpoints."""
    series = repo.usage_by_period(conn, scope, instance_id, lo, hi, granularity)
    by_category = repo.usage_by_category(conn, scope, instance_id, lo, hi)
    total = repo.usage_total(conn, scope, instance_id, lo, hi)
    currency, _ = repo.billing_meta(conn)
    return {
        "scope": scope,
        "instanceId": instance_id,
        "from": lo.isoformat(),
        "to": hi.isoformat(),
        "granularity": granularity,
        "currency": currency,
        "series": series,
        "byCategory": by_category,
        "total": total.as_json(),
    }
