import { describe, expect, it } from "vitest";

import { parseThemeMode, resolveTheme } from "../theme";

describe("theme utilities", () => {
  it("parses theme mode with fallback", () => {
    expect(parseThemeMode("light")).toBe("light");
    expect(parseThemeMode("dark")).toBe("dark");
    expect(parseThemeMode("system")).toBe("system");
    expect(parseThemeMode("unknown")).toBe("system");
    expect(parseThemeMode(null)).toBe("system");
  });

  it("resolves system mode using media preference", () => {
    expect(resolveTheme("system", true)).toBe("dark");
    expect(resolveTheme("system", false)).toBe("light");
  });

  it("returns explicit mode directly", () => {
    expect(resolveTheme("dark", false)).toBe("dark");
    expect(resolveTheme("light", true)).toBe("light");
  });
});
