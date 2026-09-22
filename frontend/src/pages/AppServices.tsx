import type { JSX } from "react";
import { useAppServices } from "../api/hooks";
import { AppServicesTable } from "../components/AppServicesTable";
import { Card, ErrorNote, LoadingRow, PageHeader } from "../components/ui";

export function AppServices(): JSX.Element {
  const appServices = useAppServices();
  return (
    <>
      <PageHeader
        title="App Services"
        subtitle={appServices.data ? `${appServices.data.length} App Services` : undefined}
      />
      <Card>
        {appServices.isPending && <LoadingRow />}
        {appServices.isError && <ErrorNote error={appServices.error} />}
        {appServices.data && <AppServicesTable appServices={appServices.data} />}
      </Card>
    </>
  );
}
