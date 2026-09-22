import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AnalyticsTable } from "../components/AnalyticsTable";
import { ClustersTable } from "../components/ClustersTable";
import { analyticsClusters, clusters } from "./fixtures";
import { renderWithProviders } from "./render";

describe("ClustersTable", () => {
  it("renders one row per cluster sorted by credits30d desc", () => {
    renderWithProviders(<ClustersTable clusters={clusters} />);
    const rows = screen.getAllByTestId("cluster-row");
    expect(rows).toHaveLength(2);
    expect(within(rows[0] as HTMLElement).getByRole("link", { name: "prod-eu" })).toHaveAttribute(
      "href",
      "/clusters/cluster-1",
    );
    expect(rows[0]).toHaveTextContent("51.20 cr");
    expect(rows[1]).toHaveTextContent("dev-free");
    expect(rows[1]).toHaveTextContent("free tier");
    expect(rows[1]).toHaveTextContent("turnedOff");
    // credits7d is null on the free-tier cluster: an em-dash, never 0
    expect(within(rows[1] as HTMLElement).getAllByText("—").length).toBeGreaterThan(0);
  });

  it("re-sorts when a column header is clicked", () => {
    renderWithProviders(<ClustersTable clusters={clusters} />);
    fireEvent.click(screen.getByRole("button", { name: /^Name/ }));
    const rows = screen.getAllByTestId("cluster-row");
    expect(rows[0]).toHaveTextContent("dev-free");
  });
});

describe("AnalyticsTable", () => {
  it("renders analytics cluster rows with size and credits", () => {
    renderWithProviders(<AnalyticsTable clusters={analyticsClusters} />);
    const rows = screen.getAllByTestId("analytics-row");
    expect(rows).toHaveLength(1);
    expect(
      within(rows[0] as HTMLElement).getByRole("link", { name: "analytics-eu" }),
    ).toHaveAttribute("href", "/analytics/analytics-1");
    expect(rows[0]).toHaveTextContent("8 vCPU · 32 GB");
    expect(rows[0]).toHaveTextContent("80.00 cr");
  });
});
