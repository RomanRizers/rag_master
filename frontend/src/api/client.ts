import type {
  ApiErrorResponse,
  ChatMessageRequest,
  ChatMessagesResponse,
  ChatSendMessageResponse,
  ChatSessionCreateResponse,
  ChatSessionListResponse,
  DocumentIndexResponse,
  DocumentIndexStatsResponse,
  DocumentListResponse,
  DocumentUploadResponse,
  JobListResponse,
  SearchRequest,
  SearchResponse
} from "../types";

export class ApiRequestError extends Error {
  readonly code: string;

  constructor(message: string, code = "request_error") {
    super(message);
    this.code = code;
  }
}

async function parseError(response: Response): Promise<never> {
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
  throw new ApiRequestError("Unexpected response");
}

async function apiGet<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    return parseError(response);
  }
  return (await response.json()) as T;
}

async function apiPostJson<TResponse, TRequest>(url: string, payload: TRequest): Promise<TResponse> {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    return parseError(response);
  }
  return (await response.json()) as TResponse;
}

export async function searchParagraphs(payload: SearchRequest): Promise<SearchResponse> {
  return apiPostJson<SearchResponse, SearchRequest>("/api/searching", payload);
}

export async function listDocuments(): Promise<DocumentListResponse> {
  return apiGet<DocumentListResponse>("/api/documents");
}

export async function uploadDocument(file: File, sourceName?: string, tags?: string[]): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.set("file", file);
  if (sourceName && sourceName.trim()) {
    formData.set("source_name", sourceName.trim());
  }
  for (const tag of tags ?? []) {
    if (tag.trim()) {
      formData.append("tags", tag.trim());
    }
  }
  const response = await fetch("/api/documents/upload", {
    method: "POST",
    body: formData
  });
  if (!response.ok) {
    return parseError(response);
  }
  return (await response.json()) as DocumentUploadResponse;
}

export async function indexDocument(documentId: string): Promise<DocumentIndexResponse> {
  const response = await fetch(`/api/documents/${documentId}/index`, {
    method: "POST"
  });
  if (!response.ok) {
    return parseError(response);
  }
  return (await response.json()) as DocumentIndexResponse;
}

export async function getDocumentIndexStats(documentId: string): Promise<DocumentIndexStatsResponse> {
  return apiGet<DocumentIndexStatsResponse>(`/api/documents/${documentId}/index-stats`);
}

export async function listJobs(status?: string, documentId?: string): Promise<JobListResponse> {
  const params = new URLSearchParams();
  if (status) {
    params.set("status", status);
  }
  if (documentId) {
    params.set("document_id", documentId);
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return apiGet<JobListResponse>(`/api/jobs${suffix}`);
}

export async function createChatSession(): Promise<ChatSessionCreateResponse> {
  const response = await fetch("/api/chat/sessions", {
    method: "POST"
  });
  if (!response.ok) {
    return parseError(response);
  }
  return (await response.json()) as ChatSessionCreateResponse;
}

export async function listChatSessions(): Promise<ChatSessionListResponse> {
  return apiGet<ChatSessionListResponse>("/api/chat/sessions");
}

export async function getChatMessages(sessionId: string): Promise<ChatMessagesResponse> {
  return apiGet<ChatMessagesResponse>(`/api/chat/sessions/${sessionId}/messages`);
}

export async function sendChatMessage(
  sessionId: string,
  payload: ChatMessageRequest
): Promise<ChatSendMessageResponse> {
  return apiPostJson<ChatSendMessageResponse, ChatMessageRequest>(
    `/api/chat/sessions/${sessionId}/messages`,
    payload
  );
}

export type StreamCallbacks = {
  onDelta?: (value: string) => void;
  onCitations?: (items: ChatSendMessageResponse["assistant_message"]["citations"]) => void;
};

export async function streamChatMessage(
  sessionId: string,
  payload: ChatMessageRequest,
  callbacks: StreamCallbacks
): Promise<void> {
  const response = await fetch(`/api/chat/sessions/${sessionId}/messages/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    return parseError(response);
  }
  if (!response.body) {
    throw new ApiRequestError("SSE stream is not available");
  }

  const decoder = new TextDecoder();
  const reader = response.body.getReader();
  let buffer = "";
  let eventName = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });

    let separatorIndex = buffer.indexOf("\n\n");
    while (separatorIndex >= 0) {
      const chunk = buffer.slice(0, separatorIndex);
      buffer = buffer.slice(separatorIndex + 2);
      for (const line of chunk.split("\n")) {
        if (line.startsWith("event:")) {
          eventName = line.slice(6).trim();
        }
        if (line.startsWith("data:")) {
          const raw = line.slice(5).trim();
          try {
            const payloadData = JSON.parse(raw) as { text?: string; items?: ChatSendMessageResponse["assistant_message"]["citations"] };
            if (eventName === "delta" && payloadData.text) {
              callbacks.onDelta?.(payloadData.text);
            } else if (eventName === "citations" && payloadData.items) {
              callbacks.onCitations?.(payloadData.items);
            }
          } catch {
            // ignore malformed line in stream
          }
        }
      }
      separatorIndex = buffer.indexOf("\n\n");
    }
  }
}
