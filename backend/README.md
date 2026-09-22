# Capella Billing API Insights — backend

FastAPI + SQLite service that syncs credit consumption and inventory from the Capella
Management API (operational clusters, App Services, Analytics clusters) and serves the JSON
contract in `docs/api-contract.md` to the frontend.

## Run locally (uv)

```bash
cd backend
uv sync                                 # creates .venv with pinned deps (Python >= 3.12)
CAPELLA_MOCK=true DB_PATH=./insights.db uv run insights serve      # http://localhost:8000
# or against Capella:
CAPELLA_API_KEY=<secret> DB_PATH=./insights.db uv run insights serve
```

Other commands:

```bash
uv run insights sync        # one-off sync (inventory + billing), prints the sync_run JSON
uv run insights db init     # create the schema at DB_PATH
uv run pytest               # tests
uv run ruff check           # lint (line length 100)
```

Docker: `docker build -t insights-backend .` then `docker run -p 8000:8000 -e CAPELLA_MOCK=true insights-backend`
(the compose file at the repo root wires the volume `/data` and the frontend).

## Environment

| Variable | Default | Meaning |
|---|---|---|
| `CAPELLA_API_KEY` | – | Bearer secret (Organization Owner). Required unless mock. |
| `CAPELLA_BASE_URL` | `https://cloudapi.cloud.couchbase.com` | Operational + Analytics APIs share it |
| `CAPELLA_ORG_ID` | auto | Otherwise discovered via `GET /v4/organizations` |
| `CAPELLA_MOCK` | `false` | Serve deterministic fixtures instead of calling Capella |
| `SYNC_BACKFILL_DAYS` | `90` | How far back the first sync fetches |
| `SYNC_REFRESH_DAYS` | `7` | Trailing window re-fetched on every sync (billing lag) |
| `SYNC_ON_START` | `true` | Run a sync when the API starts |
| `SYNC_INTERVAL_MINUTES` | `360` | Background resync cadence; `0` disables |
| `RATE_LIMIT_PER_MINUTE` | `80` | Token bucket (burst = rate/5) under Capella's 100/min |
| `DB_PATH` | `/data/insights.db` | SQLite file (WAL mode) |
| `LOG_LEVEL` | `info` | JSON logs on stdout; the API key is never logged |

`/health` reports `configured:false` when neither a key nor mock mode is set; the API still
serves whatever was synced before, and `POST /api/sync` answers `409 not_configured`.

## Endpoints

All JSON, camelCase, CORS open (local tool). Errors: `{"error": {"code", "message"}}`.

| Method + path | Purpose |
|---|---|
| `GET /health` | status, mock, configured, lastSync |
| `GET /api/organization` | org, billing currency/mode, counts, lastSync |
| `GET /api/projects` | projects with cluster counts |
| `GET /api/clusters`, `/api/clusters/{id}` | cluster cards / detail (buckets, linked App Service) |
| `GET /api/clusters/{id}/topology` | `@couchbaselabs/topology-ui` document |
| `GET /api/clusters/{id}/consumption?from&to&granularity=day\|month` | daily/monthly series by category |
| `GET /api/appservices`, `/api/appservices/{id}`, `/{id}/consumption` | App Services |
| `GET /api/analyticsclusters`, `/{id}`, `/{id}/topology`, `/{id}/consumption` | Analytics (Columnar) clusters |
| `GET /api/billing/summary?from&to` | org total, attributed vs unattributed, by category / instance |
| `GET /api/billing/consumption?from&to&groupBy=day\|category\|instance&scope=org\|cluster\|appservice\|analytics` | flexible aggregation |
| `GET /api/billing/prepaid` | prepaid credit blocks + aggregate |
| `GET /api/billing/payg?from&to` | pay-as-you-go periods |
| `GET /api/reports`, `GET /api/reports/{key}?from&to&format=json\|csv` | report registry (`consumption-summary`, `cluster-daily?clusterId=`) |
| `POST /api/sync` (202/409), `GET /api/sync/status` | trigger / inspect syncs |

`from`/`to` default to the last 30 full days ending yesterday. Credits and currency are kept
as separate nullable numbers everywhere (`null` means "not billed in that unit", never zero).

## Layout

```
src/insights/
  config.py            pydantic-settings
  capella/             client.py (httpx, token bucket, 429/5xx retry, paging), models.py,
                       mock.py + synth.py + fixtures/ (deterministic demo data)
  store/               db.py (schema, WAL), repo*.py (typed queries)
  sync/                windows.py (month windows, sync range), inventory.py, billing.py, runner.py
  topology/mapper.py   inventory -> topology-ui documents
  reports/             registry.py (extension point), builtin.py
  api/                 app.py (lifespan, DI via app.state), routes/*
  cli.py               insights serve | sync | db init
```

### Adding a report

Register a `ReportDefinition(key, title, description, params, run)` on
`insights.reports.registry.registry`; `run(ctx: ReportContext) -> ReportResult` gets an open
SQLite connection, the date range and extra query params. The API serves it as JSON and CSV
without further changes.
