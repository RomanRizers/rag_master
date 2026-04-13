import { useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import pdfWorkerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import type { ChatCitation } from "../types";

pdfjs.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

interface Props {
  citation: ChatCitation;
  onClose: () => void;
}

function normalizeSnippet(snippet: string): string[] {
  return snippet
    .toLowerCase()
    .split(/\s+/)
    .map((w) => w.replace(/[^a-zа-яё0-9]/gi, ""))
    .filter((w) => w.length > 3)
    .slice(0, 10);
}

export function PdfViewerModal({ citation, onClose }: Props) {
  const [numPages, setNumPages] = useState(0);
  const [pageNumber, setPageNumber] = useState(citation.page ?? 1);
  const [scale, setScale] = useState(1.2);
  const [loadError, setLoadError] = useState<string | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const backdropRef = useRef<HTMLDivElement>(null);

  const fileUrl = `/api/documents/${citation.document_id}/file`;
  const snippetWords = normalizeSnippet(citation.snippet ?? "");

  useEffect(() => {
    setPageNumber(citation.page ?? 1);
    setLoadError(null);
  }, [citation]);

  useEffect(() => {
    backdropRef.current?.focus();
  }, []);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") onClose();
    if (e.key === "ArrowLeft" && pageNumber > 1) setPageNumber((p) => p - 1);
    if (e.key === "ArrowRight" && pageNumber < numPages) setPageNumber((p) => p + 1);
  }

  function handleBackdropClick(e: React.MouseEvent) {
    if (e.target === backdropRef.current) onClose();
  }

  function customTextRenderer({ str }: { str: string; itemIndex: number }) {
    if (!snippetWords.length) return str;
    const lower = str.toLowerCase();
    const matches = snippetWords.filter((w) => lower.includes(w));
    if (matches.length >= 2) {
      return `<mark class="pdf-text-highlight">${str}</mark>`;
    }
    return str;
  }

  const isPdf = (citation.document_name ?? "").toLowerCase().endsWith(".pdf");

  function handleLoadError(err: Error) {
    console.error("[PdfViewerModal] Failed to load PDF:", fileUrl, err);
    setLoadError(err?.message ?? "Unknown error");
  }

  return (
    <div
      ref={backdropRef}
      className="overlay-backdrop pdf-backdrop"
      onClick={handleBackdropClick}
      onKeyDown={handleKeyDown}
      tabIndex={-1}
      role="dialog"
      aria-modal="true"
      aria-label={`Просмотр: ${citation.document_name ?? "Документ"}`}
    >
      <div className="overlay-modal pdf-viewer-modal">
        {/* Header */}
        <div className="pdf-viewer-header">
          <div className="pdf-viewer-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <rect x="4" y="2" width="16" height="20" rx="2" stroke="currentColor" strokeWidth="1.8" />
              <path d="M8 7h8M8 11h8M8 15h5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
            <div>
              <span className="section-kicker">Источник</span>
              <h3>{citation.document_name ?? "Документ"}</h3>
            </div>
          </div>
          <button
            type="button"
            className="overlay-close pdf-close-btn"
            onClick={onClose}
            aria-label="Закрыть"
          >
            ×
          </button>
        </div>

        {/* Snippet quote */}
        {citation.snippet && (
          <blockquote className="pdf-snippet-quote">
            <svg
              className="pdf-quote-icon"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="currentColor"
              aria-hidden="true"
            >
              <path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z" />
              <path d="M15 21c3 0 7-1 7-8V5c0-1.25-.757-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2h.75c0 2.25.25 4-2.75 4v3c0 1 0 1 1 1z" />
            </svg>
            <p>{citation.snippet}</p>
            {citation.page && (
              <span className="pdf-snippet-page">стр. {citation.page}</span>
            )}
          </blockquote>
        )}

        {/* PDF Viewer or fallback */}
        {isPdf && !loadError ? (
          <>
            {/* Controls */}
            <div className="pdf-controls">
              <button
                type="button"
                className="pdf-nav-btn"
                disabled={pageNumber <= 1}
                onClick={() => setPageNumber((p) => p - 1)}
                aria-label="Предыдущая страница"
              >
                ←
              </button>
              <span className="pdf-page-info">
                Страница <strong>{pageNumber}</strong>
                {numPages > 0 && <> из <strong>{numPages}</strong></>}
              </span>
              <button
                type="button"
                className="pdf-nav-btn"
                disabled={pageNumber >= numPages}
                onClick={() => setPageNumber((p) => p + 1)}
                aria-label="Следующая страница"
              >
                →
              </button>
              <div className="pdf-scale-controls">
                <button
                  type="button"
                  className="pdf-nav-btn"
                  onClick={() => setScale((s) => Math.max(0.6, s - 0.2))}
                  aria-label="Уменьшить"
                >
                  −
                </button>
                <span>{Math.round(scale * 100)}%</span>
                <button
                  type="button"
                  className="pdf-nav-btn"
                  onClick={() => setScale((s) => Math.min(2.5, s + 0.2))}
                  aria-label="Увеличить"
                >
                  +
                </button>
              </div>
            </div>

            {/* Document */}
            <div ref={wrapRef} className="pdf-document-wrap">
              <Document
                file={fileUrl}
                onLoadSuccess={({ numPages: n }) => setNumPages(n)}
                onLoadError={handleLoadError}
                loading={
                  <div className="pdf-loading">
                    <span className="chat-spinner" aria-hidden="true" />
                    <span>Загрузка документа...</span>
                  </div>
                }
              >
                <Page
                  pageNumber={pageNumber}
                  scale={scale}
                  renderTextLayer
                  renderAnnotationLayer={false}
                  customTextRenderer={customTextRenderer}
                  loading={null}
                />
              </Document>
            </div>
          </>
        ) : (
          <div className="pdf-fallback">
            {loadError ? (
              <p className="muted">Не удалось загрузить PDF-файл.{loadError && <> ({loadError})</>}</p>
            ) : (
              <p className="muted">
                Просмотр доступен только для PDF-файлов. Документ: <strong>{citation.document_name}</strong>
              </p>
            )}
            <a
              href={fileUrl}
              target="_blank"
              rel="noreferrer"
              className="primary-action"
              style={{ display: "inline-block", marginTop: 8 }}
            >
              Открыть файл ↗
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
