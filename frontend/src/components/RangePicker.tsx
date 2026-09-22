import type { JSX } from "react";
import type { RangeDays } from "../lib/ranges";
import { RANGE_OPTIONS } from "../lib/ranges";

export function RangePicker({
  value,
  onChange,
}: {
  value: RangeDays;
  onChange: (days: RangeDays) => void;
}): JSX.Element {
  return (
    <fieldset aria-label="Date range" className="inline-flex rounded-sm border border-border">
      {RANGE_OPTIONS.map((option) => (
        <button
          key={option.days}
          type="button"
          aria-pressed={value === option.days}
          onClick={() => onChange(option.days)}
          className={`px-2.5 py-1 text-label-sm first:rounded-l-sm last:rounded-r-sm ${
            value === option.days
              ? "bg-on-surface-strong text-on-fill"
              : "bg-surface text-on-surface hover:bg-surface-alt"
          }`}
        >
          {option.label}
        </button>
      ))}
    </fieldset>
  );
}
