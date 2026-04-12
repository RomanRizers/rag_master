import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

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
  const navigate = useNavigate();

  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [message, setMessage] = useState("");
  const [topK, setTopK] = useState(5);
  const [docNamesText, setDocNamesText] = useState("");
  const [tagsText, setTagsText] = useState("");
  const [selectedKnowledgeBases, setSelectedKnowledgeBases] = useState<string[]>([]);
  const [streaming, setStreaming] = useState(true);
  const [streamText, setStreamText] = useState("");
  const [streamCitations, setStreamCitations] = useState<ChatCitation[]>([]);
  const [pendingUserMessage, setPendingUserMessage] = useState<ChatMessage | null>(null);
  const [isResponding, setIsResponding] = useState(false);

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
    mutationFn: async (submission: { cleanMessage: string }) => {
      if (!activeSessionId) {
        throw new ApiRequestError("Сначала выберите или создайте сессию", "session_missing");
      }
      const cleanMessage = submission.cleanMessage;
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
      await queryClient.invalidateQueries({ queryKey: ["chat-messages", activeSessionId] });
      await queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
    onSuccess: () => {
      setMessage("");
      setPendingUserMessage(null);
      setIsResponding(false);
      setStreamText("");
      setStreamCitations([]);
    },
    onError: () => {
      setPendingUserMessage(null);
      setIsResponding(false);
      setStreamText("");
      setStreamCitations([]);
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
    const items = [...messages];
    if (pendingUserMessage) {
      items.push(pendingUserMessage);
    }
    if (isResponding) {
      items.push({
        id: "__streaming__",
        role: "assistant",
        content: streamText || "Отвечаем",
        citations: streamCitations,
        created_at: new Date().toISOString()
      });
    }
    return items;
  }, [isResponding, messages, pendingUserMessage, streamCitations, streamText]);

  function submitMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanMessage = message.trim();
    if (!cleanMessage) {
      return;
    }
    setPendingUserMessage({
      id: "__pending_user__",
      role: "user",
      content: cleanMessage,
      citations: [],
      created_at: new Date().toISOString()
    });
    setIsResponding(true);
    setStreamText("");
    setStreamCitations([]);
    sendMutation.mutate({ cleanMessage });
  }

  function toggleKnowledgeBase(value: string) {
    setSelectedKnowledgeBases((current) =>
      current.includes(value) ? current.filter((item) => item !== value) : [...current, value]
    );
  }

  const sessions = sessionsQuery.data?.sessions ?? [];
  const knowledgeBases = knowledgeBasesQuery.data?.knowledge_bases ?? [];
  const activeSession = sessions.find((session) => session.session_id === activeSessionId);

  function openCitation(citation: ChatCitation) {
    if (!citation.document_id || !citation.knowledge_base) {
      return;
    }
    const params = new URLSearchParams();
    if (citation.chunk_id) {
      params.set("chunk", citation.chunk_id);
    }
    if (citation.snippet) {
      params.set("highlight", citation.snippet.slice(0, 120));
    }
    const suffix = params.toString() ? `?${params.toString()}` : "";
    navigate(`/dataset/${encodeURIComponent(citation.knowledge_base)}/documents/${citation.document_id}${suffix}`);
  }

  return (
    <div className="chat-layout">
      <aside className="panel chat-sidebar">
        <div className="chat-sidebar-head">
          <div className="stack-xs">
            <span className="section-kicker">Chat</span>
            <h2>Conversations</h2>
            <p className="muted">Выбери сессию или создай новую.</p>
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
                className="session-delete-icon"
                aria-label={`Удалить сессию ${session.session_id.slice(0, 8)}`}
                disabled={sendMutation.isPending || deleteSessionMutation.isPending}
                onClick={() => deleteSessionMutation.mutate(session.session_id)}
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d="M9 3h6l1 2h4v2H4V5h4l1-2Zm-1 6h2v8H8V9Zm6 0h2v8h-2V9ZM6 9h12l-1 10a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L6 9Z"
                    fill="currentColor"
                  />
                </svg>
              </button>
            </div>
          ))}
        </div>
      </aside>

      <section className="panel chat-shell">
        <div className="chat-thread-head">
          <div className="chat-thread-copy">
            <div className="stack-xs">
              <span className="section-kicker">Conversation</span>
              <h2>{activeSession ? `Session ${activeSession.session_id.slice(0, 8)}` : "Chat"}</h2>
            </div>
            <div className="chat-thread-meta">
              <span className="chip chip-primary">top_k {topK}</span>
              <span className="chip">{streaming ? "streaming" : "sync mode"}</span>
              <span className="chip">
                {activeSession ? `${activeSession.message_count} msg` : "нет активной сессии"}
              </span>
              <span className="chip">
                {selectedKnowledgeBases.length > 0
                  ? `${selectedKnowledgeBases.length} knowledge bases`
                  : "all knowledge bases"}
              </span>
            </div>
          </div>
          <div className="chat-thread-actions">
            {activeSessionId && (
              <button
                type="button"
                className="ghost-action compact-delete-action"
                disabled={sendMutation.isPending || deleteSessionMutation.isPending}
                onClick={() => deleteSessionMutation.mutate(activeSessionId)}
              >
                Очистить
              </button>
            )}
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

        <div className="chat-context-bar">
          <div className="filter-headline">
            <div>
              <span className="meta-label">Knowledge base scope</span>
              <p className="muted">Выбери одну или несколько баз знаний для ответа.</p>
            </div>
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
                  <strong>{item.role === "user" ? "You" : "Assistant"}</strong>
                  <span>{formatIso(item.created_at)}</span>
                </header>
                {item.id === "__streaming__" ? (
                  <div className="chat-responding-line">
                    <span className="chat-spinner" aria-hidden="true" />
                    <span>Отвечаем</span>
                  </div>
                ) : null}
                <p>{item.content}</p>
                {item.citations.length > 0 && (
                  <ul className="citations-list">
                    {item.citations.map((citation, index) => (
                      <li key={`${item.id}-citation-${index}`} className="citation-card">
                        <button type="button" className="citation-button" onClick={() => openCitation(citation)}>
                          <strong>{citation.document_name ?? "Unknown document"}</strong>
                          {citation.page ? <span>page {citation.page}</span> : null}
                          {citation.snippet ? <p>{citation.snippet}</p> : null}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </article>
            </div>
          ))}
        </div>

        <form className="chat-composer" onSubmit={submitMessage}>
          <div className="chat-composer-main">
            <label className="chat-message-field">
              <span>Сообщение</span>
              <textarea
                rows={4}
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="Сформулируйте вопрос по документам..."
              />
            </label>
          </div>

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
              <span>document_name</span>
              <input
                type="text"
                value={docNamesText}
                placeholder="doc1.pdf, doc2.docx"
                onChange={(event) => setDocNamesText(event.target.value)}
              />
            </label>
            <label>
              <span>tags</span>
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

          <div className="chat-composer-actions">
            <button
              className="primary-action"
              type="submit"
              disabled={sendMutation.isPending || !activeSessionId}
            >
              {sendMutation.isPending ? "Отправка..." : "Отправить"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
