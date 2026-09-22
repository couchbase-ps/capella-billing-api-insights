// Capella billing category enum -> human label + stable colour. Colours come from the
// dataviz reference categorical palette (light mode, fixed slot order, never cycled).

const PALETTE = [
  "#2a78d6", // blue
  "#eb6834", // orange
  "#1baf7a", // aqua
  "#eda100", // yellow
  "#e87ba4", // magenta
  "#008300", // green
  "#4a3aa7", // violet
  "#e34948", // red
] as const;

interface CategoryMeta {
  label: string;
  color: string;
}

const KNOWN: Record<string, CategoryMeta> = {
  operationalComputeAndStorage: { label: "Compute & storage", color: PALETTE[0] },
  appServicesComputeAndStorage: { label: "App Services", color: PALETTE[1] },
  operationalBucketBackup: { label: "Bucket backups", color: PALETTE[2] },
  operationalClusterBackup: { label: "Cluster backups", color: PALETTE[3] },
  dataTransferStandard: { label: "Data transfer", color: PALETTE[4] },
  privateEndpointsStandard: { label: "Private endpoints", color: PALETTE[5] },
  dataApiStandard: { label: "Data API", color: PALETTE[6] },
};

const PREFIXES: { prefix: string; label: string; color: string }[] = [
  { prefix: "analytics", label: "Analytics", color: PALETTE[7] },
  { prefix: "aiServices", label: "AI", color: PALETTE[6] },
];

function humanize(camel: string): string {
  const spaced = camel.replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/[_-]+/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1).toLowerCase();
}

function hashSlot(key: string): number {
  let hash = 0;
  for (let i = 0; i < key.length; i += 1) {
    hash = (hash * 31 + key.charCodeAt(i)) >>> 0;
  }
  return hash % PALETTE.length;
}

export function categoryLabel(category: string): string {
  const known = KNOWN[category];
  if (known) {
    return known.label;
  }
  for (const { prefix, label } of PREFIXES) {
    if (category.startsWith(prefix)) {
      const rest = category.slice(prefix.length);
      return rest ? `${label} ${humanize(rest).toLowerCase()}` : label;
    }
  }
  return category ? humanize(category) : "Uncategorised";
}

export function categoryColor(category: string): string {
  const known = KNOWN[category];
  if (known) {
    return known.color;
  }
  for (const { prefix, color } of PREFIXES) {
    if (category.startsWith(prefix)) {
      return color;
    }
  }
  return PALETTE[hashSlot(category)] ?? PALETTE[0];
}

/** Stable ordering for legends and stacks: known categories first, then alphabetical. */
export function sortCategories(categories: Iterable<string>): string[] {
  const knownOrder = Object.keys(KNOWN);
  return Array.from(new Set(categories)).sort((a, b) => {
    const ia = knownOrder.indexOf(a);
    const ib = knownOrder.indexOf(b);
    if (ia !== -1 || ib !== -1) {
      return (ia === -1 ? knownOrder.length : ia) - (ib === -1 ? knownOrder.length : ib);
    }
    return a.localeCompare(b);
  });
}
