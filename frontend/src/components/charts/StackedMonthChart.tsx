import type { JSX } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatPeriod } from "../../lib/dates";
import { formatCredits } from "../../lib/format";

export interface StackedSeries {
  key: string;
  label: string;
  color: string;
}

export type StackedRow = { x: string } & Record<string, number | string | null>;

/**
 * One stacked bar per x value (a month, a day or an instance); the series are whatever the
 * caller pivoted (categories, plans, clusters).
 */
export function StackedMonthChart({
  rows,
  series,
  height = 220,
  testId = "stacked-month-chart",
  xFormatter = formatPeriod,
}: {
  rows: StackedRow[];
  series: StackedSeries[];
  height?: number;
  testId?: string;
  xFormatter?: (value: string) => string;
}): JSX.Element {
  if (rows.length === 0 || series.length === 0) {
    return (
      <p className="py-6 text-center text-caption text-text-muted">No credits in this range.</p>
    );
  }
  const labelOf = new Map(series.map((s) => [s.key, s.label]));
  return (
    <div style={{ height }} data-testid={testId}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={rows}
          margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
          barCategoryGap="30%"
        >
          <CartesianGrid vertical={false} stroke="#e6e6e6" />
          <XAxis
            dataKey="x"
            tickFormatter={xFormatter}
            interval="preserveStartEnd"
            minTickGap={16}
            tick={{ fontSize: 11, fill: "#5c5c5c" }}
            axisLine={{ stroke: "#e6e6e6" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#5c5c5c" }}
            axisLine={false}
            tickLine={false}
            width={64}
            tickFormatter={(value: number) => value.toLocaleString("en-US")}
          />
          <Tooltip
            cursor={{ fill: "rgba(0,0,0,0.04)" }}
            labelFormatter={(label) => xFormatter(String(label))}
            formatter={(value, name) => [
              formatCredits(Number(value)),
              labelOf.get(String(name)) ?? String(name),
            ]}
            contentStyle={{ fontSize: 12, borderRadius: 4, borderColor: "#e6e6e6" }}
          />
          <Legend
            iconType="square"
            iconSize={10}
            wrapperStyle={{ fontSize: 12 }}
            formatter={(value) => labelOf.get(String(value)) ?? String(value)}
          />
          {series.map((s) => (
            <Bar
              key={s.key}
              dataKey={s.key}
              stackId="credits"
              fill={s.color}
              stroke="#ffffff"
              strokeWidth={1}
              isAnimationActive={false}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
