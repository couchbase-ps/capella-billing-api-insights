# Capella Billing API Insights — design

Date: 2026-09-22. Status: implemented as v0.1 scaffold; the target custom credits report is
still to be defined by the owner and is a deliberate open slot (see §8).

## 1. Purpose

Give a Couchbase PS engineer, holding one Capella Management API key with the Organization
Owner role (one key = one organization = one billing account), a local tool that:

1. pulls credit consumption per cluster and per App Service from the Capella Billing API,
2. pulls the inventory (projects, clusters, service groups, buckets, App Services),
3. shows each cluster / App Service configuration with `@couchbaselabs/topology-ui`,
4. shows credit consumption over time and prepaid-credit balance,
5. leaves a clean extension point for custom credits reports.

Everything runs locally with `docker compose up`. No multi-tenant auth: the backend holds
the key, the UI is a local dashboard.

Non-goals for v0.1: forecasting, plan-vs-actual, exports beyond CSV, dark theme, mutating
anything in Capella (the tool only performs GET/POST-read calls).

## 2. Repository layout (backend and frontend split)

```
capella-billing-api-insights/
  docker-compose.yml          # backend + frontend (+ optional mock profile)
  .env.example                # CAPELLA_API_KEY, sync window, mock switch
  docs/                       # API analysis, this spec, plans
  backend/                    # Python 3.12, FastAPI, httpx, SQLite
    Dockerfile
    pyproject.toml
    src/insights/
      config.py               # pydantic-settings
      capella/client.py       # bearer auth, token-bucket limiter, 429/5xx retry, pagination
      capella/models.py       # pydantic models of the API shapes we read
      capella/mock.py         # fixture-backed client for demo/tests (CAPELLA_MOCK=true)
      store/db.py             # sqlite connection + schema
      store/repo.py           # typed repositories
      sync/inventory.py       # org -> projects -> clusters -> buckets -> app services -> endpoints
      sync/billing.py         # monthly-window categorized billing per instance + org roll-up
      sync/runner.py          # orchestrates a sync, records sync_runs
      topology/mapper.py      # Capella inventory -> topology-ui document
      reports/registry.py     # report definitions (extension point)
      reports/builtin.py      # consumption summary + per-cluster CSV
      api/app.py, api/routes/*.py
      cli.py                  # `insights sync`, `insights serve`
    tests/                    # pytest, fixtures under tests/fixtures
    vendor/capella-openapi.yaml
  frontend/                   # React 19 + TypeScript + Vite + Tailwind v4 + TanStack Query
    Dockerfile
    src/api/                  # typed client over backend JSON
    src/pages/{Overview,Clusters,ClusterDetail,AppServices,Reports}.tsx
    src/components/TopologyView.tsx   # wraps topology-ui mountTopology
    src/components/charts/*           # Recharts consumption charts
```

## 3. Backend

### 3.1 Configuration (environment)

| Variable | Default | Meaning |
|---|---|---|
| `CAPELLA_API_KEY` | required unless mock | Bearer secret |
| `CAPELLA_BASE_URL` | `https://cloudapi.cloud.couchbase.com` | |
| `CAPELLA_ORG_ID` | auto | Override; otherwise discovered via `GET /v4/organizations` |
| `CAPELLA_MOCK` | `false` | Serve fixtures instead of calling Capella |
| `SYNC_BACKFILL_DAYS` | `90` | How far back the first sync fetches |
| `SYNC_REFRESH_DAYS` | `7` | Trailing window re-fetched on every sync (billing lag) |
| `SYNC_ON_START` | `true` | Run a sync when the API starts |
| `SYNC_INTERVAL_MINUTES` | `360` | Background resync cadence; 0 disables |
| `RATE_LIMIT_PER_MINUTE` | `80` | Token bucket below Capella's 100/min |
| `DB_PATH` | `/data/insights.db` | SQLite file (compose volume) |

### 3.2 Capella client

`CapellaClient` (httpx.AsyncClient) exposes one method per operation we use, returning
pydantic models. Cross-cutting: bearer header, token-bucket limiter, retry with exponential
backoff on 429 (honouring `Retry-After` when present) and 5xx up to 5 attempts, automatic
page walking for cursor responses. `CapellaAPIError` carries `httpStatusCode`, `code`,
`message`, `hint`. A `Protocol` `CapellaSource` lets `MockCapellaClient` (JSON fixtures)
replace it for tests and for `CAPELLA_MOCK=true`.

### 3.3 Storage (SQLite)

Tables (all timestamps ISO-8601 UTC):

- `organization(id PK, name, raw_json, synced_at)`
- `project(id PK, org_id, name, raw_json)`
- `cluster(id PK, project_id, name, provider, region, version, support_plan, availability,
  state, app_service_id, free_tier INT, raw_json, synced_at)`
- `bucket(cluster_id, name, raw_json, PK(cluster_id, name))`
- `app_service(id PK, cluster_id, name, nodes, cpu, ram, version, plan, state, raw_json)`
- `app_endpoint(app_service_id, name, bucket, raw_json, PK(app_service_id, name))`
- `credit_usage(day DATE, scope TEXT, instance_id TEXT, category TEXT, credit_spend REAL,
  currency_spend REAL, currency TEXT, fetched_at, PK(day, scope, instance_id, category))`
  where `scope ∈ {org, cluster, appservice}` and `instance_id` is `''` for `org`.
- `prepaid_credit(id PK, credit_name, support_plan, start_date, expiration_date, total,
  used, remaining, remaining_percent, fetched_at)`
