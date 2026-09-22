import type { JSX } from "react";
import { useAnalyticsClusters } from "../api/hooks";
import { AnalyticsTable } from "../components/AnalyticsTable";
import { Card, ErrorNote, LoadingRow, PageHeader } from "../components/ui";

export function Analytics(): JSX.Element {
  const clusters = useAnalyticsClusters();
  return (
    <>
      <PageHeader
        title="Analytics clusters"
        subtitle={
          clusters.data ? `${clusters.data.length} Analytics (Columnar) clusters` : undefined
        }
      />
      <Card>
        {clusters.isPending && <LoadingRow />}
        {clusters.isError && <ErrorNote error={clusters.error} />}
        {clusters.data && <AnalyticsTable clusters={clusters.data} />}
      </Card>
    </>
  );
}
