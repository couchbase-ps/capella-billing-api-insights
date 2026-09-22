import type { JSX } from "react";
import { Link } from "react-router-dom";
import type { AppServiceCard } from "../api/types";
import { formatCredits, formatInteger } from "../lib/format";
import { Table, Td, Th } from "./Table";
import { StateBadge } from "./ui";

export function AppServicesTable({ appServices }: { appServices: AppServiceCard[] }): JSX.Element {
  if (appServices.length === 0) {
    return (
      <p className="py-6 text-center text-caption text-text-muted">No App Services synced yet.</p>
    );
  }
  const sorted = [...appServices].sort((a, b) => (b.credits30d ?? -1) - (a.credits30d ?? -1));
  return (
    <Table>
      <thead>
        <tr>
          <Th>Name</Th>
          <Th>Cluster</Th>
          <Th>Project</Th>
          <Th>Version</Th>
          <Th>Plan</Th>
          <Th>State</Th>
          <Th num>Nodes</Th>
          <Th>Size</Th>
          <Th num>Endpoints</Th>
          <Th num>Credits 7d</Th>
          <Th num>Credits 30d</Th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((app) => (
          <tr key={app.id} data-testid="appservice-row">
            <Td>
              <Link to={`/appservices/${app.id}`} className="text-link hover:underline">
                {app.name}
              </Link>
            </Td>
            <Td>
              <Link to={`/clusters/${app.clusterId}`} className="text-link hover:underline">
                {app.clusterName}
              </Link>
            </Td>
            <Td muted>{app.projectName}</Td>
            <Td>{app.version || "—"}</Td>
            <Td>{app.plan || "—"}</Td>
            <Td>
              <StateBadge state={app.state} />
            </Td>
            <Td num>{formatInteger(app.nodes)}</Td>
            <Td>
              {app.cpu} vCPU · {app.ram} GB
            </Td>
            <Td num>{formatInteger(app.endpoints.length)}</Td>
            <Td num>{formatCredits(app.credits7d)}</Td>
            <Td num>{formatCredits(app.credits30d)}</Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
