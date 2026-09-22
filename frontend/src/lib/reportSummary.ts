import type { ReportColumn, ReportResult, ReportRow } from "../api/types";
import type { StackedRow, StackedSeries } from "../components/charts/StackedMonthChart";
import { seriesColor } from "./categories";

export interface StackedSummary {
  rows: StackedRow[];
  series: StackedSeries[];
}

const NON_CATEGORY_KEYS = new Set([
  "month",
  "plan",
  "instance",
  "category",
  "credits",
  "grandTotal",
  "totalDevPro",
  "totalEnterprise",
  "totalBasic",
  "onDemand",
]);

function numberOf(value: string | number | null | undefined): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

/** Category columns of a wide (plan / cluster) report, in the backend's fixed order. */
export function categoryColumns(result: ReportResult): ReportColumn[] {
  return result.columns.filter(
    (column) =>
      !NON_CATEGORY_KEYS.has(column.key) &&
      (column.type === "credits" || column.type === "currency"),
  );
}

/** Row total of a wide report: the sum of its category columns (null cells count as 0). */
export function rowTotal(row: ReportRow, columns: ReportColumn[]): number {
  return columns.reduce((sum, column) => sum + numberOf(row[column.key]), 0);
}

/**
 * Pivots long or wide report rows into one stacked bar per month.
 * `seriesOf` names the series a row contributes to and `amountOf` its amount.
 * With `limit`, the smallest series are folded into "Other" so cluster charts stay legible.
 */
export function stackByMonth(
  rows: ReportRow[],
  seriesOf: (row: ReportRow) => string,
  amountOf: (row: ReportRow) => number,
  limit?: number,
): StackedSummary {
  const totals = new Map<string, number>();
  const byMonth = new Map<string, Map<string, number>>();
  for (const row of rows) {
    const month = String(row.month ?? "");
    if (!/^\d{4}-\d{2}$/.test(month)) {
      continue; // skip the Total row and anything not month-keyed
    }
    const key = seriesOf(row);
    const value = amountOf(row);
    totals.set(key, (totals.get(key) ?? 0) + value);
    const bucket = byMonth.get(month) ?? new Map<string, number>();
    bucket.set(key, (bucket.get(key) ?? 0) + value);
    byMonth.set(month, bucket);
  }
  let keys = Array.from(totals.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([key]) => key);
  let folded: string[] = [];
  if (limit !== undefined && keys.length > limit) {
    folded = keys.slice(limit);
    keys = [...keys.slice(0, limit), "Other"];
  }
  const foldedSet = new Set(folded);
  const stacked = Array.from(byMonth.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([month, bucket]) => {
      const row: StackedRow = { month };
      for (const [key, value] of bucket) {
        const target = foldedSet.has(key) ? "Other" : key;
        row[target] = numberOf(row[target]) + value;
      }
      return row;
    });
  const series: StackedSeries[] = keys.map((key, index) => ({
    key,
    label: key,
    color: key === "Other" ? "#a8a8a8" : seriesColor(index),
  }));
  return { rows: stacked, series };
}

/** Summary chart data for each of the three monthly reports. */
export function summarize(result: ReportResult): StackedSummary {
  switch (result.key) {
    case "credits-by-category":
      return stackByMonth(
        result.rows,
        (row) => String(row.category ?? "Uncategorised"),
        (row) => numberOf(row.credits),
      );
    case "credits-by-plan":
      return stackByMonth(
        result.rows,
        (row) => String(row.plan ?? "Unattributed"),
        (row) => numberOf(row.grandTotal),
      );
    default: {
      const columns = categoryColumns(result);
      return stackByMonth(
        result.rows,
        (row) => String(row.instance ?? "Unattributed"),
        (row) => rowTotal(row, columns),
        8,
      );
    }
  }
}
