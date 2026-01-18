export function formatNumber(n: number): string {
  if (n >= 1_000_000) {
    return (n / 1_000_000).toFixed(1) + "M";
  }
  if (n >= 1_000) {
    return (n / 1_000).toFixed(1) + "K";
  }
  return n.toString();
}

export function formatPercent(n: number): string {
  return (n * 100).toFixed(0) + "%";
}

export function formatConfidence(n: number): string {
  return (n * 100).toFixed(0) + "%";
}

export function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen - 3) + "...";
}

export function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

export function formatRelationshipType(type: string): string {
  // Convert camelCase to Title Case with spaces
  return type
    .replace(/([A-Z])/g, " $1")
    .replace(/^./, (s) => s.toUpperCase())
    .trim();
}
