"""HTTP client for the Capella Management API v4 and the ``CapellaSource`` protocol."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from datetime import date
from typing import Any, Protocol, runtime_checkable

import httpx

from insights.capella.limiter import RetryPolicy, Sleeper, TokenBucket
from insights.capella.models import (
    AnalyticsCluster,
    AppEndpoint,
    AppService,
    Bucket,
    CategorizedBilling,
    Cluster,
    ItemizedBilling,
    Organization,
    PayAsYouGo,
    PrepaidCredit,
    Project,
)

log = logging.getLogger(__name__)


class CapellaAPIError(Exception):
    """A non-retryable (or retry-exhausted) Capella error with the API's error body."""

    def __init__(self, http_status: int, code: int | None, message: str, hint: str = "") -> None:
        super().__init__(f"Capella {http_status} (code {code}): {message}")
        self.http_status = http_status
        self.code = code
        self.message = message
        self.hint = hint

    @classmethod
    def from_response(cls, response: httpx.Response) -> CapellaAPIError:
        body: dict[str, Any] = {}
        try:
            parsed = response.json()
            if isinstance(parsed, dict):
                body = parsed
        except ValueError:
            pass
        return cls(
            http_status=response.status_code,
            code=body.get("code"),
            message=str(body.get("message") or response.reason_phrase or "request failed"),
            hint=str(body.get("hint") or ""),
        )


@runtime_checkable
class CapellaSource(Protocol):
    """Everything the sync needs from Capella; implemented by the real and mock clients."""

    org_id: str | None
    requests_made: int

    async def list_organizations(self) -> list[Organization]: ...
    async def list_projects(self) -> list[Project]: ...
    async def list_clusters(self, project_id: str) -> list[Cluster]: ...
    async def list_buckets(self, project_id: str, cluster_id: str) -> list[Bucket]: ...
    async def list_app_services(self) -> list[AppService]: ...
    async def list_app_endpoints(
        self, project_id: str, cluster_id: str, app_service_id: str
    ) -> list[AppEndpoint]: ...
    async def list_analytics_clusters(self, project_id: str) -> list[AnalyticsCluster]: ...
    async def categorized_billing(
        self,
        start: date,
        end: date,
        instance_ids: Sequence[str] | None = None,
        project_ids: Sequence[str] | None = None,
        categories: Sequence[str] | None = None,
    ) -> CategorizedBilling: ...
    async def itemized_billing(
        self, project_id: str, cluster_id: str, start: date, end: date
    ) -> ItemizedBilling: ...
    async def prepaid_credits(self) -> list[PrepaidCredit]: ...
    async def pay_as_you_go(self, start: date, end: date) -> PayAsYouGo: ...
    async def aclose(self) -> None: ...


