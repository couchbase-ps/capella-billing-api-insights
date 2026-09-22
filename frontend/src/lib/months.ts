import type { DateRange } from "../api/hooks";
import { toIsoDate } from "./dates";

/** `YYYY-MM` of a date in UTC. */
export function toIsoMonth(date: Date): string {
  return date.toISOString().slice(0, 7);
}

export function addMonths(month: string, delta: number): string {
  const [year, mon] = month.split("-").map(Number);
  const date = new Date(Date.UTC(year ?? 1970, (mon ?? 1) - 1 + delta, 1));
  return toIsoMonth(date);
}

/** Default insights window: the last `count` months up to and including the previous month. */
export function lastMonths(count: number, now = new Date()): { from: string; to: string } {
  const current = toIsoMonth(now);
  const to = addMonths(current, -1);
  return { from: addMonths(to, -(count - 1)), to };
}

/**
 * Whole-month date range for the report API: first day of `from` to the last day of `to`,
 * never later than yesterday (UTC) because Capella publishes a day's usage the next day.
 */
export function monthRangeToDates(from: string, to: string, now = new Date()): DateRange {
  const [fy, fm] = from.split("-").map(Number);
  const [ty, tm] = to.split("-").map(Number);
  const start = new Date(Date.UTC(fy ?? 1970, (fm ?? 1) - 1, 1));
  const end = new Date(Date.UTC(ty ?? 1970, tm ?? 1, 0));
  const yesterday = new Date(now.getTime());
  yesterday.setUTCDate(yesterday.getUTCDate() - 1);
  const clipped = end.getTime() > yesterday.getTime() ? yesterday : end;
  return { from: toIsoDate(start), to: toIsoDate(clipped) };
}
