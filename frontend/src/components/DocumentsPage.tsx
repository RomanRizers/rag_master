import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createKnowledgeBase,
  deleteKnowledgeBase,
  deleteDocument,
  getDocumentIndexStats,
  indexDocument,
  listDocuments,
  listJobs,
  listKnowledgeBases,
  moveKnowledgeBaseDocuments,
  renameKnowledgeBase,
  uploadDocument
} from "../api/client";
import type { DocumentItem, JobItem } from "../types";
import { appErrorCopy } from "../utils/appError";
import { ConfirmModal } from "./ConfirmModal";
import { ErrorBanner } from "./ErrorBanner";

type StatusTone = "uploaded" | "indexing" | "indexed" | "failed";

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
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function deriveDocumentStatus(document: DocumentItem, jobs: JobItem[]): { label: string; tone: StatusTone; detail: string } {
  const activeJob = jobs.find((item) => item.status === "running" || item.status === "queued");
  const failedJob = jobs.find((item) => item.status === "failed");

  if (activeJob) {
    return {
      label: activeJob.status === "running" ? "Индексируется" : "В очереди",
      tone: "indexing",
      detail: `Прогресс ${activeJob.progress}%`
    };
  }

  if (failedJob || document.status === "failed") {
    return {
      label: "Ошибка",
      tone: "failed",
      detail: failedJob?.error_message || "Проверьте job индексации"
    };
  }

  if (document.status === "indexed") {
    return {
      label: "Индексирован",
      tone: "indexed",
      detail: "Готов для поиска и чата"
    };
  }

  return {
    label: "Загружен",
    tone: "uploaded",
    detail: "Ожидает запуска индексации"
  };
}

function knowledgeBaseAccent(index: number): string {
  const accents = ["brand", "accent", "sun", "mint", "violet", "peach"];
  return accents[index % accents.length];
}

