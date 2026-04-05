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
      <div className="result-meta">
        <span className="chip chip-primary">
          {text.relevance}: {formatRelevance(result.score)}
        </span>
        <span className="chip">
          {text.rawScore}: {formatRawScore(result.score)}
        </span>
        {result.payload.knowledge_base && (
          <span className="chip">{text.knowledgeBase}: {result.payload.knowledge_base}</span>
        )}
      </div>

      <p className="result-content">
        <strong>{text.content}: </strong>
        <HighlightText text={result.payload.content || ""} query={query} noContentLabel={text.noContent} />
      </p>

      <p className="result-keywords">
        <strong>{text.keywords}: </strong>
        {keywords.length > 0 ? keywords.join(", ") : text.noKeywords}
      </p>

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
