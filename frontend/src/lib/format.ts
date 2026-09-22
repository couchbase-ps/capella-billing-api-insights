export const ABSENT = "—";

const creditFormatter = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const integerFormatter = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const percentFormatter = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

/** Credits with 2 decimals and no unit (credits are the default unit); null renders as an em-dash, never as 0. */
export function formatCredits(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return ABSENT;
  }
  return creditFormatter.format(value);
}

export function formatCurrency(value: number | null | undefined, currency = "USD"): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return ABSENT;
  }
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(value);
  } catch {
    return `${creditFormatter.format(value)} ${currency}`;
  }
}

export function formatInteger(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return ABSENT;
  }
  return integerFormatter.format(value);
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return ABSENT;
  }
  return `${percentFormatter.format(value)}%`;
}

/** Picks credits or currency depending on the org billing mode; null stays an em-dash. */
export function formatSpend(
  credits: number | null | undefined,
  currency: number | null | undefined,
  currencyCode = "USD",
): string {
  if (credits !== null && credits !== undefined) {
    return formatCredits(credits);
  }
  if (currency !== null && currency !== undefined) {
    return formatCurrency(currency, currencyCode);
  }
  return ABSENT;
}

export function formatMib(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return ABSENT;
  }
  if (value >= 1024) {
    return `${creditFormatter.format(value / 1024)} GiB`;
  }
  return `${integerFormatter.format(value)} MiB`;
}
