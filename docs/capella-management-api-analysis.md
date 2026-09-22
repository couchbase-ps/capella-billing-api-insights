# Capella Management API v4.0 — analysis for credit-consumption insights

Source of truth: the OpenAPI document that the reference page renders,
`https://docs.couchbase.com/cloud/management-api-reference/_attachments/openapi.external.generated.yaml`
(OpenAPI 3.0.2, title "Couchbase Capella Management API", version v4.0, 179 paths, 38 tags),
downloaded 2026-09-22. A copy is committed at `backend/vendor/capella-openapi.yaml` so the
backend models can be checked against it.

## 1. Access model

| Fact | Value |
|---|---|
| Base URL | `https://cloudapi.cloud.couchbase.com` |
| Auth | `Authorization: Bearer <api key secret>` (single `token` http/bearer security scheme) |
| Rate limit | 100 requests per minute per API key; `429` with `RateLimitExceeded` body when exceeded |
| Pagination | `page`, `perPage`, `sortBy`, `sortDirection` query params; responses carry `cursor.pages{page,next,previous,last,perPage,totalItems}` and `cursor.hrefs{first,last,previous,next}` |
| Error body | `{code, hint, httpStatusCode, message}` |
| Key scope | An API key belongs to exactly one **organization**. Billing endpoints require the `organizationOwner` organization role. |
| Key expiry | 180 days by default, optional IP allow-list |

**What "billing API key tied to one billing account" means in API terms.** Capella bills at
the organization level: the organization *is* the billing account. There is no separate
billing-account identifier in the API. A key that can read billing is therefore an
organization-scoped key with the Organization Owner role, and `GET /v4/organizations` returns
exactly the one organization the key belongs to. The backend uses that call to discover the
`organizationId` instead of asking for it in configuration.

## 2. Billing endpoints (tag `Billing`, added May 2026)

The rendered docs page labels these "Categorized", "Itemized", "Prepaid Credits" and
"Pay As You Go". The real paths in the spec are:

| operationId | Method + path | Purpose |
|---|---|---|
| `categorizedBilling` | `POST /v4/organizations/{organizationId}/billing` | Spend per **category** per **period**, org-wide or filtered |
| `itemizedBillingPerCluster` | `POST /v4/organizations/{organizationId}/projects/{projectId}/clusters/{clusterId}/billing` | Same shape for one **operational** cluster, adds `clusterName` and `supportPlan` |
| `prepaidCreditsBilling` | `GET /v4/organizations/{organizationId}/billing/prePaidCredits` | Paged list of prepaid credit blocks: `total`, `used`, `remaining`, `remainingPercent`, `startDate`, `expirationDate`, `supportPlan` |
| `payAsYouGoBilling` | `GET /v4/organizations/{organizationId}/billing/payAsYouGo?startDate&endDate` | PAYG cost per period split by support plan (`basic`, `devPro`, `enterprise`) |
| `downloadCategorizedBilling` | `POST /v4/organizations/{organizationId}/billing/download` | CSV of the categorized report |
| `downloadItemizedBilling` | `POST /v4/organizations/{organizationId}/projects/{projectId}/clusters/{clusterId}/billing/download` | CSV of the itemized report |

### 2.1 Categorized billing request

```json
{
  "startDate": "2026-08-01",
  "endDate":   "2026-08-31",
  "filters": {
    "categories":  ["operationalComputeAndStorage", "..."],
    "projectIds":  ["<uuid>"],
    "instanceIds": ["<cluster id | app service id | AI workflow/model id>"]
  }
}
```

Categories (enum in the spec):

| Category | Billed resource |
|---|---|
| `operationalComputeAndStorage` | Operational cluster nodes (compute + disk) |
| `operationalBucketBackup` | Bucket backups on operational clusters |
| `operationalClusterBackup` | Cloud snapshot (cluster) backups |
| `analyticsCompute` / `analyticsStorage` / `analyticsClusterBackup` | Capella Analytics (Columnar) |
| `appServicesComputeAndStorage` | App Services nodes |
| `dataTransferStandard` | Egress / data transfer |
| `privateEndpointsStandard` | Private endpoint service |
| `dataApiStandard` | Data API usage |
| `aiServicesLLM`, `aiServicesAiGateway`, `aiServicesUdsPager`, `aiServicesSdsPager` | AI Data Plane |

The itemized-per-cluster endpoint only accepts the six operational categories
(`operationalComputeAndStorage`, `operationalBucketBackup`, `operationalClusterBackup`,
`dataApiStandard`, `dataTransferStandard`, `privateEndpointsStandard`).

### 2.2 Categorized / itemized response

```json
{
  "data": {
    "billingCurrency": "USD",
    "periods": [
      {
        "startDate": "2026-08-01", "endDate": "2026-08-01",
        "categories": [
          {"category": "operationalComputeAndStorage", "creditSpend": 12.34,
           "currencySpend": null, "contributionPercent": 91.2}
        ],
        "totalCreditSpend": 13.5, "totalCurrencySpend": null
      }
    ],
    "total": { "startDate": "...", "endDate": "...", "categories": [...],
               "totalCreditSpend": 400.1, "totalCurrencySpend": null }
  }
}
```

Two rules that drive the sync design:

1. **Period granularity depends on the requested range.** "For date ranges within a month,
   each period represents a single day. For date ranges more than a month, each period
   represents a month." To obtain a **daily** series you must request one calendar month
   (or less) per call.
