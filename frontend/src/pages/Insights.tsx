import type { JSX } from "react";
import { useMemo, useState } from "react";
import { buildUrl } from "../api/client";
import { useReport } from "../api/hooks";
import { StackedMonthChart } from "../components/charts/StackedMonthChart";
import { DownloadMenu } from "../components/DownloadMenu";
import { ReportResultTable } from "../components/ReportResultTable";
import { SegmentedControl } from "../components/SegmentedControl";
import { Card, ErrorNote, LoadingRow, PageHeader } from "../components/ui";
import { lastMonths, monthRangeToDates } from "../lib/months";
import { summarize } from "../lib/reportSummary";

type InsightKey = "credits-by-category" | "credits-by-plan" | "credits-by-cluster";

const INSIGHTS: { key: InsightKey; toggle: string; title: string; description: string }[] = [
  {
    key: "credits-by-category",
    toggle: "Categories",
    title: "Credits split up by categories",
    description: "Organization credits per month and billing category.",
  },
  {
    key: "credits-by-plan",
    toggle: "Plan",
    title: "Credits by plan",
    description: "Per month and support plan, one column per category, with a grand total.",
  },
  {
    key: "credits-by-cluster",
    toggle: "Usage per Cluster",
    title: "Credits by usage per cluster",
    description:
      "Per month and instance (App Service credits attributed to their cluster), plan totals and the estimated on-demand share.",
  },
];

const INPUT = "rounded-sm border border-border-strong px-2 py-1 text-body-sm";

function InsightCard({
  report,
  from,
  to,
}: {
  report: (typeof INSIGHTS)[number];
  from: string;
  to: string;
}): JSX.Element {
  const result = useReport(report.key, { from, to });
  const download = (format: string) => buildUrl(`/api/reports/${report.key}`, { from, to, format });
  const meta = result.data?.meta;
  const summary = useMemo(() => (result.data ? summarize(result.data) : null), [result.data]);
  return (
    <Card
      title={report.title}
      action={
        <DownloadMenu
          options={[
            { label: "CSV", href: download("csv") },
            { label: "Excel", href: download("xlsx") },
          ]}
        />
      }
    >
      <p className="mb-3 text-caption text-text-muted">
        {report.description}
        {meta?.unit && meta.unit !== "credits" ? ` Figures are in ${meta.unit}.` : ""}
        {meta?.partialMonths && meta.partialMonths.length > 0
          ? ` Partial months: ${meta.partialMonths.join(", ")}.`
          : ""}
        {meta?.onDemandMethod
          ? " On-demand credits are estimated proportionally from the pay-as-you-go spend of each plan."
          : ""}
      </p>
      {result.isPending && <LoadingRow label="Running report…" />}
      {result.isError && <ErrorNote error={result.error} />}
      {summary && (
        <div className="mb-4">
          <StackedMonthChart rows={summary.rows} series={summary.series} />
        </div>
      )}
      {result.data && <ReportResultTable result={result.data} />}
    </Card>
  );
}

export function Insights(): JSX.Element {
  const defaults = useMemo(() => lastMonths(3), []);
  const [fromMonth, setFromMonth] = useState(defaults.from);
  const [toMonth, setToMonth] = useState(defaults.to);
  const [selected, setSelected] = useState<InsightKey>("credits-by-category");
  const range = useMemo(() => monthRangeToDates(fromMonth, toMonth), [fromMonth, toMonth]);
  const report = INSIGHTS.find((entry) => entry.key === selected) ?? INSIGHTS[0];
  return (
    <>
      <PageHeader
        title="Insights"
        subtitle="Monthly credit tables with a Total row, ready to paste into an account report."
        action={
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1 text-caption text-text-muted">
              From month
              <input
                type="month"
                value={fromMonth}
                max={toMonth}
                onChange={(e) => setFromMonth(e.target.value)}
                className={INPUT}
              />
            </label>
            <label className="flex flex-col gap-1 text-caption text-text-muted">
              To month
              <input
                type="month"
                value={toMonth}
                min={fromMonth}
                onChange={(e) => setToMonth(e.target.value)}
                className={INPUT}
              />
            </label>
            <span className="pb-1.5 text-caption text-text-muted">
              {range.from} → {range.to}
            </span>
          </div>
        }
      />
      <div className="mb-4 flex justify-center">
        <SegmentedControl
          label="Insight table"
          options={INSIGHTS.map((entry) => ({ value: entry.key, label: entry.toggle }))}
          value={selected}
          onChange={setSelected}
        />
      </div>
      {report && <InsightCard key={report.key} report={report} from={range.from} to={range.to} />}
    </>
  );
}
