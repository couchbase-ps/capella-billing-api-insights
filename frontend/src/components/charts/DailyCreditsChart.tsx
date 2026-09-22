import type { JSX } from "react";
import { useMemo } from "react";
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
import type { ConsumptionPoint } from "../../api/types";
import { categoryColor, categoryLabel, sortCategories } from "../../lib/categories";
import { formatPeriod } from "../../lib/dates";
import { formatCredits } from "../../lib/format";

type Row = Record<string, number | string | null> & { period: string };

/** Pivots the long `{period, category, credits}` series into one row per period. */
export function pivotSeries(series: ConsumptionPoint[]): { rows: Row[]; categories: string[] } {
  const categories = sortCategories(series.map((point) => point.category));
  const byPeriod = new Map<string, Row>();
  for (const point of series) {
    const row: Row = byPeriod.get(point.period) ?? { period: point.period };
    if (point.credits !== null) {
      row[point.category] = (Number(row[point.category] ?? 0) || 0) + point.credits;
    }
    byPeriod.set(point.period, row);
  }
  const rows = Array.from(byPeriod.values()).sort((a, b) => a.period.localeCompare(b.period));
  return { rows, categories };
}

export function DailyCreditsChart({
  series,
  height = 260,
}: {
  series: ConsumptionPoint[];
  height?: number;
}): JSX.Element {
  const { rows, categories } = useMemo(() => pivotSeries(series), [series]);
  if (rows.length === 0) {
    return (
      <p className="py-8 text-center text-caption text-text-muted">No credits in this range.</p>
    );
  }
  return (
    <div style={{ height }} data-testid="daily-credits-chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={rows}
          margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
          barCategoryGap="20%"
        >
          <CartesianGrid vertical={false} stroke="#e6e6e6" />
          <XAxis
            dataKey="period"
            tickFormatter={formatPeriod}
            tick={{ fontSize: 11, fill: "#5c5c5c" }}
            axisLine={{ stroke: "#e6e6e6" }}
            tickLine={false}
            minTickGap={24}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#5c5c5c" }}
            axisLine={false}
            tickLine={false}
            width={56}
            tickFormatter={(value: number) => value.toLocaleString("en-US")}
          />
          <Tooltip
            cursor={{ fill: "rgba(0,0,0,0.04)" }}
            labelFormatter={(label) => formatPeriod(String(label))}
            formatter={(value, name) => [formatCredits(Number(value)), categoryLabel(String(name))]}
            contentStyle={{ fontSize: 12, borderRadius: 4, borderColor: "#e6e6e6" }}
          />
          <Legend
            iconType="square"
            iconSize={10}
            wrapperStyle={{ fontSize: 12 }}
            formatter={(value) => categoryLabel(String(value))}
          />
          {categories.map((category) => (
            <Bar
              key={category}
              dataKey={category}
              stackId="credits"
              fill={categoryColor(category)}
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
