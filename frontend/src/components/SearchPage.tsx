import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { searchParagraphs } from "../api/client";
import { STORAGE_LANG_KEY, copy, type Language } from "../i18n";
import { formatRawScore, formatRelevance } from "../utils/score";

function getInitialLanguage(): Language {
  const saved = localStorage.getItem(STORAGE_LANG_KEY);
  return saved === "en" ? "en" : "ru";
}

export function SearchPage() {
  const [language, setLanguage] = useState<Language>(getInitialLanguage);
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const text = copy[language];

  const mutation = useMutation({
    mutationFn: searchParagraphs
  });

  function switchLanguage(nextLanguage: Language) {
    setLanguage(nextLanguage);
    localStorage.setItem(STORAGE_LANG_KEY, nextLanguage);
  }

  function submitSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) {
      return;
    }

    mutation.mutate({
      query: trimmed,
      top_k: topK
    });
  }

  return (
    <div className="page">
      <header className="header">
        <div className="lang-switch" role="group" aria-label="Language switch">
          <button
            type="button"
            className={language === "ru" ? "lang-btn active" : "lang-btn"}
            onClick={() => switchLanguage("ru")}
          >
            RU
          </button>
          <button
            type="button"
            className={language === "en" ? "lang-btn active" : "lang-btn"}
            onClick={() => switchLanguage("en")}
          >
            EN
          </button>
        </div>
        <h1>{text.title}</h1>
      </header>

      <main className="content">
        <form className="search-form" onSubmit={submitSearch}>
          <input
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={text.queryPlaceholder}
            aria-label={text.queryPlaceholder}
          />
          <input
            type="number"
            min={1}
            value={topK}
            onChange={(event) => setTopK(Math.max(1, Number(event.target.value || 1)))}
            aria-label={text.topKHint}
            title={text.topKHint}
          />
          <button type="submit" disabled={mutation.isPending}>
            {text.searchButton}
          </button>
        </form>

        {mutation.isPending && <p className="status">{text.loading}</p>}

        {mutation.isError && (
          <p className="status error">
            {text.errorPrefix}: {mutation.error.message}
          </p>
        )}

        {mutation.isSuccess && mutation.data.results.length === 0 && (
          <p className="status">{text.empty}</p>
        )}

        {mutation.isSuccess && mutation.data.results.length > 0 && (
          <section className="results">
            {mutation.data.results.map((result) => (
              <article className="card" key={result.id}>
                <p>
                  <strong>{text.relevance}:</strong> {formatRelevance(result.score)}
                </p>
                <p>
                  <strong>{text.rawScore}:</strong> {formatRawScore(result.score)}
                </p>
                <p>
                  <strong>{text.content}:</strong> {result.payload.content || text.noContent}
                </p>
                <p>
                  <strong>{text.keywords}:</strong>{" "}
                  {Array.isArray(result.payload.keywords) && result.payload.keywords.length > 0
                    ? result.payload.keywords.join(", ")
                    : text.noKeywords}
                </p>
              </article>
            ))}
          </section>
        )}
      </main>
    </div>
  );
}
