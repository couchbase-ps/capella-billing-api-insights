import type { JSX } from "react";
import { Link } from "react-router-dom";
import type { InstanceShare } from "../api/types";
import { formatPercent, formatSpend } from "../lib/format";
import { Table, Td, Th } from "./Table";
import { ScopeBadge } from "./ui";

export function instanceLink(item: InstanceShare): string {
  if (item.scope === "appservice") {
    return `/appservices/${item.instanceId}`;
  }
  if (item.scope === "analytics") {
    return `/analytics/${item.instanceId}`;
  }
  return `/clusters/${item.instanceId}`;
}

export function TopConsumersTable({
  rows,
  currency,
  limit = 10,
}: {
  rows: InstanceShare[];
  currency: string;
  limit?: number;
}): JSX.Element {
  const sorted = [...rows].sort((a, b) => (b.credits ?? 0) - (a.credits ?? 0)).slice(0, limit);
  if (sorted.length === 0) {
    return (
      <p className="py-6 text-center text-caption text-text-muted">
        No attributed consumption yet.
      </p>
    );
  }
  return (
    <Table>
      <thead>
        <tr>
          <Th>Name</Th>
          <Th>Project</Th>
          <Th>Scope</Th>
          <Th num>Credits</Th>
          <Th num>Share</Th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((item) => (
          <tr key={`${item.scope}-${item.instanceId}`}>
            <Td>
              <Link to={instanceLink(item)} className="text-link hover:underline">
                {item.name}
              </Link>
            </Td>
            <Td muted>{item.projectName ?? "—"}</Td>
            <Td>
              <ScopeBadge scope={item.scope} />
            </Td>
            <Td num>{formatSpend(item.credits, item.currency, currency)}</Td>
            <Td num muted>
              {formatPercent(item.sharePercent)}
            </Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
