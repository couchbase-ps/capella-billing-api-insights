import type { JSX } from "react";
import type { ReportColumn, ReportResult, ReportRow } from "../api/types";
import { formatDate } from "../lib/dates";
import { formatCredits, formatCurrency, formatInteger } from "../lib/format";
import { Table, Td, Th } from "./Table";
import { EmptyNote } from "./ui";

function cell(column: ReportColumn, value: string | number | null | undefined): string {
  if (value === null || value === undefined) {
    return "—";
  }
  switch (column.type) {
    case "credits":
      return formatCredits(Number(value));
    case "currency":
      return formatCurrency(Number(value));
    case "number":
      return typeof value === "number" && Number.isInteger(value)
        ? formatInteger(value)
        : Number(value).toLocaleString("en-US", { maximumFractionDigits: 2 });
    case "date":
      return formatDate(String(value));
    default:
      return String(value);
  }
}

export function ReportResultTable({ result }: { result: ReportResult }): JSX.Element {
  if (result.rows.length === 0) {
    return <EmptyNote>The report returned no rows for this range.</EmptyNote>;
  }
  const numeric = (column: ReportColumn) => column.type !== "string" && column.type !== "date";
  const renderRow = (row: ReportRow, key: string) => (
    <tr key={key}>
      {result.columns.map((column) => (
        <Td key={column.key} num={numeric(column)}>
          {cell(column, row[column.key])}
        </Td>
      ))}
    </tr>
  );
  return (
    <Table>
      <thead>
        <tr>
          {result.columns.map((column) => (
            <Th key={column.key} num={numeric(column)}>
              {column.label}
            </Th>
          ))}
        </tr>
      </thead>
      <tbody>{result.rows.map((row, index) => renderRow(row, `row-${index}`))}</tbody>
      {result.totals && (
        <tfoot className="font-semibold">{renderRow(result.totals, "totals")}</tfoot>
      )}
    </Table>
  );
}
