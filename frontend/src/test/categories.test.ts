import { describe, expect, it } from "vitest";
import { categoryColor, categoryLabel, sortCategories } from "../lib/categories";

describe("category labels", () => {
  it("maps the known Capella categories to human labels", () => {
    expect(categoryLabel("operationalComputeAndStorage")).toBe("Compute & storage");
    expect(categoryLabel("appServicesComputeAndStorage")).toBe("App Services");
    expect(categoryLabel("operationalBucketBackup")).toBe("Bucket backups");
    expect(categoryLabel("operationalClusterBackup")).toBe("Cluster backups");
    expect(categoryLabel("dataTransferStandard")).toBe("Data transfer");
    expect(categoryLabel("privateEndpointsStandard")).toBe("Private endpoints");
    expect(categoryLabel("dataApiStandard")).toBe("Data API");
    expect(categoryLabel("analyticsCompute")).toBe("Analytics compute");
    expect(categoryLabel("analyticsStorage")).toBe("Analytics storage");
    expect(categoryLabel("analyticsClusterBackup")).toBe("Analytics backups");
  });

  it("derives labels for analytics* and aiServices* prefixes", () => {
    expect(categoryLabel("analyticsDataTransfer")).toBe("Analytics data transfer");
    expect(categoryLabel("aiServicesModelHosting")).toBe("AI model hosting");
  });

  it("humanises unknown categories", () => {
    expect(categoryLabel("somethingNewStandard")).toBe("Something new standard");
    expect(categoryLabel("")).toBe("Uncategorised");
  });

  it("assigns stable, distinct colours", () => {
    expect(categoryColor("operationalComputeAndStorage")).toBe(
      categoryColor("operationalComputeAndStorage"),
    );
    expect(categoryColor("operationalComputeAndStorage")).not.toBe(
      categoryColor("appServicesComputeAndStorage"),
    );
    expect(categoryColor("analyticsCompute")).not.toBe(categoryColor("analyticsStorage"));
    expect(categoryColor("unknownThing")).toMatch(/^#[0-9a-f]{6}$/);
    expect(categoryColor("unknownThing")).toBe(categoryColor("unknownThing"));
  });

  it("orders known categories first, then alphabetical", () => {
    expect(
      sortCategories(["zeta", "dataTransferStandard", "alpha", "operationalComputeAndStorage"]),
    ).toEqual(["operationalComputeAndStorage", "dataTransferStandard", "alpha", "zeta"]);
  });
});
