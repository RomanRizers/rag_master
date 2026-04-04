import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { ApiRequestError } from "../api/client";
import { DocumentsPage } from "./DocumentsPage";

type QueryState = {
  documents?: unknown;
  jobs?: unknown;
  documentsError?: unknown;
};

const queryState: QueryState = {};

vi.mock("@tanstack/react-query", () => ({
  useQuery: ({ queryKey }: { queryKey: string[] }) => {
    const key = queryKey[0];
    if (key === "documents") {
      return {
        data: queryState.documents,
        isError: Boolean(queryState.documentsError),
        error: queryState.documentsError ?? null
      };
    }
    if (key === "jobs") {
      return {
        data: queryState.jobs,
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

describe("DocumentsPage", () => {
  it("renders uploaded documents and recent indexing jobs", () => {
    queryState.documents = {
      documents: [
        {
          document_id: "doc-1",
          file_name: "handbook.pdf",
          mime_type: "application/pdf",
          size_bytes: 2048,
          status: "indexed",
          source_name: "HR Handbook",
          tags: ["hr", "policy"],
          created_at: "2026-04-04T10:00:00Z"
        }
      ]
    };
    queryState.jobs = {
      jobs: [
        {
          job_id: "job-1",
          document_id: "doc-1",
          status: "done",
          progress: 100,
          attempt: 1,
          error_code: null,
          error_message: null,
          started_at: "2026-04-04T10:01:00Z",
          finished_at: "2026-04-04T10:02:00Z"
        }
      ]
    };

    const markup = renderToStaticMarkup(<DocumentsPage />);

    expect(markup).toContain("handbook.pdf");
    expect(markup).toContain("hr, policy");
    expect(markup).toContain("done");
    expect(markup).toContain("100%");
    expect(markup).toContain("job-1");
  });

  it("shows a friendly parsing error banner", () => {
    queryState.documents = undefined;
    queryState.jobs = { jobs: [] };
    queryState.documentsError = new ApiRequestError("bad document", "parsing_failed");

    const markup = renderToStaticMarkup(<DocumentsPage />);

    expect(markup).toContain("Документ не обработан");
    expect(markup).toContain("parsing_failed");
  });
});
