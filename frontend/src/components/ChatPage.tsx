import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

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
import { PdfViewerModal } from "./PdfViewerModal";

function formatIso(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function CitationCard({
  citation,
  index,
  onClick
}: {
  citation: ChatCitation;
  index: number;
  onClick: (c: ChatCitation) => void;
}) {
  const isPdf = (citation.document_name ?? "").toLowerCase().endsWith(".pdf");

  return (
    <li className="citation-card">
      <button type="button" className="citation-button" onClick={() => onClick(citation)}>
        <span className="citation-badge">{index + 1}</span>
        <div className="citation-body">
          <div className="citation-top">
            <svg
              className="citation-doc-icon"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              aria-hidden="true"
            >
              <rect x="4" y="2" width="16" height="20" rx="2" stroke="currentColor" strokeWidth="2" />
              <path d="M8 7h8M8 11h8M8 15h5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <span className="citation-name">{citation.document_name ?? "Документ"}</span>
            {citation.page && <span className="citation-page-chip">стр. {citation.page}</span>}
            {isPdf && <span className="citation-pdf-tag">PDF</span>}
          </div>
          {citation.snippet && (
            <p className="citation-snippet">{citation.snippet.slice(0, 100)}{citation.snippet.length > 100 ? "…" : ""}</p>
          )}
        </div>
        <svg
          className="citation-arrow"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
        >
          <path d="M9 18l6-6-6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
    </li>
  );
}

function TypingDots() {
  return (
    <span className="typing-dots" aria-label="Печатает...">
      <span />
      <span />
      <span />
    </span>
  );
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
  const [pendingUserMessage, setPendingUserMessage] = useState<ChatMessage | null>(null);
  const [isResponding, setIsResponding] = useState(false);
  const [activeCitation, setActiveCitation] = useState<ChatCitation | null>(null);
  const [composerOpen, setComposerOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

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
          onCitations: (items) => setStreamCitations(items),
          onError: (_code, _message) => {
            setPendingUserMessage(null);
            setIsResponding(false);
            setStreamText("");
            setStreamCitations([]);
          }
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
    if (pendingUserMessage) items.push(pendingUserMessage);
    if (isResponding) {
      items.push({
        id: "__streaming__",
        role: "assistant",
        content: streamText || "",
        citations: streamCitations,
        created_at: new Date().toISOString()
      });
    }
    return items;
  }, [isResponding, messages, pendingUserMessage, streamCitations, streamText]);

  // Auto-scroll to bottom when messages or streaming text changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [shownMessages.length, streamText]);

  function submitMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanMessage = message.trim();
    if (!cleanMessage) return;
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

  function openCitation(citation: ChatCitation) {
    if (!citation.document_id) return;
    setActiveCitation(citation);
  }

  const sessions = sessionsQuery.data?.sessions ?? [];
  const knowledgeBases = knowledgeBasesQuery.data?.knowledge_bases ?? [];
  const activeSession = sessions.find((session) => session.session_id === activeSessionId);

  return (
    <>
      <div className="chat-layout">
        {/* Sidebar */}
        <aside className="panel chat-sidebar">
          <div className="chat-sidebar-head">
            <div className="stack-xs">
              <span className="section-kicker">Chat</span>
              <h2>Conversations</h2>
              <p className="muted">Выбери сессию или создай новую.</p>
            </div>
            <button className="primary-action" type="button" onClick={() => createSessionMutation.mutate()}>
              + Новая сессия
            </button>
          </div>

          <div className="session-list">
            {sessions.map((session) => (
              <div
                key={session.session_id}
                className={`session-item ${activeSessionId === session.session_id ? "active" : ""}`}
              >
                <button
                  type="button"
                  className="session-item-main"
                  onClick={() => setActiveSessionId(session.session_id)}
                >
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

        {/* Main chat shell */}
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
                  {activeSession ? `${activeSession.message_count} msg` : "нет сессии"}
                </span>
                <span className="chip">
                  {selectedKnowledgeBases.length > 0
                    ? `${selectedKnowledgeBases.length} KB`
                    : "all KBs"}
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

          {(sendMutation.isError ||
            messagesQuery.isError ||
            sessionsQuery.isError ||
            createSessionMutation.isError ||
            deleteSessionMutation.isError) && (
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

          {/* KB context bar */}
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

          {/* Streaming progress bar */}
          {isResponding && <div className="stream-progress-bar" aria-hidden="true" />}

          {/* Messages */}
          <div className="messages-list chat-messages-list">
            {shownMessages.length === 0 && (
              <div className="chat-empty-state">
                <div className="chat-empty-icon" aria-hidden="true">
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
                <p className="muted">Выберите сессию и отправьте первое сообщение.</p>
              </div>
            )}

            {shownMessages.map((item, msgIdx) => (
              <div
                className={`message-row ${item.role === "user" ? "user" : "assistant"}`}
                key={item.id}
                style={{ animationDelay: `${msgIdx * 30}ms` }}
              >
                <article className={`message-card ${item.role === "user" ? "user" : "assistant"}`}>
                  <header>
                    <div className="message-role-tag">
                      {item.role === "user" ? (
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                          <circle cx="12" cy="8" r="4" />
                          <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
                        </svg>
                      ) : (
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                          <path d="M12 2a10 10 0 1 0 0 20A10 10 0 0 0 12 2zm0 4a3 3 0 1 1 0 6 3 3 0 0 1 0-6zm0 12a7 7 0 0 1-5.5-2.7c.8-1.4 2.8-2.3 5.5-2.3s4.7.9 5.5 2.3A7 7 0 0 1 12 18z" />
                        </svg>
                      )}
                      <strong>{item.role === "user" ? "Вы" : "Ассистент"}</strong>
                    </div>
                    <span className="message-time">{formatIso(item.created_at)}</span>
                  </header>

                  {/* Streaming indicator */}
                  {item.id === "__streaming__" && !streamText && (
                    <div className="chat-responding-line">
                      <TypingDots />
                      <span>Думаю...</span>
                    </div>
                  )}

                  {item.content && (
                    <div className="message-content markdown-body">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {item.content}
                      </ReactMarkdown>
                    </div>
                  )}

                  {/* Citations */}
                  {item.citations.length > 0 && (
                    <div className="citations-section">
                      <span className="citations-label">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                          <path d="M12 2a10 10 0 1 0 0 20A10 10 0 0 0 12 2zm1 14H11v-5h2v5zm0-7H11V7h2v2z" />
                        </svg>
                        Источники ({item.citations.length})
                      </span>
                      <ul className="citations-list">
                        {item.citations.map((citation, index) => (
                          <CitationCard
                            key={`${item.id}-citation-${index}`}
                            citation={citation}
                            index={index}
                            onClick={openCitation}
                          />
                        ))}
                      </ul>
                    </div>
                  )}
                </article>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Composer */}
          <form className="chat-composer" onSubmit={submitMessage}>
            <div className="chat-composer-main">
              <label className="chat-message-field">
                <span>Сообщение</span>
                <textarea
                  rows={4}
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  placeholder="Сформулируйте вопрос по документам..."
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                      e.preventDefault();
                      e.currentTarget.form?.requestSubmit();
                    }
                  }}
                />
              </label>
            </div>

            <div className="chat-composer-controls">
              <button
                type="button"
                className={`composer-toggle-btn ${composerOpen ? "open" : ""}`}
                onClick={() => setComposerOpen((v) => !v)}
                aria-expanded={composerOpen}
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
                </svg>
                Параметры
                <svg
                  className="composer-toggle-chevron"
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                  aria-hidden="true"
                >
                  <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>

              {composerOpen && (
                <div className="composer-advanced">
                  <label>
                    <span>top_k</span>
                    <input
                      type="number"
                      min={1}
                      max={50}
                      value={topK}
                      onChange={(e) => setTopK(Number(e.target.value) || 5)}
                    />
                  </label>
                  <label>
                    <span>document_name</span>
                    <input
                      type="text"
                      value={docNamesText}
                      placeholder="doc1.pdf, doc2.docx"
                      onChange={(e) => setDocNamesText(e.target.value)}
                    />
                  </label>
                  <label>
                    <span>tags</span>
                    <input
                      type="text"
                      value={tagsText}
                      placeholder="finance, hr"
                      onChange={(e) => setTagsText(e.target.value)}
                    />
                  </label>
                  <label className="toggle-line">
                    <input
                      type="checkbox"
                      checked={streaming}
                      onChange={(e) => setStreaming(e.target.checked)}
                    />
                    <span>Streaming SSE</span>
                  </label>
                </div>
              )}

              <div className="chat-composer-actions">
                <span className="muted" style={{ fontSize: "0.76rem" }}>Ctrl+Enter</span>
                <button
                  className="primary-action send-btn"
                  type="submit"
                  disabled={sendMutation.isPending || !activeSessionId}
                >
                  {sendMutation.isPending ? (
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                      <span className="chat-spinner" aria-hidden="true" style={{ width: 12, height: 12 }} />
                      Отправка...
                    </span>
                  ) : (
                    <>
                      Отправить
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                        <path d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </>
                  )}
                </button>
              </div>
            </div>
          </form>
        </section>
      </div>

      {/* PDF Viewer Modal */}
      {activeCitation && (
        <PdfViewerModal
          citation={activeCitation}
          onClose={() => setActiveCitation(null)}
        />
      )}
    </>
  );
}
