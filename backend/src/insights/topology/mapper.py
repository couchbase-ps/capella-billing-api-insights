"""Map Capella inventory (raw API JSON) to ``@couchbaselabs/topology-ui`` documents.

See ``docs/capella-management-api-analysis.md`` §5 and §7. Figures Capella does not report
are emitted as ``{"value": null, "status": "absent"}`` so the renderer prints an em-dash.
"""

from __future__ import annotations

from typing import Any


def absent() -> dict[str, Any]:
    return {"value": None, "status": "absent"}


def status_of(state: str | None) -> str:
    """``HEALTHY`` for Capella's ``healthy``; otherwise the raw state upper-cased."""
    if not state:
        return "UNKNOWN"
    return "HEALTHY" if state == "healthy" else state.upper()


def memory_gb(ram: int | float | None) -> str | dict[str, Any]:
    return absent() if ram is None else f"{ram:g} GB"


def _resources(compute: dict[str, Any] | None) -> dict[str, Any]:
    compute = compute or {}
    cpu = compute.get("cpu")
    return {"cpus": cpu if cpu is not None else absent(), "memory": memory_gb(compute.get("ram"))}


def _node_name(services_label: str, disk: dict[str, Any] | None) -> str:
    """Short tile label: the disk size and type (``100GB gp3``) when known, else the services.

    topology-ui middle-elides long node names, so the label must stay under ~12 characters;
    the services are already drawn on the tile.
    """
    if not disk:
        return services_label
    parts: list[str] = []
    if disk.get("storage") is not None:
        parts.append(f"{disk['storage']}GB")
    if disk.get("type"):
        parts.append(str(disk["type"]))
    return " ".join(parts) if parts else services_label


def _service_label(service: str) -> str:
    return service[:1].upper() + service[1:]


def _server_group(group: dict[str, Any], status: str) -> dict[str, Any]:
    services = [str(s) for s in group.get("services") or []]
    node = group.get("node") or {}
    name = "/".join(services) or "nodes"
    total = group.get("numOfNodes")
    return {
        "name": name,
        "status": status,
        "nodes": [
            {
                "name": _node_name(name, node.get("disk")),
                "resources": _resources(node.get("compute")),
                "services": [_service_label(s) for s in services],
                "status": status,
                "total": total if total is not None else absent(),
            }
        ],
    }


def _bucket(bucket: dict[str, Any]) -> dict[str, Any]:
    stats = bucket.get("stats") or {}
    quota = bucket.get("memoryAllocationInMb")
    used = stats.get("memoryUsedInMib")
    backend = (bucket.get("storageBackend") or "").lower()
    kind = bucket.get("type") or ""
    if kind == "ephemeral" or backend == "ephemeral":
        bucket_type = "ephemeral"
    elif backend in {"magma", "couchstore"} or kind == "couchbase":
        bucket_type = "couchbase"
    else:
        bucket_type = kind or absent()
    ratio: float | dict[str, Any]
    if quota and used is not None:
        ratio = round(used / quota, 2)
    else:
        ratio = absent()
    return {
        "name": bucket.get("name"),
        "type": bucket_type,
        "quota": f"{quota} MB" if quota is not None else absent(),
        "documents": stats.get("itemCount") if stats.get("itemCount") is not None else absent(),
        "replicas": bucket.get("replicas") if bucket.get("replicas") is not None else absent(),
        "ratio": ratio,
        "eviction": bucket.get("evictionPolicy") or absent(),
    }


def _cluster_resources(groups: list[dict[str, Any]]) -> dict[str, Any]:
    cpus = 0
    ram = 0
    for group in groups:
        n = group.get("numOfNodes") or 0
        compute = (group.get("node") or {}).get("compute") or {}
        cpus += n * (compute.get("cpu") or 0)
        ram += n * (compute.get("ram") or 0)
    if not groups:
        return {"cpus": absent(), "memory": absent()}
    return {"cpus": cpus, "memory": memory_gb(ram)}


def _mobile(app_service: dict[str, Any], endpoints: list[dict[str, Any]]) -> dict[str, Any]:
    status = status_of(app_service.get("currentState"))
    nodes = app_service.get("nodes")
    mobile: dict[str, Any] = {
        "status": status,
        "resources": _resources(app_service.get("compute")),
        "groups": [
            {
                "name": app_service.get("name"),
                "status": status,
                "instances": [
                    {
                        "name": app_service.get("name"),
                        # topology-ui prints nodeIp verbatim ("undefined" when missing).
                        "nodeIp": app_service.get("name") or "",
                        "resources": _resources(app_service.get("compute")),
                        "status": status,
                        "total": nodes if nodes is not None else absent(),
                    }
                ],
            }
        ],
        "databases": [{"name": e.get("name")} for e in endpoints],
    }
    if app_service.get("version"):
        mobile["version"] = app_service["version"]
    return mobile


def cluster_to_topology(
    cluster: dict[str, Any],
    buckets: list[dict[str, Any]],
    app_service: dict[str, Any] | None = None,
    endpoints: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the topology-ui document for an operational cluster.

    ``cluster`` / ``buckets`` / ``app_service`` / ``endpoints`` are the raw Capella JSON objects
    as stored in ``raw_json``. ``mobile`` is present only when an App Service is attached.
    """
    status = status_of(cluster.get("currentState"))
    groups = list(cluster.get("serviceGroups") or [])
    doc: dict[str, Any] = {
        "name": cluster.get("name"),
        "status": status,
        "resources": _cluster_resources(groups),
        "serverGroups": [_server_group(g, status) for g in groups],
        "buckets": [_bucket(b) for b in buckets],
    }
    version = (cluster.get("couchbaseServer") or {}).get("version")
    if version:
        # topology-ui prints "v" + version verbatim, so an unknown version is omitted, not absent().
        doc["version"] = version
    if app_service is not None:
        doc["mobile"] = _mobile(app_service, endpoints or [])
    return doc


def analytics_to_topology(cluster: dict[str, Any]) -> dict[str, Any]:
    """Topology-ui document for an Analytics (Columnar) cluster: one ``analytics`` group."""
    status = status_of(cluster.get("currentState"))
    nodes = cluster.get("nodes")
    compute = cluster.get("compute") or {}
    resources = _resources(compute)
    total_cpus = (nodes or 0) * (compute.get("cpu") or 0)
    total_ram = (nodes or 0) * (compute.get("ram") or 0)
    return {
        "name": cluster.get("name"),
        "status": status,
        "resources": {"cpus": total_cpus, "memory": memory_gb(total_ram)} if nodes else resources,
        "serverGroups": [
            {
                "name": "analytics",
                "status": status,
                "nodes": [
                    {
                        "name": "analytics",
                        "resources": resources,
                        "services": ["Analytics"],
                        "status": status,
                        "total": nodes if nodes is not None else absent(),
                    }
                ],
            }
        ],
    }
