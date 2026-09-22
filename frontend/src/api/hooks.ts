import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "./client";
import type {
  AppServiceCard,
  BillingSummary,
  ClusterCard,
  ClusterDetail,
  Consumption,
  Granularity,
  Health,
  OrgDailyConsumption,
  Organization,
  Prepaid,
  ReportDefinition,
  ReportResult,
  SyncStart,
  SyncStatus,
  TopologyDocument,
} from "./types";

export interface DateRange {
  from: string;
  to: string;
}

export const queryKeys = {
  health: ["health"] as const,
  organization: ["organization"] as const,
  clusters: ["clusters"] as const,
  cluster: (id: string) => ["clusters", id] as const,
  clusterTopology: (id: string) => ["clusters", id, "topology"] as const,
  clusterConsumption: (id: string, range: DateRange, granularity: Granularity) =>
    ["clusters", id, "consumption", range.from, range.to, granularity] as const,
  appServices: ["appservices"] as const,
  appServiceConsumption: (id: string, range: DateRange, granularity: Granularity) =>
    ["appservices", id, "consumption", range.from, range.to, granularity] as const,
  billingSummary: (range: DateRange) => ["billing", "summary", range.from, range.to] as const,
  billingDaily: (range: DateRange) => ["billing", "daily", range.from, range.to] as const,
  prepaid: ["billing", "prepaid"] as const,
  reports: ["reports"] as const,
  report: (key: string, params: Record<string, string>) => ["reports", key, params] as const,
  syncStatus: ["sync", "status"] as const,
};

export function useHealth() {
  return useQuery({ queryKey: queryKeys.health, queryFn: () => apiGet<Health>("/health") });
}

export function useOrganization() {
  return useQuery({
    queryKey: queryKeys.organization,
    queryFn: () => apiGet<Organization>("/api/organization"),
  });
}

export function useClusters() {
  return useQuery({
    queryKey: queryKeys.clusters,
    queryFn: () => apiGet<ClusterCard[]>("/api/clusters"),
  });
}

export function useCluster(id: string) {
  return useQuery({
    queryKey: queryKeys.cluster(id),
    queryFn: () => apiGet<ClusterDetail>(`/api/clusters/${encodeURIComponent(id)}`),
  });
}

export function useClusterTopology(id: string) {
  return useQuery({
    queryKey: queryKeys.clusterTopology(id),
    queryFn: () => apiGet<TopologyDocument>(`/api/clusters/${encodeURIComponent(id)}/topology`),
  });
}

export function useClusterConsumption(id: string, range: DateRange, granularity: Granularity) {
  return useQuery({
    queryKey: queryKeys.clusterConsumption(id, range, granularity),
    queryFn: () =>
      apiGet<Consumption>(`/api/clusters/${encodeURIComponent(id)}/consumption`, {
        ...range,
        granularity,
      }),
  });
}

export function useAppServices() {
  return useQuery({
    queryKey: queryKeys.appServices,
    queryFn: () => apiGet<AppServiceCard[]>("/api/appservices"),
  });
}

export function useAppServiceConsumption(id: string, range: DateRange, granularity: Granularity) {
  return useQuery({
    queryKey: queryKeys.appServiceConsumption(id, range, granularity),
    queryFn: () =>
      apiGet<Consumption>(`/api/appservices/${encodeURIComponent(id)}/consumption`, {
        ...range,
        granularity,
      }),
  });
}

export function useBillingSummary(range: DateRange) {
  return useQuery({
    queryKey: queryKeys.billingSummary(range),
    queryFn: () => apiGet<BillingSummary>("/api/billing/summary", range),
  });
}

export function useOrgDailyConsumption(range: DateRange) {
  return useQuery({
    queryKey: queryKeys.billingDaily(range),
    queryFn: () =>
      apiGet<OrgDailyConsumption>("/api/billing/consumption", {
        ...range,
        groupBy: "day",
        scope: "org",
      }),
  });
}

export function usePrepaid() {
  return useQuery({
    queryKey: queryKeys.prepaid,
    queryFn: () => apiGet<Prepaid>("/api/billing/prepaid"),
  });
}

export function useReports() {
  return useQuery({
    queryKey: queryKeys.reports,
    queryFn: () => apiGet<ReportDefinition[]>("/api/reports"),
  });
}

export function useReport(key: string | null, params: Record<string, string>) {
  return useQuery({
    queryKey: queryKeys.report(key ?? "", params),
    queryFn: () =>
      apiGet<ReportResult>(`/api/reports/${encodeURIComponent(key ?? "")}`, {
        ...params,
        format: "json",
      }),
    enabled: key !== null,
  });
}

/** Polls every 2s while a sync is running so the status card and "Sync now" button update. */
export function useSyncStatus() {
  return useQuery({
    queryKey: queryKeys.syncStatus,
    queryFn: () => apiGet<SyncStatus>("/api/sync/status"),
    refetchInterval: (query) => (query.state.data?.running ? 2000 : false),
  });
}

export function useStartSync() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiPost<SyncStart>("/api/sync"),
    onSettled: () => queryClient.invalidateQueries({ queryKey: queryKeys.syncStatus }),
  });
}

/** Call once a running sync has finished so every page re-reads the fresh data. */
export function useInvalidateAll() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries();
}
