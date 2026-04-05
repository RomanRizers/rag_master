import { afterEach, describe, expect, it, vi } from "vitest";

import { searchParagraphs } from "./client";

describe("api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns parsed response on success", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ results: [{ id: "1", score: 0.5, payload: {} }], total: 1 }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );

    vi.stubGlobal("fetch", fetchMock);

    const result = await searchParagraphs({ query: "hello", top_k: 2, filters: { knowledge_bases: ["policies"] } });

    expect(fetchMock).toHaveBeenCalledWith("/api/searching", expect.any(Object));
    expect(result.total).toBe(1);
    expect(result.results).toHaveLength(1);
  });

  it("throws ApiRequestError with backend code/message", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ error: { code: "storage_error", message: "Qdrant unavailable" } }), {
        status: 503,
        headers: { "Content-Type": "application/json" }
      })
    );

    vi.stubGlobal("fetch", fetchMock);

    await expect(searchParagraphs({ query: "hello", top_k: 2 })).rejects.toMatchObject({
      code: "storage_error",
      message: "Qdrant unavailable"
    });
  });

  it("falls back to HTTP status when response is not JSON", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response("Service unavailable", {
        status: 503,
        headers: { "Content-Type": "text/plain" }
      })
    );

    vi.stubGlobal("fetch", fetchMock);

    await expect(searchParagraphs({ query: "hello", top_k: 2 })).rejects.toMatchObject({
      code: "request_error",
      message: "HTTP 503"
    });
  });
});
