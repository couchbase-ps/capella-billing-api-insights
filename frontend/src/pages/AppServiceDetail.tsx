import type { JSX } from "react";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useAppServiceConsumption, useAppServices } from "../api/hooks";
import { ConsumptionSection } from "../components/ConsumptionSection";
import { Table, Td, Th } from "../components/Table";
import { Card, ErrorNote, Facts, LoadingRow, PageHeader, StateBadge } from "../components/ui";
import { formatCredits, formatInteger } from "../lib/format";
import type { RangeDays } from "../lib/ranges";
import { lastDays } from "../lib/ranges";

export function AppServiceDetail(): JSX.Element {
  const { id = "" } = useParams();
  const [days, setDays] = useState<RangeDays>(30);
  const range = useMemo(() => lastDays(days), [days]);
  // The contract has no /api/appservices/{id}; the card comes from the list.
  const list = useAppServices();
  const consumption = useAppServiceConsumption(id, range, "day");

  if (list.isPending) {
    return <LoadingRow />;
  }
  if (list.isError) {
    return <ErrorNote error={list.error} />;
  }
  const app = list.data.find((item) => item.id === id);
  if (!app) {
    return <ErrorNote error={new Error(`App Service ${id} not found`)} />;
  }
  return (
    <>
      <PageHeader
        title={app.name}
        subtitle={`${app.projectName} · ${app.provider}`}
        backTo={{ to: "/appservices", label: "App Services" }}
        action={<StateBadge state={app.state} />}
      />
      <Card>
        <Facts
          items={[
            {
              label: "Cluster",
              value: (
                <Link to={`/clusters/${app.clusterId}`} className="text-link hover:underline">
                  {app.clusterName}
                </Link>
              ),
            },
            { label: "Version", value: app.version || "—" },
            { label: "Plan", value: app.plan || "—" },
            {
              label: "Nodes",
              value: `${formatInteger(app.nodes)} × ${app.cpu} vCPU / ${app.ram} GB`,
            },
            { label: "Credits 7d", value: formatCredits(app.credits7d) },
            { label: "Credits 30d", value: formatCredits(app.credits30d) },
          ]}
        />
      </Card>
      <Card title="App Endpoints" className="mt-4">
        {app.endpoints.length === 0 ? (
          <p className="text-caption text-text-muted">No endpoints.</p>
        ) : (
          <Table>
            <thead>
              <tr>
                <Th>Endpoint</Th>
                <Th>Bucket</Th>
                <Th>State</Th>
              </tr>
            </thead>
            <tbody>
              {app.endpoints.map((endpoint) => (
                <tr key={endpoint.name}>
                  <Td>{endpoint.name}</Td>
                  <Td>{endpoint.bucket}</Td>
                  <Td>
                    <StateBadge state={endpoint.state} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
      <div className="mt-4">
        <ConsumptionSection query={consumption} range={range} days={days} onDaysChange={setDays} />
      </div>
    </>
  );
}
