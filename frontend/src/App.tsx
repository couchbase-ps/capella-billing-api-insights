import type { JSX } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Analytics } from "./pages/Analytics";
import { AnalyticsDetail } from "./pages/AnalyticsDetail";
import { AppServiceDetail } from "./pages/AppServiceDetail";
import { AppServices } from "./pages/AppServices";
import { ClusterDetail } from "./pages/ClusterDetail";
import { Clusters } from "./pages/Clusters";
import { Insights } from "./pages/Insights";
import { Overview } from "./pages/Overview";
import { Reports } from "./pages/Reports";

export function App(): JSX.Element {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Overview />} />
        <Route path="/clusters" element={<Clusters />} />
        <Route path="/clusters/:id" element={<ClusterDetail />} />
        <Route path="/appservices" element={<AppServices />} />
        <Route path="/appservices/:id" element={<AppServiceDetail />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/analytics/:id" element={<AnalyticsDetail />} />
        <Route path="/insights" element={<Insights />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