2. **Credits vs currency are mutually exclusive.** `creditSpend` is null when the
   organization is billed in currency and vice versa. Every stored figure keeps both
   columns and the `billingCurrency`.

Documented data lag: the UI docs say usage "can take up to 5 days to appear", and hourly
charges for a day are reflected the next calendar day. The backend therefore always
re-fetches a trailing window (default 7 days) on every sync.

## 3. Best way to extract per-cluster credit consumption

Three candidate strategies were compared:

| Strategy | Requests for C clusters, A app services, M months | Covers app services? | Daily granularity? |
|---|---|---|---|
| A. `itemizedBillingPerCluster` per cluster per month | C × M | No (clusters only) | Yes |
| B. `categorizedBilling` with `filters.instanceIds=[id]` per instance per month | (C + A) × M | Yes | Yes |
| C. One org-wide `categorizedBilling` per month, then attribute | M | Not attributable | Yes, but not per instance |

**Chosen: B, with C as the org-level roll-up and A kept for cross-checking.**
`categorizedBilling` filtered by a single `instanceIds` entry is the only call that returns a
per-instance, per-day, per-category series for both clusters and App Services (and later AI
instances) with one code path. The org-wide call (C) is cheap and gives the authoritative
total, so the backend stores both and can show "unattributed" spend
(org total − Σ instances). The itemized call (A) additionally reports `supportPlan` and is
used for the per-cluster CSV export.

Request budget at 100 req/min: a fleet of 20 clusters + 5 App Services over 6 months is
150 billing calls plus ~30 inventory calls, so a full backfill takes about two minutes with
the built-in token-bucket limiter (default 80 req/min to leave headroom for other users of
the same key). Incremental syncs only touch the current and previous month.

## 4. Inventory endpoints used for the topology view

| operationId | Path | Used for |
|---|---|---|
| `listOrganizations` | `GET /v4/organizations` | Discover the org id + name for the key |
| `listProjects` | `GET /v4/organizations/{org}/projects` | Project names |
| `listClusters` | `GET /v4/organizations/{org}/projects/{project}/clusters` | Cluster inventory: `serviceGroups[].node.compute{cpu,ram}`, `node.disk{type,storage,iops}`, `numOfNodes`, `services[]`, `cloudProvider{type,region}`, `couchbaseServer.version`, `support.plan`, `availability.type`, `currentState`, `appServiceId` |
| `listBuckets` | `GET .../clusters/{cluster}/buckets` | Bucket rows: `memoryAllocationInMb`, `replicas`, `evictionPolicy`, `storageBackend`, `stats{itemCount,memoryUsedInMib,diskUsedInMib}` |
| `listAppServices` | `GET /v4/organizations/{org}/appservices` | App Service inventory: `nodes`, `compute{cpu,ram}`, `version`, `plan`, `clusterId`, `currentState` |
| `listAppEndpoints` | `GET .../appservices/{id}/appEndpoints` | App Endpoint names + bucket (rendered as mobile "databases") |
| `getOnOffSchedule` | `GET .../clusters/{cluster}/onOffSchedule` | Optional; explains low compute spend on scheduled clusters |
| `getClusterStats` | `GET .../clusters/{cluster}/stats` | `freeMemoryInMb`, `totalMemoryInMb`, `maxReplicas` |

Free-tier clusters live under `/clusters/freeTier/{id}` and are not billed; they are listed
but skipped by the billing sync.

## 5. Mapping Capella inventory to `@couchbaselabs/topology-ui`

`topology-ui` (v1.3.0 on npm) renders a `{name, version, resources, serverGroups[], buckets[],
mobile{}}` document. Mapping:

| topology-ui field | Capella source |
|---|---|
| `name`, `version`, `status` | `cluster.name`, `couchbaseServer.version`, `currentState` (HEALTHY when `healthy`, else the raw state upper-cased) |
| `serverGroups[i].name` | `"<services joined>"` e.g. `data/query/index` (Capella service groups have no name) |
| `serverGroups[i].nodes[0]` | One node per service group with `total = numOfNodes` (stacked-card rendering), `resources = {cpus: compute.cpu, memory: compute.ram}`, `services` capitalised (`data` → `Data`), `disk` shown in the node name suffix |
| `buckets[]` | `listBuckets`: `quota = memoryAllocationInMb`, `documents = stats.itemCount`, `replicas`, `type` from `storageBackend` (`magma`/`couchstore` → `couchbase`, `ephemeral`), `eviction = evictionPolicy`, `ratio` = memoryUsed / quota |
| `mobile.version`, `mobile.resources` | App Service `version`, `compute` |
| `mobile.groups[0].instances[0]` | One instance with `total = nodes`, `name = appService.name` |
| `mobile.databases[]` | App Endpoint names |

Missing figures are passed as `{value: null, status: "absent"}` so the renderer prints an
em-dash instead of inventing a value.

## 6. Other endpoint groups (not used now, worth knowing)

Events (`listEvents`, filterable by cluster) can explain spend changes (scale, turn on/off).
Audit logs, backups, alert integrations, CMEK, private endpoints, network peers, database
credentials, query indexes, replications, sample buckets, users, API keys, AI Data Plane
(models, workflows, providers) are all read/write management surfaces outside the reporting
scope. `Api Keys` `createOrganizationAPIKey` can mint further keys but this tool never does.
