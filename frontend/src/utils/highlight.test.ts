import { describe, expect, it } from "vitest";

import { buildHighlightSegments } from "./highlight";

describe("buildHighlightSegments", () => {
  it("returns whole string when query empty", () => {
    expect(buildHighlightSegments("Hello", "")).toEqual([{ text: "Hello", matched: false }]);
  });

  it("highlights case-insensitive matches", () => {
    expect(buildHighlightSegments("Hello HeLLo", "hello")).toEqual([
      { text: "Hello", matched: true },
      { text: " ", matched: false },
      { text: "HeLLo", matched: true }
    ]);
  });

  it("keeps unmatched parts", () => {
    expect(buildHighlightSegments("abc-xyz", "x")).toEqual([
      { text: "abc-", matched: false },
      { text: "x", matched: true },
      { text: "yz", matched: false }
    ]);
  });
});
