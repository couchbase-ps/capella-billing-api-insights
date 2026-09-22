# Capella Billing API Insights

Custom credit-consumption reports and insights for one Couchbase Capella organization,
built on the public [Capella Management API v4.0](https://docs.couchbase.com/cloud/management-api-reference/index.html)
Billing endpoints and the [Capella Analytics Management API](https://docs.couchbase.com/analytics/management-api-reference/index.html),
with operational cluster, Analytics (Columnar) cluster and App Service configurations rendered by
[`@couchbaselabs/topology-ui`](https://github.com/couchbaselabs/topology-ui).

One Capella API key = one organization = one billing account. The key must carry the
**Organization Owner** role, which the Billing endpoints require.

```
backend/    Python 3.12 · FastAPI · httpx · SQLite     — Capella sync, storage, report engine, JSON API
frontend/   React 19 · Vite · Tailwind v4 · Recharts   — dashboard, topology view, reports UI
docs/       API analysis, design spec, backend⇄frontend contract
```

## Quick start (Docker Compose)

```bash
cp .env.example .env            # put your CAPELLA_API_KEY in .env
docker compose up --build
```

- UI: http://localhost:5173
- API: http://localhost:8000 (`/health`, `/api/...`, OpenAPI at `/docs`)

The first start backfills the last 90 days of billing (configurable) and re-syncs every
6 hours. Trigger a sync any time from the Overview page or with `curl -X POST localhost:8000/api/sync`.

### Demo without a key

```bash
CAPELLA_MOCK=true docker compose up --build
```

serves deterministic fixtures (2 projects, 4 clusters, 1 Analytics cluster, 1 App Service, 90 days of synthetic
credits) so the UI and the report engine can be explored offline.

## What it extracts and how

See [docs/capella-management-api-analysis.md](docs/capella-management-api-analysis.md) for
the full endpoint analysis. In short:

- **Per-instance daily credits**: `POST /v4/organizations/{org}/billing` (categorized
  billing) once per calendar month per operational cluster / Analytics cluster / App Service with
  `filters.instanceIds=[id]`. Capella only returns daily periods when the requested range is
  within one month, so the sync splits ranges on month boundaries.
- **Org roll-up**: the same call without filters, so unattributed spend
  (org total minus the sum of instances) is visible.
- **Prepaid credits**: `GET .../billing/prePaidCredits` (blocks with total/used/remaining/expiry).
- **Pay-as-you-go**: `GET .../billing/payAsYouGo`.
- **Inventory**: organizations, projects, clusters (service groups, node sizes, disks),
  buckets, App Services and App Endpoints, plus Analytics clusters (nodes, compute, plan)
  from the Analytics API using the same key, all mapped to the topology-ui document.

Rate limit is 100 requests/minute per key; the client uses a token bucket at 80/min plus
retry with backoff on 429/5xx. Billing data lags up to a few days, so every sync re-fetches
a trailing window (default 7 days).

## Custom reports

Reports are `ReportDefinition`s registered in `backend/src/insights/reports/`. Two are built
in (`consumption-summary`, `cluster-daily`); the target custom credits report will be added
there once its definition is agreed (see the design spec §8).

## Development

Backend: `cd backend && uv sync && CAPELLA_MOCK=true uv run insights serve` (tests: `uv run pytest`).
Frontend: `cd frontend && npm ci && npm run dev` (gates: `npm run lint && npm run typecheck && npm test && npm run build`).

## Documents

- [Capella Management API analysis](docs/capella-management-api-analysis.md)
- [Design spec](docs/superpowers/specs/2026-09-22-capella-billing-insights-design.md)
- [Backend ⇄ frontend API contract](docs/api-contract.md)
