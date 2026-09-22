/** Case-insensitive "every word matches somewhere" filter over the given string fields. */
export function matchesSearch<T>(item: T, query: string, fields: (item: T) => unknown[]): boolean {
  const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  if (words.length === 0) {
    return true;
  }
  const haystack = fields(item)
    .filter((value) => value !== null && value !== undefined)
    .map((value) => String(value).toLowerCase())
    .join(" ");
  return words.every((word) => haystack.includes(word));
}

export function filterBySearch<T>(items: T[], query: string, fields: (item: T) => unknown[]): T[] {
  return items.filter((item) => matchesSearch(item, query, fields));
}
