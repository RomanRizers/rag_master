import { describe, expect, it } from "vitest";

import { extractKeywords, filterByKeywords, sortResults } from "./search";
import type { SearchResult } from "../types";

const sample: SearchResult[] = [
  {
    id: "1",
    score: 0.9,
    payload: { content: "A", keywords: ["Gas", "Oil"] }
  },
  {
    id: "2",
    score: 0.5,
    payload: { content: "BBBB", keywords: ["oil", "Energy"] }
  },
  {
    id: "3",
    score: 0.7,
    payload: { content: "CC", keywords: [] }
  }
];

describe("search utils", () => {
  it("extracts unique keywords", () => {
    expect(extractKeywords(sample)).toEqual(["Energy", "Gas", "Oil"]);
  });

  it("filters by all selected keywords", () => {
    const filtered = filterByKeywords(sample, ["oil", "gas"]);
    expect(filtered.map((item) => item.id)).toEqual(["1"]);
  });

  it("sorts by relevance descending", () => {
    const sorted = sortResults(sample, "relevance_desc");
    expect(sorted.map((item) => item.id)).toEqual(["1", "3", "2"]);
  });

  it("sorts by content length ascending", () => {
    const sorted = sortResults(sample, "content_length_asc");
    expect(sorted.map((item) => item.id)).toEqual(["1", "3", "2"]);
  });
});
