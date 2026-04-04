import { describe, expect, it } from "vitest";

import { ApiRequestError } from "../api/client";
import { appErrorCopy, resolveAppError } from "./appError";

describe("resolveAppError", () => {
  it("maps llm_unavailable to a friendly banner message", () => {
    const result = resolveAppError(new ApiRequestError("upstream failed", "llm_unavailable"), appErrorCopy.ru);

    expect(result.title).toBe("LLM недоступна");
    expect(result.message).toBe("Проверьте настройки провайдера и readiness backend.");
    expect(result.code).toBe("llm_unavailable");
  });

  it("maps parsing_failed to a user-facing upload message", () => {
    const result = resolveAppError(new ApiRequestError("parser crashed", "parsing_failed"), appErrorCopy.ru);

    expect(result.title).toBe("Документ не обработан");
    expect(result.message).toContain("Парсинг файла");
  });

  it("falls back to backend message for unknown api codes", () => {
    const result = resolveAppError(new ApiRequestError("custom failure", "custom_code"), appErrorCopy.en);

    expect(result.title).toBe("Error");
    expect(result.message).toBe("custom failure");
    expect(result.code).toBe("custom_code");
  });
});
