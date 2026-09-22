import type { JSX } from "react";
import type { Prepaid, PrepaidCredit } from "../api/types";
import { formatDate } from "../lib/dates";
import { formatCredits, formatPercent } from "../lib/format";

function barColor(percent: number): string {
  if (percent <= 10) {
    return "bg-primary";
  }
  if (percent <= 25) {
    return "bg-tertiary";
  }
  return "bg-success";
}

function CreditBlock({ block }: { block: PrepaidCredit }): JSX.Element {
  const percent = Math.max(0, Math.min(100, block.remainingPercent));
  return (
    <div className="rounded-md border border-border bg-surface p-3">
      <div className="flex items-baseline justify-between gap-2">
        <p className="truncate text-label-md text-on-surface-strong" title={block.creditName}>
          {block.creditName}
        </p>
        <span className="shrink-0 text-caption text-text-muted">{block.supportPlan}</span>
      </div>
      <p className="mt-1 text-heading-md tabular-nums">
        {formatCredits(block.remaining)}
        <span className="text-unit text-text-muted"> of {formatCredits(block.total)}</span>
      </p>
      <div
        className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-alt"
        role="progressbar"
        aria-valuenow={Math.round(percent)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${block.creditName} remaining`}
      >
        <div className={`h-full ${barColor(percent)}`} style={{ width: `${percent}%` }} />
      </div>
      <p className="mt-1 flex justify-between text-caption text-text-muted">
        <span>{formatPercent(block.remainingPercent)} remaining</span>
        <span>expires {formatDate(block.expirationDate)}</span>
      </p>
    </div>
  );
}

export function PrepaidCards({ prepaid }: { prepaid: Prepaid }): JSX.Element {
  if (prepaid.credits.length === 0) {
    return (
      <p className="py-4 text-caption text-text-muted">
        No prepaid credit blocks on this organization.
      </p>
    );
  }
  const aggregate = prepaid.aggregate;
  return (
    <div>
      <div className="mb-3 flex flex-wrap items-baseline gap-x-6 gap-y-1">
        <p className="text-heading-lg tabular-nums text-on-surface-strong">
          {formatCredits(aggregate.remaining)}
          <span className="text-unit text-text-muted">
            {" "}
            remaining of {formatCredits(aggregate.total)}
          </span>
        </p>
        <p className="text-caption text-text-muted">
          {formatPercent(aggregate.remainingPercent)} left · used {formatCredits(aggregate.used)} ·
          fetched {formatDate(prepaid.fetchedAt)}
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {prepaid.credits.map((block) => (
          <CreditBlock key={block.id} block={block} />
        ))}
      </div>
    </div>
  );
}
