import { describe, expect, it } from "vitest";
import { formatDate, formatDateTime, formatPeriod } from "../lib/dates";
import {
  formatCredits,
  formatCurrency,
  formatInteger,
  formatPercent,
  formatSpend,
} from "../lib/format";
import { lastDays } from "../lib/ranges";

describe("format helpers", () => {
  it("formats credits with two decimals and no unit", () => {
    expect(formatCredits(12.5)).toBe("12.50");
    expect(formatCredits(1234567.891)).toBe("1,234,567.89");
    expect(formatCredits(0)).toBe("0.00");
  });

  it("renders null as an em-dash, never as zero", () => {
    expect(formatCredits(null)).toBe("—");
    expect(formatCurrency(null)).toBe("—");
    expect(formatPercent(null)).toBe("—");
    expect(formatInteger(undefined)).toBe("—");
    expect(formatSpend(null, null)).toBe("—");
  });

  it("formats currency with Intl", () => {
    expect(formatCurrency(1234.5, "USD")).toBe("$1,234.50");
    expect(formatCurrency(10, "EUR")).toBe("€10.00");
  });

  it("prefers credits over currency in formatSpend", () => {
    expect(formatSpend(5, 100)).toBe("5.00");
    expect(formatSpend(null, 100, "USD")).toBe("$100.00");
  });

  it("formats percentages with one decimal", () => {
    expect(formatPercent(44.44)).toBe("44.4%");
  });
});

describe("date helpers", () => {
  it("formats YYYY-MM-DD dates in UTC", () => {
    expect(formatDate("2026-08-01")).toBe("Aug 1, 2026");
    expect(formatDate(null)).toBe("—");
  });

  it("formats timestamps in UTC", () => {
    expect(formatDateTime("2026-09-22T06:04:12Z")).toContain("Sep 22, 2026");
    expect(formatDateTime("2026-09-22T06:04:12Z")).toContain("06:04");
  });

  it("formats chart periods for day and month granularity", () => {
    expect(formatPeriod("2026-08-01")).toBe("Aug 1");
    expect(formatPeriod("2026-08")).toBe("Aug 2026");
  });

  it("computes the last N full days ending yesterday", () => {
    const now = new Date("2026-09-22T10:00:00Z");
    expect(lastDays(7, now)).toEqual({ from: "2026-09-15", to: "2026-09-21" });
    expect(lastDays(30, now)).toEqual({ from: "2026-08-23", to: "2026-09-21" });
  });
});
