import type { DateRange } from "../api/hooks";
import { addDays, toIsoDate } from "./dates";

export type RangeDays = 7 | 30 | 90;

export const RANGE_OPTIONS: { days: RangeDays; label: string }[] = [
  { days: 7, label: "Last 7 days" },
  { days: 30, label: "Last 30 days" },
  { days: 90, label: "Last 90 days" },
];

/** Last N full days ending yesterday (UTC), matching the backend default window. */
export function lastDays(days: RangeDays, now = new Date()): DateRange {
  const yesterday = addDays(now, -1);
  return { from: toIsoDate(addDays(yesterday, -(days - 1))), to: toIsoDate(yesterday) };
}
