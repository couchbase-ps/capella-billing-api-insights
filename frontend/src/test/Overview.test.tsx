import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "../App";
import { defaultRoutes, healthUnconfigured } from "./fixtures";
import { renderWithProviders, stubFetch } from "./render";

describe("Overview", () => {
  it("shows the setup banner when /health reports configured:false", async () => {
    stubFetch(defaultRoutes({ "/health": healthUnconfigured }));
    renderWithProviders(<App />, { route: "/" });
    expect(await screen.findByText("Backend not configured")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /Sync now/ })).toBeDisabled();
  });

  it("renders the org name, prepaid block and top consumers with scope badges", async () => {
    stubFetch(defaultRoutes());
    renderWithProviders(<App />, { route: "/" });
    expect(await screen.findByText("Acme Corp")).toBeInTheDocument();
    expect(await screen.findByText("Enterprise commit 2026")).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "analytics-eu" })).toHaveAttribute(
      "href",
      "/analytics/analytics-1",
    );
    // nav item + scope badge in the top consumers table
    expect(screen.getAllByText("Analytics").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("App Service")).toBeInTheDocument();
    expect(screen.queryByText("Backend not configured")).not.toBeInTheDocument();
  });
});
