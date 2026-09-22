import { Download, Play } from "lucide-react";
import type { JSX } from "react";
import { useMemo, useState } from "react";
import { buildUrl } from "../api/client";
import { useAnalyticsClusters, useClusters, useReport, useReports } from "../api/hooks";
import type { ReportDefinition } from "../api/types";
import { ReportResultTable } from "../components/ReportResultTable";
import { Card, EmptyNote, ErrorNote, LoadingRow, PageHeader } from "../components/ui";
import { lastDays } from "../lib/ranges";

function ParamForm({
  report,
  onRun,
}: {
  report: ReportDefinition;
  onRun: (params: Record<string, string>) => void;
}): JSX.Element {
  const defaults = lastDays(30);
  const [from, setFrom] = useState(defaults.from);
  const [to, setTo] = useState(defaults.to);
  const [clusterId, setClusterId] = useState("");
  const needsCluster = report.params.some((param) => param.name === "clusterId");
  const clusters = useClusters();
  const analyticsClusters = useAnalyticsClusters();
  const input = "rounded-sm border border-border-strong px-2 py-1 text-body-sm";
  return (
    <form
      className="flex flex-wrap items-end gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        onRun(needsCluster ? { from, to, clusterId } : { from, to });
      }}
    >
      <label className="flex flex-col gap-1 text-caption text-text-muted">
        From
        <input
          type="date"
          value={from}
          onChange={(e) => setFrom(e.target.value)}
          className={input}
          required
        />
      </label>
      <label className="flex flex-col gap-1 text-caption text-text-muted">
        To
        <input
          type="date"
          value={to}
          onChange={(e) => setTo(e.target.value)}
          className={input}
          required
        />
      </label>
      {needsCluster && (
        <label className="flex flex-col gap-1 text-caption text-text-muted">
          Cluster
          <select
            value={clusterId}
            onChange={(e) => setClusterId(e.target.value)}
            className={input}
            required
          >
            <option value="">Select a cluster…</option>
            <optgroup label="Operational clusters">
              {clusters.data?.map((cluster) => (
                <option key={cluster.id} value={cluster.id}>
                  {cluster.name} ({cluster.projectName})
                </option>
              ))}
            </optgroup>
            <optgroup label="Analytics clusters">
              {analyticsClusters.data?.map((cluster) => (
                <option key={cluster.id} value={cluster.id}>
                  {cluster.name} ({cluster.projectName})
                </option>
              ))}
            </optgroup>
          </select>
        </label>
      )}
      <button
        type="submit"
        className="inline-flex items-center gap-1.5 rounded-sm bg-primary px-3 py-1.5 text-label-sm text-on-fill hover:bg-secondary"
      >
        <Play size={14} aria-hidden="true" />
        Run
      </button>
    </form>
  );
}

export function Reports(): JSX.Element {
  const reports = useReports();
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [runParams, setRunParams] = useState<Record<string, string> | null>(null);
  const selected = useMemo(
    () => reports.data?.find((report) => report.key === selectedKey) ?? null,
    [reports.data, selectedKey],
  );
  const result = useReport(runParams ? selectedKey : null, runParams ?? {});
  const csvHref =
    selectedKey && runParams
      ? buildUrl(`/api/reports/${encodeURIComponent(selectedKey)}`, { ...runParams, format: "csv" })
      : null;

  return (
    <>
      <PageHeader
        title="Reports"
        subtitle="Registered report definitions; run one over a date range."
      />
      <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
        <Card title="Available reports">
          {reports.isPending && <LoadingRow />}
          {reports.isError && <ErrorNote error={reports.error} />}
          <ul className="flex flex-col gap-1">
            {reports.data?.map((report) => (
              <li key={report.key}>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedKey(report.key);
                    setRunParams(null);
                  }}
                  aria-pressed={selectedKey === report.key}
                  className={`w-full rounded-sm px-2 py-1.5 text-left hover:bg-surface-alt ${
                    selectedKey === report.key ? "bg-surface-accent" : ""
                  }`}
                >
                  <span className="block text-label-md">{report.title}</span>
                  <span className="block text-caption text-text-muted">{report.description}</span>
                </button>
              </li>
            ))}
          </ul>
        </Card>
        <div>
          {selected ? (
            <Card
              title={selected.title}
              action={
                csvHref && (
                  <a
                    href={csvHref}
                    download
                    className="inline-flex items-center gap-1 rounded-sm border border-border px-2.5 py-1 text-label-sm hover:bg-surface-alt"
                  >
                    <Download size={14} aria-hidden="true" />
                    Download CSV
                  </a>
                )
              }
            >
              <ParamForm key={selected.key} report={selected} onRun={setRunParams} />
              <div className="mt-4">
                {result.isFetching && <LoadingRow label="Running report…" />}
                {result.isError && <ErrorNote error={result.error} />}
                {result.data && !result.isFetching && <ReportResultTable result={result.data} />}
              </div>
            </Card>
          ) : (
            <Card>
              <EmptyNote>Select a report to run it.</EmptyNote>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