class CapellaClient:
    """Async client: bearer auth, token-bucket limiter, retry on 429/5xx, page walking."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://cloudapi.cloud.couchbase.com",
        rate_limit_per_minute: float = 80,
        org_id: str | None = None,
        *,
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
        limiter: TokenBucket | None = None,
        retry: RetryPolicy | None = None,
        sleep: Sleeper = asyncio.sleep,
    ) -> None:
        self.org_id = org_id
        self.requests_made = 0
        self._limiter = limiter or TokenBucket(rate_limit_per_minute)
        self._retry = retry or RetryPolicy()
        self._sleep = sleep
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
            timeout=timeout,
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> CapellaClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    # --- transport ----------------------------------------------------------------------

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform one API call with limiter + retries; return the parsed JSON object."""
        attempts = self._retry.max_attempts
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            await self._limiter.acquire()
            self.requests_made += 1
            try:
                response = await self._http.request(method, path, params=params, json=json)
            except httpx.TransportError as exc:
                last_error = exc
                log.warning("capella transport error %s %s: %s", method, path, exc)
                if attempt == attempts:
                    break
                await self._sleep(self._retry.delay_for(attempt))
                continue
            if response.is_success:
                if not response.content:
                    return {}
                payload = response.json()
                return payload if isinstance(payload, dict) else {"data": payload}
            if self._retry.should_retry(response.status_code):
                last_error = CapellaAPIError.from_response(response)
                allowed = self._retry.attempts_for(response.status_code)
                log.warning(
                    "capella %s %s -> %s (attempt %d/%d)",
                    method,
                    path,
                    response.status_code,
                    attempt,
                    allowed,
                )
                if attempt >= allowed:
                    break
                delay = self._retry.delay_for(attempt, response.headers.get("Retry-After"))
                await self._sleep(delay)
                continue
            raise CapellaAPIError.from_response(response)
        assert last_error is not None
        if isinstance(last_error, CapellaAPIError):
            raise last_error
        raise CapellaAPIError(0, None, f"transport error: {last_error}")

    async def walk_pages(
        self, path: str, params: dict[str, Any] | None = None, per_page: int = 100
    ) -> list[dict[str, Any]]:
        """GET every page of a cursor-paginated list and return the concatenated ``data``."""
        items: list[dict[str, Any]] = []
        page = 1
        while True:
            query = {**(params or {}), "page": page, "perPage": per_page}
            payload = await self.request("GET", path, params=query)
            data = payload.get("data") or []
            items.extend(data)
            cursor = payload.get("cursor") or {}
            next_page = (cursor.get("pages") or {}).get("next")
            if not next_page or next_page <= page or not data:
                return items
            page = int(next_page)

    def _org(self) -> str:
        if not self.org_id:
            raise RuntimeError("organization id not set; call list_organizations() first")
        return self.org_id

    # --- inventory ----------------------------------------------------------------------

    async def list_organizations(self) -> list[Organization]:
        """List organizations visible to the key (exactly one) and remember its id."""
        payload = await self.request("GET", "/v4/organizations")
        orgs = [Organization.model_validate(item) for item in payload.get("data") or []]
        if orgs and self.org_id is None:
            self.org_id = orgs[0].id
        return orgs

    async def list_projects(self) -> list[Project]:
        rows = await self.walk_pages(f"/v4/organizations/{self._org()}/projects")
        return [Project.model_validate(row) for row in rows]

    async def list_clusters(self, project_id: str) -> list[Cluster]:
        path = f"/v4/organizations/{self._org()}/projects/{project_id}/clusters"
        return [Cluster.model_validate(row) for row in await self.walk_pages(path)]

    async def list_buckets(self, project_id: str, cluster_id: str) -> list[Bucket]:
        path = (
            f"/v4/organizations/{self._org()}/projects/{project_id}/clusters/{cluster_id}/buckets"
        )
        payload = await self.request("GET", path)
        return [Bucket.model_validate(row) for row in payload.get("data") or []]

    async def list_app_services(self) -> list[AppService]:
        rows = await self.walk_pages(f"/v4/organizations/{self._org()}/appservices")
        return [AppService.model_validate(row) for row in rows]

    async def list_app_endpoints(
        self, project_id: str, cluster_id: str, app_service_id: str
    ) -> list[AppEndpoint]:
        path = (
            f"/v4/organizations/{self._org()}/projects/{project_id}/clusters/{cluster_id}"
            f"/appservices/{app_service_id}/appEndpoints"
        )
        return [AppEndpoint.model_validate(row) for row in await self.walk_pages(path)]

    async def list_analytics_clusters(self, project_id: str) -> list[AnalyticsCluster]:
        """Analytics (Columnar) clusters of a project via the Analytics Management API."""
        path = f"/v4/organizations/{self._org()}/projects/{project_id}/analyticsClusters"
        return [AnalyticsCluster.model_validate(row) for row in await self.walk_pages(path)]

    # --- billing ------------------------------------------------------------------------

    async def categorized_billing(
        self,
        start: date,
        end: date,
        instance_ids: Sequence[str] | None = None,
        project_ids: Sequence[str] | None = None,
        categories: Sequence[str] | None = None,
    ) -> CategorizedBilling:
        """``POST /billing``: spend per category per period, optionally filtered."""
        body: dict[str, Any] = {"startDate": start.isoformat(), "endDate": end.isoformat()}
        filters: dict[str, Any] = {}
        if instance_ids:
            filters["instanceIds"] = list(instance_ids)
        if project_ids:
            filters["projectIds"] = list(project_ids)
        if categories:
            filters["categories"] = list(categories)
        if filters:
            body["filters"] = filters
        payload = await self.request("POST", f"/v4/organizations/{self._org()}/billing", json=body)
        return CategorizedBilling.model_validate(payload["data"])

    async def itemized_billing(
        self, project_id: str, cluster_id: str, start: date, end: date
    ) -> ItemizedBilling:
        path = (
            f"/v4/organizations/{self._org()}/projects/{project_id}/clusters/{cluster_id}/billing"
        )
        body = {"startDate": start.isoformat(), "endDate": end.isoformat()}
        payload = await self.request("POST", path, json=body)
        return ItemizedBilling.model_validate(payload["data"])

    async def prepaid_credits(self) -> list[PrepaidCredit]:
        rows = await self.walk_pages(f"/v4/organizations/{self._org()}/billing/prePaidCredits")
        return [PrepaidCredit.model_validate(row) for row in rows]

    async def pay_as_you_go(self, start: date, end: date) -> PayAsYouGo:
        payload = await self.request(
            "GET",
            f"/v4/organizations/{self._org()}/billing/payAsYouGo",
            params={"startDate": start.isoformat(), "endDate": end.isoformat()},
        )
        return PayAsYouGo.model_validate(payload["data"])
