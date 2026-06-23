export function normalizeCategoryName(name: string): string {
  return name.trim();
}

export function isDuplicateCategoryName(
  nodes: { id: string; name_ja: string }[],
  name: string,
  excludeId?: string,
): boolean {
  const normalized = normalizeCategoryName(name);
  return nodes.some(
    (node) =>
      node.id !== excludeId &&
      normalizeCategoryName(node.name_ja) === normalized,
  );
}
