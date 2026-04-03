import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  ApiRequestError,
  createChatSession,
  getChatMessages,
  listChatSessions,
  sendChatMessage,
  streamChatMessage
} from "../api/client";
import type { ChatCitation, ChatMessage } from "../types";

function formatIso(value?: string | null): string {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

export function ChatPage() {
  const queryClient = useQueryClient();

  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [message, setMessage] = useState("");
  const [topK, setTopK] = useState(5);
  const [docNamesText, setDocNamesText] = useState("");
  const [tagsText, setTagsText] = useState("");
  const [streaming, setStreaming] = useState(true);
  const [streamText, setStreamText] = useState("");
  const [streamCitations, setStreamCitations] = useState<ChatCitation[]>([]);

  const sessionsQuery = useQuery({
    queryKey: ["chat-sessions"],
    queryFn: listChatSessions,
    refetchInterval: 5000
  });

  const messagesQuery = useQuery({
    queryKey: ["chat-messages", activeSessionId],
    queryFn: () => getChatMessages(activeSessionId),
    enabled: Boolean(activeSessionId)
  });

  const createSessionMutation = useMutation({
    mutationFn: createChatSession,
    onSuccess: (payload) => {
      setActiveSessionId(payload.session_id);
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
    }
  });

  const sendMutation = useMutation({
    mutationFn: async () => {
      if (!activeSessionId) {
        throw new ApiRequestError("Сначала выберите или создайте сессию", "session_missing");
      }
      const cleanMessage = message.trim();
      if (!cleanMessage) {
        throw new ApiRequestError("Введите сообщение", "message_required");
      }
      const documentNames = docNamesText
        .split(",")
        .map((item) => item.trim())
        .filter((item) => item.length > 0);
      const tags = tagsText
        .split(",")
        .map((item) => item.trim())
        .filter((item) => item.length > 0);

      const payload = {
        message: cleanMessage,
        top_k: topK,
        filters: {
          document_names: documentNames,
          tags
        }
      };

      if (!streaming) {
        await sendChatMessage(activeSessionId, payload);
      } else {
        setStreamText("");
        setStreamCitations([]);
        await streamChatMessage(activeSessionId, payload, {
          onDelta: (value) => setStreamText((current) => current + value),
          onCitations: (items) => setStreamCitations(items)
        });
      }
      setMessage("");
      await queryClient.invalidateQueries({ queryKey: ["chat-messages", activeSessionId] });
      await queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
    }
  });

  useEffect(() => {
    const sessions = sessionsQuery.data?.sessions ?? [];
    if (!activeSessionId && sessions.length > 0) {
      setActiveSessionId(sessions[0].session_id);
    }
  }, [activeSessionId, sessionsQuery.data?.sessions]);

  const messages = messagesQuery.data?.messages ?? [];
  const shownMessages = useMemo(() => {
    if (!streaming || !sendMutation.isPending || !streamText) {
      return messages;
    }
    const placeholder: ChatMessage = {
      id: "__streaming__",
      role: "assistant",
      content: streamText,
      citations: streamCitations,
      created_at: new Date().toISOString()
    };
    return [...messages, placeholder];
  }, [messages, sendMutation.isPending, streamCitations, streamText, streaming]);

  function submitMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    sendMutation.mutate();
  }

  function errorText(value: unknown): string {
    if (value instanceof ApiRequestError) {
      return `${value.code}: ${value.message}`;
    }
    if (value instanceof Error) {
      return value.message;
    }
    return "Unexpected error";
  }

  return (
    <div className="workspace-grid">
      <section className="panel sessions-panel">
        <div className="panel-head">
          <h2>Chat Sessions</h2>
          <p>Управление диалогами и контекстом.</p>
        </div>
        <button className="primary-action" type="button" onClick={() => createSessionMutation.mutate()}>
          Новая сессия
        </button>
        <div className="session-list">
          {(sessionsQuery.data?.sessions ?? []).map((session) => (
            <button
              key={session.session_id}
              type="button"
              className={`session-item ${activeSessionId === session.session_id ? "active" : ""}`}
              onClick={() => setActiveSessionId(session.session_id)}
            >
              <strong>{session.session_id.slice(0, 8)}</strong>
              <span>{session.message_count} msg</span>
              <span>{formatIso(session.last_message_at ?? session.created_at)}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="panel chat-panel">
        <div className="panel-head">
          <h2>Chat</h2>
          <p>Ответы модели с цитатами из документов.</p>
        </div>

        <form className="chat-controls" onSubmit={submitMessage}>
          <label>
            <span>Сообщение</span>
            <textarea
              rows={3}
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder="Сформулируйте вопрос по документам..."
            />
          </label>
          <div className="chat-options">
            <label>
              <span>top_k</span>
              <input
                type="number"
                min={1}
                max={50}
                value={topK}
                onChange={(event) => setTopK(Number(event.target.value) || 5)}
              />
            </label>
            <label>
              <span>Фильтр по document_name</span>
              <input
                type="text"
                value={docNamesText}
                placeholder="doc1.pdf, doc2.docx"
                onChange={(event) => setDocNamesText(event.target.value)}
              />
            </label>
            <label>
              <span>Фильтр по tags</span>
              <input
                type="text"
                value={tagsText}
                placeholder="finance, hr"
                onChange={(event) => setTagsText(event.target.value)}
              />
            </label>
            <label className="toggle-line">
              <input type="checkbox" checked={streaming} onChange={(event) => setStreaming(event.target.checked)} />
              <span>Streaming SSE</span>
            </label>
            <button className="primary-action" type="submit" disabled={sendMutation.isPending || !activeSessionId}>
              {sendMutation.isPending ? "Отправка..." : "Отправить"}
            </button>
          </div>
        </form>

        {(sendMutation.isError || messagesQuery.isError || sessionsQuery.isError || createSessionMutation.isError) && (
          <p className="inline-error" role="alert">
            {errorText(sendMutation.error ?? messagesQuery.error ?? sessionsQuery.error ?? createSessionMutation.error)}
          </p>
        )}

        <div className="messages-list">
          {shownMessages.length === 0 && <p className="muted">Выберите сессию и отправьте первое сообщение.</p>}
          {shownMessages.map((item) => (
            <article className={`message-card ${item.role === "user" ? "user" : "assistant"}`} key={item.id}>
              <header>
                <strong>{item.role}</strong>
                <span>{formatIso(item.created_at)}</span>
              </header>
              <p>{item.content}</p>
              {item.citations.length > 0 && (
                <ul className="citations-list">
                  {item.citations.map((citation, index) => (
                    <li key={`${item.id}-citation-${index}`}>
                      <strong>{citation.document_name ?? "Unknown document"}</strong>
                      {citation.page ? `, page ${citation.page}` : ""}
                      {citation.snippet ? ` — ${citation.snippet}` : ""}
                    </li>
                  ))}
                </ul>
              )}
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
