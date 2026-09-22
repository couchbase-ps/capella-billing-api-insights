import type { JSX } from "react";

export interface SegmentOption<T extends string> {
  value: T;
  label: string;
}

/** A toggle button group: exactly one option is active. */
export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: SegmentOption<T>[];
  value: T;
  onChange: (value: T) => void;
  label: string;
}): JSX.Element {
  return (
    <fieldset
      aria-label={label}
      className="m-0 inline-flex overflow-hidden rounded-sm border border-border-strong p-0 text-label-sm"
    >
      {options.map((option, index) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(option.value)}
            className={`px-3 py-1.5 ${index > 0 ? "border-l border-border-strong" : ""} ${
              active ? "bg-primary text-on-fill" : "bg-surface text-on-surface hover:bg-surface-alt"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </fieldset>
  );
}
