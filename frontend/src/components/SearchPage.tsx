import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";

import { ApiRequestError, searchParagraphs } from "../api/client";
import { STORAGE_LANG_KEY, copy, type Language } from "../i18n";
import { getSystemPrefersDark, parseThemeMode, resolveTheme, STORAGE_THEME_KEY, type ThemeMode } from "../theme";
import { extractKeywords, filterByKeywords, sortResults, type SortMode } from "../utils/search";
import { ResultCard } from "./ResultCard";
import { ResultsControls } from "./ResultsControls";
import { SearchStatus } from "./SearchStatus";
import { SearchToolbar } from "./SearchToolbar";

function getInitialLanguage(): Language {
  const saved = localStorage.getItem(STORAGE_LANG_KEY);
  return saved === "en" ? "en" : "ru";
}

type CopiedState = Record<string, { content: boolean; keywords: boolean }>;

async function safeCopy(text: string): Promise<boolean> {
  if (!text.trim()) {
    return false;
  }

  if (navigator.clipboard && navigator.clipboard.writeText) {
    await navigator.clipboard.writeText(text);
    return true;
  }

  return false;
}

export function SearchPage() {
  const [language, setLanguage] = useState<Language>(getInitialLanguage);
  const [themeMode, setThemeMode] = useState<ThemeMode>(() =>
    parseThemeMode(localStorage.getItem(STORAGE_THEME_KEY))
  );
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [sortMode, setSortMode] = useState<SortMode>("relevance_desc");
  const [selectedKeywords, setSelectedKeywords] = useState<string[]>([]);
  const [copied, setCopied] = useState<CopiedState>({});

  const text = copy[language];

  const mutation = useMutation({
    mutationFn: searchParagraphs
  });

  const allKeywords = useMemo(
    () => extractKeywords(mutation.data?.results ?? []),
    [mutation.data?.results]
  );

  const visibleResults = useMemo(() => {
    const source = mutation.data?.results ?? [];
    return sortResults(filterByKeywords(source, selectedKeywords), sortMode);
  }, [mutation.data?.results, selectedKeywords, sortMode]);

  useEffect(() => {
    function applyTheme() {
      const nextTheme = resolveTheme(themeMode, getSystemPrefersDark());
      document.documentElement.setAttribute("data-theme", nextTheme);
    }

    applyTheme();

    if (themeMode !== "system") {
      return;
    }

    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    if (typeof mediaQuery.addEventListener === "function") {
      mediaQuery.addEventListener("change", applyTheme);
      return () => mediaQuery.removeEventListener("change", applyTheme);
    }
    mediaQuery.addListener(applyTheme);
    return () => mediaQuery.removeListener(applyTheme);
  }, [themeMode]);

  function switchLanguage(nextLanguage: Language) {
    setLanguage(nextLanguage);
    localStorage.setItem(STORAGE_LANG_KEY, nextLanguage);
  }

  function switchTheme(nextTheme: ThemeMode) {
    setThemeMode(nextTheme);
    localStorage.setItem(STORAGE_THEME_KEY, nextTheme);
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) {
      return;
    }

    setSelectedKeywords([]);
    setCopied({});

    mutation.mutate({
      query: trimmed,
      top_k: topK
    });
  }

  function toggleKeyword(value: string) {
    setSelectedKeywords((current) =>
      current.includes(value) ? current.filter((item) => item !== value) : [...current, value]
    );
  }

  function markCopied(id: string, field: "content" | "keywords") {
    setCopied((current) => ({
      ...current,
      [id]: {
        content: field === "content",
        keywords: field === "keywords"
      }
    }));

    window.setTimeout(() => {
      setCopied((current) => {
        const next = { ...current };
        delete next[id];
        return next;
      });
    }, 1200);
  }

  async function copyContent(id: string, content: string) {
    const ok = await safeCopy(content);
    if (ok) {
      markCopied(id, "content");
    }
  }

  async function copyKeywords(id: string, keywords: string[]) {
    const ok = await safeCopy(keywords.join(", "));
    if (ok) {
      markCopied(id, "keywords");
    }
  }

  return (
    <div className="page-shell">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />

      <main className="page">
        <SearchToolbar
          language={language}
          onSwitchLanguage={switchLanguage}
          themeMode={themeMode}
          onThemeModeChange={switchTheme}
          query={query}
          onQueryChange={setQuery}
          topK={topK}
          onTopKChange={setTopK}
          onSubmit={submitSearch}
          loading={mutation.isPending}
          text={text}
        />

        <section className="results-zone">
          <SearchStatus
            loading={mutation.isPending}
            isError={mutation.isError}
            errorMessage={
              mutation.error instanceof ApiRequestError ? mutation.error.message : text.unexpectedError
            }
            isSuccess={mutation.isSuccess}
            total={mutation.data?.total ?? 0}
            visible={visibleResults.length}
            text={text}
          />

          {mutation.isSuccess && mutation.data.results.length > 0 && (
            <>
              <ResultsControls
                sortMode={sortMode}
                onSortModeChange={setSortMode}
                allKeywords={allKeywords}
                selectedKeywords={selectedKeywords}
                onToggleKeyword={toggleKeyword}
                onClearKeywords={() => setSelectedKeywords([])}
                text={text}
              />

              <div className="results-grid">
                {visibleResults.map((result, index) => (
                  <div className="result-animated" key={result.id} style={{ animationDelay: `${index * 55}ms` }}>
                    <ResultCard
                      result={result}
                      query={query}
                      text={text}
                      copiedState={copied[result.id] ?? { content: false, keywords: false }}
                      onCopyContent={() => copyContent(result.id, result.payload.content || "")}
                      onCopyKeywords={() => copyKeywords(result.id, result.payload.keywords ?? [])}
                    />
                  </div>
                ))}
              </div>
            </>
          )}
        </section>
      </main>
    </div>
  );
}
