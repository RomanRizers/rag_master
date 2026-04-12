import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  createKnowledgeBase,
  deleteKnowledgeBase,
  deleteDocument,
  getDocumentChunks,
  getDocumentIndexStats,
  indexDocument,
  listDocuments,
  listJobs,
  listKnowledgeBases,
  reindexKnowledgeBase,
  renameKnowledgeBase,
  updateKnowledgeBase,
  uploadDocument
} from "../api/client";
import type { DocumentChunkItem, DocumentItem, JobItem, KnowledgeBaseItem } from "../types";
import { appErrorCopy, resolveAppError } from "../utils/appError";
import { ErrorBanner } from "./ErrorBanner";

type StatsByDocument = Record<
  string,
  {
    chunks_count: number;
    latest_job_status?: string | null;
    keywords?: string[];
    index_profile?: {
      profile_mode?: string;
      chunk_size_tokens?: number;
      chunk_overlap_tokens?: number;
      chunk_keyword_limit?: number;
    } | null;
  }
>;

const PROFILE_PRESETS = {
  precision: {
    chunk_size_tokens: 220,
    chunk_overlap_tokens: 40,
    chunk_keyword_limit: 5
  },
  balanced: {
    chunk_size_tokens: 320,
    chunk_overlap_tokens: 64,
    chunk_keyword_limit: 6
  },
  recall: {
    chunk_size_tokens: 480,
    chunk_overlap_tokens: 96,
    chunk_keyword_limit: 8
  }
} as const;

type KnowledgeBaseSettingsState = {
  profile_mode: string;
  chunk_size_tokens: number;
  chunk_overlap_tokens: number;
  chunk_keyword_limit: number;
};

