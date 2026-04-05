import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  ApiRequestError,
  createChatSession,
  deleteChatSession,
  getChatMessages,
  listChatSessions,
  listKnowledgeBases,
  sendChatMessage,
  streamChatMessage
} from "../api/client";
import type { ChatCitation, ChatMessage } from "../types";
import { appErrorCopy } from "../utils/appError";
import { ErrorBanner } from "./ErrorBanner";

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
  const [selectedKnowledgeBases, setSelectedKnowledgeBases] = useState<string[]>([]);
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

  const knowledgeBasesQuery = useQuery({
    queryKey: ["knowledge-bases"],
    queryFn: listKnowledgeBases,
    refetchInterval: 7000
  });

  const createSessionMutation = useMutation({
    mutationFn: createChatSession,
    onSuccess: (payload) => {
      setActiveSessionId(payload.session_id);
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
    }
  });

  const deleteSessionMutation = useMutation({
    mutationFn: deleteChatSession,
    onSuccess: async (_, sessionId) => {
      const sessions = sessionsQuery.data?.sessions ?? [];
      if (activeSessionId === sessionId) {
        const nextSession = sessions.find((session) => session.session_id !== sessionId);
        setActiveSessionId(nextSession?.session_id ?? "");
      }
      setStreamText("");
      setStreamCitations([]);
      await queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
      await queryClient.invalidateQueries({ queryKey: ["chat-messages"] });
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
          tags,
          knowledge_bases: selectedKnowledgeBases
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

  function toggleKnowledgeBase(value: string) {
    setSelectedKnowledgeBases((current) =>
      current.includes(value) ? current.filter((item) => item !== value) : [...current, value]
    );
  }

  const sessions = sessionsQuery.data?.sessions ?? [];
  const knowledgeBases = knowledgeBasesQuery.data?.knowledge_bases ?? [];

  return (
    <div className="chat-layout">
      <aside className="panel chat-sidebar">
        <div className="panel-head">
          <div>
            <span className="section-kicker">Chat</span>
            <h2>Sessions</h2>
            <p>Левая колонка только для выбора диалога и базовых действий.</p>
          </div>
          <button className="primary-action" type="button" onClick={() => createSessionMutation.mutate()}>
            Новая сессия
          </button>
        </div>

        <div className="session-list">
          {sessions.map((session) => (
            <div
              key={session.session_id}
              className={`session-item ${activeSessionId === session.session_id ? "active" : ""}`}
            >
              <button type="button" className="session-item-main" onClick={() => setActiveSessionId(session.session_id)}>
                <span className="session-kicker">Session</span>
                <strong>{session.session_id.slice(0, 8)}</strong>
                <span>{session.message_count} msg</span>
                <span>{formatIso(session.last_message_at ?? session.created_at)}</span>
              </button>
              <button
                type="button"
                className="session-delete-button"
                aria-label={`Удалить сессию ${session.session_id.slice(0, 8)}`}
                disabled={sendMutation.isPending || deleteSessionMutation.isPending}
                onClick={() => deleteSessionMutation.mutate(session.session_id)}
              >
                Удалить
              </button>
            </div>
          ))}
        </div>
      </aside>

      <section className="panel chat-shell">
        <div className="chat-header">
          <div className="panel-head">
            <div>
              <span className="section-kicker">Conversation</span>
              <h2>{activeSessionId ? `Session ${activeSessionId.slice(0, 8)}` : "Chat"}</h2>
              <p>Полноценная рабочая лента без тяжёлых dashboard-блоков.</p>
            </div>
          </div>
          <div className="chat-active-filters">
            <span className="chip chip-primary">top_k {topK}</span>
            <span className="chip">{streaming ? "streaming on" : "streaming off"}</span>
            <span className="chip">
              {selectedKnowledgeBases.length > 0
                ? `базы: ${selectedKnowledgeBases.join(", ")}`
                : "все базы знаний"}
            </span>
          </div>
        </div>

        {(
          sendMutation.isError ||
          messagesQuery.isError ||
          sessionsQuery.isError ||
          createSessionMutation.isError ||
          deleteSessionMutation.isError
        ) && (
          <ErrorBanner
            error={
              sendMutation.error ??
              messagesQuery.error ??
              sessionsQuery.error ??
              createSessionMutation.error ??
              deleteSessionMutation.error
            }
            copy={appErrorCopy.ru}
            className="inline-error"
          />
        )}

        <div className="messages-list chat-messages-list">
          {shownMessages.length === 0 && (
            <div className="chat-empty-state">
              <p className="muted">Выберите сессию и отправьте первое сообщение.</p>
            </div>
          )}
          {shownMessages.map((item) => (
            <div className={`message-row ${item.role === "user" ? "user" : "assistant"}`} key={item.id}>
              <article className={`message-card ${item.role === "user" ? "user" : "assistant"}`}>
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
            </div>
          ))}
        </div>

        <form className="chat-composer" onSubmit={submitMessage}>
          <label className="chat-message-field">
            <span>Сообщение</span>
            <textarea
              rows={4}
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder="Сформулируйте вопрос по документам..."
            />
          </label>

          <div className="chat-composer-sidebar">
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
          </div>

          <div className="chat-kb-row">
            <div className="filter-headline">
              <span>Базы знаний</span>
              {selectedKnowledgeBases.length > 0 && (
                <button type="button" className="text-button" onClick={() => setSelectedKnowledgeBases([])}>
                  Сбросить
                </button>
              )}
            </div>
            <div className="keyword-chips">
              {knowledgeBases.map((item) => (
                <button
                  key={item.name}
                  type="button"
                  className={`keyword-chip ${selectedKnowledgeBases.includes(item.name) ? "active" : ""}`}
                  onClick={() => toggleKnowledgeBase(item.name)}
                >
                  {item.name} ({item.document_count})
                </button>
              ))}
            </div>
          </div>

          <div className="chat-composer-actions">
            <button
              className="primary-action"
              type="submit"
              disabled={sendMutation.isPending || !activeSessionId}
            >
              {sendMutation.isPending ? "Отправка..." : "Отправить"}
            </button>
            {activeSessionId && (
              <button
                type="button"
                className="danger-action"
                disabled={sendMutation.isPending || deleteSessionMutation.isPending}
                onClick={() => deleteSessionMutation.mutate(activeSessionId)}
              >
                Удалить чат
              </button>
            )}
          </div>
        </form>
      </section>
    </div>
  );
}
