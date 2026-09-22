# Custom billing reports (defined 2026-09-22)

All three reports group credits **by calendar month** over the selected date range and end
with a **Total** row that sums every numeric column. Values are Capella credits (or the
billing currency when the organization is billed in currency; the unit is reported in the
result). Absent cells are `null` (rendered as "—"), never zero.

## Category labels

The Capella Billing API reports usage in API category codes. The reports render them with the
labels used in Capella's own usage report. Order is fixed so the tables always line up:

| Column label | API category | Notes |
|---|---|---|
| Backup | `operationalBucketBackup` | bucket backups |
| Cluster Backup | `operationalClusterBackup` | cloud snapshot backups |
| Cluster | `operationalComputeAndStorage` | operational nodes compute + storage |
| Data Transfer | `dataTransferStandard` | |
| Private Endpoints | `privateEndpointsStandard` | |
| Data API | `dataApiStandard` | |
| Columnar Compute | `analyticsCompute` | Analytics clusters |
| Columnar Storage | `analyticsStorage` | Analytics clusters |
| Columnar Backup | `analyticsClusterBackup` | Analytics clusters |
| AppServices Fixed | `appServicesComputeAndStorage` | App Service nodes |
| AppServices Variable | *(no API category yet)* | column kept for parity with the Capella usage report; stays empty until the API exposes a variable App Services category |
| AI LLM / AI Gateway / AI UDS Pager / AI SDS Pager | `aiServicesLLM`, `aiServicesAiGateway`, `aiServicesUdsPager`, `aiServicesSdsPager` | AI Data Plane |

Any category the API returns that is not in this table is appended as its own column with a
humanised label, so new Capella categories never get silently dropped.

## Report 1 — `credits-by-category`: Credits split up by categories

| Month | Row Labels | Sum of consumed Credits |
|---|---|---|
| 2026-07 | Cluster | 1234.5 |
| 2026-07 | Backup | 12.1 |
| … | … | … |
| Total | | 9876.5 |

Source: the **org-level** categorized billing rows (scope `org`), so the figures reconcile with
Capella's billing overview. One row per month × category with non-null spend; categories in
the fixed order above.

## Report 2 — `credits-by-plan`: Credits by plan, categories transposed

| Month | Credit Plan | Backup | Cluster | Data Transfer | Private Endpoints | Columnar Compute | Columnar Storage | AppServices Fixed | AppServices Variable | … | Grand Total |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-07 | Developer Pro | | | | | | | | | | |
| 2026-07 | Enterprise | | | | | | | | | | |
| 2026-07 | Unattributed | | | | | | | | | | |
| Total | | | | | | | | | | | |

"Credit Plan" is the **support plan of the instance** that consumed the credits (operational
cluster `support.plan`, Analytics cluster `support.plan`, App Service `plan`): `Basic`,
`Developer Pro`, `Enterprise`. Instance-level rows (scopes `cluster`, `analytics`,
`appservice`) are summed per month × plan × category. The difference between the org total and
the sum of instances for a month appears as plan `Unattributed`, so the Grand Total column
always reconciles with report 1.

## Report 3 — `credits-by-cluster`: Credits by usage per cluster

| Month | Cluster Instance Name | Backup | Cluster | Data Transfer | Private Endpoints | Columnar Compute | Columnar Storage | AppServices Fixed | AppServices Variable | … | Total Plan Developer Pro | Total Plan Enterprise | Total On-demand Credits |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-07 | prod-eu | | | | | | | | | | | | |
| 2026-07 | analytics-eu | | | | | | | | | | | | |
| 2026-07 | Unattributed | | | | | | | | | | | | |
| Total | | | | | | | | | | | | | |

Rows: one per month × instance. **App Service credits are attributed to the operational
cluster they are attached to** (`appService.clusterId`) and land in the AppServices columns of
that cluster's row; an App Service whose cluster is unknown gets its own row. Analytics
clusters are their own rows. `Unattributed` holds the org remainder.

- `Total Plan Developer Pro` / `Total Plan Enterprise` (and `Total Plan Basic` when any Basic
  instance exists): the row's total credits when the instance's plan matches, otherwise null.
- `Total On-demand Credits`: the estimated part of the row's credits that was billed
  pay-as-you-go rather than drawn from prepaid credits. Capella only reports pay-as-you-go
  per month **per plan** (`payAsYouGoBilling.cost.{basic,devPro,enterprise}`), not per
  instance, so the report computes for each month and plan
  `onDemandRatio = min(1, paygSpend(plan) / totalSpend(plan))` and multiplies the row's credits
  by the ratio of its plan. The result carries `method: "proportional-by-plan"` in its
  metadata; when no pay-as-you-go data exists for the month the cell is null.

## API

`GET /api/reports/{key}?from=YYYY-MM-DD&to=YYYY-MM-DD&format=json|csv` for the three keys
above. `from`/`to` are clipped to whole months for grouping (a partial month is labelled with
its month and flagged `partialMonths` in the result metadata). JSON shape per
`docs/api-contract.md`; `totals` is the Total row. `meta` carries `unit` (`credits` or the
currency code), `categoryOrder`, `partialMonths`, and for report 3 `onDemandMethod`.
