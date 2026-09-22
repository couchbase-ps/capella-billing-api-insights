import type { JSX } from "react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { ClusterCard } from "../api/types";
import { formatCredits, formatInteger } from "../lib/format";
import { Table, Td, Th } from "./Table";
import { StateBadge, Tag } from "./ui";

type SortKey = "name" | "projectName" | "credits7d" | "credits30d" | "nodes";

function compare(a: ClusterCard, b: ClusterCard, key: SortKey): number {
  const va = a[key];
  const vb = b[key];
  if (typeof va === "string" && typeof vb === "string") {
    return va.localeCompare(vb);
  }
  return (Number(vb ?? -1) || 0) - (Number(va ?? -1) || 0);
}

export function ClustersTable({ clusters }: { clusters: ClusterCard[] }): JSX.Element {
  const [sortKey, setSortKey] = useState<SortKey>("credits30d");
  const sorted = useMemo(
    () => [...clusters].sort((a, b) => compare(a, b, sortKey)),
    [clusters, sortKey],
  );
  if (clusters.length === 0) {
    return <p className="py-6 text-center text-caption text-text-muted">No clusters synced yet.</p>;
  }
  const sortable = (key: SortKey) => ({ onClick: () => setSortKey(key), active: sortKey === key });
  return (
    <Table>
      <thead>
        <tr>
          <Th {...sortable("name")}>Name</Th>
          <Th {...sortable("projectName")}>Project</Th>
          <Th>Provider / region</Th>
          <Th>Version</Th>
          <Th>Plan</Th>
          <Th>Availability</Th>
          <Th>State</Th>
          <Th num {...sortable("nodes")}>
            Nodes
          </Th>
          <Th num {...sortable("credits7d")}>
            Credits 7d
          </Th>
          <Th num {...sortable("credits30d")}>
            Credits 30d
          </Th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((cluster) => (
          <tr key={cluster.id} data-testid="cluster-row">
            <Td>
              <Link to={`/clusters/${cluster.id}`} className="text-link hover:underline">
                {cluster.name}
              </Link>
              {cluster.freeTier && <Tag>free tier</Tag>}
            </Td>
            <Td muted>{cluster.projectName}</Td>
            <Td>
              {cluster.provider} · {cluster.region}
            </Td>
            <Td>{cluster.version || "—"}</Td>
            <Td>{cluster.supportPlan || "—"}</Td>
            <Td>{cluster.availability || "—"}</Td>
            <Td>
              <StateBadge state={cluster.state} />
            </Td>
            <Td num>{formatInteger(cluster.nodes)}</Td>
            <Td num>{formatCredits(cluster.credits7d)}</Td>
            <Td num>{formatCredits(cluster.credits30d)}</Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
