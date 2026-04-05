import { formatRawScore, formatRelevance } from "../utils/score";
import { HighlightText } from "./HighlightText";
import type { SearchResult } from "../types";

type ResultCardCopy = {
  relevance: string;
  rawScore: string;
  knowledgeBase: string;
  source: string;
  document: string;
  page: string;
  excerpt: string;
  content: string;
  keywords: string;
  noContent: string;
  noKeywords: string;
  copyContent: string;
  copyKeywords: string;
  copied: string;
  details: string;
};

type ResultCardProps = {
  result: SearchResult;
  query: string;
  text: ResultCardCopy;
  copiedState: { content: boolean; keywords: boolean };
  onCopyContent: () => void;
  onCopyKeywords: () => void;
  onOpenDetails: () => void;
};

export function ResultCard({
  result,
  query,
  text,
  copiedState,
  onCopyContent,
  onCopyKeywords,
  onOpenDetails
}: ResultCardProps) {
  const keywords = result.payload.keywords ?? [];
  const documentName = result.payload.document_name?.trim() || "Untitled document";
  const pageLabel = typeof result.payload.page === "number" ? `${text.page} ${result.payload.page}` : null;

  return (
    <article className="result-card">
      <div className="result-card-head">
        <div className="result-source-block">
          <span className="result-section-label">{text.source}</span>
          <strong>{documentName}</strong>
          <div className="result-source-meta">
            {result.payload.knowledge_base && <span className="chip">{result.payload.knowledge_base}</span>}
            {pageLabel && <span className="chip">{pageLabel}</span>}
          </div>
        </div>
        <div className="result-score-stack">
          <span className="chip chip-primary">
            {text.relevance}: {formatRelevance(result.score)}
          </span>
          <span className="chip">
            {text.rawScore}: {formatRawScore(result.score)}
          </span>
        </div>
      </div>

      <div className="result-body">
        <div className="result-excerpt-block">
          <span className="result-section-label">{text.excerpt}</span>
          <p className="result-content">
            <HighlightText text={result.payload.content || ""} query={query} noContentLabel={text.noContent} />
          </p>
        </div>

        <div className="result-footer">
          <div className="result-taxonomy">
            <span className="result-section-label">{text.keywords}</span>
            <div className="result-keyword-list">
              {keywords.length > 0 ? (
                keywords.map((keyword) => (
                  <span key={keyword} className="keyword-chip">
                    {keyword}
                  </span>
                ))
              ) : (
                <p className="result-keywords-empty">{text.noKeywords}</p>
              )}
            </div>
          </div>

          <div className="result-actions">
            <button type="button" className="secondary-action" onClick={onOpenDetails}>
              {text.details}
            </button>
            <button type="button" className="ghost-button" onClick={onCopyContent}>
              {copiedState.content ? text.copied : text.copyContent}
            </button>
            <button type="button" className="ghost-button" onClick={onCopyKeywords}>
              {copiedState.keywords ? text.copied : text.copyKeywords}
            </button>
          </div>
        </div>
      </div>
    </article>
  );
}
