import type { JSX, ReactNode } from "react";

/** Dense table primitives; numeric cells get `num` for right alignment + tabular figures. */
export function Table({ children }: { children: ReactNode }): JSX.Element {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-body-sm">{children}</table>
    </div>
  );
}

export function Th({
  children,
  num = false,
  onClick,
  active = false,
}: {
  children: ReactNode;
  num?: boolean;
  onClick?: () => void;
  active?: boolean;
}): JSX.Element {
  const align = num ? "text-right" : "text-left";
  const base = `border-b border-border-strong px-2 py-1.5 text-label-upper uppercase text-text-muted ${align}`;
  if (!onClick) {
    return <th className={base}>{children}</th>;
  }
  return (
    <th className={base} aria-sort={active ? "descending" : undefined}>
      <button
        type="button"
        onClick={onClick}
        className={`cursor-pointer hover:text-on-surface ${active ? "text-on-surface-strong" : ""}`}
      >
        {children}
        {active ? " ↓" : ""}
      </button>
    </th>
  );
}

export function Td({
  children,
  num = false,
  muted = false,
}: {
  children: ReactNode;
  num?: boolean;
  muted?: boolean;
}): JSX.Element {
  return (
    <td
      className={`border-b border-border px-2 py-1.5 ${num ? "text-right tabular-nums" : ""} ${muted ? "text-text-muted" : ""}`}
    >
      {children}
    </td>
  );
}