- `payg_period(day DATE PK, basic, dev_pro, enterprise, total, currency, fetched_at)`
- `sync_run(id PK, started_at, finished_at, status, requests_made, error, detail_json)`

Daily rows are upserted; a re-fetch of a window replaces the rows for that window and
scope so Capella's late corrections win.

### 3.4 Sync algorithm

```
sync():
  org = discover()                       # GET /v4/organizations (or CAPELLA_ORG_ID)
  projects = walk(listProjects)
  for p in projects: clusters += walk(listClusters(p))
  for c in clusters (non free-tier): buckets[c] = listBuckets(c)
  appservices = walk(listAppServices)
  for a in appservices: endpoints[a] = walk(listAppEndpoints(a))
  window = [max(first_missing_day, today-BACKFILL), yesterday]
           ∪ [today-REFRESH, yesterday]
  for each calendar month m overlapping window:
     org_usage   = categorizedBilling(m)                        # scope=org
     for c in billable clusters: categorizedBilling(m, instanceIds=[c.id])   # scope=cluster
     for a in appservices:       categorizedBilling(m, instanceIds=[a.id])   # scope=appservice
     payg = payAsYouGoBilling(m)
  prepaid = walk(prepaidCreditsBilling)
  upsert everything; record sync_run
```

Month windows are clipped to the requested range and never cross a month boundary so
Capella returns daily periods. Failures of one instance are recorded in `sync_run.detail`
and do not abort the run.

### 3.5 HTTP API (consumed by the frontend)

All under `/api`, JSON, no auth.

| Method + path | Returns |
|---|---|
| `GET /health` | `{status, mock, lastSync}` |
| `GET /api/organization` | org + counts + last sync |
| `GET /api/projects` | projects with cluster counts |
| `GET /api/clusters` | cluster cards: id, name, project, provider/region, version, plan, state, nodes, appServiceId, `credits30d`, `credits7d` |
| `GET /api/clusters/{id}` | cluster detail with buckets and linked App Service |
| `GET /api/clusters/{id}/topology` | topology-ui document |
| `GET /api/clusters/{id}/consumption?from&to&granularity=day|month` | `{series:[{day, category, credits, currency}], total}` |
| `GET /api/appservices` | App Service cards with credits |
| `GET /api/appservices/{id}/consumption?...` | same shape |
| `GET /api/billing/summary?from&to` | org total by category + unattributed remainder |
| `GET /api/billing/consumption?from&to&groupBy=category|instance|day` | flexible aggregation |
| `GET /api/billing/prepaid` | prepaid credit blocks + aggregate remaining |
| `GET /api/billing/payg?from&to` | PAYG periods |
| `GET /api/reports` | registered report definitions |
| `GET /api/reports/{key}?from&to&format=json|csv` | run a report |
| `POST /api/sync` | trigger a sync (202, or 409 if one is running) |
| `GET /api/sync/status` | last runs |

### 3.6 Reports extension point

`reports/registry.py` holds `ReportDefinition(key, title, description, params, run)`. A
report receives a `ReportContext` (repositories + date range) and returns a `ReportResult`
(columns, rows, totals) that the API serialises to JSON or CSV. Built-ins: `consumption-summary`
(per instance per category over the range) and `cluster-daily` (one cluster, day rows). The
owner's custom credits report will be added as another definition without touching the API.

## 4. Frontend

React 19, Vite, TypeScript strict, Tailwind v4 (`@theme` tokens, Couchbase brand colours
reused from the sibling project), TanStack Query for server state, Recharts for charts,
`@couchbaselabs/topology-ui` for topology. Pages:

- **Overview**: prepaid credits remaining (cards per credit block), org credits over time
  stacked by category, top consumers table, sync status + "Sync now".
- **Clusters**: table with provider, region, plan, state, nodes, credits 7d/30d.
- **Cluster detail**: topology-ui render (cluster + attached App Service), daily credits chart
  by category, category table, link to CSV.
- **App Services**: table + detail reuse of the consumption chart.
- **Reports**: list of registered reports, run with a date range, download CSV.

`TopologyView` copies `node_modules/@couchbaselabs/topology-ui/images` into `public/topology-ui/images`
at build time and calls `mountTopology(el, doc, {assetRoot})`.

## 5. Docker compose

Services: `backend` (uv-based python image, port 8000, volume `insights-data:/data`),
`frontend` (node build served by `vite preview`/nginx, port 5173, proxies `/api` and `/health`
to backend). Profile `mock` starts the same stack with `CAPELLA_MOCK=true` for demos.

## 6. Error handling

- Missing key without mock: backend starts, `/health` reports `configured:false`, sync
  refuses with a clear message; UI shows a setup banner.
- Capella 401/403: sync_run failed with the Capella message; UI banner.
- 429: limiter + retry; surfaced only if retries are exhausted.
- Partial failures per instance are stored and displayed as "partial" in the sync status.

## 7. Testing

Backend: pytest with fixture JSON (recorded shapes from the OpenAPI examples); unit tests for
month-window splitting, limiter/retry, topology mapping, upsert semantics and report output.
Frontend: vitest + Testing Library for the topology mapper glue and the consumption table.
End-to-end: `docker compose --profile mock up` and a browser smoke check.

## 8. Open slot: the custom credits report

The owner will define the target report later. What is already in place for it: daily
per-instance per-category credit rows, inventory joins (project, plan, provider, region,
node sizes), prepaid balance, and the report registry. Expected additions: a new
`ReportDefinition`, a page or table in `Reports`, and possibly new sync fields.
