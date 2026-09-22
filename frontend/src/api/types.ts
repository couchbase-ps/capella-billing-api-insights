// Hand-written mirror of docs/api-contract.md (v0.1). Keys are camelCase exactly as the
// backend returns them. Money/credit figures are numbers or null (null = not billed in that
// unit, never zero).

export type SyncStatusValue = "success" | "partial" | "failed" | "running";

export interface SyncRunSummary {
  id: number;
  startedAt: string;
  finishedAt: string | null;
  status: SyncStatusValue;
  requestsMade: number;
  error: string | null;
}

export interface Health {
  status: string;
  mock: boolean;
  configured: boolean;
  lastSync: SyncRunSummary | null;
}

export type BillingMode = "credits" | "currency" | "unknown";

export interface Organization {
  id: string;
  name: string;
  billingCurrency: string;
  billingMode: BillingMode;
  counts: { projects: number; clusters: number; appServices: number; analyticsClusters: number };
  lastSync: SyncRunSummary | null;
}

export interface Project {
  id: string;
  name: string;
  clusterCount: number;
}

export interface ServiceGroup {
  services: string[];
  numOfNodes: number;
  cpu: number;
  ram: number;
  diskType: string;
  diskGb: number;
  iops: number | null;
}

export interface ClusterCard {
  id: string;
  name: string;
  projectId: string;
  projectName: string;
  provider: string;
  region: string;
  version: string;
  supportPlan: string;
  availability: string;
  state: string;
  freeTier: boolean;
  nodes: number;
  serviceGroups: ServiceGroup[];
  appServiceId: string | null;
  credits7d: number | null;
  credits30d: number | null;
  currency7d: number | null;
  currency30d: number | null;
}

export interface Bucket {
  name: string;
  storageBackend: string;
  memoryAllocationInMb: number;
  replicas: number;
  evictionPolicy: string;
  itemCount: number | null;
  memoryUsedInMib: number | null;
  diskUsedInMib: number | null;
  timeToLiveInSeconds: number;
}

export interface AppEndpoint {
  name: string;
  bucket: string;
  state: string;
}

export interface AppServiceCard {
  id: string;
  name: string;
  clusterId: string;
  clusterName: string;
  projectId: string;
  projectName: string;
  provider: string;
  nodes: number;
  cpu: number;
  ram: number;
  version: string;
  plan: string;
  state: string;
  endpoints: AppEndpoint[];
  credits7d: number | null;
  credits30d: number | null;
  currency7d: number | null;
  currency30d: number | null;
}

export interface ClusterDetail extends ClusterCard {
  buckets: Bucket[];
  appService: AppServiceCard | null;
  connectionString: string | null;
  createdAt: string | null;
}

export interface AnalyticsClusterCard {
  id: string;
  name: string;
  projectId: string;
  projectName: string;
  provider: string;
  region: string;
  nodes: number;
  cpu: number;
  ram: number;
  supportPlan: string;
  availability: string;
  state: string;
  credits7d: number | null;
  credits30d: number | null;
  currency7d: number | null;
  currency30d: number | null;
}

export interface AnalyticsClusterDetail extends AnalyticsClusterCard {
  createdAt: string | null;
}

export interface Money {
  credits: number | null;
  currency: number | null;
}

export type Scope = "org" | "cluster" | "appservice" | "analytics";
export type Granularity = "day" | "month";

export interface ConsumptionPoint extends Money {
  period: string;
  category: string;
}

export interface CategoryTotal extends Money {
  category: string;
  contributionPercent: number | null;
}

export interface Consumption {
  scope: Scope;
  instanceId: string;
  from: string;
  to: string;
  granularity: Granularity;
  currency: string;
  series: ConsumptionPoint[];
  byCategory: CategoryTotal[];
  total: Money;
}

export interface InstanceShare extends Money {
  scope: Scope;
  instanceId: string;
  name: string;
  projectName: string | null;
  sharePercent: number | null;
}

