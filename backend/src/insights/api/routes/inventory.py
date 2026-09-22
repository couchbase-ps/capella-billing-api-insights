"""Projects, operational clusters, App Services and Analytics clusters."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Query, Request

from insights.api import serializers as ser
from insights.api.deps import get_db, resolve_range, today
from insights.api.errors import ApiError
from insights.store import repo
from insights.topology.mapper import analytics_to_topology, cluster_to_topology

router = APIRouter(prefix="/api")

Granularity = Literal["day", "month"]


@router.get("/projects")
def projects(request: Request) -> list[dict[str, Any]]:
    with get_db(request).session() as conn:
        return repo.list_projects_with_counts(conn)


# --- operational clusters ---------------------------------------------------------------


@router.get("/clusters")
def clusters(request: Request) -> list[dict[str, Any]]:
    with get_db(request).session() as conn:
        credits = ser.CreditWindows(conn, "cluster", today(request))
        return [ser.cluster_card(row, credits) for row in repo.list_clusters(conn)]


def _cluster_or_404(conn: Any, cluster_id: str) -> repo.ClusterRow:
    row = repo.get_cluster(conn, cluster_id)
    if row is None:
        raise ApiError(404, "not_found", f"cluster '{cluster_id}' not found")
    return row


@router.get("/clusters/{cluster_id}")
def cluster_detail(request: Request, cluster_id: str) -> dict[str, Any]:
    with get_db(request).session() as conn:
        row = _cluster_or_404(conn, cluster_id)
        now = today(request)
        card = ser.cluster_card(row, ser.CreditWindows(conn, "cluster", now))
        buckets = [ser.bucket_json(b) for b in repo.list_buckets(conn, cluster_id)]
        service = repo.get_app_service_for_cluster(conn, cluster_id)
        service_card = None
        if service is not None:
            endpoints = repo.list_app_endpoints(conn, service.id)
            service_card = ser.app_service_card(
                service, endpoints, ser.CreditWindows(conn, "appservice", now)
            )
    return {
        **card,
        "buckets": buckets,
        "appService": service_card,
        "connectionString": row.raw.get("connectionString"),
        "createdAt": ser.created_at(row.raw),
    }


@router.get("/clusters/{cluster_id}/topology")
def cluster_topology(request: Request, cluster_id: str) -> dict[str, Any]:
    with get_db(request).session() as conn:
        row = _cluster_or_404(conn, cluster_id)
        buckets = repo.list_buckets(conn, cluster_id)
        service = repo.get_app_service_for_cluster(conn, cluster_id)
        endpoints = repo.list_app_endpoints(conn, service.id) if service else []
    return cluster_to_topology(row.raw, buckets, service.raw if service else None, endpoints)


@router.get("/clusters/{cluster_id}/consumption")
def cluster_consumption(
    request: Request,
    cluster_id: str,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    granularity: Granularity = "day",
) -> dict[str, Any]:
    lo, hi = resolve_range(date_from, date_to, today(request))
    with get_db(request).session() as conn:
        _cluster_or_404(conn, cluster_id)
        return ser.consumption_payload(conn, "cluster", cluster_id, lo, hi, granularity)


# --- app services -----------------------------------------------------------------------


@router.get("/appservices")
def app_services(request: Request) -> list[dict[str, Any]]:
    with get_db(request).session() as conn:
        credits = ser.CreditWindows(conn, "appservice", today(request))
        return [
            ser.app_service_card(row, repo.list_app_endpoints(conn, row.id), credits)
            for row in repo.list_app_services(conn)
        ]


@router.get("/appservices/{app_service_id}")
def app_service_detail(request: Request, app_service_id: str) -> dict[str, Any]:
    with get_db(request).session() as conn:
        row = repo.get_app_service(conn, app_service_id)
        if row is None:
            raise ApiError(404, "not_found", f"app service '{app_service_id}' not found")
        credits = ser.CreditWindows(conn, "appservice", today(request))
        card = ser.app_service_card(row, repo.list_app_endpoints(conn, row.id), credits)
    return {**card, "createdAt": ser.created_at(row.raw)}


@router.get("/appservices/{app_service_id}/consumption")
def app_service_consumption(
    request: Request,
    app_service_id: str,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    granularity: Granularity = "day",
) -> dict[str, Any]:
    lo, hi = resolve_range(date_from, date_to, today(request))
    with get_db(request).session() as conn:
        if repo.get_app_service(conn, app_service_id) is None:
            raise ApiError(404, "not_found", f"app service '{app_service_id}' not found")
        return ser.consumption_payload(conn, "appservice", app_service_id, lo, hi, granularity)


# --- analytics clusters -----------------------------------------------------------------


def _analytics_or_404(conn: Any, cluster_id: str) -> repo.AnalyticsClusterRow:
    row = repo.get_analytics_cluster(conn, cluster_id)
    if row is None:
        raise ApiError(404, "not_found", f"analytics cluster '{cluster_id}' not found")
    return row


@router.get("/analyticsclusters")
def analytics_clusters(request: Request) -> list[dict[str, Any]]:
    with get_db(request).session() as conn:
        credits = ser.CreditWindows(conn, "analytics", today(request))
        return [ser.analytics_card(row, credits) for row in repo.list_analytics_clusters(conn)]


@router.get("/analyticsclusters/{cluster_id}")
def analytics_detail(request: Request, cluster_id: str) -> dict[str, Any]:
    with get_db(request).session() as conn:
        row = _analytics_or_404(conn, cluster_id)
        card = ser.analytics_card(row, ser.CreditWindows(conn, "analytics", today(request)))
    return {**card, "createdAt": ser.created_at(row.raw)}


@router.get("/analyticsclusters/{cluster_id}/topology")
def analytics_topology(request: Request, cluster_id: str) -> dict[str, Any]:
    with get_db(request).session() as conn:
        row = _analytics_or_404(conn, cluster_id)
    return analytics_to_topology(row.raw)


@router.get("/analyticsclusters/{cluster_id}/consumption")
def analytics_consumption(
    request: Request,
    cluster_id: str,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    granularity: Granularity = "day",
) -> dict[str, Any]:
    lo, hi = resolve_range(date_from, date_to, today(request))
    with get_db(request).session() as conn:
        _analytics_or_404(conn, cluster_id)
        return ser.consumption_payload(conn, "analytics", cluster_id, lo, hi, granularity)
