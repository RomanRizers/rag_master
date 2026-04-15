import type { FormEvent } from "react";

type SearchToolbarCopy = {
  title: string;
  subtitle: string;
  queryPlaceholder: string;
  topKLabel: string;
  topKHint: string;
  searchButton: string;
};

type SearchToolbarProps = {
  query: string;
  onQueryChange: (value: string) => void;
  topK: number;
  onTopKChange: (value: number) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  loading: boolean;
  text: SearchToolbarCopy;
};

export function SearchToolbar({
  query,
  onQueryChange,
  topK,
  onTopKChange,
  onSubmit,
  loading,
  text
}: SearchToolbarProps) {
  return (
    <section className="toolbar-card search-toolbar">
      <div className="toolbar-topline">
        <div className="toolbar-copy">
          <span className="section-kicker">Search</span>
          <h2>{text.title}</h2>
          <p>{text.subtitle}</p>
        </div>
      </div>

      <form className="search-form" onSubmit={onSubmit}>
        <div className="search-input-wrap">
          <svg
            className="search-input-icon"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
            <path d="M21 21l-4.35-4.35" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <input
            className="search-input"
            type="text"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            placeholder={text.queryPlaceholder}
            aria-label={text.queryPlaceholder}
            autoComplete="off"
            autoFocus
          />
          {loading && <span className="search-spinner" aria-hidden="true" />}
        </div>

        <div className="search-form-footer">
          <label className="search-topk-label">
            <span className="meta-label">{text.topKLabel}</span>
            <div className="search-topk-stepper">
              <button
                type="button"
                className="topk-step-btn"
                onClick={() => onTopKChange(Math.max(1, topK - 1))}
                aria-label="Уменьшить"
              >−</button>
              <input
                type="number"
                min={1}
                max={50}
                value={topK}
                onChange={(e) => onTopKChange(Math.max(1, Math.min(50, Number(e.target.value || 1))))}
                aria-label={text.topKHint}
                title={text.topKHint}
                className="topk-input"
              />
              <button
                type="button"
                className="topk-step-btn"
                onClick={() => onTopKChange(Math.min(50, topK + 1))}
                aria-label="Увеличить"
              >+</button>
            </div>
          </label>

          <button type="submit" className="primary-action search-submit-btn" disabled={loading}>
            {loading ? (
              <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                <span className="chat-spinner" style={{ width: 13, height: 13 }} aria-hidden="true" />
                Поиск...
              </span>
            ) : (
              <>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2.2" />
                  <path d="M21 21l-4.35-4.35" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
                </svg>
                {text.searchButton}
              </>
            )}
          </button>
        </div>
      </form>
    </section>
  );
}
