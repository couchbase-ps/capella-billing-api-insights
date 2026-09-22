import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TopologyView } from "../components/TopologyView";
import { topology } from "./fixtures";

describe("TopologyView", () => {
  it("mounts the topology-ui renderer for a sample document", () => {
    const { container } = render(<TopologyView document={topology} />);
    const root = container.querySelector(".cb-topology-renderer");
    expect(root).not.toBeNull();
    expect(screen.getByTestId("topology-view")).toHaveTextContent("prod-eu");
    expect(root?.textContent).toContain("travel");
    expect(root?.textContent).toContain("3x");
    const images = Array.from(container.querySelectorAll("image, img"));
    expect(images.length).toBeGreaterThan(0);
    for (const image of images) {
      const href =
        image.getAttribute("xlink:href") ?? image.getAttribute("href") ?? image.getAttribute("src");
      expect(href).toMatch(/^\/topology-ui\/images\//);
    }
  });
});
