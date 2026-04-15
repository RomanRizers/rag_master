import type { SortMode } from "../utils/search";

type ResultsControlsCopy = {
  sortLabel: string;
  filterLabel: string;
  clearFilters: string;
  sortRelevanceDesc: string;
  sortRelevanceAsc: string;
  sortContentLengthDesc: string;
  sortContentLengthAsc: string;
};

type ResultsControlsProps = {
  sortMode: SortMode;
  onSortModeChange: (value: SortMode) => void;
  allKeywords: string[];
  selectedKeywords: string[];
  onToggleKeyword: (value: string) => void;
  onClearKeywords: () => void;
  text: ResultsControlsCopy;
};

export function ResultsControls({
  sortMode,
  onSortModeChange,
  allKeywords,
  selectedKeywords,
  onToggleKeyword,
  onClearKeywords,
  text
}: ResultsControlsProps) {
  return (
    <section className="results-controls" aria-label="Result controls">
      <div className="controls-grid">
        <label className="controls-label">
          {text.sortLabel}
          <select value={sortMode} onChange={(event) => onSortModeChange(event.target.value as SortMode)}>
            <option value="relevance_desc">{text.sortRelevanceDesc}</option>
            <option value="relevance_asc">{text.sortRelevanceAsc}</option>
            <option value="content_length_desc">{text.sortContentLengthDesc}</option>
            <option value="content_length_asc">{text.sortContentLengthAsc}</option>
          </select>
        </label>
      </div>

      {allKeywords.length > 0 && (
        <div className="keyword-filter">
          <div className="filter-headline">
            <span>{text.filterLabel}</span>
            {selectedKeywords.length > 0 && (
              <button type="button" className="text-button" onClick={onClearKeywords}>
                {text.clearFilters}
              </button>
            )}
          </div>
          <div className="keyword-chips">
            {allKeywords.map((keyword) => {
              const active = selectedKeywords.includes(keyword);
              return (
                <button
                  type="button"
                  key={keyword}
                  className={active ? "keyword-chip active" : "keyword-chip"}
                  onClick={() => onToggleKeyword(keyword)}
                >
                  {keyword}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}
