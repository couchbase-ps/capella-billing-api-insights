import type { JSX } from "react";
import { useMemo, useState } from "react";
import { useClusters } from "../api/hooks";
import { ClustersTable } from "../components/ClustersTable";
import { SearchBox } from "../components/SearchBox";
import { Card, EmptyNote, ErrorNote, LoadingRow, PageHeader } from "../components/ui";
import { filterBySearch } from "../lib/search";

export function Clusters(): JSX.Element {
  const clusters = useClusters();
  const [query, setQuery] = useState("");
  const filtered = useMemo(
    () =>
      clusters.data
        ? filterBySearch(clusters.data, query, (c) => [
            c.name,
            c.projectName,
            c.provider,
            c.region,
            c.version,
            c.supportPlan,
            c.state,
            c.availability,
            c.freeTier ? "free tier" : "",
          ])
        : null,
    [clusters.data, query],
  );
  const count =
    clusters.data && filtered
      ? filtered.length === clusters.data.length
        ? `${clusters.data.length} operational clusters`
        : `${filtered.length} of ${clusters.data.length} operational clusters`
      : undefined;
  return (
    <>
      <PageHeader
        title="Clusters"
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
          <EmptyNote>No operational clusters match "{query}".</EmptyNote>
        )}
        {filtered && filtered.length > 0 && <ClustersTable clusters={filtered} />}
        {clusters.data && clusters.data.length === 0 && (
          <EmptyNote>No operational clusters yet.</EmptyNote>
        )}
      </Card>
    </>
  );
}
