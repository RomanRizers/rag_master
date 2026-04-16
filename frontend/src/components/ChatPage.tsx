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
import { useLang } from "../LangContext";
import { ErrorBanner } from "./ErrorBanner";
import { PdfViewerModal } from "./PdfViewerModal";

function makeFormatIso(t: ReturnType<typeof useLang>) {
  return function formatIso(value?: string | null): string {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    const now = new Date();
    const diff = (now.getTime() - date.getTime()) / 1000;
    if (diff < 60) return t.justNow;
    if (diff < 3600) return `${Math.floor(diff / 60)} ${t.minAgo}`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} ${t.hoursAgo}`;
    return date.toLocaleDateString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  };
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
  const t = useLang();
  return (
    <span className="typing-dots" aria-label={t.chatTyping}>
      <span />
      <span />
      <span />
    </span>
  );
}

function KBSelectorModal({
  knowledgeBases,
  selected,
  onToggle,
  onClear,
  onClose
}: {
  knowledgeBases: { name: string; document_count: number }[];
  selected: string[];
  onToggle: (name: string) => void;
  onClear: () => void;
  onClose: () => void;
}) {
  const t = useLang();
  const hint = selected.length === 0
    ? t.kbModalHintAll
    : t.kbModalHintSelected.replace("{n}", String(selected.length)).replace("{total}", String(knowledgeBases.length));

  return (
    <div className="kb-modal-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-label={t.kbModalTitle}>
      <div className="kb-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="kb-modal-header">
          <div>
            <p className="section-kicker">{t.filterLabel}</p>
            <h3>{t.kbModalTitle}</h3>
          </div>
          <button type="button" className="kb-modal-close" onClick={onClose} aria-label={t.chatClearCancel}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M18 6 6 18M6 6l12 12" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        <p className="kb-modal-hint muted">{hint}</p>

        {knowledgeBases.length === 0 ? (
          <div className="kb-modal-empty muted">{t.kbModalEmpty}</div>
        ) : (
          <div className="kb-modal-grid">
            {knowledgeBases.map((kb) => {
              const active = selected.includes(kb.name);
              return (
                <button
                  key={kb.name}
                  type="button"
                  className={`kb-modal-chip ${active ? "active" : ""}`}
                  onClick={() => onToggle(kb.name)}
                >
                  <span className="kb-modal-chip-check" aria-hidden="true">
                    {active ? (
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                        <path d="M20 6 9 17l-5-5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    ) : null}
                  </span>
                  <span className="kb-modal-chip-name">{kb.name}</span>
                  <span className="kb-modal-chip-count">{kb.document_count} {t.kbDoc}</span>
                </button>
              );
            })}
          </div>
        )}

        <div className="kb-modal-footer">
          <button type="button" className="ghost-action" onClick={onClear} disabled={selected.length === 0}>
            {t.kbModalReset}
          </button>
          <button type="button" className="primary-action" onClick={onClose}>
            {t.kbModalApply}
          </button>
        </div>
      </div>
    </div>
  );
}

export function ChatPage() {
  const queryClient = useQueryClient();
  const t = useLang();
  const formatIso = makeFormatIso(t);

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
  const [kbModalOpen, setKbModalOpen] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const paramsPopoverRef = useRef<HTMLDivElement>(null);

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
      // Open KB modal when creating a new session
      setKbModalOpen(true);
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
        throw new ApiRequestError(t.msgSessionMissing, "session_missing");
      }
      const cleanMessage = submission.cleanMessage;
      if (!cleanMessage) {
        throw new ApiRequestError(t.msgMessageRequired, "message_required");
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

  // Close params popover on outside click
  useEffect(() => {
    if (!composerOpen) return;
    function onPointerDown(e: PointerEvent) {
      if (paramsPopoverRef.current && !paramsPopoverRef.current.contains(e.target as Node)) {
        setComposerOpen(false);
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [composerOpen]);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [message]);

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
              <span className="section-kicker">{t.chatSessions}</span>
              <h2>{t.chatDialogues}</h2>
            </div>
            <button
              className="primary-action"
              type="button"
              disabled={createSessionMutation.isPending}
              onClick={() => createSessionMutation.mutate()}
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
              </svg>
              {t.chatNewSession}
            </button>
          </div>

          <div className="session-list">
            {sessionsQuery.isLoading && (
              <>
                {[1, 2, 3].map((i) => (
                  <div key={i} className="session-skeleton" />
                ))}
              </>
            )}
            {!sessionsQuery.isLoading && sessions.length === 0 && (
              <p className="muted" style={{ fontSize: "0.83rem", textAlign: "center", padding: "12px 0" }}>
                {t.chatNoSessions}
              </p>
            )}
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
                  <div className="session-item-avatar" aria-hidden="true">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
                    </svg>
                  </div>
                  <div className="session-item-info">
                    <strong className="session-item-id">#{session.session_id.slice(0, 8)}</strong>
                    <span className="session-item-meta">{session.message_count} {t.sessMsg} · {formatIso(session.last_message_at ?? session.created_at)}</span>
                  </div>
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
          {/* Header */}
          <div className="chat-thread-head">
            <div className="chat-thread-copy">
              <div className="chat-session-title">
                <span className="section-kicker">Chat</span>
                <span className="chat-session-id">{activeSession ? `#${activeSession.session_id.slice(0, 8)}` : "—"}</span>
              </div>
              <div className="chat-thread-meta">
                <span className="chip chip-primary">top_k {topK}</span>
                <span className="chip">{streaming ? "streaming" : "sync"}</span>
                {activeSession && (
                  <span className="chip">{activeSession.message_count} {t.sessMsg}</span>
                )}
                <button
                  type="button"
                  className={`kb-scope-chip ${selectedKnowledgeBases.length > 0 ? "kb-scope-chip--active" : ""}`}
                  onClick={() => setKbModalOpen(true)}
                  title={t.chatSelectKBs}
                >
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <ellipse cx="12" cy="6" rx="8" ry="3" stroke="currentColor" strokeWidth="2" />
                    <path d="M4 6v6c0 1.66 3.58 3 8 3s8-1.34 8-3V6" stroke="currentColor" strokeWidth="2" />
                    <path d="M4 12v6c0 1.66 3.58 3 8 3s8-1.34 8-3v-6" stroke="currentColor" strokeWidth="2" />
                  </svg>
                  {selectedKnowledgeBases.length > 0
                    ? `${selectedKnowledgeBases.length} KB`
                    : t.chatAllKBs}
                </button>
                <div className="params-popover-wrap" ref={paramsPopoverRef}>
                  <button
                    type="button"
                    className={`kb-scope-chip ${composerOpen ? "kb-scope-chip--active" : ""}`}
                    onClick={() => setComposerOpen((v) => !v)}
                    title={t.chatParams}
                  >
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                      <circle cx="12" cy="12" r="3" fill="currentColor" />
                      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" stroke="currentColor" strokeWidth="2" />
                    </svg>
                    {t.chatParams}
                  </button>
                  {composerOpen && (
                    <div className="composer-advanced--popover">
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
                      <div className="params-divider" />
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer" }} onClick={() => setStreaming((v) => !v)}>
                        <input
                          type="checkbox"
                          checked={streaming}
                          onChange={(e) => setStreaming(e.target.checked)}
                          onClick={(e) => e.stopPropagation()}
                        />
                        <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Streaming SSE</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
            <div className="chat-thread-actions">
              {activeSessionId && !confirmClear && (
                <button
                  type="button"
                  className="ghost-action compact-delete-action"
                  disabled={sendMutation.isPending || deleteSessionMutation.isPending}
                  onClick={() => setConfirmClear(true)}
                >
                  {t.chatClear}
                </button>
              )}
              {confirmClear && (
                <div className="confirm-clear-row">
                  <span className="confirm-clear-label">{t.chatClearConfirm}</span>
                  <button
                    type="button"
                    className="danger-action confirm-clear-yes"
                    disabled={deleteSessionMutation.isPending}
                    onClick={() => { deleteSessionMutation.mutate(activeSessionId); setConfirmClear(false); }}
                  >
                    Да
                  </button>
                  <button
                    type="button"
                    className="ghost-action confirm-clear-no"
                    onClick={() => setConfirmClear(false)}
                  >
                    Отмена
                  </button>
                </div>
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

          {/* Streaming progress bar */}
          {isResponding && <div className="stream-progress-bar" aria-hidden="true" />}

          {/* Messages */}
          <div className="chat-messages-wrapper">
          <div className="messages-list chat-messages-list">
            {shownMessages.length === 0 && (
              <div className="chat-empty-state">
                <div className="chat-empty-icon" aria-hidden="true">
                  <svg width="52" height="52" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"
                      stroke="currentColor"
                      strokeWidth="1.2"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
                <div className="chat-empty-text">
                  <p style={{ fontWeight: 700, margin: 0 }}>{t.chatEmptyTitle}</p>
                  <p className="muted" style={{ margin: 0 }}>{t.chatEmptyHint}</p>
                </div>
                <div className="chat-empty-suggestions">
                  {[t.chatSuggestion1, t.chatSuggestion2, t.chatSuggestion3].map((s) => (
                    <button
                      key={s}
                      type="button"
                      className="chat-suggestion-chip"
                      onClick={() => { setMessage(s); textareaRef.current?.focus(); }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
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
                      <strong>{item.role === "user" ? t.chatYou : t.chatAssistant}</strong>
                    </div>
                    <span className="message-time">{formatIso(item.created_at)}</span>
                  </header>

                  {item.id === "__streaming__" && !streamText && (
                    <div className="chat-responding-line">
                      <TypingDots />
                      <span>{t.chatThinking}</span>
                    </div>
                  )}

                  {item.content && (
                    <div className="message-content markdown-body">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {item.content}
                      </ReactMarkdown>
                      {item.id === "__streaming__" && streamText && (
                        <span className="stream-cursor" aria-hidden="true" />
                      )}
                    </div>
                  )}

                  {item.citations.length > 0 && (
                    <div className="citations-section">
                      <span className="citations-label">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                          <path d="M12 2a10 10 0 1 0 0 20A10 10 0 0 0 12 2zm1 14H11v-5h2v5zm0-7H11V7h2v2z" />
                        </svg>
                        {t.chatSources} ({item.citations.length})
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
          </div>

          {/* Composer */}
          <form className="chat-composer" onSubmit={submitMessage}>
            <div className="chat-composer-inner">
              <div className="chat-textarea-wrap">
                <textarea
                  ref={textareaRef}
                  className="chat-textarea"
                  rows={1}
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  placeholder={t.chatPlaceholder}
                  disabled={!activeSessionId || sendMutation.isPending}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                      e.preventDefault();
                      e.currentTarget.form?.requestSubmit();
                    }
                  }}
                />
                <button
                  className="send-icon-btn"
                  type="submit"
                  disabled={sendMutation.isPending || !activeSessionId}
                  aria-label={t.chatSend}
                >
                  {sendMutation.isPending ? (
                    <span className="chat-spinner" aria-hidden="true" />
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                      <path d="M12 19V5M5 12l7-7 7 7" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </button>
                {message.length > 60 && (
                  <span className={`char-counter ${message.length > 1000 ? "char-counter--warn" : ""}`}>
                    {message.length}
                  </span>
                )}
              </div>

            </div>
          </form>
        </section>
      </div>

      {/* KB Selector Modal */}
      {kbModalOpen && (
        <KBSelectorModal
          knowledgeBases={knowledgeBases}
          selected={selectedKnowledgeBases}
          onToggle={toggleKnowledgeBase}
          onClear={() => setSelectedKnowledgeBases([])}
          onClose={() => setKbModalOpen(false)}
        />
      )}

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
