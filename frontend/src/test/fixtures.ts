// Sample payloads shaped exactly like docs/api-contract.md.
import type {
  AnalyticsClusterCard,
  AppServiceCard,
  BillingSummary,
  ClusterCard,
  ClusterDetail,
  Consumption,
  Health,
  Organization,
  OrgDailyConsumption,
  Prepaid,
  ReportDefinition,
  ReportResult,
  SyncRunSummary,
  SyncStatus,
  TopologyDocument,
} from "../api/types";

export const lastSync: SyncRunSummary = {
  id: 3,
  startedAt: "2026-09-22T06:00:00Z",
  finishedAt: "2026-09-22T06:04:12Z",
  status: "success",
  requestsMade: 42,
  error: null,
};

export const health: Health = { status: "ok", mock: false, configured: true, lastSync };
export const healthUnconfigured: Health = {
  status: "ok",
  mock: false,
  configured: false,
  lastSync: null,
};

export const organization: Organization = {
  id: "org-1",
  name: "Acme Corp",
  billingCurrency: "USD",
  billingMode: "credits",
  counts: { projects: 2, clusters: 2, appServices: 1, analyticsClusters: 1 },
  lastSync,
};

export const appService: AppServiceCard = {
  id: "app-1",
  name: "prod-eu-app",
  clusterId: "cluster-1",
  clusterName: "prod-eu",
  projectId: "proj-1",
  projectName: "Prod",
  provider: "aws",
  nodes: 2,
  cpu: 2,
  ram: 4,
  version: "3.2",
  plan: "enterprise",
  state: "healthy",
  endpoints: [{ name: "travel", bucket: "travel", state: "online" }],
  credits7d: 3.1,
  credits30d: 12.0,
  currency7d: null,
  currency30d: null,
};

export const clusters: ClusterCard[] = [
  {
    id: "cluster-1",
    name: "prod-eu",
    projectId: "proj-1",
    projectName: "Prod",
    provider: "aws",
    region: "eu-west-1",
    version: "7.6.4",
    supportPlan: "enterprise",
    availability: "multi",
    state: "healthy",
    freeTier: false,
    nodes: 6,
    serviceGroups: [
      {
        services: ["data", "query", "index"],
        numOfNodes: 3,
        cpu: 4,
        ram: 16,
        diskType: "gp3",
        diskGb: 50,
        iops: 3000,
      },
      {
        services: ["search"],
        numOfNodes: 3,
        cpu: 4,
        ram: 16,
        diskType: "gp3",
        diskGb: 50,
        iops: 3000,
      },
    ],
    appServiceId: "app-1",
    credits7d: 12.5,
    credits30d: 51.2,
    currency7d: null,
    currency30d: null,
  },
  {
    id: "cluster-2",
    name: "dev-free",
    projectId: "proj-2",
    projectName: "Dev",
    provider: "gcp",
    region: "us-east1",
    version: "7.6.4",
    supportPlan: "basic",
    availability: "single",
    state: "turnedOff",
    freeTier: true,
    nodes: 1,
    serviceGroups: [
      {
        services: ["data", "query", "index", "search"],
        numOfNodes: 1,
        cpu: 2,
        ram: 8,
        diskType: "pd-ssd",
        diskGb: 50,
        iops: null,
      },
    ],
    appServiceId: null,
    credits7d: null,
    credits30d: 0.75,
    currency7d: null,
    currency30d: null,
  },
];

export const clusterDetail: ClusterDetail = {
  ...(clusters[0] as ClusterCard),
  buckets: [
    {
      name: "travel",
      storageBackend: "magma",
      memoryAllocationInMb: 1024,
      replicas: 1,
      evictionPolicy: "fullEviction",
      itemCount: 1200000,
      memoryUsedInMib: 800,
      diskUsedInMib: 4000,
      timeToLiveInSeconds: 0,
    },
  ],
  appService,
  connectionString: "couchbases://cb.example.cloud.couchbase.com",
  createdAt: "2026-01-15T10:00:00Z",
};

export const analyticsClusters: AnalyticsClusterCard[] = [
  {
    id: "analytics-1",
    name: "analytics-eu",
    projectId: "proj-1",
    projectName: "Prod",
    provider: "aws",
    region: "eu-west-1",
    nodes: 4,
    cpu: 8,
    ram: 32,
    supportPlan: "enterprise",
    availability: "multi",
    state: "healthy",
    credits7d: 20.0,
    credits30d: 80.0,
    currency7d: null,
    currency30d: null,
  },
];

export const topology: TopologyDocument = {
  name: "prod-eu",
  version: "7.6.4",
  status: "HEALTHY",
  serverGroups: [
    {
      name: "data/query/index",
      status: "HEALTHY",
      nodes: [
        {
          name: "data/query/index (gp3 50 GB)",
          total: 3,
          resources: { cpus: 4, memory: 16 },
          services: ["Data", "Query", "Index"],
          status: "HEALTHY",
        },
      ],
    },
    {
      name: "search",
      status: "HEALTHY",
      nodes: [
        {
          name: "search (gp3 50 GB)",
          total: 3,
          resources: { cpus: 4, memory: 16 },
          services: ["Search"],
          status: "HEALTHY",
        },
      ],
    },
  ],
  buckets: [
    {
      name: "travel",
      type: "couchbase",
      quota: 1024,
      documents: 1200000,
      replicas: 1,
      ratio: 78,
      eviction: "fullEviction",
    },
    {
      name: "empty",
      type: "ephemeral",
      quota: 256,
      documents: { value: null, status: "absent" },
      replicas: 0,
      ratio: { value: null, status: "absent" },
    },
  ],
  mobile: {
    version: "3.2",
    resources: { cpus: 2, memory: 4 },
    groups: [{ name: "prod-eu-app", instances: [{ name: "prod-eu-app", nodeIp: "", total: 2 }] }],
    databases: [{ name: "travel" }],
  },
};