export interface BillingSummary {
  from: string;
  to: string;
  currency: string;
  org: Money;
  attributed: Money;
  unattributed: Money;
  byCategory: CategoryTotal[];
  byInstance: InstanceShare[];
}

/** `GET /api/billing/consumption?groupBy=day&scope=org` — org daily totals stacked by category. */
export interface OrgDailyConsumption {
  groupBy: "day";
  rows: ConsumptionPoint[];
}

export interface PrepaidCredit {
  id: string;
  creditName: string;
  supportPlan: string;
  startDate: string;
  expirationDate: string;
  total: number;
  used: number;
  remaining: number;
  remainingPercent: number;
}

export interface PrepaidAggregate {
  total: number;
  used: number;
  remaining: number;
  remainingPercent: number;
}

export interface Prepaid {
  credits: PrepaidCredit[];
  aggregate: PrepaidAggregate;
  fetchedAt: string | null;
}

export interface PaygPeriod {
  period: string;
  basic: number;
  devPro: number;
  enterprise: number;
  total: number;
}

export interface Payg {
  currency: string;
  periods: PaygPeriod[];
  total: Omit<PaygPeriod, "period">;
}

export type ReportParamType = "date" | "string" | "number";

export interface ReportParam {
  name: string;
  type: ReportParamType;
  required: boolean;
}

export interface ReportDefinition {
  key: string;
  title: string;
  description: string;
  params: ReportParam[];
}

export type ReportColumnType = "string" | "number" | "date" | "month" | "credits" | "currency";

export interface ReportColumn {
  key: string;
  label: string;
  type: ReportColumnType;
}

export type ReportRow = Record<string, string | number | null>;

export interface ReportResult {
  key: string;
  title: string;
  from: string;
  to: string;
  columns: ReportColumn[];
  rows: ReportRow[];
  totals: ReportRow | null;
  meta?: ReportMeta;
}

export interface ReportMeta {
  unit?: string;
  categoryOrder?: string[];
  partialMonths?: string[];
  onDemandMethod?: string;
}

export interface SyncStart {
  runId: number;
  status: "running";
}

export interface SyncFailure {
  scope: Scope;
  instanceId: string;
  message: string;
}

export interface SyncRun extends SyncRunSummary {
  detail: {
    clustersSynced: number;
    appServicesSynced: number;
    analyticsClustersSynced: number;
    billingWindows: number;
    failures: SyncFailure[];
  } | null;
}

export interface SyncStatus {
  running: boolean;
  runs: SyncRun[];
}

export interface ApiErrorEnvelope {
  error: { code: string; message: string };
}

// --- topology-ui document (docs/capella-management-api-analysis.md §5) ------------------

export type FigureStatus = "ok" | "zero" | "absent" | "partial" | "failed";

export interface FigureObject {
  value: number | string | null;
  unit?: string;
  status?: FigureStatus;
  reason?: string;
}

export type Figure = number | string | FigureObject | null;

export interface TopologyResources {
  memory?: Figure;
  cpus?: Figure;
}

export interface TopologyNode {
  name: string;
  total?: number;
  resources?: TopologyResources;
  services?: string[];
  status?: string;
}

export interface TopologyServerGroup {
  name: string;
  nodes: TopologyNode[];
  status?: string;
}

export interface TopologyBucket {
  name: string;
  type?: string;
  quota?: Figure;
  documents?: Figure;
  replicas?: Figure;
  ratio?: Figure;
  eviction?: Figure;
  ttl?: Figure;
  connectors?: string[];
}

export interface TopologyMobileInstance {
  name: string;
  total?: number;
  nodeIp?: string;
  resources?: TopologyResources;
}

export interface TopologyMobile {
  version?: string;
  resources?: TopologyResources;
  groups?: { name: string; instances: TopologyMobileInstance[] }[];
  databases?: { name: string }[];
  publicAddress?: string;
}

export interface TopologyDocument {
  name: string;
  version?: string;
  status?: string;
  nodesPerLine?: number;
  resources?: TopologyResources;
  serverGroups?: TopologyServerGroup[];
  buckets?: TopologyBucket[];
  mobile?: TopologyMobile;
}
