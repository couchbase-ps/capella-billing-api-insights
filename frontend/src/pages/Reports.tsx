import { Download } from "lucide-react";
import type { JSX } from "react";
import { useEffect, useMemo, useState } from "react";
import { buildUrl } from "../api/client";
import { useAnalyticsClusters, useClusters, useReport, useReports } from "../api/hooks";
import type { ReportDefinition, ReportParam } from "../api/types";
import { ReportResultTable } from "../components/ReportResultTable";
import { SegmentedControl } from "../components/SegmentedControl";
import { Card, EmptyNote, ErrorNote, LoadingRow, PageHeader } from "../components/ui";
import { reportDefaultRange } from "../lib/months";

const INPUT = "rounded-sm border border-border-strong px-2 py-1 text-body-sm";

function ClusterFilter({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}): JSX.Element {
  const clusters = useClusters();
  const analytics = useAnalyticsClusters();
  return (
    <label className="flex flex-col gap-1 text-caption text-text-muted">
      Cluster
      <select value={value} onChange={(e) => onChange(e.target.value)} className={INPUT}>
        <option value="">Select a cluster…</option>
        <optgroup label="Operational clusters">
          {clusters.data?.map((cluster) => (
            <option key={cluster.id} value={cluster.id}>
              {cluster.name} ({cluster.projectName})
            </option>
          ))}
        </optgroup>
        <optgroup label="Analytics clusters">
          {analytics.data?.map((cluster) => (
            <option key={cluster.id} value={cluster.id}>
              {cluster.name} ({cluster.projectName})
            </option>
          ))}
        </optgroup>
      </select>
    </label>
  );
}

/** Extra filters a report declares besides the date range (today: `clusterId`). */
function ExtraFilters({
  params,
  values,
  onChange,
}: {
  params: ReportParam[];
  values: Record<string, string>;
  onChange: (name: string, value: string) => void;
}): JSX.Element | null {
  const extras = params.filter((param) => param.name !== "from" && param.name !== "to");
  if (extras.length === 0) {
    return null;
  }
  return (
    <>
      {extras.map((param) =>
        param.name === "clusterId" ? (
          <ClusterFilter
            key={param.name}
            value={values[param.name] ?? ""}
            onChange={(value) => onChange(param.name, value)}
          />
        ) : (
          <label key={param.name} className="flex flex-col gap-1 text-caption text-text-muted">
            {param.name}
            <input
              type={param.type === "date" ? "date" : "text"}
              value={values[param.name] ?? ""}
              onChange={(e) => onChange(param.name, e.target.value)}
              className={INPUT}
              required={param.required}
            />
          </label>
        ),
      )}
    </>
  );
}

function ReportResult({
  report,
  params,
}: {
  report: ReportDefinition;
  params: Record<string, string>;
}): JSX.Element {
  const missing = report.params.filter((param) => param.required && !params[param.name]);
  const ready = missing.length === 0;
  const result = useReport(ready ? report.key : null, params);
  const csvHref = ready
    ? buildUrl(`/api/reports/${encodeURIComponent(report.key)}`, { ...params, format: "csv" })
    : null;
  return (
    <Card
      title={report.title}
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
      <p className="mb-3 text-caption text-text-muted">{report.description}</p>
      {!ready && (
        <EmptyNote>
          Select{" "}
          {missing
            .map((param) => (param.name === "clusterId" ? "a cluster" : param.name))
            .join(", ")}{" "}
          to run this report.
        </EmptyNote>
      )}
      {ready && result.isFetching && <LoadingRow label="Running report…" />}
      {ready && result.isError && <ErrorNote error={result.error} />}
      {ready && result.data && !result.isFetching && <ReportResultTable result={result.data} />}
    </Card>
  );
}

export function Reports(): JSX.Element {
  const reports = useReports();
  const defaults = useMemo(() => reportDefaultRange(), []);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [from, setFrom] = useState(defaults.from);
  const [to, setTo] = useState(defaults.to);
  const [extras, setExtras] = useState<Record<string, string>>({});

  useEffect(() => {
    if (selectedKey === null && reports.data && reports.data.length > 0) {
      setSelectedKey(reports.data[0]?.key ?? null);
    }
  }, [reports.data, selectedKey]);

  const selected = reports.data?.find((report) => report.key === selectedKey) ?? null;
  const params = useMemo(() => ({ from, to, ...extras }), [from, to, extras]);

  return (
    <>
      <PageHeader
        title="Reports"
        subtitle="Registered report definitions; pick one and adjust the filters."
        action={
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1 text-caption text-text-muted">
              From
              <input
                type="date"
                value={from}
                max={to}
                onChange={(e) => setFrom(e.target.value)}
                className={INPUT}
              />
            </label>
            <label className="flex flex-col gap-1 text-caption text-text-muted">
              To
              <input
                type="date"
                value={to}
                min={from}
                onChange={(e) => setTo(e.target.value)}
                className={INPUT}
              />
            </label>
            {selected && (
              <ExtraFilters
                params={selected.params}
                values={extras}
                onChange={(name, value) => setExtras((prev) => ({ ...prev, [name]: value }))}
              />
            )}
          </div>
        }
      />
      {reports.isPending && <LoadingRow />}
      {reports.isError && <ErrorNote error={reports.error} />}
      {reports.data && reports.data.length > 0 && selectedKey && (
        <div className="mb-4">
          <SegmentedControl
            label="Available reports"
            options={reports.data.map((report) => ({ value: report.key, label: report.title }))}
            value={selectedKey}
            onChange={(key) => {
              setSelectedKey(key);
              setExtras({});
            }}
          />
        </div>
      )}
      {selected ? (
        <ReportResult key={selected.key} report={selected} params={params} />
      ) : (
        reports.data && (
          <Card>
            <EmptyNote>No reports are registered.</EmptyNote>
          </Card>
        )
      )}
    </>
  );
}
