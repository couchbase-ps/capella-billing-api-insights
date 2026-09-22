import { Search, X } from "lucide-react";
import type { JSX } from "react";

/** Text filter input for list pages; clears with the × button. */
export function SearchBox({
  value,
  onChange,
  placeholder = "Search…",
  label = "Search",
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  label?: string;
}): JSX.Element {
  return (
    <div className="relative">
      <Search
        size={14}
        aria-hidden="true"
        className="pointer-events-none absolute top-1/2 left-2 -translate-y-1/2 text-text-muted"
      />
      <input
        type="search"
        aria-label={label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-64 rounded-sm border border-border-strong py-1 pr-7 pl-7 text-body-sm"
      />
      {value && (
        <button
          type="button"
          aria-label="Clear search"
          onClick={() => onChange("")}
          className="absolute top-1/2 right-1.5 -translate-y-1/2 text-text-muted hover:text-on-surface"
        >
          <X size={14} aria-hidden="true" />
        </button>
      )}
    </div>
  );
}
