import type { JSX } from "react";
import type { CategoryTotal } from "../api/types";
import { categoryColor, categoryLabel } from "../lib/categories";
import { formatCurrency, formatPercent, formatSpend } from "../lib/format";
import { Table, Td, Th } from "./Table";

export function CategoryTable({
  rows,
  currency,
  showCurrency = false,
}: {
  rows: CategoryTotal[];
  currency: string;
  showCurrency?: boolean;
}): JSX.Element {
  if (rows.length === 0) {
    return (
      <p className="py-6 text-center text-caption text-text-muted">No categories in this range.</p>
    );
  }
  const sorted = [...rows].sort((a, b) => (b.credits ?? 0) - (a.credits ?? 0));
  return (
    <Table>
      <thead>
        <tr>
          <Th>Category</Th>
          <Th num>Credits</Th>
          {showCurrency && <Th num>{currency}</Th>}
          <Th num>Share</Th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((row) => (
          <tr key={row.category}>
            <Td>
              <span
                className="mr-2 inline-block h-2.5 w-2.5 rounded-sm align-middle"
                style={{ background: categoryColor(row.category) }}
                aria-hidden="true"
              />
              {categoryLabel(row.category)}
            </Td>
            <Td num>{formatSpend(row.credits, showCurrency ? null : row.currency, currency)}</Td>
            {showCurrency && <Td num>{formatCurrency(row.currency, currency)}</Td>}
            <Td num muted>
              {formatPercent(row.contributionPercent)}
            </Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
