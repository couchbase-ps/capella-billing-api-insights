import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "../App";
import type { ReportResult } from "../api/types";
import { defaultRoutes } from "./fixtures";
import { renderWithProviders, stubFetch } from "./render";

const byCategory: ReportResult = {
  key: "credits-by-category",
  title: "Credits split up by categories",
  from: "2026-06-01",
  to: "2026-08-31",
  columns: [
    { key: "month", label: "Month", type: "month" },
    { key: "category", label: "Row Labels", type: "string" },
    { key: "credits", label: "Sum of consumed Credits", type: "credits" },
  ],
  rows: [
    { month: "2026-07", category: "Cluster", credits: 1200.5 },
    { month: "2026-07", category: "Backup", credits: 10 },
  ],
  totals: { month: "Total", category: null, credits: 1210.5 },
  meta: { unit: "credits", partialMonths: [] },
};

const byCluster: ReportResult = {
  key: "credits-by-cluster",
  title: "Credits by usage per cluster",
  from: "2026-06-01",
  to: "2026-08-31",
  columns: [
    { key: "month", label: "Month", type: "month" },
    { key: "instance", label: "Cluster Instance Name", type: "string" },
    { key: "cluster", label: "Cluster", type: "credits" },
    { key: "onDemand", label: "Total On-demand Credits", type: "credits" },
  ],
  rows: [{ month: "2026-07", instance: "prod-eu", cluster: 1200.5, onDemand: null }],
  totals: { month: "Total", instance: null, cluster: 1200.5, onDemand: null },
  meta: { unit: "credits", onDemandMethod: "proportional-by-plan" },
};

describe("Insights", () => {
  it("renders the three monthly tables with their Total rows and CSV links", async () => {
    stubFetch(
      defaultRoutes({
        "/api/reports/credits-by-category": byCategory,
        "/api/reports/credits-by-plan": { ...byCategory, key: "credits-by-plan", rows: [] },
        "/api/reports/credits-by-cluster": byCluster,
      }),
    );
    renderWithProviders(<App />, { route: "/insights" });
    expect(await screen.findByText("Sum of consumed Credits")).toBeInTheDocument();
    expect(await screen.findByText("Cluster Instance Name")).toBeInTheDocument();
    expect(screen.getAllByText("Total").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("Jul 2026").length).toBeGreaterThanOrEqual(2);
    const links = screen.getAllByRole("link", { name: /Download CSV/ });
    expect(links).toHaveLength(3);
    expect(links[0]).toHaveAttribute(
      "href",
      expect.stringContaining("/api/reports/credits-by-category?"),
    );
    expect(await screen.findByText(/estimated proportionally/)).toBeInTheDocument();
  });
});
