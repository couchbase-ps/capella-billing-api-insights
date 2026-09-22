# Backend ⇄ Frontend API contract (v0.1)

Base path `/api`. All responses are JSON, UTF-8, camelCase keys. Dates are `YYYY-MM-DD`;
timestamps are ISO-8601 UTC strings. Money/credit figures are numbers or `null` (null means
"not billed in that unit", never zero). Errors: `{"error": {"code": "<slug>", "message": "..."}}`
with an appropriate HTTP status.

## Health

`GET /health` →
```json
{"status":"ok","mock":false,"configured":true,
 "lastSync":{"id":3,"startedAt":"...","finishedAt":"...","status":"success","requestsMade":42,"error":null}}
```
`lastSync` is `null` before the first run. `status` ∈ `success | partial | failed | running`.

## Organization

`GET /api/organization` →
```json
{"id":"uuid","name":"Acme","billingCurrency":"USD","billingMode":"credits",
 "counts":{"projects":2,"clusters":5,"appServices":1,"analyticsClusters":1},
 "lastSync":{...same as health...}}
```
`billingMode` ∈ `credits | currency | unknown`, derived from which spend column is populated.

## Inventory

`GET /api/projects` → `[{"id","name","clusterCount":3}]`

`GET /api/clusters` →
```json
[{"id":"uuid","name":"prod-eu","projectId":"uuid","projectName":"Prod",
  "provider":"aws","region":"eu-west-1","version":"7.6.4","supportPlan":"enterprise",
  "availability":"multi","state":"healthy","freeTier":false,
  "nodes":6,"serviceGroups":[{"services":["data","query","index"],"numOfNodes":3,"cpu":4,"ram":16,"diskType":"gp3","diskGb":50,"iops":3000}],
  "appServiceId":"uuid|null",
  "credits7d":12.5,"credits30d":51.2,"currency7d":null,"currency30d":null}]
```

`GET /api/clusters/{id}` → the card above plus
```json
{"buckets":[{"name":"travel","storageBackend":"magma","memoryAllocationInMb":1024,"replicas":1,
             "evictionPolicy":"fullEviction","itemCount":1200000,"memoryUsedInMib":800,"diskUsedInMib":4000,"timeToLiveInSeconds":0}],
 "appService":{...app service card...}|null,
 "connectionString":"couchbases://...","createdAt":"..."}
```

`GET /api/clusters/{id}/topology` → the `@couchbaselabs/topology-ui` document (see
`docs/capella-management-api-analysis.md` §5). Node figures use `{value, unit, status}` when
absent.

`GET /api/appservices` →
```json
[{"id":"uuid","name":"prod-eu-app","clusterId":"uuid","clusterName":"prod-eu",
  "projectId":"uuid","projectName":"Prod","provider":"aws","nodes":2,"cpu":2,"ram":4,
  "version":"3.2","plan":"enterprise","state":"healthy",
  "endpoints":[{"name":"travel","bucket":"travel","state":"online"}],
  "credits7d":3.1,"credits30d":12.0,"currency7d":null,"currency30d":null}]
```

`GET /api/analyticsclusters` →
```json
[{"id":"uuid","name":"analytics-eu","projectId":"uuid","projectName":"Prod",
  "provider":"aws","region":"eu-west-1","nodes":4,"cpu":8,"ram":32,
  "supportPlan":"enterprise","availability":"multi","state":"healthy",
  "credits7d":20.0,"credits30d":80.0,"currency7d":null,"currency30d":null}]
```
`GET /api/analyticsclusters/{id}` → the card plus `{"createdAt":"...|null"}`.
`GET /api/analyticsclusters/{id}/topology` → topology-ui document: one server group `analytics`,
one node with `total = nodes`, `services: ["Analytics"]`, no `buckets`, no `mobile`.

## Consumption

