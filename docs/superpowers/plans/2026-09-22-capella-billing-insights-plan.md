# Implementation plan — v0.1 scaffold (2026-09-22)

Executed as two parallel work streams against the spec and `docs/api-contract.md`, then an
integration pass.

## Stream A — backend (`backend/`)
1. Project skeleton: pyproject (pinned), Dockerfile, ruff, CLI (`serve`, `sync`, `db init`).
2. Settings (§3.1) and SQLite schema + repositories (§3.3).
3. Capella client: bearer auth, token bucket, 429/5xx retry, page walking; `CapellaSource` Protocol.
4. Mock client with deterministic fixtures (inventory + synthetic daily billing honouring the month-window rule).
5. Sync: `month_windows`/`sync_range` pure functions → inventory sync → billing sync → runner with lock, sync_run records, background scheduler.
6. Topology mapper (analysis §5).
7. Report registry + built-ins (`consumption-summary`, `cluster-daily`) with CSV.
8. FastAPI routes for every contract endpoint; tests for each layer.

## Stream B — frontend (`frontend/`)
1. Vite + React 19 + TS + Tailwind v4 + TanStack Query + router; Couchbase tokens from the sibling project.
2. Typed API client + hooks from the contract.
3. `TopologyView` around `@couchbaselabs/topology-ui` (asset copy script, scoped CSS).
4. Pages: Overview, Clusters, ClusterDetail, AppServices, AppServiceDetail, Reports.
5. Recharts consumption charts with a stable category palette; formatting helpers (null → "—").
6. Vitest coverage for helpers, TopologyView, tables, setup banner; lint/typecheck/build gates.

## Integration
1. `docker compose` with `CAPELLA_MOCK=true`; smoke every page in the browser.
2. Fix contract mismatches on either side; commit; push to `couchbase-ps/capella-billing-api-insights`.
