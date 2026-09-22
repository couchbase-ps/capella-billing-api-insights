import { describe, expect, it } from "vitest";
import { addMonths, lastMonths, monthRangeToDates } from "../lib/months";

describe("months", () => {
  it("adds and subtracts months across year boundaries", () => {
    expect(addMonths("2026-01", -1)).toBe("2025-12");
    expect(addMonths("2026-11", 2)).toBe("2027-01");
  });

  it("defaults to the last N full months ending with the previous month", () => {
    expect(lastMonths(3, new Date("2026-09-22T10:00:00Z"))).toEqual({
      from: "2026-06",
      to: "2026-08",
    });
  });

  it("expands months to whole-month dates and clips the end to yesterday", () => {
    const now = new Date("2026-09-22T10:00:00Z");
    expect(monthRangeToDates("2026-06", "2026-08", now)).toEqual({
      from: "2026-06-01",
      to: "2026-08-31",
    });
    expect(monthRangeToDates("2026-07", "2026-09", now)).toEqual({
      from: "2026-07-01",
      to: "2026-09-21",
    });
  });
});

describe("reportDefaultRange", () => {
  it("spans the first day of the previous month to the last day of the current month", async () => {
    const { reportDefaultRange } = await import("../lib/months");
    expect(reportDefaultRange(new Date("2026-09-22T10:00:00Z"))).toEqual({
      from: "2026-08-01",
      to: "2026-09-30",
    });
    expect(reportDefaultRange(new Date("2026-01-05T10:00:00Z"))).toEqual({
      from: "2025-12-01",
      to: "2026-01-31",
    });
  });
});
