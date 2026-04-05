import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { ApiRequestError, listKnowledgeBases, searchParagraphs } from "../api/client";
import { STORAGE_LANG_KEY, copy, type Language } from "../i18n";
import { getSystemPrefersDark, parseThemeMode, resolveTheme, STORAGE_THEME_KEY, type ThemeMode } from "../theme";
import { appErrorCopy } from "../utils/appError";
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

type SearchPageProps = {
  embedded?: boolean;
};

export function SearchPage({ embedded = false }: SearchPageProps) {
  const [language, setLanguage] = useState<Language>(getInitialLanguage);
  const [themeMode, setThemeMode] = useState<ThemeMode>(() =>
    parseThemeMode(localStorage.getItem(STORAGE_THEME_KEY))
  );
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [sortMode, setSortMode] = useState<SortMode>("relevance_desc");
  const [selectedKeywords, setSelectedKeywords] = useState<string[]>([]);
  const [selectedKnowledgeBases, setSelectedKnowledgeBases] = useState<string[]>([]);
  const [copied, setCopied] = useState<CopiedState>({});
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null);

  const text = copy[language];

  const mutation = useMutation({
    mutationFn: searchParagraphs
  });

  const knowledgeBasesQuery = useQuery({
    queryKey: ["knowledge-bases"],
    queryFn: listKnowledgeBases,
    refetchInterval: 7000
  });

  const allKeywords = useMemo(
    () => extractKeywords(mutation.data?.results ?? []),
    [mutation.data?.results]
  );

  const totalResults = mutation.data?.total ?? 0;
  const indexedKnowledgeBaseCount = knowledgeBasesQuery.data?.knowledge_bases?.length ?? 0;
  const activeScopeLabel =
    selectedKnowledgeBases.length > 0 ? selectedKnowledgeBases.join(", ") : text.knowledgeBase;
  const visibleResults = useMemo(() => {
    const source = mutation.data?.results ?? [];
    return sortResults(filterByKeywords(source, selectedKeywords), sortMode);
  }, [mutation.data?.results, selectedKeywords, sortMode]);
  const topKnowledgeBases = useMemo(() => {
    return [...(knowledgeBasesQuery.data?.knowledge_bases ?? [])]
      .sort((left, right) => right.document_count - left.document_count)
      .slice(0, 4);
  }, [knowledgeBasesQuery.data?.knowledge_bases]);
  const visibleKnowledgeBaseCount = useMemo(() => {
    const ids = new Set<string>();
    for (const item of visibleResults) {
      if (item.payload.knowledge_base) {
        ids.add(item.payload.knowledge_base);
      }
    }
    return ids.size;
  }, [visibleResults]);
  const selectedResult = useMemo(
    () => visibleResults.find((item) => item.id === selectedResultId) ?? null,
    [visibleResults, selectedResultId]
  );

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

  useEffect(() => {
    if (!selectedResultId) {
      return;
    }

    const exists = visibleResults.some((item) => item.id === selectedResultId);
    if (!exists) {
      setSelectedResultId(null);
    }
  }, [selectedResultId, visibleResults]);

  useEffect(() => {
    if (!selectedResultId) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setSelectedResultId(null);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedResultId]);

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
    setSelectedResultId(null);

    mutation.mutate({
      query: trimmed,
      top_k: topK,
      filters: {
        knowledge_bases: selectedKnowledgeBases
      }
    });
  }

  function toggleKeyword(value: string) {
    setSelectedKeywords((current) =>
      current.includes(value) ? current.filter((item) => item !== value) : [...current, value]
    );
  }

  function toggleKnowledgeBase(value: string) {
    setSelectedKnowledgeBases((current) =>
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

  function openDocument(resultId: string, page?: number | null) {
    const item = visibleResults.find((result) => result.id === resultId);
    const documentId = item?.payload.document_id;
    if (!documentId) {
      return;
    }

    const baseUrl = `/api/documents/${encodeURIComponent(documentId)}/content`;
    const targetUrl = typeof page === "number" ? `${baseUrl}#page=${page}` : baseUrl;
    window.open(targetUrl, "_blank", "noopener,noreferrer");
  }

  const content = (
    <>
      <div className="search-workspace">
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

        <section className="panel search-intelligence-panel">
          <div className="search-intelligence-top">
            <div className="panel-head">
              <h2>Search Scope</h2>
              <p>Контекст поиска, активные базы знаний и быстрый срез по выдаче.</p>
            </div>
            <div className="search-insight-grid">
              <article className="search-insight-card">
                <span>Query</span>
                <strong>{query.trim() || "—"}</strong>
              </article>
              <article className="search-insight-card">
                <span>Visible</span>
                <strong>{visibleResults.length}</strong>
              </article>
              <article className="search-insight-card">
                <span>Knowledge Bases</span>
                <strong>{visibleKnowledgeBaseCount || indexedKnowledgeBaseCount}</strong>
              </article>
              <article className="search-insight-card">
                <span>top_k</span>
                <strong>{topK}</strong>
              </article>
            </div>
          </div>

          <div className="search-context-grid">
            <section className="results-controls knowledge-base-filter search-scope-card">
              <div className="filter-headline">
                <span>{text.knowledgeBase}</span>
                {selectedKnowledgeBases.length > 0 && (
                  <button type="button" className="text-button" onClick={() => setSelectedKnowledgeBases([])}>
                    {text.clearFilters}
                  </button>
                )}
              </div>
              <div className="keyword-chips">
                {(knowledgeBasesQuery.data?.knowledge_bases ?? []).map((item) => (
                  <button
                    key={item.name}
                    type="button"
                    className={`keyword-chip ${selectedKnowledgeBases.includes(item.name) ? "active" : ""}`}
                    onClick={() => toggleKnowledgeBase(item.name)}
                  >
                    {item.name} ({item.document_count})
                  </button>
                ))}
              </div>
            </section>

            <aside className="search-context-rail">
              <article className="search-rail-card">
                <span>Active Scope</span>
                <strong>{activeScopeLabel}</strong>
              </article>
              <article className="search-rail-card">
                <span>Top Indexed Bases</span>
                <div className="search-rail-list">
                  {topKnowledgeBases.length === 0 && <p className="muted">Пока нет баз знаний.</p>}
                  {topKnowledgeBases.map((item) => (
                    <div key={item.name} className="search-rail-item">
                      <strong>{item.name}</strong>
                      <span>{item.document_count} docs</span>
                    </div>
                  ))}
                </div>
              </article>
            </aside>
          </div>
        </section>

        <section className="results-zone search-results-shell">
          <SearchStatus
            loading={mutation.isPending}
            isError={mutation.isError}
            error={mutation.error instanceof ApiRequestError ? mutation.error : new Error(text.unexpectedError)}
            isSuccess={mutation.isSuccess}
            total={totalResults}
            visible={visibleResults.length}
            text={text}
            errorCopy={appErrorCopy[language]}
          />

          {mutation.isSuccess && mutation.data.results.length > 0 && (
            <>
              <div className="search-results-grid">
                <div className="search-results-main">
                  <ResultsControls
                    sortMode={sortMode}
                    onSortModeChange={setSortMode}
                    allKeywords={allKeywords}
                    selectedKeywords={selectedKeywords}
                    onToggleKeyword={toggleKeyword}
                    onClearKeywords={() => setSelectedKeywords([])}
                    text={text}
                  />

                  <div className="results-grid search-results-cards">
                    {visibleResults.map((result, index) => (
                      <div className="result-animated" key={result.id} style={{ animationDelay: `${index * 55}ms` }}>
                        <ResultCard
                          result={result}
                          query={query}
                          text={text}
                          copiedState={copied[result.id] ?? { content: false, keywords: false }}
                          onCopyContent={() => copyContent(result.id, result.payload.content || "")}
                          onCopyKeywords={() => copyKeywords(result.id, result.payload.keywords ?? [])}
                          onOpenDetails={() => setSelectedResultId(result.id)}
                        />
                      </div>
                    ))}
                  </div>
                </div>

                <aside className="search-results-side">
                  <article className="panel search-summary-card">
                    <div className="panel-head">
                      <h2>Result Summary</h2>
                      <p>Быстрый аналитический срез по текущей выдаче.</p>
                    </div>
                    <div className="search-summary-grid">
                      <div>
                        <span>Results</span>
                        <strong>{visibleResults.length}</strong>
                      </div>
                      <div>
                        <span>Keywords</span>
                        <strong>{allKeywords.length}</strong>
                      </div>
                      <div>
                        <span>Scoped KB</span>
                        <strong>{selectedKnowledgeBases.length || indexedKnowledgeBaseCount}</strong>
                      </div>
                    </div>
                  </article>

                  <article className="panel search-summary-card">
                    <div className="panel-head">
                      <h2>Keyword Focus</h2>
                      <p>Самые заметные ключевые слова текущего результата.</p>
                    </div>
                    <div className="keyword-chips">
                      {allKeywords.length === 0 && <p className="muted">Ключевые слова появятся после первого поиска.</p>}
                      {allKeywords.slice(0, 10).map((keyword) => (
                        <button
                          type="button"
                          key={keyword}
                          className={selectedKeywords.includes(keyword) ? "keyword-chip active" : "keyword-chip"}
                          onClick={() => toggleKeyword(keyword)}
                        >
                          {keyword}
                        </button>
                      ))}
                    </div>
                  </article>
                </aside>
              </div>
            </>
          )}
        </section>
      </div>

      {selectedResult && (
        <>
          <button
            type="button"
            aria-label={text.close}
            className="search-drawer-backdrop"
            onClick={() => setSelectedResultId(null)}
          />
          <aside className="search-drawer panel" aria-label={text.fullPreview}>
            <div className="search-drawer-head">
              <div className="panel-head">
                <h2>{text.fullPreview}</h2>
                <p>{selectedResult.payload.document_name?.trim() || "Untitled document"}</p>
              </div>
              <button type="button" className="ghost-button" onClick={() => setSelectedResultId(null)}>
                {text.close}
              </button>
            </div>

            <div className="search-drawer-meta">
              <div>
                <span>{text.knowledgeBase}</span>
                <strong>{selectedResult.payload.knowledge_base || "—"}</strong>
              </div>
              <div>
                <span>{text.page}</span>
                <strong>{selectedResult.payload.page ?? "—"}</strong>
              </div>
              <div>
                <span>{text.relevance}</span>
                <strong>{selectedResult.score.toFixed(3)}</strong>
              </div>
            </div>

            <div className="search-drawer-body">
              <section className="search-drawer-section">
                <span className="result-section-label">{text.excerpt}</span>
                <div className="search-drawer-content">
                  {selectedResult.payload.content || text.noContent}
                </div>
              </section>

              <section className="search-drawer-section">
                <span className="result-section-label">{text.keywords}</span>
                <div className="result-keyword-list">
                  {(selectedResult.payload.keywords ?? []).length > 0 ? (
                    (selectedResult.payload.keywords ?? []).map((keyword) => (
                      <span key={keyword} className="keyword-chip">
                        {keyword}
                      </span>
                    ))
                  ) : (
                    <p className="result-keywords-empty">{text.noKeywords}</p>
                  )}
                </div>
              </section>
            </div>

            <div className="search-drawer-actions">
              <button
                type="button"
                className="primary-action"
                onClick={() => openDocument(selectedResult.id)}
                disabled={!selectedResult.payload.document_id}
              >
                {text.openDocument}
              </button>
              <button
                type="button"
                className="secondary-action"
                onClick={() => openDocument(selectedResult.id, selectedResult.payload.page)}
                disabled={!selectedResult.payload.document_id || typeof selectedResult.payload.page !== "number"}
              >
                {text.openPage}
              </button>
              <button
                type="button"
                className="secondary-action"
                onClick={() => copyContent(selectedResult.id, selectedResult.payload.content || "")}
              >
                {copied[selectedResult.id]?.content ? text.copied : text.copyContent}
              </button>
              <button
                type="button"
                className="ghost-button"
                onClick={() => copyKeywords(selectedResult.id, selectedResult.payload.keywords ?? [])}
              >
                {copied[selectedResult.id]?.keywords ? text.copied : text.copyKeywords}
              </button>
            </div>
          </aside>
        </>
      )}
    </>
  );

  if (embedded) {
    return <div className="search-embedded">{content}</div>;
  }

  return (
    <div className="page-shell">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />
      <main className="page">{content}</main>
    </div>
  );
}
