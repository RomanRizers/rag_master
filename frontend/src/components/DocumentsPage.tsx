import { useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
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

export function DocumentsPage() {
  const queryClient = useQueryClient();

  const [file, setFile] = useState<File | null>(null);
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
      setFile(null);
      setSourceName("");
      setTagsText("");
      setKnowledgeBase("default");
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

  const recentJobs = useMemo(() => jobs.slice(0, 10), [jobs]);

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
      knowledgeBase
    });
  }

  const knowledgeBases = knowledgeBasesQuery.data?.knowledge_bases ?? [];

  return (
    <div className="workspace-grid">
      <section className="panel">
        <div className="panel-head">
          <h2>Documents</h2>
          <p>Загрузка и индексация файлов в RAG-пайплайн.</p>
        </div>

        <form className="upload-form" onSubmit={submitUpload}>
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
              placeholder="Например: HR handbook"
              onChange={(event) => setSourceName(event.target.value)}
            />
          </label>
          <label>
            <span>Теги (через запятую)</span>
            <input
              type="text"
              value={tagsText}
              placeholder="finance, legal"
              onChange={(event) => setTagsText(event.target.value)}
            />
          </label>
          <label>
            <span>База знаний</span>
            <input
              type="text"
              list="knowledge-base-options"
              value={knowledgeBase}
              placeholder="Например: policies"
              onChange={(event) => setKnowledgeBase(event.target.value)}
            />
            <datalist id="knowledge-base-options">
              {knowledgeBases.map((item) => (
                <option key={item.name} value={item.name} />
              ))}
            </datalist>
          </label>
          <button className="primary-action" type="submit" disabled={!file || uploadMutation.isPending}>
            {uploadMutation.isPending ? "Загрузка..." : "Загрузить"}
          </button>
        </form>

        {(
          uploadMutation.isError ||
          documentsQuery.isError ||
          indexMutation.isError ||
          statsMutation.isError ||
          deleteMutation.isError
        ) && (
          <ErrorBanner
            error={
              uploadMutation.error ??
              documentsQuery.error ??
              indexMutation.error ??
              statsMutation.error ??
              deleteMutation.error
            }
            copy={appErrorCopy.ru}
            className="inline-error"
          />
        )}

        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Файл</th>
                <th>Размер</th>
                <th>База знаний</th>
                <th>Теги</th>
                <th>Статус</th>
                <th>Chunks</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.length === 0 && (
                <tr>
                  <td colSpan={7}>Документы пока не загружены.</td>
                </tr>
              )}
              {documents.map((document: DocumentItem) => {
                const stats = statsByDocument[document.document_id];
                const docJobs = jobsByDocument.get(document.document_id) ?? [];
                const hasRunning = docJobs.some((job) => job.status === "queued" || job.status === "running");
                return (
                  <tr key={document.document_id}>
                    <td>
                      <strong>{document.file_name}</strong>
                      <div className="muted">{formatIso(document.created_at)}</div>
                    </td>
                    <td>{formatBytes(document.size_bytes)}</td>
                    <td>{document.knowledge_base}</td>
                    <td>{document.tags.length ? document.tags.join(", ") : "—"}</td>
                    <td>{document.status}</td>
                    <td>{stats?.chunks_count ?? "—"}</td>
                    <td>
                      <div className="table-actions">
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
                          Обновить stats
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
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>Jobs</h2>
          <p>Последние задачи индексации.</p>
        </div>
        <div className="jobs-list">
          {recentJobs.length === 0 && <p className="muted">Пока нет jobs.</p>}
          {recentJobs.map((job) => (
            <article className="job-card" key={job.job_id}>
              <div className="job-head">
                <strong>{job.status}</strong>
                <span>{job.progress}%</span>
              </div>
              <div className="job-body">
                <p>job: {job.job_id}</p>
                <p>document: {job.document_id}</p>
                <p>attempt: {job.attempt}</p>
                {job.error_message && <p className="inline-error">{job.error_message}</p>}
                <p className="muted">
                  {formatIso(job.started_at)} → {formatIso(job.finished_at)}
                </p>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
