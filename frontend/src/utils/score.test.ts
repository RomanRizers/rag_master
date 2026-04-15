import { describe, expect, it } from "vitest";

import { formatRawScore, formatRelevance } from "./score";

describe("score formatting", () => {
  it("formats relevance from cosine-like score", () => {
    expect(formatRelevance(0.8)).toBe("90.0%");
  });

  it("formats raw score", () => {
    expect(formatRawScore(0.8170706)).toBe("0.817071");
  });

  it("handles non-finite score", () => {
    expect(formatRelevance(undefined)).toBe("N/A");
    expect(formatRawScore(undefined)).toBe("N/A");
  });
});
