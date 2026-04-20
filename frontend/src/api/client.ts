import type {
  ApiErrorResponse,
  ChatMessageRequest,
  ChatMessagesResponse,
  ChatSendMessageResponse,
  ChatSessionCreateResponse,
  ChatSessionDeleteResponse,
  ChatSessionListResponse,
  DocumentDeleteResponse,
  DocumentChunksResponse,
  DocumentIndexResponse,
  DocumentIndexStatsResponse,
  DocumentListResponse,
  KnowledgeBaseCreateResponse,
  KnowledgeBaseListResponse,
  DocumentUploadResponse,
  JobListResponse,
  KnowledgeBaseDeleteResponse,
  KnowledgeBaseReindexResponse,
  KnowledgeBaseResponse,
  KnowledgeBaseUpdateRequest,
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

async function apiDelete<T>(url: string): Promise<T> {
  const response = await fetch(url, {
    method: "DELETE"
  });
  if (!response.ok) {
    return parseError(response);
  }
  return (await response.json()) as T;
}

export async function searchParagraphs(payload: SearchRequest): Promise<SearchResponse> {
  return apiPostJson<SearchResponse, SearchRequest>("/api/searching", payload);
}

export async function listDocuments(): Promise<DocumentListResponse> {
  return apiGet<DocumentListResponse>("/api/documents");
}

export async function listKnowledgeBases(): Promise<KnowledgeBaseListResponse> {
  return apiGet<KnowledgeBaseListResponse>("/api/knowledge-bases");
}

export async function createKnowledgeBase(name: string): Promise<KnowledgeBaseCreateResponse> {
  return apiPostJson<KnowledgeBaseCreateResponse, { name: string }>("/api/knowledge-bases", {
    name
  });
}

export async function renameKnowledgeBase(currentName: string, name: string): Promise<KnowledgeBaseResponse> {
  return updateKnowledgeBase(currentName, { name });
}

export async function updateKnowledgeBase(
  currentName: string,
  payload: KnowledgeBaseUpdateRequest
): Promise<KnowledgeBaseResponse> {
  const response = await fetch(`/api/knowledge-bases/${encodeURIComponent(currentName)}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    return parseError(response);
  }
  return (await response.json()) as KnowledgeBaseResponse;
}

export async function deleteKnowledgeBase(name: string): Promise<KnowledgeBaseDeleteResponse> {
  return apiDelete<KnowledgeBaseDeleteResponse>(`/api/knowledge-bases/${encodeURIComponent(name)}`);
}

export async function reindexKnowledgeBase(name: string): Promise<KnowledgeBaseReindexResponse> {
  const response = await fetch(`/api/knowledge-bases/${encodeURIComponent(name)}/reindex`, {
    method: "POST"
  });
  if (!response.ok) {
    return parseError(response);
  }
  return (await response.json()) as KnowledgeBaseReindexResponse;
}

export async function uploadDocument(
  file: File,
  sourceName?: string,
  tags?: string[],
  knowledgeBase?: string
): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.set("file", file);
  if (sourceName && sourceName.trim()) {
    formData.set("source_name", sourceName.trim());
  }
  if (knowledgeBase && knowledgeBase.trim()) {
    formData.set("knowledge_base", knowledgeBase.trim());
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

export async function indexDocument(documentId: string, delimiters?: string[]): Promise<DocumentIndexResponse> {
  const hasDelimiters = delimiters && delimiters.length > 0;
  const response = await fetch(`/api/documents/${documentId}/index`, {
    method: "POST",
    ...(hasDelimiters && {
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ delimiters }),
    }),
  });
  if (!response.ok) {
    return parseError(response);
  }
  return (await response.json()) as DocumentIndexResponse;
}

export async function getDocumentIndexStats(documentId: string): Promise<DocumentIndexStatsResponse> {
  return apiGet<DocumentIndexStatsResponse>(`/api/documents/${documentId}/index-stats`);
}

export async function getDocumentChunks(documentId: string): Promise<DocumentChunksResponse> {
  return apiGet<DocumentChunksResponse>(`/api/documents/${documentId}/chunks`);
}

export async function deleteDocument(documentId: string): Promise<DocumentDeleteResponse> {
  return apiDelete<DocumentDeleteResponse>(`/api/documents/${documentId}`);
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

export async function deleteChatSession(sessionId: string): Promise<ChatSessionDeleteResponse> {
  return apiDelete<ChatSessionDeleteResponse>(`/api/chat/sessions/${sessionId}`);
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
  onError?: (code: string, message: string) => void;
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

  try {
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
              const payloadData = JSON.parse(raw) as {
                text?: string;
                items?: ChatSendMessageResponse["assistant_message"]["citations"];
                code?: string;
                message?: string;
              };
              if (eventName === "delta" && payloadData.text) {
                callbacks.onDelta?.(payloadData.text);
              } else if (eventName === "citations" && payloadData.items) {
                callbacks.onCitations?.(payloadData.items);
              } else if (eventName === "error") {
                callbacks.onError?.(payloadData.code ?? "stream_error", payloadData.message ?? "Stream error");
                return;
              }
            } catch {
              // ignore malformed SSE line
            }
          }
        }
        separatorIndex = buffer.indexOf("\n\n");
      }
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : "Network error";
    callbacks.onError?.("network_error", message);
  }
}
