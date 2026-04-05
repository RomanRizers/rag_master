import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  createKnowledgeBase,
  deleteDocument,
  getDocumentIndexStats,
  indexDocument,
  listDocuments,
  listJobs,
  listKnowledgeBases,
  uploadDocument
} from "../api/client";
import type { DocumentItem, JobItem } from "../types";
import { appErrorCopy } from "../utils/appError";
import { ErrorBanner } from "./ErrorBanner";

type StatsByDocument = Record<string, { chunks_count: number; latest_job_status?: string | null }>;

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

export function DocumentsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const params = useParams<{ datasetName?: string }>();

  const [file, setFile] = useState<File | null>(null);
  const [newKnowledgeBaseName, setNewKnowledgeBaseName] = useState("");
  const [datasetPage, setDatasetPage] = useState(1);
  const [datasetPageSize, setDatasetPageSize] = useState(8);
  const [sourceName, setSourceName] = useState("");
  const [tagsText, setTagsText] = useState("");
  const [knowledgeBase, setKnowledgeBase] = useState("default");
  const [statsByDocument, setStatsByDocument] = useState<StatsByDocument>({});

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
      setNewKnowledgeBaseName("");
      setKnowledgeBase(payload.name);
      navigate(`/dataset/${encodeURIComponent(payload.name)}`);
    }
  });

  const indexMutation = useMutation({
    mutationFn: indexDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    }
  });

  const statsMutation = useMutation({
    mutationFn: getDocumentIndexStats,
    onSuccess: (stats) => {
      setStatsByDocument((current) => ({
        ...current,
        [stats.document_id]: {
          chunks_count: stats.chunks_count,
          latest_job_status: stats.latest_job?.status ?? null
        }
      }));
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
      document_count: items.length
    }));
  }, [documentsByKnowledgeBase, knowledgeBasesQuery.data?.knowledge_bases]);

  useEffect(() => {
    setDatasetPage(1);
  }, [datasetPageSize]);

  const activeKnowledgeBase = useMemo(() => {
    const routeValue = params.datasetName ? decodeURIComponent(params.datasetName) : "";
    if (!routeValue) {
      return "";
    }

    const exists = knowledgeBases.some((item) => item.name === routeValue);
    return exists ? routeValue : "";
  }, [knowledgeBases, params.datasetName]);

  useEffect(() => {
    if (activeKnowledgeBase) {
      setKnowledgeBase(activeKnowledgeBase);
    }
  }, [activeKnowledgeBase]);

  const selectedDocuments = activeKnowledgeBase
    ? documentsByKnowledgeBase.get(activeKnowledgeBase) ?? []
    : documents;

  const selectedJobs = useMemo(() => {
    const ids = new Set(selectedDocuments.map((document) => document.document_id));
    return jobs.filter((job) => ids.has(job.document_id)).slice(0, 8);
  }, [jobs, selectedDocuments]);

  const indexedDocumentsCount = useMemo(
    () => selectedDocuments.filter((item) => item.status === "indexed").length,
    [selectedDocuments]
  );

  const selectedDatasetInfo = knowledgeBases.find((item) => item.name === activeKnowledgeBase);
  const totalDatasetPages = Math.max(1, Math.ceil(knowledgeBases.length / datasetPageSize));
  const currentDatasetPage = Math.min(datasetPage, totalDatasetPages);
  const visibleKnowledgeBases = knowledgeBases.slice(
    (currentDatasetPage - 1) * datasetPageSize,
    currentDatasetPage * datasetPageSize
  );

  function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      return;
    }
    const tags = tagsText
      .split(",")
      .map((tag) => tag.trim())
      .filter((tag) => tag.length > 0);

    uploadMutation.mutate({
      file,
      sourceName,
      tags,
      knowledgeBase: activeKnowledgeBase || knowledgeBase
    });
  }

  function submitKnowledgeBaseCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = newKnowledgeBaseName.trim();
    if (!trimmed) {
      return;
    }
    createKnowledgeBaseMutation.mutate(trimmed);
  }

  return (
    <div className="page-section">
      {(uploadMutation.isError ||
        createKnowledgeBaseMutation.isError ||
        documentsQuery.isError ||
        indexMutation.isError ||
        statsMutation.isError ||
        deleteMutation.isError) && (
        <ErrorBanner
          error={
            uploadMutation.error ??
            createKnowledgeBaseMutation.error ??
            documentsQuery.error ??
            indexMutation.error ??
            statsMutation.error ??
            deleteMutation.error
          }
          copy={appErrorCopy.ru}
          className="inline-error"
        />
      )}

      {!activeKnowledgeBase && (
        <section className="dataset-board panel">
          <div className="dataset-board-head">
            <div className="panel-head">
              <div>
                <span className="section-kicker">Dataset</span>
                <h2>Knowledge Bases</h2>
                <p>Сначала выбери базу знаний, затем работай с документами внутри неё.</p>
              </div>
            </div>
            <div className="dataset-board-actions">
              <span className="chip">{knowledgeBases.length} баз</span>
              <span className="chip">{documents.length} документов</span>
              <label className="dataset-page-size">
                <span>Показывать</span>
                <select
                  value={datasetPageSize}
                  onChange={(event) => setDatasetPageSize(Number(event.target.value))}
                >
                  <option value={6}>6</option>
                  <option value={8}>8</option>
                  <option value={12}>12</option>
                  <option value={16}>16</option>
                </select>
              </label>
              <form className="dataset-create-form" onSubmit={submitKnowledgeBaseCreate}>
                <input
                  type="text"
                  value={newKnowledgeBaseName}
                  placeholder="Новая база знаний"
                  onChange={(event) => setNewKnowledgeBaseName(event.target.value)}
                />
                <button
                  type="submit"
                  className="primary-action"
                  disabled={createKnowledgeBaseMutation.isPending || !newKnowledgeBaseName.trim()}
                >
                  {createKnowledgeBaseMutation.isPending ? "Создание..." : "Create Dataset"}
                </button>
              </form>
            </div>
          </div>

          <div className="dataset-grid">
            {visibleKnowledgeBases.map((item) => {
              const kbDocuments = documentsByKnowledgeBase.get(item.name) ?? [];
              const newestDocument = kbDocuments
                .slice()
                .sort((left, right) => (left.created_at < right.created_at ? 1 : -1))[0];
              const indexedCount = kbDocuments.filter((document) => document.status === "indexed").length;

              return (
                <button
                  key={item.name}
                  type="button"
                  className="dataset-tile"
                  onClick={() => {
                    setKnowledgeBase(item.name);
                    navigate(`/dataset/${encodeURIComponent(item.name)}`);
                  }}
                >
                  <div className="dataset-tile-badge">{makeDatasetBadge(item.name)}</div>
                  <div className="dataset-tile-copy">
                    <div className="dataset-tile-topline">
                      <strong>{item.name}</strong>
                      <span className="dataset-tile-count">{item.document_count} files</span>
                    </div>
                    <div className="dataset-tile-metrics">
                      <span className="dataset-pill">{indexedCount} indexed</span>
                      <span className="dataset-pill">{item.document_count - indexedCount} pending</span>
                    </div>
                    <span>{newestDocument ? formatIso(newestDocument.created_at) : "empty dataset"}</span>
                  </div>
                </button>
              );
            })}
          </div>

          {knowledgeBases.length > datasetPageSize && (
            <div className="dataset-pagination">
              <span className="muted">
                Page {currentDatasetPage} / {totalDatasetPages}
              </span>
              <div className="dataset-pagination-actions">
                <button
                  type="button"
                  className="secondary-action"
                  disabled={currentDatasetPage <= 1}
                  onClick={() => setDatasetPage((current) => Math.max(1, current - 1))}
                >
                  Назад
                </button>
                <button
                  type="button"
                  className="secondary-action"
                  disabled={currentDatasetPage >= totalDatasetPages}
                  onClick={() => setDatasetPage((current) => Math.min(totalDatasetPages, current + 1))}
                >
                  Далее
                </button>
              </div>
            </div>
          )}
        </section>
      )}

      {activeKnowledgeBase && (
        <section className="dataset-detail-layout">
          <aside className="dataset-sidebar panel">
            <div className="dataset-breadcrumbs">
              <Link to="/dataset">Dataset</Link>
              <span>/</span>
              <span>{activeKnowledgeBase}</span>
            </div>
            <div className="dataset-sidebar-header">
              <div className="dataset-sidebar-badge">{makeDatasetBadge(activeKnowledgeBase)}</div>
              <div className="stack-xs">
                <strong className="dataset-sidebar-title">{activeKnowledgeBase}</strong>
                <span className="muted">
                  {selectedDatasetInfo?.document_count ?? selectedDocuments.length} files
                </span>
              </div>
            </div>

            <div className="dataset-sidebar-stats">
              <article className="summary-chip-card">
                <span>Indexed</span>
                <strong>{indexedDocumentsCount}</strong>
              </article>
              <article className="summary-chip-card">
                <span>Total</span>
                <strong>{selectedDocuments.length}</strong>
              </article>
            </div>

            <form className="upload-form dataset-upload-form" onSubmit={submitUpload}>
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
                <input
                  type="text"
                  value={sourceName}
                  placeholder="Например: ГОСТ 30753"
                  onChange={(event) => setSourceName(event.target.value)}
                />
              </label>
              <label>
                <span>Теги</span>
                <input
                  type="text"
                value={tagsText}
                placeholder="gost, fittings"
                onChange={(event) => setTagsText(event.target.value)}
              />
              </label>
              <button className="primary-action" type="submit" disabled={!file || uploadMutation.isPending}>
                {uploadMutation.isPending ? "Загрузка..." : "Добавить документ"}
              </button>
            </form>
          </aside>

          <section className="dataset-main panel">
            <div className="dataset-main-head">
              <div className="panel-head">
                <div>
                  <span className="section-kicker">Dataset</span>
                  <h2>{activeKnowledgeBase}</h2>
                  <p>Документы, индексация и статусы внутри выбранной базы знаний.</p>
                </div>
              </div>
              <Link to="/dataset" className="secondary-action dataset-back-link">
                Все базы знаний
              </Link>
            </div>

            {selectedDocuments.length === 0 ? (
              <div className="chat-empty-state">
                <p className="muted">В этой базе знаний пока нет документов.</p>
              </div>
            ) : (
              <div className="dataset-table-wrap">
                <div className="dataset-table">
                  <div className="dataset-table-head">
                    <span>Name</span>
                    <span>Upload date</span>
                    <span>Status</span>
                    <span>Chunks</span>
                    <span>Tags</span>
                    <span>Action</span>
                  </div>

                  {selectedDocuments.map((document) => {
                    const stats = statsByDocument[document.document_id];
                    const docJobs = jobsByDocument.get(document.document_id) ?? [];
                    const hasRunning = docJobs.some((job) => job.status === "queued" || job.status === "running");

                    return (
                      <article key={document.document_id} className="dataset-row">
                        <div className="dataset-cell dataset-cell-name">
                          <strong>{document.file_name}</strong>
                          <span className="muted">{formatBytes(document.size_bytes)}</span>
                        </div>
                        <div className="dataset-cell">
                          <span>{formatIso(document.created_at)}</span>
                        </div>
                        <div className="dataset-cell">
                          <span className={`document-status-badge status-${document.status}`}>{document.status}</span>
                        </div>
                        <div className="dataset-cell">
                          <span>{stats?.chunks_count ?? "—"}</span>
                        </div>
                        <div className="dataset-cell">
                          <span>{document.tags.length ? document.tags.join(", ") : "—"}</span>
                        </div>
                        <div className="dataset-cell dataset-cell-actions">
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
                            className="ghost-action"
                            disabled={statsMutation.isPending || deleteMutation.isPending}
                            onClick={() => statsMutation.mutate(document.document_id)}
                          >
                            Stats
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
              </div>
            )}

            <section className="subpanel">
              <div className="section-head-row">
                <div>
                  <h3>Recent jobs</h3>
                  <p className="muted">Последние операции по этой базе знаний.</p>
                </div>
              </div>

              <div className="jobs-list compact-jobs-list">
                {selectedJobs.length === 0 && <p className="muted">Пока нет jobs.</p>}
                {selectedJobs.map((job) => (
                  <article className="job-card" key={job.job_id}>
                    <div className="job-head">
                      <strong>{job.status}</strong>
                      <span>{job.progress}%</span>
                    </div>
                    <div className="job-body">
                      <p>{job.job_id}</p>
                      <p>{job.document_id}</p>
                      <p className="muted">
                        {formatIso(job.started_at)} → {formatIso(job.finished_at)}
                      </p>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          </section>
        </section>
      )}
    </div>
  );
}
