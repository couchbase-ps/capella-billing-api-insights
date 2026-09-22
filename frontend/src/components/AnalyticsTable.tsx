import type { JSX } from "react";
import { Link } from "react-router-dom";
import type { AnalyticsClusterCard } from "../api/types";
import { formatCredits, formatInteger } from "../lib/format";
import { Table, Td, Th } from "./Table";
import { StateBadge } from "./ui";

export function AnalyticsTable({ clusters }: { clusters: AnalyticsClusterCard[] }): JSX.Element {
  if (clusters.length === 0) {
    return (
      <p className="py-6 text-center text-caption text-text-muted">
        No Analytics clusters synced yet.
      </p>
    );
  }
  const sorted = [...clusters].sort((a, b) => (b.credits30d ?? -1) - (a.credits30d ?? -1));
  return (
    <Table>
      <thead>
        <tr>
          <Th>Name</Th>
          <Th>Project</Th>
          <Th>Provider / region</Th>
          <Th>Plan</Th>
          <Th>Availability</Th>
          <Th>State</Th>
          <Th num>Nodes</Th>
          <Th>Size</Th>
          <Th num>Credits 7d</Th>
          <Th num>Credits 30d</Th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((cluster) => (
          <tr key={cluster.id} data-testid="analytics-row">
            <Td>
              <Link to={`/analytics/${cluster.id}`} className="text-link hover:underline">
                {cluster.name}
              </Link>
            </Td>
            <Td muted>{cluster.projectName}</Td>
            <Td>
              {cluster.provider} · {cluster.region}
            </Td>
            <Td>{cluster.supportPlan || "—"}</Td>
            <Td>{cluster.availability || "—"}</Td>
            <Td>
              <StateBadge state={cluster.state} />
            </Td>
            <Td num>{formatInteger(cluster.nodes)}</Td>
            <Td>
              {cluster.cpu} vCPU · {cluster.ram} GB
            </Td>
            <Td num>{formatCredits(cluster.credits7d)}</Td>
            <Td num>{formatCredits(cluster.credits30d)}</Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