export function DocumentsPage() {
  const queryClient = useQueryClient();

  const [selectedKnowledgeBase, setSelectedKnowledgeBase] = useState<string>("default");
  const [createKnowledgeBaseName, setCreateKnowledgeBaseName] = useState("");
  const [renameKnowledgeBaseName, setRenameKnowledgeBaseName] = useState("");
  const [moveTargetKnowledgeBase, setMoveTargetKnowledgeBase] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [sourceName, setSourceName] = useState("");
  const [tagsText, setTagsText] = useState("");
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [activeDocumentId, setActiveDocumentId] = useState<string | null>(null);
  const [documentToDelete, setDocumentToDelete] = useState<DocumentItem | null>(null);
  const [knowledgeBaseToDelete, setKnowledgeBaseToDelete] = useState<string | null>(null);

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

  const documentStatsQuery = useQuery({
    queryKey: ["document-index-stats", activeDocumentId],
    queryFn: () => getDocumentIndexStats(activeDocumentId || ""),
    enabled: Boolean(activeDocumentId),
    refetchInterval: 4000
  });

  const knowledgeBasesQuery = useQuery({
    queryKey: ["knowledge-bases"],
    queryFn: listKnowledgeBases,
    refetchInterval: 7000
  });

  const createKnowledgeBaseMutation = useMutation({
    mutationFn: createKnowledgeBase,
    onSuccess: (item) => {
      queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
      setSelectedKnowledgeBase(item.name);
      setCreateKnowledgeBaseName("");
    }
  });

  const uploadMutation = useMutation({
    mutationFn: (payload: { file: File; sourceName: string; tags: string[]; knowledgeBase: string }) =>
      uploadDocument(payload.file, payload.sourceName, payload.tags, payload.knowledgeBase),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
      setSelectedKnowledgeBase(variables.knowledgeBase);
      setFile(null);
      setSourceName("");
      setTagsText("");
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
    onSuccess: () => {
      setDocumentToDelete(null);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
    }
  });

  const renameKnowledgeBaseMutation = useMutation({
    mutationFn: (payload: { currentName: string; nextName: string }) =>
      renameKnowledgeBase(payload.currentName, payload.nextName),
    onSuccess: (item) => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
      setSelectedKnowledgeBase(item.name);
      setRenameKnowledgeBaseName("");
      setMoveTargetKnowledgeBase("");
      setSelectedDocumentIds([]);
    }
  });

  const deleteKnowledgeBaseMutation = useMutation({
    mutationFn: deleteKnowledgeBase,
    onSuccess: () => {
      setKnowledgeBaseToDelete(null);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
      setSelectedDocumentIds([]);
      setMoveTargetKnowledgeBase("");
    }
  });

  const moveDocumentsMutation = useMutation({
    mutationFn: (payload: { sourceKnowledgeBase: string; documentIds: string[]; targetKnowledgeBase: string }) =>
      moveKnowledgeBaseDocuments(payload.sourceKnowledgeBase, payload.documentIds, payload.targetKnowledgeBase),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
      setSelectedKnowledgeBase(variables.targetKnowledgeBase);
      setMoveTargetKnowledgeBase("");
      setSelectedDocumentIds([]);
    }
  });

  const documents = documentsQuery.data?.documents ?? [];
  const jobs = jobsQuery.data?.jobs ?? [];
  const knowledgeBases = knowledgeBasesQuery.data?.knowledge_bases ?? [];
  const effectiveSelectedKnowledgeBase =
    knowledgeBases.some((item) => item.name === selectedKnowledgeBase)
      ? selectedKnowledgeBase
      : (knowledgeBases[0]?.name ?? selectedKnowledgeBase);

  useEffect(() => {
    if (knowledgeBases.length === 0) {
      return;
    }
    const exists = knowledgeBases.some((item) => item.name === effectiveSelectedKnowledgeBase);
    if (!exists) {
      setSelectedKnowledgeBase(knowledgeBases[0].name);
    }
  }, [knowledgeBases, selectedKnowledgeBase]);

  useEffect(() => {
    setSelectedDocumentIds([]);
    setRenameKnowledgeBaseName("");
    setMoveTargetKnowledgeBase("");
  }, [effectiveSelectedKnowledgeBase]);

  useEffect(() => {
    if (!activeDocumentId) {
      return;
    }
    const exists = documents.some((item) => item.document_id === activeDocumentId);
    if (!exists) {
      setActiveDocumentId(null);
    }
  }, [activeDocumentId, documents]);

  useEffect(() => {
    if (!activeDocumentId) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setActiveDocumentId(null);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeDocumentId]);

  const jobsByDocument = useMemo(() => {
    const grouped = new Map<string, JobItem[]>();
    for (const job of jobs) {
      const existing = grouped.get(job.document_id) ?? [];
      existing.push(job);
      grouped.set(job.document_id, existing);
    }
    return grouped;
  }, [jobs]);

  const selectedDocuments = useMemo(
    () => documents.filter((item) => item.knowledge_base === effectiveSelectedKnowledgeBase),
    [documents, effectiveSelectedKnowledgeBase]
  );

  const selectedDocumentIdSet = useMemo(
    () => new Set(selectedDocuments.map((item) => item.document_id)),
    [selectedDocuments]
  );

  const selectedJobs = useMemo(
    () => jobs.filter((item) => selectedDocumentIdSet.has(item.document_id)).slice(0, 8),
    [jobs, selectedDocumentIdSet]
  );

  const activeKnowledgeBase = useMemo(
    () => knowledgeBases.find((item) => item.name === effectiveSelectedKnowledgeBase) ?? null,
    [knowledgeBases, effectiveSelectedKnowledgeBase]
  );
  const activeDocument = useMemo(
    () => documents.find((item) => item.document_id === activeDocumentId) ?? null,
    [activeDocumentId, documents]
  );

  const totalDocuments = documents.length;
  const indexedDocuments = documents.filter((item) => item.status === "indexed").length;
  const activeJobsCount = jobs.filter((item) => item.status === "queued" || item.status === "running").length;
  const availableMoveTargets = knowledgeBases.filter((item) => item.name !== effectiveSelectedKnowledgeBase);

  function openDocument(documentId: string) {
    const targetUrl = `/api/documents/${encodeURIComponent(documentId)}/content`;
    window.open(targetUrl, "_blank", "noopener,noreferrer");
  }

  function submitKnowledgeBase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!createKnowledgeBaseName.trim()) {
      return;
    }
    createKnowledgeBaseMutation.mutate(createKnowledgeBaseName.trim());
  }

  function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || !effectiveSelectedKnowledgeBase) {
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
      knowledgeBase: effectiveSelectedKnowledgeBase
    });
  }

  function submitRenameKnowledgeBase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!renameKnowledgeBaseName.trim() || !activeKnowledgeBase) {
      return;
    }
    renameKnowledgeBaseMutation.mutate({
      currentName: activeKnowledgeBase.name,
      nextName: renameKnowledgeBaseName.trim()
    });
  }

  function toggleDocumentSelection(documentId: string) {
    setSelectedDocumentIds((current) =>
      current.includes(documentId) ? current.filter((item) => item !== documentId) : [...current, documentId]
    );
  }

  function submitMoveDocuments(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeKnowledgeBase || selectedDocumentIds.length === 0 || !moveTargetKnowledgeBase) {
      return;
    }
    moveDocumentsMutation.mutate({
      sourceKnowledgeBase: activeKnowledgeBase.name,
      documentIds: selectedDocumentIds,
      targetKnowledgeBase: moveTargetKnowledgeBase
    });
  }

  const combinedError =
    createKnowledgeBaseMutation.error ??
    renameKnowledgeBaseMutation.error ??
    deleteKnowledgeBaseMutation.error ??
    moveDocumentsMutation.error ??
    uploadMutation.error ??
    documentsQuery.error ??
    jobsQuery.error ??
    knowledgeBasesQuery.error ??
    indexMutation.error ??
    deleteMutation.error;

  return (
    <div className="dataset-page">
      <section className="panel dataset-hero">
        <div className="dataset-hero-copy">
          <div className="panel-head">
            <h2>Knowledge Datasets</h2>
            <p>База знаний как рабочая единица: выбрал набор, загрузил документы, отслеживаешь индексацию.</p>
          </div>
          <div className="dataset-kpi-grid">
            <article className="documents-kpi-card">
              <span>Баз знаний</span>
              <strong>{knowledgeBases.length}</strong>
            </article>
            <article className="documents-kpi-card">
              <span>Документов</span>
              <strong>{totalDocuments}</strong>
            </article>
            <article className="documents-kpi-card">
              <span>Индексировано</span>
              <strong>{indexedDocuments}</strong>
            </article>
            <article className="documents-kpi-card">
              <span>Активные jobs</span>
              <strong>{activeJobsCount}</strong>
            </article>
          </div>
        </div>

        <form className="dataset-create-form" onSubmit={submitKnowledgeBase}>
          <label>
            <span>Новая база знаний</span>
            <input
              type="text"
              value={createKnowledgeBaseName}
              placeholder="Например: Насосное оборудование"
              onChange={(event) => setCreateKnowledgeBaseName(event.target.value)}
            />
          </label>
          <button type="submit" className="primary-action" disabled={createKnowledgeBaseMutation.isPending}>
            {createKnowledgeBaseMutation.isPending ? "Создание..." : "Создать базу"}
          </button>
          <p className="muted dataset-create-hint">После создания база появится карточкой и станет точкой входа для загрузки документов.</p>
        </form>
      </section>

      {combinedError && <ErrorBanner error={combinedError} copy={appErrorCopy.ru} className="inline-error" />}

      <section className="dataset-card-grid" aria-label="Knowledge bases">
        {knowledgeBases.length === 0 && (
          <article className="dataset-card dataset-card-empty">
            <strong>Пока нет баз знаний</strong>
            <p className="muted">Создай первую базу, затем загружай в неё документы и запускай индексацию.</p>
          </article>
        )}
        {knowledgeBases.map((item, index) => {
          const accent = knowledgeBaseAccent(index);
          const isActive = item.name === effectiveSelectedKnowledgeBase;
          return (
            <button
              key={item.name}
              type="button"
              className={`dataset-card ${isActive ? "active" : ""}`}
              data-accent={accent}
              style={{ animationDelay: `${index * 55}ms` }}
              onClick={() => setSelectedKnowledgeBase(item.name)}
            >
              <span className="dataset-card-badge">{item.name.slice(0, 1).toUpperCase()}</span>
              <div className="dataset-card-body">
                <strong>{item.name}</strong>
                <span>{item.document_count} files</span>
                <span>{formatIso(item.created_at)}</span>
              </div>
            </button>
          );
        })}
      </section>

      <section className="documents-workspace dataset-workspace">
        <section className="documents-main dataset-main">
          <section className="panel dataset-detail-shell">
            <div className="dataset-detail-head">
              <div>
                <span className="dataset-section-kicker">Активная база</span>
                <h2>{activeKnowledgeBase?.name ?? effectiveSelectedKnowledgeBase}</h2>
                <p>
                  {activeKnowledgeBase
                    ? `${activeKnowledgeBase.document_count} документов, создана ${formatIso(activeKnowledgeBase.created_at)}`
                    : "Выбери базу знаний, чтобы увидеть её документы и jobs."}
                </p>
              </div>
              <div className="dataset-detail-stats">
                <article>
                  <span>Документов</span>
                  <strong>{selectedDocuments.length}</strong>
                </article>
                <article>
                  <span>В индексации</span>
                  <strong>{selectedJobs.filter((job) => job.status === "running" || job.status === "queued").length}</strong>
                </article>
                <article>
                  <span>Готово</span>
                  <strong>{selectedDocuments.filter((item) => item.status === "indexed").length}</strong>
                </article>
              </div>
            </div>

            <div className="dataset-toolbar">
              <form className="dataset-toolbar-form" onSubmit={submitRenameKnowledgeBase}>
                <label>
                  <span>Переименовать базу</span>
                  <input
                    type="text"
                    value={renameKnowledgeBaseName}
                    placeholder={activeKnowledgeBase?.name ?? "Новое имя"}
                    onChange={(event) => setRenameKnowledgeBaseName(event.target.value)}
                  />
                </label>
                <button
                  type="submit"
                  className="secondary-action"
                  disabled={!activeKnowledgeBase || !renameKnowledgeBaseName.trim() || renameKnowledgeBaseMutation.isPending}
                >
                  {renameKnowledgeBaseMutation.isPending ? "Сохраняю..." : "Переименовать"}
                </button>
              </form>
              <button
                type="button"
                className="danger-action"
                disabled={!activeKnowledgeBase || activeKnowledgeBase.document_count > 0 || deleteKnowledgeBaseMutation.isPending}
                onClick={() => activeKnowledgeBase && setKnowledgeBaseToDelete(activeKnowledgeBase.name)}
              >
                {deleteKnowledgeBaseMutation.isPending ? "Удаляю..." : "Удалить пустую базу"}
              </button>
            </div>

            <div className="dataset-detail-grid">
              <form className="upload-form dataset-upload-panel" onSubmit={submitUpload}>
                <div className="panel-head">
                  <h3>Добавить документ</h3>
                  <p>Документ попадет в базу `{effectiveSelectedKnowledgeBase}` и затем может быть отправлен в индексацию.</p>
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
                  <input
                    type="text"
                    value={sourceName}
                    placeholder="Например: ГОСТ 30753-2001"
                    onChange={(event) => setSourceName(event.target.value)}
                  />
                </label>
                <label>
                  <span>Теги</span>
                  <input
                    type="text"
                    value={tagsText}
                    placeholder="gost, pipes, fittings"
                    onChange={(event) => setTagsText(event.target.value)}
                  />
                </label>
                <button type="submit" className="primary-action" disabled={!file || uploadMutation.isPending || !effectiveSelectedKnowledgeBase}>
                  {uploadMutation.isPending ? "Загрузка..." : `Загрузить в ${effectiveSelectedKnowledgeBase}`}
                </button>
              </form>

              <aside className="dataset-status-panel">
                <div className="panel-head">
                  <h3>Статусы</h3>
                  <p>Быстрый срез по состояниям документов в выбранной базе.</p>
                </div>
                <div className="dataset-status-stack">
                  <article className="dataset-status-card">
                    <span>Загружено</span>
                    <strong>{selectedDocuments.filter((item) => item.status === "uploaded").length}</strong>
                  </article>
                  <article className="dataset-status-card status-indexing-card">
                    <span>Индексируется</span>
                    <strong>{selectedJobs.filter((job) => job.status === "running" || job.status === "queued").length}</strong>
                  </article>
                  <article className="dataset-status-card status-indexed-card">
                    <span>Индексировано</span>
                    <strong>{selectedDocuments.filter((item) => item.status === "indexed").length}</strong>
                  </article>
                  <article className="dataset-status-card status-failed-card">
                    <span>Ошибки</span>
                    <strong>
                      {
                        selectedDocuments.filter((item) => item.status === "failed").length +
                        selectedJobs.filter((job) => job.status === "failed").length
                      }
                    </strong>
                  </article>
                </div>
              </aside>
            </div>
          </section>

          <section className="panel documents-library-panel dataset-documents-panel">
            <div className="panel-head">
              <h2>Документы базы</h2>
              <p>Статус, теги, ручной запуск индексации и удаление прямо в списке.</p>
            </div>
            <form className="dataset-bulk-toolbar" onSubmit={submitMoveDocuments}>
              <div className="dataset-bulk-copy">
                <strong>Массовые действия</strong>
                <span>{selectedDocumentIds.length > 0 ? `Выбрано ${selectedDocumentIds.length}` : "Выбери документы для переноса"}</span>
              </div>
              <label>
                <span>Перенести в базу</span>
                <select value={moveTargetKnowledgeBase} onChange={(event) => setMoveTargetKnowledgeBase(event.target.value)}>
                  <option value="">Выбери базу</option>
                  {availableMoveTargets.map((item) => (
                    <option key={item.name} value={item.name}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="submit"
                className="secondary-action"
                disabled={selectedDocumentIds.length === 0 || !moveTargetKnowledgeBase || moveDocumentsMutation.isPending}
              >
                {moveDocumentsMutation.isPending ? "Перенос..." : "Перенести выбранные"}
              </button>
              <button
                type="button"
                className="ghost-action"
                disabled={selectedDocuments.length === 0}
                onClick={() =>
                  setSelectedDocumentIds(
                    selectedDocumentIds.length === selectedDocuments.length
                      ? []
                      : selectedDocuments.map((item) => item.document_id)
                  )
                }
              >
                {selectedDocumentIds.length === selectedDocuments.length && selectedDocuments.length > 0 ? "Снять всё" : "Выбрать всё"}
              </button>
            </form>
            {selectedDocuments.length === 0 && <p className="muted">В этой базе пока нет документов.</p>}
            <div className="dataset-document-grid">
              {selectedDocuments.map((document, index) => {
                const docJobs = jobsByDocument.get(document.document_id) ?? [];
                const status = deriveDocumentStatus(document, docJobs);
                const activeJob = docJobs.find((item) => item.status === "running" || item.status === "queued");
                return (
                  <article
                    key={document.document_id}
                    className="dataset-document-card"
                    style={{ animationDelay: `${index * 45}ms` }}
                  >
                    <label className="dataset-document-select">
                      <input
                        type="checkbox"
                        checked={selectedDocumentIds.includes(document.document_id)}
                        onChange={() => toggleDocumentSelection(document.document_id)}
                      />
                      <span>Выбрать документ</span>
                    </label>
                    <div className="dataset-document-top">
                      <div>
                        <strong>{document.file_name}</strong>
                        <p className="muted">{formatIso(document.created_at)}</p>
                      </div>
                      <span className={`document-status-badge status-${status.tone}`}>{status.label}</span>
                    </div>
                    <p className="dataset-document-detail">{status.detail}</p>
                    <div className="dataset-document-meta">
                      <div>
                        <span>Размер</span>
                        <strong>{formatBytes(document.size_bytes)}</strong>
                      </div>
                      <div>
                        <span>Source</span>
                        <strong>{document.source_name || "-"}</strong>
                      </div>
                      <div>
                        <span>Теги</span>
                        <strong>{document.tags.length > 0 ? document.tags.join(", ") : "-"}</strong>
                      </div>
                      <div>
                        <span>Job</span>
                        <strong>{activeJob ? `${activeJob.status} ${activeJob.progress}%` : "-"}</strong>
                      </div>
                    </div>
                    <div className="document-card-actions">
                      <button
                        type="button"
                        className="ghost-action"
                        onClick={() => setActiveDocumentId(document.document_id)}
                      >
                        Подробнее
                      </button>
                      <button
                        type="button"
                        className="secondary-action"
                        disabled={indexMutation.isPending || Boolean(activeJob)}
                        onClick={() => indexMutation.mutate(document.document_id)}
                      >
                        {activeJob ? "В работе" : "Запустить индексацию"}
                      </button>
                      <button
                        type="button"
                        className="danger-action"
                        disabled={deleteMutation.isPending || Boolean(activeJob)}
                        onClick={() => setDocumentToDelete(document)}
                      >
                        Удалить
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          </section>
        </section>

        <aside className="documents-side dataset-side">
          <section className="panel dataset-jobs-panel">
            <div className="panel-head">
              <h2>Jobs базы</h2>
              <p>Последние задачи индексации по выбранной базе знаний.</p>
            </div>
            <div className="jobs-list jobs-timeline">
              {selectedJobs.length === 0 && <p className="muted">Для этой базы jobs пока нет.</p>}
              {selectedJobs.map((job) => (
                <article className="job-card job-card-strong" key={job.job_id}>
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
                      {formatIso(job.started_at)} {"->"} {formatIso(job.finished_at)}
                    </p>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </aside>
      </section>

      {activeDocument && (
        <>
          <button
            type="button"
            aria-label="Закрыть документ"
            className="search-drawer-backdrop"
            onClick={() => setActiveDocumentId(null)}
          />
          <aside className="search-drawer panel dataset-document-drawer" aria-label="Document details">
            <div className="search-drawer-head">
              <div className="panel-head">
                <h2>{activeDocument.file_name}</h2>
                <p>{activeDocument.knowledge_base}</p>
              </div>
              <button type="button" className="ghost-button" onClick={() => setActiveDocumentId(null)}>
                Закрыть
              </button>
            </div>

            <div className="search-drawer-meta">
              <div>
                <span>Статус</span>
                <strong>{deriveDocumentStatus(activeDocument, jobsByDocument.get(activeDocument.document_id) ?? []).label}</strong>
              </div>
              <div>
                <span>Размер</span>
                <strong>{formatBytes(activeDocument.size_bytes)}</strong>
              </div>
              <div>
                <span>Chunks</span>
                <strong>{documentStatsQuery.data?.chunks_count ?? "—"}</strong>
              </div>
            </div>

            <div className="search-drawer-body">
              <section className="search-drawer-section">
                <span className="result-section-label">Метаданные</span>
                <div className="dataset-drawer-grid">
                  <div>
                    <span>Source</span>
                    <strong>{activeDocument.source_name || "—"}</strong>
                  </div>
                  <div>
                    <span>Создан</span>
                    <strong>{formatIso(activeDocument.created_at)}</strong>
                  </div>
                  <div>
                    <span>Теги</span>
                    <strong>{activeDocument.tags.length > 0 ? activeDocument.tags.join(", ") : "—"}</strong>
                  </div>
                  <div>
                    <span>Latest job</span>
                    <strong>{documentStatsQuery.data?.latest_job?.status ?? "—"}</strong>
                  </div>
                </div>
              </section>

              <section className="search-drawer-section">
                <span className="result-section-label">Последние jobs</span>
                <div className="dataset-drawer-jobs">
                  {(jobsByDocument.get(activeDocument.document_id) ?? []).slice(0, 4).map((job) => (
                    <article key={job.job_id} className="dataset-drawer-job">
                      <strong>{job.status}</strong>
                      <span>{job.progress}%</span>
                      <span>{formatIso(job.started_at)}</span>
                    </article>
                  ))}
                  {(jobsByDocument.get(activeDocument.document_id) ?? []).length === 0 && (
                    <p className="result-keywords-empty">Jobs пока нет.</p>
                  )}
                </div>
              </section>
            </div>

            <div className="search-drawer-actions">
              <button type="button" className="primary-action" onClick={() => openDocument(activeDocument.document_id)}>
                Открыть документ
              </button>
              <button
                type="button"
                className="secondary-action"
                disabled={indexMutation.isPending}
                onClick={() => indexMutation.mutate(activeDocument.document_id)}
              >
                Запустить индексацию
              </button>
              <button
                type="button"
                className="danger-action"
                disabled={deleteMutation.isPending}
                onClick={() => {
                  setActiveDocumentId(null);
                  setDocumentToDelete(activeDocument);
                }}
              >
                Удалить
              </button>
            </div>
          </aside>
        </>
      )}

      <ConfirmModal
        open={Boolean(documentToDelete)}
        title="Удалить документ?"
        description={
          documentToDelete
            ? `Документ "${documentToDelete.file_name}" будет удалён вместе с индексом и связанными jobs.`
            : ""
        }
        confirmLabel="Удалить документ"
        pending={deleteMutation.isPending}
        onCancel={() => setDocumentToDelete(null)}
        onConfirm={() => {
          if (documentToDelete) {
            deleteMutation.mutate(documentToDelete.document_id);
          }
        }}
      />

      <ConfirmModal
        open={Boolean(knowledgeBaseToDelete)}
        title="Удалить базу знаний?"
        description={
          knowledgeBaseToDelete
            ? `Пустая база "${knowledgeBaseToDelete}" будет удалена без возможности восстановления.`
            : ""
        }
        confirmLabel="Удалить базу"
        pending={deleteKnowledgeBaseMutation.isPending}
        onCancel={() => setKnowledgeBaseToDelete(null)}
        onConfirm={() => {
          if (knowledgeBaseToDelete) {
            deleteKnowledgeBaseMutation.mutate(knowledgeBaseToDelete);
          }
        }}
      />
    </div>
  );
}