function formatBytes(value: number): string {
  if (!Number.isFinite(value) || value <= 0) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB"];
  let current = value;
  let unitIndex = 0;
  while (current >= 1024 && unitIndex < units.length - 1) {
    current /= 1024;
    unitIndex += 1;
  }
  return `${current.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

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

function makeDatasetBadge(name: string): string {
  const trimmed = name.trim();
  if (!trimmed) {
    return "KB";
  }
  const parts = trimmed.split(/\s+/).filter(Boolean);
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  return parts
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

function chunkPreview(value: string): string {
  const normalized = value.replace(/\s+/g, " ").trim();
  if (normalized.length <= 240) {
    return normalized;
  }
  return `${normalized.slice(0, 240)}…`;
}

export function DocumentsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const params = useParams<{ datasetName?: string; documentId?: string }>();

  const [file, setFile] = useState<File | null>(null);
  const [isCreateKnowledgeBaseOpen, setIsCreateKnowledgeBaseOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [newKnowledgeBaseName, setNewKnowledgeBaseName] = useState("");
  const [datasetPage, setDatasetPage] = useState(1);
  const [datasetPageSize, setDatasetPageSize] = useState(8);
  const [sourceName, setSourceName] = useState("");
  const [tagsText, setTagsText] = useState("");
  const [knowledgeBase, setKnowledgeBase] = useState("default");
  const [statsByDocument, setStatsByDocument] = useState<StatsByDocument>({});
  const [knowledgeBaseSettings, setKnowledgeBaseSettings] = useState<KnowledgeBaseSettingsState>({
    profile_mode: "balanced",
    chunk_size_tokens: 320,
    chunk_overlap_tokens: 64,
    chunk_keyword_limit: 6
  });
  const [chunkSearch, setChunkSearch] = useState("");
  const [selectedChunk, setSelectedChunk] = useState<DocumentChunkItem | null>(null);

  const documentsQuery = useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments,
    refetchInterval: 7000
  });

  const jobsQuery = useQuery({
    queryKey: ["jobs"],
    queryFn: () => listJobs(),
    refetchInterval: 4000
  });

  const knowledgeBasesQuery = useQuery({
    queryKey: ["knowledge-bases"],
    queryFn: listKnowledgeBases,
    refetchInterval: 7000
  });

  const uploadMutation = useMutation({
    mutationFn: (payload: { file: File; sourceName: string; tags: string[]; knowledgeBase: string }) =>
      uploadDocument(payload.file, payload.sourceName, payload.tags, payload.knowledgeBase),
    onSuccess: (_, payload) => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
      setFile(null);
      setSourceName("");
      setTagsText("");
      setKnowledgeBase(payload.knowledgeBase);
      navigate(`/dataset/${encodeURIComponent(payload.knowledgeBase)}`);
    }
  });

  const createKnowledgeBaseMutation = useMutation({
    mutationFn: createKnowledgeBase,
    onSuccess: (payload) => {
      queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
      setIsCreateKnowledgeBaseOpen(false);
      setNewKnowledgeBaseName("");
      navigate(`/dataset/${encodeURIComponent(payload.name)}`);
    }
  });

  const renameKnowledgeBaseMutation = useMutation({
    mutationFn: ({ currentName, nextName }: { currentName: string; nextName: string }) =>
      renameKnowledgeBase(currentName, nextName),
    onSuccess: (payload, variables) => {
      queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      if (activeKnowledgeBase === variables.currentName) {
        navigate(`/dataset/${encodeURIComponent(payload.name)}`);
      }
    }
  });

  const deleteKnowledgeBaseMutation = useMutation({
    mutationFn: deleteKnowledgeBase,
    onSuccess: (_, deletedName) => {
      queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      if (activeKnowledgeBase === deletedName) {
        navigate("/dataset");
      }
    }
  });

  const updateKnowledgeBaseMutation = useMutation({
    mutationFn: ({ name, payload }: { name: string; payload: KnowledgeBaseSettingsState }) =>
      updateKnowledgeBase(name, payload),
    onSuccess: (payload) => {
      queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
      setKnowledgeBaseSettings({
        profile_mode: payload.profile_mode,
        chunk_size_tokens: payload.chunk_size_tokens,
        chunk_overlap_tokens: payload.chunk_overlap_tokens,
        chunk_keyword_limit: payload.chunk_keyword_limit
      });
      setIsSettingsOpen(false);
    }
  });

  const reindexKnowledgeBaseMutation = useMutation({
    mutationFn: reindexKnowledgeBase,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      setIsSettingsOpen(false);
    }
  });

  const indexMutation = useMutation({
    mutationFn: indexDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    }
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: (_, documentId) => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
      setStatsByDocument((current) => {
        const next = { ...current };
        delete next[documentId];
        return next;
      });
      if (activeDocumentId === documentId && activeKnowledgeBase) {
        navigate(`/dataset/${encodeURIComponent(activeKnowledgeBase)}`);
      }
    }
  });

  const documents = documentsQuery.data?.documents ?? [];
  const jobs = jobsQuery.data?.jobs ?? [];

  const jobsByDocument = useMemo(() => {
    const grouped = new Map<string, JobItem[]>();
    for (const job of jobs) {
      const existing = grouped.get(job.document_id) ?? [];
      existing.push(job);
      grouped.set(job.document_id, existing);
    }
    return grouped;
  }, [jobs]);

  const documentsByKnowledgeBase = useMemo(() => {
    const grouped = new Map<string, DocumentItem[]>();
    for (const document of documents) {
      const key = document.knowledge_base || "default";
      const existing = grouped.get(key) ?? [];
      existing.push(document);
      grouped.set(key, existing);
    }
    return grouped;
  }, [documents]);

  const knowledgeBases = useMemo(() => {
    const apiItems = knowledgeBasesQuery.data?.knowledge_bases ?? [];
    if (apiItems.length > 0) {
      return apiItems;
    }
    return Array.from(documentsByKnowledgeBase.entries()).map(([name, items]) => ({
      name,
      document_count: items.length,
      created_at: null,
      profile_mode: "balanced",
      chunk_size_tokens: 320,
      chunk_overlap_tokens: 64,
      chunk_keyword_limit: 6
    }));
  }, [documentsByKnowledgeBase, knowledgeBasesQuery.data?.knowledge_bases]);

  const activeKnowledgeBase = useMemo(() => {
    const routeValue = params.datasetName ? decodeURIComponent(params.datasetName) : "";
    if (!routeValue) {
      return "";
    }
    return knowledgeBases.some((item) => item.name === routeValue) ? routeValue : routeValue;
  }, [knowledgeBases, params.datasetName]);

  const activeDocumentId = params.documentId ?? "";
  const selectedDatasetInfo = knowledgeBases.find((item) => item.name === activeKnowledgeBase) ?? null;
  const selectedDocuments = useMemo(
    () => [...(documentsByKnowledgeBase.get(activeKnowledgeBase) ?? [])].sort((a, b) => b.created_at.localeCompare(a.created_at)),
    [activeKnowledgeBase, documentsByKnowledgeBase]
  );
  const activeDocument = selectedDocuments.find((item) => item.document_id === activeDocumentId) ?? null;

  const documentChunksQuery = useQuery({
    queryKey: ["document-chunks", activeDocumentId],
    queryFn: () => getDocumentChunks(activeDocumentId),
    enabled: Boolean(activeDocumentId),
    refetchInterval: activeDocumentId ? 10000 : false
  });

  useEffect(() => {
    if (!selectedDatasetInfo) {
      return;
    }
    setKnowledgeBase(activeKnowledgeBase || selectedDatasetInfo.name);
    setKnowledgeBaseSettings({
      profile_mode: selectedDatasetInfo.profile_mode,
      chunk_size_tokens: selectedDatasetInfo.chunk_size_tokens,
      chunk_overlap_tokens: selectedDatasetInfo.chunk_overlap_tokens,
      chunk_keyword_limit: selectedDatasetInfo.chunk_keyword_limit
    });
  }, [activeKnowledgeBase, selectedDatasetInfo]);

  useEffect(() => {
    if (!activeKnowledgeBase || selectedDocuments.length === 0) {
      return;
    }
    let cancelled = false;
    const missing = selectedDocuments
      .map((document) => document.document_id)
      .filter((documentId) => !statsByDocument[documentId]);
    if (missing.length === 0) {
      return;
    }
    Promise.all(missing.map((documentId) => getDocumentIndexStats(documentId)))
      .then((items) => {
        if (cancelled) {
          return;
        }
        setStatsByDocument((current) => {
          const next = { ...current };
          for (const stats of items) {
            next[stats.document_id] = {
              chunks_count: stats.chunks_count,
              latest_job_status: stats.latest_job?.status ?? null,
              keywords: stats.keywords,
              index_profile: stats.index_profile
            };
          }
          return next;
        });
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [activeKnowledgeBase, selectedDocuments, statsByDocument]);

  useEffect(() => {
    setSelectedChunk(null);
    setChunkSearch("");
  }, [activeDocumentId]);

  const selectedJobs = useMemo(() => {
    return jobs.filter((job) => {
      const document = documents.find((item) => item.document_id === job.document_id);
      return document?.knowledge_base === activeKnowledgeBase;
    });
  }, [activeKnowledgeBase, documents, jobs]);

  const indexedDocumentsCount = selectedDocuments.filter((item) => item.status === "indexed").length;
  const pendingDocumentsCount = selectedDocuments.filter((item) => item.status !== "indexed").length;

  const filteredKnowledgeBases = useMemo(() => {
    return [...knowledgeBases].sort((a, b) => b.document_count - a.document_count || a.name.localeCompare(b.name));
  }, [knowledgeBases]);

  const pagedKnowledgeBases = useMemo(() => {
    const start = (datasetPage - 1) * datasetPageSize;
    return filteredKnowledgeBases.slice(start, start + datasetPageSize);
  }, [datasetPage, datasetPageSize, filteredKnowledgeBases]);

  const datasetPageCount = Math.max(1, Math.ceil(filteredKnowledgeBases.length / datasetPageSize));

  const visibleChunks = useMemo(() => {
    const chunks = documentChunksQuery.data?.chunks ?? [];
    const query = chunkSearch.trim().toLowerCase();
    if (!query) {
      return chunks;
    }
    return chunks.filter((chunk) => {
      const haystack = [chunk.content, chunk.section, chunk.keywords.join(" "), chunk.heading_path.join(" ")]
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });
  }, [chunkSearch, documentChunksQuery.data?.chunks]);

  function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || !knowledgeBase.trim()) {
      return;
    }
    const tags = tagsText
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    uploadMutation.mutate({
      file,
      sourceName: sourceName.trim(),
      tags,
      knowledgeBase: knowledgeBase.trim()
    });
  }

  function submitKnowledgeBaseCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!newKnowledgeBaseName.trim()) {
      return;
    }
    createKnowledgeBaseMutation.mutate(newKnowledgeBaseName.trim());
  }

  function submitKnowledgeBaseSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeKnowledgeBase) {
      return;
    }
    updateKnowledgeBaseMutation.mutate({
      name: activeKnowledgeBase,
      payload: {
        profile_mode: knowledgeBaseSettings.profile_mode,
        chunk_size_tokens: knowledgeBaseSettings.chunk_size_tokens,
        chunk_overlap_tokens: knowledgeBaseSettings.chunk_overlap_tokens,
        chunk_keyword_limit: knowledgeBaseSettings.chunk_keyword_limit
      }
    });
  }

  function applyProfilePreset(profileMode: keyof typeof PROFILE_PRESETS) {
    const preset = PROFILE_PRESETS[profileMode];
    setKnowledgeBaseSettings({
      profile_mode: profileMode,
      chunk_size_tokens: preset.chunk_size_tokens,
      chunk_overlap_tokens: preset.chunk_overlap_tokens,
      chunk_keyword_limit: preset.chunk_keyword_limit
    });
  }

  function handleRenameKnowledgeBase(currentName: string) {
    const nextName = window.prompt("Новое имя базы знаний", currentName)?.trim();
    if (!nextName || nextName === currentName) {
      return;
    }
    renameKnowledgeBaseMutation.mutate({ currentName, nextName });
  }

  function handleDeleteKnowledgeBase(item: KnowledgeBaseItem) {
    if (item.document_count > 0) {
      return;
    }
    if (!window.confirm(`Удалить базу знаний "${item.name}"?`)) {
      return;
    }
    deleteKnowledgeBaseMutation.mutate(item.name);
  }

  function renderDatasetGrid() {
    return (
      <div className="documents-layout">
        <div className="panel dataset-page-head">
          <div className="panel-head">
            <div>
              <span className="section-kicker">Dataset</span>
              <h2>Knowledge bases</h2>
              <p>Выбери базу знаний, затем работай с документами и индексацией внутри отдельного экрана.</p>
            </div>
            <div className="dataset-top-actions">
              <button className="secondary-action" type="button" onClick={() => setIsCreateKnowledgeBaseOpen(true)}>
                Create Knowledge Base
              </button>
            </div>
          </div>
          <div className="dataset-grid">
            {pagedKnowledgeBases.map((item) => (
              <article key={item.name} className="dataset-card">
                <Link className="dataset-card-link" to={`/dataset/${encodeURIComponent(item.name)}`}>
                  <div className="dataset-card-head">
                    <span className="dataset-card-badge">{makeDatasetBadge(item.name)}</span>
                    <span className="dataset-pill">{item.profile_mode}</span>
                  </div>
                  <div className="stack-xs">
                    <strong className="dataset-card-title">{item.name}</strong>
                    <span className="muted">{item.document_count} files</span>
                  </div>
                  <div className="dataset-card-metrics">
                    <span>{item.chunk_size_tokens} tokens</span>
                    <span>{item.chunk_keyword_limit} kw/chunk</span>
                  </div>
                </Link>
                <div className="dataset-card-actions">
                  <button type="button" className="card-icon-btn" onClick={() => handleRenameKnowledgeBase(item.name)}>
                    Rename
                  </button>
                  <button
                    type="button"
                    className="card-icon-btn danger"
                    disabled={item.document_count > 0}
                    onClick={() => handleDeleteKnowledgeBase(item)}
                  >
                    Delete
                  </button>
                </div>
              </article>
            ))}
          </div>
          <div className="dataset-pagination">
            <div className="dataset-page-size">
              <span>Show</span>
              <select value={datasetPageSize} onChange={(event) => setDatasetPageSize(Number(event.target.value))}>
                <option value={6}>6</option>
                <option value={8}>8</option>
                <option value={12}>12</option>
                <option value={16}>16</option>
              </select>
            </div>
            <div className="dataset-page-controls">
              <button type="button" className="ghost-action" disabled={datasetPage <= 1} onClick={() => setDatasetPage((page) => Math.max(1, page - 1))}>
                Назад
              </button>
              <span>
                Page {datasetPage} / {datasetPageCount}
              </span>
              <button
                type="button"
                className="ghost-action"
                disabled={datasetPage >= datasetPageCount}
                onClick={() => setDatasetPage((page) => Math.min(datasetPageCount, page + 1))}
              >
                Далее
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  function renderDatasetDetail() {
    return (
      <div className="documents-layout">
        <section className="panel dataset-detail-shell">
          <div className="dataset-detail-top">
            <div className="dataset-breadcrumbs">
              <Link to="/dataset">Dataset</Link>
              <span>/</span>
              <span>{activeKnowledgeBase}</span>
            </div>
            <div className="dataset-detail-head">
              <div className="dataset-detail-copy">
                <div className="dataset-card-head">
                  <span className="dataset-card-badge">{makeDatasetBadge(activeKnowledgeBase)}</span>
                  <span className="dataset-pill">{selectedDatasetInfo?.profile_mode ?? "balanced"}</span>
                </div>
                <h2>{activeKnowledgeBase}</h2>
                <p>Документы внутри базы знаний. Нажми на документ, чтобы открыть чанки и их keywords.</p>
              </div>
              <div className="dataset-detail-actions">
                <button type="button" className="secondary-action" onClick={() => setIsSettingsOpen(true)}>
                  Knowledge Base Settings
                </button>
                <Link to="/dataset" className="ghost-action dataset-back-link">
                  Все базы знаний
                </Link>
              </div>
            </div>
            <div className="dataset-overview-grid">
              <article className="summary-chip-card">
                <span>Total documents</span>
                <strong>{selectedDocuments.length}</strong>
              </article>
              <article className="summary-chip-card">
                <span>Indexed</span>
                <strong>{indexedDocumentsCount}</strong>
              </article>
              <article className="summary-chip-card">
                <span>Pending</span>
                <strong>{pendingDocumentsCount}</strong>
              </article>
              <article className="summary-chip-card">
                <span>Chunk size</span>
                <strong>{selectedDatasetInfo?.chunk_size_tokens ?? knowledgeBaseSettings.chunk_size_tokens}</strong>
              </article>
            </div>
          </div>

          <div className="dataset-detail-grid">
            <aside className="dataset-side-rail">
              <form className="upload-form dataset-upload-panel" onSubmit={submitUpload}>
                <div className="section-head-row">
                  <div>
                    <h3>Add document</h3>
                    <p className="muted">Загрузка документа сразу в выбранную базу знаний.</p>
                  </div>
                </div>
                <label>
                  <span>Файл</span>
                  <input
                    type="file"
                    accept=".txt,.pdf,.docx"
                    onChange={(event) => {
                      const selected = event.target.files?.[0] ?? null;
                      setFile(selected);
                    }}
                  />
                </label>
                <label>
                  <span>Source name</span>
                  <input type="text" value={sourceName} placeholder="Например: ГОСТ 17375" onChange={(event) => setSourceName(event.target.value)} />
                </label>
                <label>
                  <span>Tags</span>
                  <input type="text" value={tagsText} placeholder="gost, bends" onChange={(event) => setTagsText(event.target.value)} />
                </label>
                <button className="primary-action" type="submit" disabled={!file || uploadMutation.isPending}>
                  {uploadMutation.isPending ? "Загрузка..." : "Add file"}
                </button>
              </form>

              <section className="subpanel">
                <div className="section-head-row">
                  <div>
                    <h3>Recent jobs</h3>
                    <p className="muted">Последние операции по этой базе знаний.</p>
                  </div>
                </div>
                <div className="jobs-list compact-jobs-list">
                  {selectedJobs.length === 0 && <p className="muted">Пока нет jobs.</p>}
                  {selectedJobs.slice(0, 6).map((job) => (
                    <article className="job-card" key={job.job_id}>
                      <div className="job-head">
                        <strong>{job.status}</strong>
                        <span>{job.progress}%</span>
                      </div>
                      <div className="job-body">
                        <p>{job.job_id}</p>
                        <p>{job.document_id}</p>
                        <p className="muted">{formatIso(job.started_at)}</p>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            </aside>

            <section className="dataset-main-stage">
              <div className="section-head-row">
                <div>
                  <h3>Documents</h3>
                  <p className="muted">Открывай документ, чтобы посмотреть чанки и auto-generated keywords.</p>
                </div>
              </div>
              {selectedDocuments.length === 0 ? (
                <div className="chat-empty-state">
                  <p className="muted">В этой базе знаний пока нет документов.</p>
                </div>
              ) : (
                <div className="dataset-document-list">
                  {selectedDocuments.map((document) => {
                    const stats = statsByDocument[document.document_id];
                    const docJobs = jobsByDocument.get(document.document_id) ?? [];
                    const hasRunning = docJobs.some((job) => job.status === "queued" || job.status === "running");
                    return (
                      <article
                        key={document.document_id}
                        className="dataset-document-card"
                        role="button"
                        tabIndex={0}
                        onClick={() =>
                          navigate(`/dataset/${encodeURIComponent(activeKnowledgeBase)}/documents/${document.document_id}`)
                        }
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            navigate(`/dataset/${encodeURIComponent(activeKnowledgeBase)}/documents/${document.document_id}`);
                          }
                        }}
                      >
                        <div className="dataset-document-copy">
                          <strong>{document.file_name}</strong>
                          <span className="muted">
                            {formatBytes(document.size_bytes)} · {formatIso(document.created_at)}
                          </span>
                          {stats?.keywords?.length ? (
                            <div className="dataset-keyword-preview">
                              {stats.keywords.slice(0, 4).map((keyword) => (
                                <span className="chip muted-chip" key={`${document.document_id}-${keyword}`}>
                                  {keyword}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="muted">Keywords появятся после индексации.</span>
                          )}
                        </div>
                        <div className="dataset-document-meta">
                          <span className={`document-status-badge status-${document.status}`}>{document.status}</span>
                          <span>{stats?.chunks_count ?? "—"} chunks</span>
                          <span>{document.tags.length ? document.tags.join(", ") : "—"}</span>
                        </div>
                        <div className="dataset-document-actions" onClick={(event) => event.stopPropagation()}>
                          <button
                            type="button"
                            className="secondary-action"
                            disabled={indexMutation.isPending || hasRunning}
                            onClick={() => indexMutation.mutate(document.document_id)}
                          >
                            {hasRunning ? "В процессе..." : "Индексировать"}
                          </button>
                          <button
                            type="button"
                            className="danger-action"
                            disabled={deleteMutation.isPending || hasRunning}
                            onClick={() => deleteMutation.mutate(document.document_id)}
                          >
                            Удалить
                          </button>
                        </div>
                      </article>
                    );
                  })}
                </div>
              )}
            </section>
          </div>
        </section>
      </div>
    );
  }

  function renderDocumentDetail() {
    if (!activeDocument) {
      return (
        <div className="documents-layout">
          <section className="panel">
            <p className="muted">Документ не найден в выбранной базе знаний.</p>
          </section>
        </div>
      );
    }

    return (
      <div className="documents-layout">
        <section className="panel dataset-document-shell">
          <div className="dataset-breadcrumbs">
            <Link to="/dataset">Dataset</Link>
            <span>/</span>
            <Link to={`/dataset/${encodeURIComponent(activeKnowledgeBase)}`}>{activeKnowledgeBase}</Link>
            <span>/</span>
            <span>{activeDocument.file_name}</span>
          </div>

          <div className="dataset-document-top">
            <div>
              <span className="section-kicker">Document</span>
              <h2>{activeDocument.file_name}</h2>
              <p>
                {formatBytes(activeDocument.size_bytes)} · {formatIso(activeDocument.created_at)} · {documentChunksQuery.data?.chunks.length ?? 0} chunks
              </p>
            </div>
            <div className="dataset-detail-actions">
              <button type="button" className="secondary-action" onClick={() => setIsSettingsOpen(true)}>
                Knowledge Base Settings
              </button>
              <Link to={`/dataset/${encodeURIComponent(activeKnowledgeBase)}`} className="ghost-action">
                К документам
              </Link>
            </div>
          </div>

          <div className="dataset-document-meta-grid">
            <article className="summary-chip-card">
              <span>Status</span>
              <strong>{activeDocument.status}</strong>
            </article>
            <article className="summary-chip-card">
              <span>Source</span>
              <strong>{activeDocument.source_name || "—"}</strong>
            </article>
            <article className="summary-chip-card">
              <span>Tags</span>
              <strong>{activeDocument.tags.length ? activeDocument.tags.join(", ") : "—"}</strong>
            </article>
            <article className="summary-chip-card">
              <span>Chunk keywords</span>
              <strong>{selectedDatasetInfo?.chunk_keyword_limit ?? knowledgeBaseSettings.chunk_keyword_limit}</strong>
            </article>
          </div>

          <div className="dataset-chunks-toolbar">
            <div className="section-head-row">
              <div>
                <h3>Chunks</h3>
                <p className="muted">Нажми на чанк, чтобы открыть полный текст и keywords.</p>
              </div>
            </div>
            <input
              type="search"
              value={chunkSearch}
              placeholder="Поиск по чанкам и keywords"
              onChange={(event) => setChunkSearch(event.target.value)}
            />
          </div>

          <div className="dataset-chunk-list">
            {documentChunksQuery.isLoading && <p className="muted">Загрузка чанков...</p>}
            {documentChunksQuery.isError && (
              <p className="muted">{resolveAppError(documentChunksQuery.error, appErrorCopy.ru).message}</p>
            )}
            {!documentChunksQuery.isLoading && !visibleChunks.length && <p className="muted">Нет чанков для отображения.</p>}
            {visibleChunks.map((chunk) => (
              <article
                key={chunk.chunk_id}
                className="dataset-chunk-card"
                role="button"
                tabIndex={0}
                onClick={() => setSelectedChunk(chunk)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    setSelectedChunk(chunk);
                  }
                }}
              >
                <div className="dataset-chunk-head">
                  <div>
                    <strong>Chunk #{chunk.chunk_index + 1}</strong>
                    <span className="muted">
                      {chunk.page ? `page ${chunk.page}` : "page —"}
                      {chunk.section ? ` · ${chunk.section}` : ""}
                    </span>
                  </div>
                  <div className="dataset-chunk-meta">
                    {chunk.block_type ? <span className="dataset-pill subtle">{chunk.block_type}</span> : null}
                    <span>{chunk.token_count} tokens</span>
                  </div>
                </div>
                <p>{chunkPreview(chunk.content)}</p>
                <div className="dataset-keyword-preview">
                  {chunk.keywords.map((keyword) => (
                    <span className="chip muted-chip" key={`${chunk.chunk_id}-${keyword}`}>
                      {keyword}
                    </span>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    );
  }

  const pageError = (
    documentsQuery.error ??
      jobsQuery.error ??
      knowledgeBasesQuery.error ??
      uploadMutation.error ??
      createKnowledgeBaseMutation.error ??
      renameKnowledgeBaseMutation.error ??
      deleteKnowledgeBaseMutation.error ??
      updateKnowledgeBaseMutation.error ??
      reindexKnowledgeBaseMutation.error ??
      indexMutation.error ??
      deleteMutation.error ??
      documentChunksQuery.error
  );

  return (
    <div className="page-section">
      {pageError ? <ErrorBanner error={pageError} copy={appErrorCopy.ru} className="status status-error" /> : null}

      {activeKnowledgeBase ? (activeDocumentId ? renderDocumentDetail() : renderDatasetDetail()) : renderDatasetGrid()}

      {isCreateKnowledgeBaseOpen ? (
        <div className="overlay-backdrop" onClick={() => setIsCreateKnowledgeBaseOpen(false)}>
          <section className="overlay-modal" onClick={(event) => event.stopPropagation()}>
            <div className="overlay-head">
              <div>
                <span className="section-kicker">Dataset</span>
                <h3>Create Knowledge Base</h3>
              </div>
              <button type="button" className="overlay-close" onClick={() => setIsCreateKnowledgeBaseOpen(false)}>
                ×
              </button>
            </div>
            <form className="overlay-form" onSubmit={submitKnowledgeBaseCreate}>
              <label>
                <span>Name</span>
                <input
                  type="text"
                  value={newKnowledgeBaseName}
                  placeholder="Например: СДТ Отводы"
                  onChange={(event) => setNewKnowledgeBaseName(event.target.value)}
                />
              </label>
              <div className="overlay-actions">
                <button type="button" className="ghost-action" onClick={() => setIsCreateKnowledgeBaseOpen(false)}>
                  Отмена
                </button>
                <button type="submit" className="primary-action" disabled={createKnowledgeBaseMutation.isPending}>
                  {createKnowledgeBaseMutation.isPending ? "Создание..." : "Create Knowledge Base"}
                </button>
              </div>
            </form>
          </section>
        </div>
      ) : null}

      {isSettingsOpen && activeKnowledgeBase ? (
        <div className="overlay-backdrop" onClick={() => setIsSettingsOpen(false)}>
          <section className="overlay-modal settings-modal" onClick={(event) => event.stopPropagation()}>
            <div className="overlay-head">
              <div>
                <span className="section-kicker">Settings</span>
                <h3>Knowledge Base Settings</h3>
                <p className="muted">Одна кнопка открытия, спокойный modal, только то, что реально влияет на индекс.</p>
              </div>
              <button type="button" className="overlay-close" onClick={() => setIsSettingsOpen(false)}>
                ×
              </button>
            </div>
            <form className="overlay-form" onSubmit={submitKnowledgeBaseSettings}>
              <label>
                <span>Preset</span>
                <select
                  value={knowledgeBaseSettings.profile_mode}
                  onChange={(event) => applyProfilePreset(event.target.value as keyof typeof PROFILE_PRESETS)}
                >
                  <option value="precision">Precision</option>
                  <option value="balanced">Balanced</option>
                  <option value="recall">Recall</option>
                </select>
              </label>
              <div className="settings-form-grid">
                <label>
                  <span>Chunk size</span>
                  <input
                    type="number"
                    min={128}
                    max={480}
                    value={knowledgeBaseSettings.chunk_size_tokens}
                    onChange={(event) =>
                      setKnowledgeBaseSettings((current) => ({
                        ...current,
                        chunk_size_tokens: Number(event.target.value)
                      }))
                    }
                  />
                </label>
                <label>
                  <span>Overlap</span>
                  <input
                    type="number"
                    min={0}
                    max={479}
                    value={knowledgeBaseSettings.chunk_overlap_tokens}
                    onChange={(event) =>
                      setKnowledgeBaseSettings((current) => ({
                        ...current,
                        chunk_overlap_tokens: Number(event.target.value)
                      }))
                    }
                  />
                </label>
                <label>
                  <span>Keywords per chunk</span>
                  <input
                    type="number"
                    min={1}
                    max={32}
                    value={knowledgeBaseSettings.chunk_keyword_limit}
                    onChange={(event) =>
                      setKnowledgeBaseSettings((current) => ({
                        ...current,
                        chunk_keyword_limit: Number(event.target.value)
                      }))
                    }
                  />
                </label>
              </div>
              <div className="overlay-actions">
                <button
                  type="button"
                  className="ghost-action"
                  disabled={reindexKnowledgeBaseMutation.isPending}
                  onClick={() => reindexKnowledgeBaseMutation.mutate(activeKnowledgeBase)}
                >
                  {reindexKnowledgeBaseMutation.isPending ? "Реиндексация..." : "Reindex all"}
                </button>
                <button type="submit" className="primary-action" disabled={updateKnowledgeBaseMutation.isPending}>
                  {updateKnowledgeBaseMutation.isPending ? "Сохранение..." : "Save settings"}
                </button>
              </div>
            </form>
          </section>
        </div>
      ) : null}

      {selectedChunk ? (
        <div className="overlay-backdrop" onClick={() => setSelectedChunk(null)}>
          <section className="overlay-modal chunk-modal" onClick={(event) => event.stopPropagation()}>
            <div className="overlay-head">
              <div>
                <span className="section-kicker">Chunk</span>
                <h3>Chunk #{selectedChunk.chunk_index + 1}</h3>
                <p className="muted">
                  {selectedChunk.page ? `page ${selectedChunk.page}` : "page —"}
                  {selectedChunk.section ? ` · ${selectedChunk.section}` : ""}
                </p>
              </div>
              <button type="button" className="overlay-close" onClick={() => setSelectedChunk(null)}>
                ×
              </button>
            </div>
            <div className="chunk-modal-body">
              <section className="chunk-content-panel">
                <span className="meta-label">Chunk</span>
                <div className="chunk-content-box">{selectedChunk.content}</div>
              </section>
              <section className="chunk-keywords-panel">
                <span className="meta-label">Keywords</span>
                <div className="dataset-keyword-preview">
                  {selectedChunk.keywords.map((keyword) => (
                    <span className="chip" key={`${selectedChunk.chunk_id}-modal-${keyword}`}>
                      {keyword}
                    </span>
                  ))}
                </div>
                {selectedChunk.heading_path.length ? (
                  <>
                    <span className="meta-label">Heading path</span>
                    <div className="dataset-keyword-preview">
                      {selectedChunk.heading_path.map((item) => (
                        <span className="chip muted-chip" key={`${selectedChunk.chunk_id}-heading-${item}`}>
                          {item}
                        </span>
                      ))}
                    </div>
                  </>
                ) : null}
              </section>
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
