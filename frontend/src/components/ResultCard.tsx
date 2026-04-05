import { formatRawScore, formatRelevance } from "../utils/score";
import { HighlightText } from "./HighlightText";
import type { SearchResult } from "../types";

type ResultCardCopy = {
  relevance: string;
  rawScore: string;
  knowledgeBase: string;
  content: string;
  keywords: string;
  noContent: string;
  noKeywords: string;
  copyContent: string;
  copyKeywords: string;
  copied: string;
};

type ResultCardProps = {
  result: SearchResult;
  query: string;
  text: ResultCardCopy;
  copiedState: { content: boolean; keywords: boolean };
  onCopyContent: () => void;
  onCopyKeywords: () => void;
};

export function ResultCard({
  result,
  query,
  text,
  copiedState,
  onCopyContent,
  onCopyKeywords
}: ResultCardProps) {
  const keywords = result.payload.keywords ?? [];

  return (
    <article className="result-card">
      <div className="result-card-head">
        <div className="result-card-copy">
          <strong>{result.payload.document_name ?? "Unknown document"}</strong>
          <div className="result-meta">
            {result.payload.knowledge_base && (
              <span className="chip">{text.knowledgeBase}: {result.payload.knowledge_base}</span>
            )}
            {typeof result.payload.page === "number" && <span className="chip">page {result.payload.page}</span>}
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
        <p className="result-content">
          <HighlightText text={result.payload.content || ""} query={query} noContentLabel={text.noContent} />
        </p>

        <div className="result-keywords">
          <span className="meta-label">{text.keywords}</span>
          <div className="keyword-chips">
            {keywords.length > 0 ? (
              keywords.map((keyword) => (
                <span key={keyword} className="chip">
                  {keyword}
                </span>
              ))
            ) : (
              <span className="muted">{text.noKeywords}</span>
            )}
          </div>
        </div>
      </div>

      <div className="result-actions">
        <button type="button" className="ghost-button" onClick={onCopyContent}>
          {copiedState.content ? text.copied : text.copyContent}
        </button>
        <button type="button" className="ghost-button" onClick={onCopyKeywords}>
          {copiedState.keywords ? text.copied : text.copyKeywords}
        </button>
      </div>
    </article>
  );
}