export const consumption: Consumption = {
  scope: "cluster",
  instanceId: "cluster-1",
  from: "2026-08-23",
  to: "2026-09-21",
  granularity: "day",
  currency: "USD",
  series: [
    {
      period: "2026-09-19",
      category: "operationalComputeAndStorage",
      credits: 10.2,
      currency: null,
    },
    { period: "2026-09-19", category: "dataTransferStandard", credits: 0.4, currency: null },
    {
      period: "2026-09-20",
      category: "operationalComputeAndStorage",
      credits: 10.1,
      currency: null,
    },
    {
      period: "2026-09-21",
      category: "operationalComputeAndStorage",
      credits: 10.3,
      currency: null,
    },
    { period: "2026-09-21", category: "operationalBucketBackup", credits: 1.1, currency: null },
  ],
  byCategory: [
    {
      category: "operationalComputeAndStorage",
      credits: 30.6,
      currency: null,
      contributionPercent: 95.3,
    },
    { category: "operationalBucketBackup", credits: 1.1, currency: null, contributionPercent: 3.4 },
    { category: "dataTransferStandard", credits: 0.4, currency: null, contributionPercent: 1.3 },
  ],
  total: { credits: 32.1, currency: null },
};

export const orgDaily: OrgDailyConsumption = {
  groupBy: "day",
  rows: consumption.series.map((row) => ({ ...row })),
};

export const billingSummary: BillingSummary = {
  from: "2026-08-23",
  to: "2026-09-21",
  currency: "USD",
  org: { credits: 900.0, currency: null },
  attributed: { credits: 850.0, currency: null },
  unattributed: { credits: 50.0, currency: null },
  byCategory: consumption.byCategory,
  byInstance: [
    {
      scope: "cluster",
      instanceId: "cluster-1",
      name: "prod-eu",
      projectName: "Prod",
      credits: 400.0,
      currency: null,
      sharePercent: 44.4,
    },
    {
      scope: "analytics",
      instanceId: "analytics-1",
      name: "analytics-eu",
      projectName: "Prod",
      credits: 300.0,
      currency: null,
      sharePercent: 33.3,
    },
    {
      scope: "appservice",
      instanceId: "app-1",
      name: "prod-eu-app",
      projectName: "Prod",
      credits: 150.0,
      currency: null,
      sharePercent: 16.7,
    },
  ],
};

export const prepaid: Prepaid = {
  credits: [
    {
      id: "credit-1",
      creditName: "Enterprise commit 2026",
      supportPlan: "enterprise",
      startDate: "2026-01-01",
      expirationDate: "2026-12-31",
      total: 10000,
      used: 4200.5,
      remaining: 5799.5,
      remainingPercent: 58.0,
    },
  ],
  aggregate: { total: 10000, used: 4200.5, remaining: 5799.5, remainingPercent: 58.0 },
  fetchedAt: "2026-09-22T06:04:00Z",
};

export const reports: ReportDefinition[] = [
  {
    key: "consumption-summary",
    title: "Consumption summary",
    description: "Credits per instance per category over the range.",
    params: [
      { name: "from", type: "date", required: true },
      { name: "to", type: "date", required: true },
    ],
  },
  {
    key: "cluster-daily",
    title: "Cluster daily credits",
    description: "One row per day for one cluster.",
    params: [
      { name: "from", type: "date", required: true },
      { name: "to", type: "date", required: true },
      { name: "clusterId", type: "string", required: true },
    ],
  },
];

export const reportResult: ReportResult = {
  key: "consumption-summary",
  title: "Consumption summary",
  from: "2026-08-23",
  to: "2026-09-21",
  columns: [
    { key: "instance", label: "Instance", type: "string" },
    { key: "category", label: "Category", type: "string" },
    { key: "credits", label: "Credits", type: "credits" },
  ],
  rows: [{ instance: "prod-eu", category: "operationalComputeAndStorage", credits: 30.6 }],
  totals: { instance: "Total", category: null, credits: 30.6 },
};

export const syncStatus: SyncStatus = {
  running: false,
  runs: [
    {
      ...lastSync,
      detail: {
        clustersSynced: 2,
        appServicesSynced: 1,
        analyticsClustersSynced: 1,
        billingWindows: 6,
        failures: [],
      },
    },
  ],
};

/** Default route table for the hand-written fetch stub used by page tests. */
export function defaultRoutes(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    "/health": health,
    "/api/organization": organization,
    "/api/clusters": clusters,
    "/api/clusters/cluster-1": clusterDetail,
    "/api/clusters/cluster-1/topology": topology,
    "/api/clusters/cluster-1/consumption": consumption,
    "/api/appservices": [appService],
    "/api/analyticsclusters": analyticsClusters,
    "/api/billing/summary": billingSummary,
    "/api/billing/consumption": orgDaily,
    "/api/billing/prepaid": prepaid,
    "/api/reports": reports,
    "/api/reports/consumption-summary": reportResult,
    "/api/sync/status": syncStatus,
    ...overrides,
  };
}
