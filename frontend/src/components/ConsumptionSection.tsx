import type { UseQueryResult } from "@tanstack/react-query";
import { Download } from "lucide-react";
import type { JSX } from "react";
import { buildUrl } from "../api/client";
import type { DateRange } from "../api/hooks";
import type { Consumption } from "../api/types";
import { formatDate } from "../lib/dates";
import { formatSpend } from "../lib/format";
import type { RangeDays } from "../lib/ranges";
import { CategoryTable } from "./CategoryTable";
import { DailyCreditsChart } from "./charts/DailyCreditsChart";
import { RangePicker } from "./RangePicker";
import { Card, ErrorNote, LoadingRow } from "./ui";

/** Range picker + daily stacked chart + category table; shared by the three detail pages. */
export function ConsumptionSection({
  query,
  range,
  days,
  onDaysChange,
  csvClusterId,
}: {
  query: UseQueryResult<Consumption>;
  range: DateRange;
  days: RangeDays;
  onDaysChange: (days: RangeDays) => void;
  csvClusterId?: string;
}): JSX.Element {
  const csvHref = csvClusterId
    ? buildUrl("/api/reports/cluster-daily", { clusterId: csvClusterId, ...range, format: "csv" })
    : null;
  const data = query.data;
  return (
    <>
      <Card
        title={
          <>
            Daily credits
            <span className="ml-2 font-normal text-caption text-text-muted">
              {formatDate(range.from)} – {formatDate(range.to)}
              {data
                ? ` · total ${formatSpend(data.total.credits, data.total.currency, data.currency)}`
                : ""}
            </span>
          </>
        }
        action={
          <div className="flex items-center gap-2">
            <RangePicker value={days} onChange={onDaysChange} />
            {csvHref && (
              <a
                href={csvHref}
                download
                className="inline-flex items-center gap-1 rounded-sm border border-border px-2.5 py-1 text-label-sm hover:bg-surface-alt"
              >
                <Download size={14} aria-hidden="true" />
                Download CSV
              </a>
            )}
          </div>
        }
      >
        {query.isPending && <LoadingRow />}
        {query.isError && <ErrorNote error={query.error} />}
        {data && <DailyCreditsChart series={data.series} />}
      </Card>
      <Card title="By category" className="mt-4">
        {query.isPending && <LoadingRow />}
        {data && <CategoryTable rows={data.byCategory} currency={data.currency} />}
      </Card>
    </>
  );
}
