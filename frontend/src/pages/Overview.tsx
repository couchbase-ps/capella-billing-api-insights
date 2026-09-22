import type { JSX } from "react";
import { useMemo, useState } from "react";
import { useBillingSummary, useHealth, useOrgDailyConsumption, usePrepaid } from "../api/hooks";
import { DailyCreditsChart } from "../components/charts/DailyCreditsChart";
import { PrepaidCards } from "../components/PrepaidCards";
import { RangePicker } from "../components/RangePicker";
import { SyncStatusCard } from "../components/SyncStatusCard";
import { TopConsumersTable } from "../components/TopConsumersTable";
import { Card, ErrorNote, LoadingRow, PageHeader } from "../components/ui";
import { formatDate } from "../lib/dates";
import { formatSpend } from "../lib/format";
import type { RangeDays } from "../lib/ranges";
import { lastDays } from "../lib/ranges";

export function Overview(): JSX.Element {
  const [days, setDays] = useState<RangeDays>(30);
  const range = useMemo(() => lastDays(days), [days]);
  const health = useHealth();
  const prepaid = usePrepaid();
  const daily = useOrgDailyConsumption(range);
  const summary = useBillingSummary(range);
  const configured = health.data?.configured ?? true;
  const currency = summary.data?.currency ?? "USD";

  return (
    <>
      <PageHeader
        title="Overview"
        subtitle={`${formatDate(range.from)} – ${formatDate(range.to)}`}
        action={<RangePicker value={days} onChange={setDays} />}
      />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Prepaid credits" className="lg:col-span-2">
          {prepaid.isPending && <LoadingRow />}
          {prepaid.isError && <ErrorNote error={prepaid.error} />}
          {prepaid.data && <PrepaidCards prepaid={prepaid.data} />}
        </Card>
        <SyncStatusCard disabled={!configured} />
      </div>
      <Card
        className="mt-4"
        title={
          <>
            Organization credits by category
            {summary.data && (
              <span className="ml-2 font-normal text-caption text-text-muted">
                total {formatSpend(summary.data.org.credits, summary.data.org.currency, currency)}
              </span>
            )}
          </>
        }
      >
        {daily.isPending && <LoadingRow />}
        {daily.isError && <ErrorNote error={daily.error} />}
        {daily.data && <DailyCreditsChart series={daily.data.rows} />}
      </Card>
      <Card
        className="mt-4"
        title="Top consumers"
        action={
          summary.data && (
            <span className="text-caption text-text-muted">
              attributed{" "}
              {formatSpend(
                summary.data.attributed.credits,
                summary.data.attributed.currency,
                currency,
              )}{" "}
              · unattributed{" "}
              {formatSpend(
                summary.data.unattributed.credits,
                summary.data.unattributed.currency,
                currency,
              )}
            </span>
          )
        }
      >
        {summary.isPending && <LoadingRow />}
        {summary.isError && <ErrorNote error={summary.error} />}
        {summary.data && <TopConsumersTable rows={summary.data.byInstance} currency={currency} />}
      </Card>
    </>
  );
}
