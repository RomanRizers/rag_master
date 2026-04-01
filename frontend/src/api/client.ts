import type { ApiErrorResponse, SearchRequest, SearchResponse } from "../types";

export class ApiRequestError extends Error {
  readonly code: string;

  constructor(message: string, code = "request_error") {
    super(message);
    this.code = code;
  }
}

export async function searchParagraphs(payload: SearchRequest): Promise<SearchResponse> {
  const response = await fetch("/api/searching", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const fallback = `HTTP ${response.status}`;
    try {
      const errorPayload = (await response.json()) as ApiErrorResponse;
      throw new ApiRequestError(errorPayload.error.message || fallback, errorPayload.error.code);
    } catch (error) {
      if (error instanceof ApiRequestError) {
        throw error;
      }
      throw new ApiRequestError(fallback);
    }
  }

  return (await response.json()) as SearchResponse;
}
