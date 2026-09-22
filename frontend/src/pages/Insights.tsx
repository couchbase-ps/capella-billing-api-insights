import { Download } from "lucide-react";
import type { JSX } from "react";
import { useMemo, useState } from "react";
import { buildUrl } from "../api/client";
import { useReport } from "../api/hooks";
import { ReportResultTable } from "../components/ReportResultTable";
import { Card, ErrorNote, LoadingRow, PageHeader } from "../components/ui";
import { lastMonths, monthRangeToDates } from "../lib/months";

const INSIGHTS: { key: string; title: string; description: string }[] = [
  {
    key: "credits-by-category",
    title: "Credits split up by categories",
    description: "Organization credits per month and billing category.",
  },
  {
    key: "credits-by-plan",
    title: "Credits by plan",
    description: "Per month and support plan, one column per category, with a grand total.",
  },
  {
    key: "credits-by-cluster",
    title: "Credits by usage per cluster",
    description:
      "Per month and instance (App Service credits attributed to their cluster), plan totals and the estimated on-demand share.",
  },
];

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
  const csvHref = buildUrl(`/api/reports/${report.key}`, { from, to, format: "csv" });
  const meta = result.data?.meta;
  return (
    <Card
      title={report.title}
      action={
        <a
          href={csvHref}
          download
          className="inline-flex items-center gap-1 rounded-sm border border-border px-2.5 py-1 text-label-sm hover:bg-surface-alt"
        >
          <Download size={14} aria-hidden="true" />
          Download CSV
        </a>
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
      {result.data && <ReportResultTable result={result.data} />}
    </Card>
  );
}

export function Insights(): JSX.Element {
  const defaults = useMemo(() => lastMonths(3), []);
  const [fromMonth, setFromMonth] = useState(defaults.from);
  const [toMonth, setToMonth] = useState(defaults.to);
  const range = useMemo(() => monthRangeToDates(fromMonth, toMonth), [fromMonth, toMonth]);
  const input = "rounded-sm border border-border-strong px-2 py-1 text-body-sm";
  return (
    <>
      <PageHeader
        title="Insights"
        subtitle="Monthly credit tables with a Total row, ready to paste into an account report."
      />
      <form className="mb-4 flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
        <label className="flex flex-col gap-1 text-caption text-text-muted">
          From month
          <input
            type="month"
            value={fromMonth}
            max={toMonth}
            onChange={(e) => setFromMonth(e.target.value)}
            className={input}
          />
        </label>
        <label className="flex flex-col gap-1 text-caption text-text-muted">
          To month
          <input
            type="month"
            value={toMonth}
            min={fromMonth}
            onChange={(e) => setToMonth(e.target.value)}
            className={input}
          />
        </label>
        <span className="pb-1.5 text-caption text-text-muted">
          {range.from} → {range.to}
        </span>
      </form>
      <div className="flex flex-col gap-4">
        {INSIGHTS.map((report) => (
          <InsightCard key={report.key} report={report} from={range.from} to={range.to} />
        ))}
      </div>
    </>
  );
}
