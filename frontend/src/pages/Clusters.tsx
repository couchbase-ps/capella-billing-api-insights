import type { JSX } from "react";
import { useClusters } from "../api/hooks";
import { ClustersTable } from "../components/ClustersTable";
import { Card, ErrorNote, LoadingRow, PageHeader } from "../components/ui";

export function Clusters(): JSX.Element {
  const clusters = useClusters();
  return (
    <>
      <PageHeader
        title="Clusters"
        subtitle={clusters.data ? `${clusters.data.length} operational clusters` : undefined}
      />
      <Card>
        {clusters.isPending && <LoadingRow />}
        {clusters.isError && <ErrorNote error={clusters.error} />}
        {clusters.data && <ClustersTable clusters={clusters.data} />}
      </Card>
    </>
  );
}
