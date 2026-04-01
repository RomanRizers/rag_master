import type { SearchResult } from "../types";

export type SortMode = "relevance_desc" | "relevance_asc" | "content_length_desc" | "content_length_asc";

export function normalizeKeyword(value: string): string {
  return value.trim().toLowerCase();
}

export function extractKeywords(results: SearchResult[]): string[] {
  const map = new Map<string, string>();

  for (const result of results) {
    for (const keyword of result.payload.keywords ?? []) {
      const normalized = normalizeKeyword(keyword);
      if (!normalized) {
        continue;
      }
      if (!map.has(normalized)) {
        map.set(normalized, keyword.trim());
      }
    }
  }

  return [...map.values()].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
}

export function filterByKeywords(results: SearchResult[], selected: string[]): SearchResult[] {
  if (selected.length === 0) {
    return results;
  }

  const expected = new Set(selected.map(normalizeKeyword));

  return results.filter((result) => {
    const keywords = new Set((result.payload.keywords ?? []).map(normalizeKeyword));
    for (const item of expected) {
      if (!keywords.has(item)) {
        return false;
      }
    }
    return true;
  });
}

function contentLength(result: SearchResult): number {
  return result.payload.content?.trim().length ?? 0;
}

export function sortResults(results: SearchResult[], mode: SortMode): SearchResult[] {
  const prepared = [...results];

  switch (mode) {
    case "relevance_asc":
      return prepared.sort((left, right) => left.score - right.score);
    case "content_length_desc":
      return prepared.sort((left, right) => contentLength(right) - contentLength(left));
    case "content_length_asc":
      return prepared.sort((left, right) => contentLength(left) - contentLength(right));
    case "relevance_desc":
    default:
      return prepared.sort((left, right) => right.score - left.score);
  }
}
