import { fireEvent, screen } from "@testing-library/react";
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
  it("shows one monthly table at a time with a summary chart, Total row and CSV link", async () => {
    stubFetch(
      defaultRoutes({
        "/api/reports/credits-by-category": byCategory,
        "/api/reports/credits-by-plan": { ...byCategory, key: "credits-by-plan", rows: [] },
        "/api/reports/credits-by-cluster": byCluster,
      }),
    );
    renderWithProviders(<App />, { route: "/insights" });
    expect(await screen.findByText("Sum of consumed Credits")).toBeInTheDocument();
    expect(screen.getByTestId("stacked-month-chart")).toBeInTheDocument();
    expect(screen.getAllByText("Total").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Jul 2026").length).toBeGreaterThanOrEqual(1);
    const links = screen.getAllByRole("link", { name: /Download CSV/ });
    expect(links).toHaveLength(1);
    expect(links[0]).toHaveAttribute(
      "href",
      expect.stringContaining("/api/reports/credits-by-category?"),
    );
    expect(screen.queryByText("Cluster Instance Name")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Usage per Cluster" }));
    expect(await screen.findByText("Cluster Instance Name")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Usage per Cluster" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(await screen.findByText(/estimated proportionally/)).toBeInTheDocument();
  });
});
