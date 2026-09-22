const dateFormatter = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "short",
  day: "numeric",
  timeZone: "UTC",
});
const dateTimeFormatter = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
  timeZone: "UTC",
  timeZoneName: "short",
});
const shortDayFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  timeZone: "UTC",
});

function parse(value: string): Date | null {
  const date = new Date(value.length === 10 ? `${value}T00:00:00Z` : value);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** `YYYY-MM-DD` -> "Aug 1, 2026". Invalid or empty input renders as an em-dash. */
export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const date = parse(value);
  return date ? dateFormatter.format(date) : value;
}

/** ISO timestamp -> "Sep 22, 2026, 14:03 UTC". */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const date = parse(value);
  return date ? dateTimeFormatter.format(date) : value;
}

/** Axis ticks: `YYYY-MM-DD` -> "Aug 1"; `YYYY-MM` -> "Aug 2026". */
export function formatPeriod(period: string): string {
  if (/^\d{4}-\d{2}$/.test(period)) {
    const date = parse(`${period}-01`);
    return date
      ? new Intl.DateTimeFormat("en-US", {
          month: "short",
          year: "numeric",
          timeZone: "UTC",
        }).format(date)
      : period;
  }
  const date = parse(period);
  return date ? shortDayFormatter.format(date) : period;
}

export function toIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function addDays(date: Date, days: number): Date {
  const copy = new Date(date.getTime());
  copy.setUTCDate(copy.getUTCDate() + days);
  return copy;
}

export function formatRelativeAge(iso: string | null | undefined, now = new Date()): string {
  if (!iso) {
    return "—";
  }
  const date = parse(iso);
  if (!date) {
    return iso;
  }
  const minutes = Math.max(0, Math.round((now.getTime() - date.getTime()) / 60000));
  if (minutes < 1) {
    return "just now";
  }
  if (minutes < 60) {
    return `${minutes} min ago`;
  }
  const hours = Math.round(minutes / 60);
  if (hours < 48) {
    return `${hours} h ago`;
  }
  return `${Math.round(hours / 24)} d ago`;
}
