import type { JSX, ReactNode } from "react";
import { Link } from "react-router-dom";
import type { StateTone } from "../lib/state";
import { stateTone } from "../lib/state";

export function Card({
  title,
  action,
  children,
  className = "",
}: {
  title?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}): JSX.Element {
  return (
    <section className={`rounded-md border border-border bg-surface shadow-float ${className}`}>
      {(title || action) && (
        <header className="flex items-center justify-between gap-2 border-b border-border px-4 py-2.5">
          {title ? <h2 className="text-heading-sm">{title}</h2> : <span />}
          {action}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function PageHeader({
  title,
  subtitle,
  action,
  backTo,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
  backTo?: { to: string; label: string };
}): JSX.Element {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        {backTo && (
          <Link to={backTo.to} className="text-caption text-link hover:underline">
            ← {backTo.label}
          </Link>
        )}
        <h1 className="text-heading-lg text-on-surface-strong">{title}</h1>
        {subtitle && <p className="text-caption text-text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

const TONE_CLASSES: Record<StateTone, string> = {
  good: "bg-green-50 text-success-text border-green-200",
  off: "bg-surface-alt text-text-muted border-border-strong",
  bad: "bg-red-50 text-error-text border-red-200",
  warn: "bg-surface-accent text-warning-text border-amber-200",
};

export function StateBadge({ state }: { state: string | null | undefined }): JSX.Element {
  const tone = stateTone(state);
  return (
    <span
      className={`inline-block rounded-full border px-2 py-0.5 text-label-sm ${TONE_CLASSES[tone]}`}
    >
      {state ?? "unknown"}
    </span>
  );
}

export function Tag({ children }: { children: ReactNode }): JSX.Element {
  return (
    <span className="ml-1 inline-block rounded-sm border border-border bg-surface-alt px-1.5 py-0.5 text-label-upper uppercase text-text-muted">
      {children}
    </span>
  );
}

export function ScopeBadge({ scope }: { scope: string }): JSX.Element {
  const label =
    scope === "appservice" ? "App Service" : scope === "analytics" ? "Analytics" : "Cluster";
  return (
    <span className="inline-block rounded-sm border border-border px-1.5 py-0.5 text-label-sm text-text-muted">
      {label}
    </span>
  );
}

export function Facts({ items }: { items: { label: string; value: ReactNode }[] }): JSX.Element {
  return (
    <dl className="grid grid-cols-2 gap-x-6 gap-y-2 md:grid-cols-4">
      {items.map((item) => (
        <div key={item.label}>
          <dt className="text-label-upper uppercase text-text-muted">{item.label}</dt>
          <dd className="text-body tabular-nums">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function LoadingRow({ label = "Loading…" }: { label?: string }): JSX.Element {
  return <p className="py-6 text-center text-caption text-text-muted">{label}</p>;
}

export function ErrorNote({ error }: { error: unknown }): JSX.Element {
  const message = error instanceof Error ? error.message : String(error);
  return (
    <p
      role="alert"
      className="rounded-sm border border-error/40 bg-red-50 px-3 py-2 text-body-sm text-error-text"
    >
      {message}
    </p>
  );
}

export function EmptyNote({ children }: { children: ReactNode }): JSX.Element {
  return <p className="py-6 text-center text-caption text-text-muted">{children}</p>;
}
