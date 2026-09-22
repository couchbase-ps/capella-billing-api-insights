import type { JSX } from "react";
import { useMemo, useState } from "react";
import { useAnalyticsClusters } from "../api/hooks";
import { AnalyticsTable } from "../components/AnalyticsTable";
import { SearchBox } from "../components/SearchBox";
import { Card, EmptyNote, ErrorNote, LoadingRow, PageHeader } from "../components/ui";
import { filterBySearch } from "../lib/search";

export function Analytics(): JSX.Element {
  const clusters = useAnalyticsClusters();
  const [query, setQuery] = useState("");
  const filtered = useMemo(
    () =>
      clusters.data
        ? filterBySearch(clusters.data, query, (c) => [
            c.name,
            c.projectName,
            c.provider,
            c.region,
            c.supportPlan,
            c.state,
            c.availability,
          ])
        : null,
    [clusters.data, query],
  );
  const count =
    clusters.data && filtered
      ? filtered.length === clusters.data.length
        ? `${clusters.data.length} Analytics (Columnar) clusters`
        : `${filtered.length} of ${clusters.data.length} Analytics (Columnar) clusters`
      : undefined;
  return (
    <>
      <PageHeader
        title="Analytics clusters"
        subtitle={count}
        action={
          <SearchBox
            value={query}
            onChange={setQuery}
            placeholder="Search name, project, provider, region, plan, state…"
          />
        }
      />
      <Card>
        {clusters.isPending && <LoadingRow />}
        {clusters.isError && <ErrorNote error={clusters.error} />}
        {filtered && filtered.length === 0 && clusters.data && clusters.data.length > 0 && (
          <EmptyNote>No Analytics (Columnar) clusters match "{query}".</EmptyNote>
        )}
        {filtered && filtered.length > 0 && <AnalyticsTable clusters={filtered} />}
        {clusters.data && clusters.data.length === 0 && (
          <EmptyNote>No Analytics (Columnar) clusters yet.</EmptyNote>
        )}
      </Card>
    </>
  );
}
