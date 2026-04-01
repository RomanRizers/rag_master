import type { Language } from "../i18n";

type SearchToolbarCopy = {
  title: string;
  subtitle: string;
  queryPlaceholder: string;
  topKLabel: string;
  topKHint: string;
  searchButton: string;
};

type SearchToolbarProps = {
  language: Language;
  onSwitchLanguage: (nextLanguage: Language) => void;
  query: string;
  onQueryChange: (value: string) => void;
  topK: number;
  onTopKChange: (value: number) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  loading: boolean;
  text: SearchToolbarCopy;
};

export function SearchToolbar({
  language,
  onSwitchLanguage,
  query,
  onQueryChange,
  topK,
  onTopKChange,
  onSubmit,
  loading,
  text
}: SearchToolbarProps) {
  return (
    <header className="hero">
      <div className="hero-top">
        <div className="lang-switch" role="group" aria-label="Language switch">
          <button
            type="button"
            className={language === "ru" ? "lang-btn active" : "lang-btn"}
            onClick={() => onSwitchLanguage("ru")}
          >
            RU
          </button>
          <button
            type="button"
            className={language === "en" ? "lang-btn active" : "lang-btn"}
            onClick={() => onSwitchLanguage("en")}
          >
            EN
          </button>
        </div>
      </div>

      <h1>{text.title}</h1>
      <p>{text.subtitle}</p>

      <form className="search-panel" onSubmit={onSubmit}>
        <label className="field field-query">
          <span>{text.queryPlaceholder}</span>
          <input
            type="text"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder={text.queryPlaceholder}
            aria-label={text.queryPlaceholder}
            autoComplete="off"
          />
        </label>

        <label className="field field-topk">
          <span>{text.topKLabel}</span>
          <input
            type="number"
            min={1}
            max={50}
            value={topK}
            onChange={(event) => onTopKChange(Math.max(1, Math.min(50, Number(event.target.value || 1))))}
            aria-label={text.topKHint}
            title={text.topKHint}
          />
        </label>

        <button type="submit" className="primary-button" disabled={loading}>
          {loading ? "..." : text.searchButton}
        </button>
      </form>
    </header>
  );
}
import type { FormEvent } from "react";