`GET /api/clusters/{id}/consumption?from&to&granularity=day|month` and
`GET /api/appservices/{id}/consumption?...`, `GET /api/analyticsclusters/{id}/consumption?...` →
```json
{"scope":"cluster|appservice|analytics","instanceId":"uuid","from":"2026-08-01","to":"2026-08-31","granularity":"day",
 "currency":"USD",
 "series":[{"period":"2026-08-01","category":"operationalComputeAndStorage","credits":10.2,"currency":null}],
 "byCategory":[{"category":"operationalComputeAndStorage","credits":300.1,"currency":null,"contributionPercent":88.4}],
 "total":{"credits":339.5,"currency":null}}
```
`from`/`to` default to the last 30 full days (ending yesterday). `month` granularity sums the
days; `period` is then `YYYY-MM`.

`GET /api/billing/summary?from&to` →
```json
{"from":"...","to":"...","currency":"USD",
 "org":{"credits":900.0,"currency":null},
 "attributed":{"credits":850.0,"currency":null},
 "unattributed":{"credits":50.0,"currency":null},
 "byCategory":[{"category":"...","credits":...,"currency":...,"contributionPercent":...}],
 "byInstance":[{"scope":"cluster|appservice|analytics","instanceId":"uuid","name":"prod-eu","projectName":"Prod","credits":400.0,"currency":null,"sharePercent":44.4}]}
```

`GET /api/billing/consumption?from&to&groupBy=day|category|instance&scope=org|cluster|appservice|analytics`
→ `{"groupBy":"day","rows":[{"key":"2026-08-01","credits":..,"currency":..}]}` — for
`groupBy=day` on `scope=org` the rows are the org-level daily totals stacked by category:
`[{"period":"2026-08-01","category":"...","credits":..,"currency":..}]`.

`GET /api/billing/prepaid` →
```json
{"credits":[{"id":"..","creditName":"..","supportPlan":"enterprise","startDate":"...","expirationDate":"...",
             "total":10000,"used":4200.5,"remaining":5799.5,"remainingPercent":58.0}],
 "aggregate":{"total":10000,"used":4200.5,"remaining":5799.5,"remainingPercent":58.0},
 "fetchedAt":"..."}
```

`GET /api/billing/payg?from&to` →
`{"currency":"USD","periods":[{"period":"2026-08-01","basic":0,"devPro":10.1,"enterprise":20.2,"total":30.3}],"total":{...same keys...}}`

## Reports

`GET /api/reports` → `[{"key":"consumption-summary","title":"...","description":"...","params":[{"name":"from","type":"date","required":true}, ...]}]`

Built-in report params: `consumption-summary` (from, to) rows cover every scope including `analytics`; `cluster-daily` (from, to, `clusterId` = an operational **or** Analytics cluster id, the backend resolves the scope); the three monthly custom reports `credits-by-category`, `credits-by-plan`, `credits-by-cluster` (from, to) defined in `docs/custom-reports.md`.

`GET /api/reports/{key}?from&to&format=json|csv` → JSON:
`{"key","title","from","to","columns":[{"key":"cluster","label":"Cluster","type":"string|number|date|month|credits|currency"}],"rows":[{...}],"totals":{...}|null,"meta":{"unit":"credits|USD","categoryOrder":[...],"partialMonths":[...],"onDemandMethod":"proportional-by-plan"}}` — `totals` is the Total row keyed by column key (label columns hold `"Total"` in the first column and null elsewhere); `meta` keys are optional per report.
CSV: `text/csv` with `Content-Disposition: attachment; filename=<key>-<from>_to_<to>.csv`.

## Sync

`POST /api/sync` → `202 {"runId":4,"status":"running"}` or `409 {"error":{"code":"sync_running",...}}`
`GET /api/sync/status` → `{"running":false,"runs":[{"id","startedAt","finishedAt","status","requestsMade","error","detail":{"clustersSynced":5,"appServicesSynced":1,"analyticsClustersSynced":1,"billingWindows":6,"failures":[{"scope":"cluster","instanceId":"..","message":".."}]}}]}` (last 10 runs, newest first)
