import type { JSX } from "react";
import { useMemo, useState } from "react";
import { useAppServices } from "../api/hooks";
import { AppServicesTable } from "../components/AppServicesTable";
import { SearchBox } from "../components/SearchBox";
import { Card, EmptyNote, ErrorNote, LoadingRow, PageHeader } from "../components/ui";
import { filterBySearch } from "../lib/search";

export function AppServices(): JSX.Element {
  const appServices = useAppServices();
  const [query, setQuery] = useState("");
  const filtered = useMemo(
    () =>
      appServices.data
        ? filterBySearch(appServices.data, query, (c) => [
            c.name,
            c.clusterName,
            c.projectName,
            c.provider,
            c.version,
            c.plan,
            c.state,
          ])
        : null,
    [appServices.data, query],
  );
  const count =
    appServices.data && filtered
      ? filtered.length === appServices.data.length
        ? `${appServices.data.length} App Services`
        : `${filtered.length} of ${appServices.data.length} App Services`
      : undefined;
  return (
    <>
      <PageHeader
        title="App Services"
        subtitle={count}
        action={
          <SearchBox
            value={query}
            onChange={setQuery}
            placeholder="Search name, cluster, project, plan, state…"
          />
        }
      />
      <Card>
        {appServices.isPending && <LoadingRow />}
        {appServices.isError && <ErrorNote error={appServices.error} />}
        {filtered && filtered.length === 0 && appServices.data && appServices.data.length > 0 && (
          <EmptyNote>No App Services match "{query}".</EmptyNote>
        )}
        {filtered && filtered.length > 0 && <AppServicesTable appServices={filtered} />}
        {appServices.data && appServices.data.length === 0 && (
          <EmptyNote>No App Services yet.</EmptyNote>
        )}
      </Card>
    </>
  );
}
