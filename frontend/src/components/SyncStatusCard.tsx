import { RefreshCw } from "lucide-react";
import type { JSX } from "react";
import { useEffect, useRef } from "react";
import { useInvalidateAll, useStartSync, useSyncStatus } from "../api/hooks";
import type { SyncRun } from "../api/types";
import { formatDateTime, formatRelativeAge } from "../lib/dates";
import { formatInteger } from "../lib/format";
import { Card, StateBadge } from "./ui";

function RunSummary({ run }: { run: SyncRun }): JSX.Element {
  const detail = run.detail;
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-body-sm">
      <dt className="text-text-muted">Status</dt>
      <dd>
        <StateBadge state={run.status === "success" ? "healthy" : run.status} />
      </dd>
      <dt className="text-text-muted">Started</dt>
      <dd title={formatDateTime(run.startedAt)}>{formatRelativeAge(run.startedAt)}</dd>
      <dt className="text-text-muted">Finished</dt>
      <dd>{run.finishedAt ? formatDateTime(run.finishedAt) : "—"}</dd>
      <dt className="text-text-muted">Requests</dt>
      <dd className="tabular-nums">{formatInteger(run.requestsMade)}</dd>
      {detail && (
        <>
          <dt className="text-text-muted">Synced</dt>
          <dd className="tabular-nums">
            {detail.clustersSynced} clusters · {detail.appServicesSynced} app services ·{" "}
            {detail.analyticsClustersSynced ?? 0} analytics · {detail.billingWindows} windows
          </dd>
        </>
      )}
      {run.error && (
        <>
          <dt className="text-text-muted">Error</dt>
          <dd className="text-error-text">{run.error}</dd>
        </>
      )}
      {detail && detail.failures.length > 0 && (
        <>
          <dt className="text-text-muted">Failures</dt>
          <dd>
            <ul className="list-disc pl-4 text-caption text-warning-text">
              {detail.failures.map((failure) => (
                <li key={`${failure.scope}-${failure.instanceId}`}>
                  {failure.scope} {failure.instanceId}: {failure.message}
                </li>
              ))}
            </ul>
          </dd>
        </>
      )}
    </dl>
  );
}

export function SyncStatusCard({ disabled = false }: { disabled?: boolean }): JSX.Element {
  const status = useSyncStatus();
  const start = useStartSync();
  const invalidateAll = useInvalidateAll();
  const wasRunning = useRef(false);
  const running = status.data?.running ?? false;

  useEffect(() => {
    if (wasRunning.current && !running) {
      invalidateAll();
    }
    wasRunning.current = running;
  }, [running, invalidateAll]);

  const last = status.data?.runs[0];
  return (
    <Card
      title="Sync"
      action={
        <button
          type="button"
          disabled={disabled || running || start.isPending}
          onClick={() => start.mutate()}
          className="inline-flex items-center gap-1.5 rounded-sm bg-primary px-3 py-1 text-label-sm text-on-fill hover:bg-secondary disabled:cursor-not-allowed disabled:bg-text-disabled"
        >
          <RefreshCw size={14} className={running ? "animate-spin" : ""} aria-hidden="true" />
          {running ? "Syncing…" : "Sync now"}
        </button>
      }
    >
      {status.isError && <p className="text-body-sm text-error-text">Sync status unavailable.</p>}
      {start.isError && <p className="mb-2 text-body-sm text-error-text">{start.error.message}</p>}
      {last ? (
        <RunSummary run={last} />
      ) : (
        <p className="text-caption text-text-muted">No sync has run yet.</p>
      )}
    </Card>
  );
}
