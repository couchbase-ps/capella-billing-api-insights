import type { JSX } from "react";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useCluster, useClusterConsumption, useClusterTopology } from "../api/hooks";
import type { Bucket, ClusterDetail as ClusterDetailData } from "../api/types";
import { ConsumptionSection } from "../components/ConsumptionSection";
import { Table, Td, Th } from "../components/Table";
import { TopologyView } from "../components/TopologyView";
import { Card, ErrorNote, Facts, LoadingRow, PageHeader, StateBadge, Tag } from "../components/ui";
import { formatDate } from "../lib/dates";
import { formatCredits, formatInteger, formatMib } from "../lib/format";
import type { RangeDays } from "../lib/ranges";
import { lastDays } from "../lib/ranges";

function BucketsTable({ buckets }: { buckets: Bucket[] }): JSX.Element {
  if (buckets.length === 0) {
    return <p className="py-4 text-caption text-text-muted">No buckets.</p>;
  }
  return (
    <Table>
      <thead>
        <tr>
          <Th>Bucket</Th>
          <Th>Backend</Th>
          <Th num>Quota</Th>
          <Th num>Replicas</Th>
          <Th>Eviction</Th>
          <Th num>Items</Th>
          <Th num>Memory used</Th>
          <Th num>Disk used</Th>
          <Th num>TTL (s)</Th>
        </tr>
      </thead>
      <tbody>
        {buckets.map((bucket) => (
          <tr key={bucket.name}>
            <Td>{bucket.name}</Td>
            <Td>{bucket.storageBackend}</Td>
            <Td num>{formatMib(bucket.memoryAllocationInMb)}</Td>
            <Td num>{formatInteger(bucket.replicas)}</Td>
            <Td>{bucket.evictionPolicy}</Td>
            <Td num>{formatInteger(bucket.itemCount)}</Td>
            <Td num>{formatMib(bucket.memoryUsedInMib)}</Td>
            <Td num>{formatMib(bucket.diskUsedInMib)}</Td>
            <Td num>{formatInteger(bucket.timeToLiveInSeconds)}</Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

function AppServiceCard({ cluster }: { cluster: ClusterDetailData }): JSX.Element {
  const app = cluster.appService;
  if (!app) {
    return <p className="text-caption text-text-muted">No App Service linked to this cluster.</p>;
  }
  return (
    <Facts
      items={[
        {
          label: "App Service",
          value: (
            <Link to={`/appservices/${app.id}`} className="text-link hover:underline">
              {app.name}
            </Link>
          ),
        },
        { label: "State", value: <StateBadge state={app.state} /> },
        { label: "Nodes", value: `${app.nodes} × ${app.cpu} vCPU / ${app.ram} GB` },
        { label: "Endpoints", value: formatInteger(app.endpoints.length) },
        { label: "Credits 30d", value: formatCredits(app.credits30d) },
      ]}
    />
  );
}

export function ClusterDetail(): JSX.Element {
  const { id = "" } = useParams();
  const [days, setDays] = useState<RangeDays>(30);
  const range = useMemo(() => lastDays(days), [days]);
  const cluster = useCluster(id);
  const topology = useClusterTopology(id);
  const consumption = useClusterConsumption(id, range, "day");

  if (cluster.isPending) {
    return <LoadingRow />;
  }
  if (cluster.isError) {
    return <ErrorNote error={cluster.error} />;
  }
  const data = cluster.data;
  return (
    <>
      <PageHeader
        title={
          <>
            {data.name}
            {data.freeTier && <Tag>free tier</Tag>}
          </>
        }
        subtitle={`${data.projectName} · ${data.provider} ${data.region}`}
        backTo={{ to: "/clusters", label: "Clusters" }}
        action={<StateBadge state={data.state} />}
      />
      <Card>
        <Facts
          items={[
            { label: "Version", value: data.version || "—" },
            { label: "Plan", value: data.supportPlan || "—" },
            { label: "Availability", value: data.availability || "—" },
            { label: "Nodes", value: formatInteger(data.nodes) },
            { label: "Credits 7d", value: formatCredits(data.credits7d) },
            { label: "Credits 30d", value: formatCredits(data.credits30d) },
            { label: "Created", value: formatDate(data.createdAt) },
            {
              label: "Connection",
              value: (
                <code className="break-all font-mono text-caption">
                  {data.connectionString ?? "—"}
                </code>
              ),
            },
          ]}
        />
      </Card>
      <Card title="Topology" className="mt-4">
        {topology.isPending && <LoadingRow />}
        {topology.isError && <ErrorNote error={topology.error} />}
        {topology.data && <TopologyView document={topology.data} />}
      </Card>
      <div className="mt-4">
        <ConsumptionSection
          query={consumption}
          range={range}
          days={days}
          onDaysChange={setDays}
          csvClusterId={id}
        />
      </div>
      <Card title="Buckets" className="mt-4">
        <BucketsTable buckets={data.buckets} />
      </Card>
      <Card title="Linked App Service" className="mt-4">
        <AppServiceCard cluster={data} />
      </Card>
    </>
  );
}
