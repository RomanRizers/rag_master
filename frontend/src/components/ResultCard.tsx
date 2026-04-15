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

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(Math.min(1, Math.max(0, score)) * 100);
  const hue = Math.round(pct * 1.2); // 0→red, 100→green-ish
  const color = `hsl(${hue}, 72%, 42%)`;
  return (
    <div className="score-bar-wrap" title={`Relevance: ${pct}%`}>
      <div className="score-bar-track">
        <div
          className="score-bar-fill"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className="score-bar-label" style={{ color }}>{pct}%</span>
    </div>
  );
}

function CopyBtn({
  label,
  done,
  onClick,
  icon
}: {
  label: string;
  done: boolean;
  onClick: () => void;
  icon: React.ReactNode;
}) {
  return (
    <button
      type="button"
      className={`icon-copy-btn ${done ? "copied" : ""}`}
      onClick={onClick}
      title={label}
      aria-label={label}
    >
      {done ? (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      ) : (
        icon
      )}
    </button>
  );
}

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
          <div className="result-doc-name">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <rect x="4" y="2" width="16" height="20" rx="2" stroke="currentColor" strokeWidth="1.8" />
              <path d="M8 7h8M8 11h8M8 15h5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
            <strong>{result.payload.document_name ?? "Unknown document"}</strong>
          </div>
          <div className="result-meta">
            {result.payload.knowledge_base && (
              <span className="chip">{result.payload.knowledge_base}</span>
            )}
            {typeof result.payload.page === "number" && (
              <span className="chip">стр. {result.payload.page}</span>
            )}
          </div>
        </div>
        <ScoreBar score={result.score} />
      </div>

      <div className="result-body">
        <p className="result-content">
          <HighlightText text={result.payload.content || ""} query={query} noContentLabel={text.noContent} />
        </p>

        {keywords.length > 0 && (
          <div className="result-keywords">
            <span className="meta-label">{text.keywords}</span>
            <div className="keyword-chips">
              {keywords.map((keyword) => (
                <span key={keyword} className="chip">
                  {keyword}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="result-actions">
        <CopyBtn
          label={copiedState.content ? text.copied : text.copyContent}
          done={copiedState.content}
          onClick={onCopyContent}
          icon={
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <rect x="9" y="9" width="13" height="13" rx="2" stroke="currentColor" strokeWidth="1.8" />
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" stroke="currentColor" strokeWidth="1.8" />
            </svg>
          }
        />
        <CopyBtn
          label={copiedState.keywords ? text.copied : text.copyKeywords}
          done={copiedState.keywords}
          onClick={onCopyKeywords}
          icon={
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
              <circle cx="7" cy="7" r="1.5" fill="currentColor" />
            </svg>
          }
        />
      </div>
    </article>
  );
}
