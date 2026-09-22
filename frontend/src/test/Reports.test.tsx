import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "../App";
import { defaultRoutes } from "./fixtures";
import { renderWithProviders, stubFetch } from "./render";

describe("Reports", () => {
  it("preselects the first report, defaults the range, and shows extra filters per report", async () => {
    stubFetch(defaultRoutes());
    renderWithProviders(<App />, { route: "/reports" });
    // the first registered report runs straight away with the default range
    expect(await screen.findByRole("button", { name: "Consumption summary" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    const from = screen.getByLabelText("From") as HTMLInputElement;
    const to = screen.getByLabelText("To") as HTMLInputElement;
    expect(from.value).toMatch(/^\d{4}-\d{2}-01$/);
    expect(to.value).toMatch(/^\d{4}-\d{2}-(28|29|30|31)$/);
    expect(screen.queryByLabelText("Cluster")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Cluster daily credits" }));
    expect(await screen.findByLabelText("Cluster")).toBeInTheDocument();
    expect(screen.getByText(/Select a cluster to run this report/)).toBeInTheDocument();
  });
});
