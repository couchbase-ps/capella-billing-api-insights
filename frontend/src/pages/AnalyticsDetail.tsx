import type { JSX } from "react";
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useAnalyticsCluster, useAnalyticsConsumption, useAnalyticsTopology } from "../api/hooks";
import { ConsumptionSection } from "../components/ConsumptionSection";
import { TopologyView } from "../components/TopologyView";
import { Card, ErrorNote, Facts, LoadingRow, PageHeader, StateBadge } from "../components/ui";
import { formatDate } from "../lib/dates";
import { formatCredits, formatInteger } from "../lib/format";
import type { RangeDays } from "../lib/ranges";
import { lastDays } from "../lib/ranges";

export function AnalyticsDetail(): JSX.Element {
  const { id = "" } = useParams();
  const [days, setDays] = useState<RangeDays>(30);
  const range = useMemo(() => lastDays(days), [days]);
  const cluster = useAnalyticsCluster(id);
  const topology = useAnalyticsTopology(id);
  const consumption = useAnalyticsConsumption(id, range, "day");

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
        title={data.name}
        subtitle={`${data.projectName} · ${data.provider} ${data.region}`}
        backTo={{ to: "/analytics", label: "Analytics clusters" }}
        action={<StateBadge state={data.state} />}
      />
      <Card>
        <Facts
          items={[
            { label: "Plan", value: data.supportPlan || "—" },
            { label: "Availability", value: data.availability || "—" },
            {
              label: "Nodes",
              value: `${formatInteger(data.nodes)} × ${data.cpu} vCPU / ${data.ram} GB`,
            },
            { label: "Created", value: formatDate(data.createdAt) },
            { label: "Credits 7d", value: formatCredits(data.credits7d) },
            { label: "Credits 30d", value: formatCredits(data.credits30d) },
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
    </>
  );
}
