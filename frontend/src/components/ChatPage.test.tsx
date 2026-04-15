import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ApiRequestError } from "../api/client";
import { ChatPage } from "./ChatPage";

type QueryState = {
  sessions?: unknown;
  messages?: unknown;
  sessionsError?: unknown;
};

const queryState: QueryState = {};

vi.mock("@tanstack/react-query", () => ({
  useQuery: ({ queryKey }: { queryKey: string[] }) => {
    const key = queryKey[0];
    if (key === "chat-sessions") {
      return {
        data: queryState.sessions,
        isError: Boolean(queryState.sessionsError),
        error: queryState.sessionsError ?? null
      };
    }
    if (key === "chat-messages") {
      return {
        data: queryState.messages,
        isError: false,
        error: null
      };
    }
    if (key === "knowledge-bases") {
      return {
        data: { knowledge_bases: [{ name: "policies", document_count: 2 }] },
        isError: false,
        error: null
      };
    }
    return {
      data: undefined,
      isError: false,
      error: null
    };
  },
  useMutation: () => ({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    error: null
  }),
  useQueryClient: () => ({
    invalidateQueries: vi.fn()
  })
}));

describe("ChatPage", () => {
  it("renders sessions, messages and assistant citations", () => {
    queryState.sessions = {
      sessions: [
        {
          session_id: "12345678-aaaa-bbbb-cccc-1234567890ab",
          created_at: "2026-04-04T11:00:00Z",
          message_count: 2,
          last_message_at: "2026-04-04T11:05:00Z"
        }
      ]
    };
    queryState.messages = {
      session_id: "12345678-aaaa-bbbb-cccc-1234567890ab",
      messages: [
        {
          id: "msg-1",
          role: "user",
          content: "Что в политике отпусков?",
          citations: [],
          created_at: "2026-04-04T11:04:00Z"
        },
        {
          id: "msg-2",
          role: "assistant",
          content: "В документе описан базовый лимит отпусков.",
          citations: [
            {
              document_id: "doc-1",
              document_name: "handbook.pdf",
              chunk_id: "chunk-1",
              page: 4,
              snippet: "Employees receive 28 calendar days of paid leave."
            }
          ],
          created_at: "2026-04-04T11:05:00Z"
        }
      ]
    };

    const markup = renderToStaticMarkup(
      <MemoryRouter>
        <ChatPage />
      </MemoryRouter>
    );

    expect(markup).toContain("12345678");
    expect(markup).toContain("Что в политике отпусков?");
    expect(markup).toContain("В документе описан базовый лимит отпусков.");
    expect(markup).toContain("handbook.pdf");
    expect(markup).toContain("page 4");
    expect(markup).toContain("Employees receive 28 calendar days of paid leave.");
  });

  it("shows a friendly llm_unavailable banner", () => {
    queryState.sessions = undefined;
    queryState.messages = undefined;
    queryState.sessionsError = new ApiRequestError("provider unavailable", "llm_unavailable");

    const markup = renderToStaticMarkup(
      <MemoryRouter>
        <ChatPage />
      </MemoryRouter>
    );

    expect(markup).toContain("LLM недоступна");
    expect(markup).toContain("llm_unavailable");
  });
});
