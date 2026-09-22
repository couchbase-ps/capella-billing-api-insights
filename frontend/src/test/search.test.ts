import { describe, expect, it } from "vitest";
import { filterBySearch, matchesSearch } from "../lib/search";

const items = [
  { name: "prod-eu", project: "Production", region: "eu-west-1", state: "healthy" },
  { name: "dev-sandbox", project: "Development", region: "eastus", state: "turnedOff" },
];
const fields = (c: (typeof items)[number]) => [c.name, c.project, c.region, c.state];

describe("search", () => {
  it("matches every word case-insensitively across the fields", () => {
    expect(filterBySearch(items, "PROD eu", fields).map((c) => c.name)).toEqual(["prod-eu"]);
    expect(filterBySearch(items, "turnedoff", fields).map((c) => c.name)).toEqual(["dev-sandbox"]);
    expect(filterBySearch(items, "prod eastus", fields)).toEqual([]);
  });

  it("treats a blank query as no filter and ignores null fields", () => {
    expect(filterBySearch(items, "   ", fields)).toHaveLength(2);
    expect(matchesSearch({ name: null }, "x", (c) => [c.name])).toBe(false);
  });
});
