import { useEffect, useRef, useState, type FormEvent } from "react";

type KnowledgeBase = { name: string; document_count: number };

type SearchToolbarProps = {
  query: string;
  onQueryChange: (value: string) => void;
  topK: number;
  onTopKChange: (value: number) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  loading: boolean;
  knowledgeBases: KnowledgeBase[];
  selectedKnowledgeBases: string[];
  onToggleKnowledgeBase: (name: string) => void;
  onClearKnowledgeBases: () => void;
};

export function SearchToolbar({
  query,
  onQueryChange,
  topK,
  onTopKChange,
  onSubmit,
  loading,
  knowledgeBases,
  selectedKnowledgeBases,
  onToggleKnowledgeBase,
  onClearKnowledgeBases,
}: SearchToolbarProps) {
  const [kbOpen, setKbOpen] = useState(false);
  const kbRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!kbOpen) return;
    function onPointerDown(e: PointerEvent) {
      if (kbRef.current && !kbRef.current.contains(e.target as Node)) {
        setKbOpen(false);
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [kbOpen]);

  return (
    <form className="search-composer" onSubmit={onSubmit}>
      <div className="search-composer-inner">
        <svg className="search-input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
          <path d="M21 21l-4.35-4.35" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>

        <input
          className="search-input"
          type="text"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="Введите поисковый запрос…"
          autoComplete="off"
          autoFocus
        />

        <div className="search-composer-controls">
          {/* KB selector */}
          <div className="search-kb-wrap" ref={kbRef}>
            <button
              type="button"
              className={`search-chip-btn ${selectedKnowledgeBases.length > 0 ? "active" : ""}`}
              onClick={() => setKbOpen((v) => !v)}
            >
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <ellipse cx="12" cy="6" rx="8" ry="3" stroke="currentColor" strokeWidth="2" />
                <path d="M4 6v6c0 1.66 3.58 3 8 3s8-1.34 8-3V6" stroke="currentColor" strokeWidth="2" />
                <path d="M4 12v6c0 1.66 3.58 3 8 3s8-1.34 8-3v-6" stroke="currentColor" strokeWidth="2" />
              </svg>
              {selectedKnowledgeBases.length > 0 ? `${selectedKnowledgeBases.length} KB` : "Все базы"}
            </button>

            {kbOpen && (
              <div className="search-kb-popover">
                <div className="search-kb-popover-head">
                  <span>База знаний</span>
                  {selectedKnowledgeBases.length > 0 && (
                    <button type="button" className="search-kb-clear" onClick={onClearKnowledgeBases}>
                      Сбросить
                    </button>
                  )}
                </div>
                <div className="search-kb-list">
                  {knowledgeBases.length === 0 && (
                    <p className="search-kb-empty">Нет баз знаний</p>
                  )}
                  {knowledgeBases.map((kb) => {
                    const active = selectedKnowledgeBases.includes(kb.name);
                    return (
                      <button
                        key={kb.name}
                        type="button"
                        className={`search-kb-item ${active ? "active" : ""}`}
                        onClick={() => onToggleKnowledgeBase(kb.name)}
                      >
                        <span className="search-kb-check">
                          {active && (
                            <svg width="11" height="11" viewBox="0 0 24 24" fill="none">
                              <path d="M20 6 9 17l-5-5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                          )}
                        </span>
                        <span className="search-kb-name">{kb.name}</span>
                        <span className="search-kb-count">{kb.document_count}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* top_k */}
          <div className="search-topk-wrap">
            <span className="search-topk-label">top</span>
            <input
              type="number"
              min={1}
              max={50}
              value={topK}
              onChange={(e) => onTopKChange(Math.max(1, Math.min(50, Number(e.target.value) || 1)))}
              className="search-topk-input"
            />
          </div>

          {/* Submit */}
          <button type="submit" className="send-icon-btn" disabled={loading} aria-label="Найти">
            {loading ? (
              <span className="chat-spinner" aria-hidden="true" />
            ) : (
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2.2" />
                <path d="M21 21l-4.35-4.35" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
              </svg>
            )}
          </button>
        </div>
      </div>
    </form>
  );
}
