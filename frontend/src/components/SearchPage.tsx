import { useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { ApiRequestError, listKnowledgeBases, searchParagraphs } from "../api/client";
import { copy, type Language } from "../i18n";
import { appErrorCopy } from "../utils/appError";
import { extractKeywords, filterByKeywords, sortResults, type SortMode } from "../utils/search";
import { ResultCard } from "./ResultCard";
import { ResultsControls } from "./ResultsControls";
import { SearchStatus } from "./SearchStatus";
import { SearchToolbar } from "./SearchToolbar";

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
  language?: Language;
};

export function SearchPage({ embedded = false, language = "ru" }: SearchPageProps) {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [sortMode, setSortMode] = useState<SortMode>("relevance_desc");
  const [selectedKeywords, setSelectedKeywords] = useState<string[]>([]);
  const [selectedKnowledgeBases, setSelectedKnowledgeBases] = useState<string[]>([]);
  const [copied, setCopied] = useState<CopiedState>({});

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

  const visibleResults = useMemo(() => {
    const source = mutation.data?.results ?? [];
    return sortResults(filterByKeywords(source, selectedKeywords), sortMode);
  }, [mutation.data?.results, selectedKeywords, sortMode]);

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

  const knowledgeBases = knowledgeBasesQuery.data?.knowledge_bases ?? [];

  const content = (
    <div className="page-section">
      <SearchToolbar
        query={query}
        onQueryChange={setQuery}
        topK={topK}
        onTopKChange={setTopK}
        onSubmit={submitSearch}
        loading={mutation.isPending}
        text={text}
      />

      <section className="toolbar-card">
        <div className="toolbar-inline">
          <div className="toolbar-copy compact">
            <span className="section-kicker">{text.knowledgeBase}</span>
            <h2>Scope</h2>
          </div>
          {selectedKnowledgeBases.length > 0 && (
            <button type="button" className="text-button" onClick={() => setSelectedKnowledgeBases([])}>
              {text.clearFilters}
            </button>
          )}
        </div>
        <div className="keyword-chips">
          {knowledgeBases.map((item) => (
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

      <SearchStatus
        loading={mutation.isPending}
        isError={mutation.isError}
        error={mutation.error instanceof ApiRequestError ? mutation.error : new Error(text.unexpectedError)}
        isSuccess={mutation.isSuccess}
        total={mutation.data?.total ?? 0}
        visible={visibleResults.length}
        text={text}
        errorCopy={appErrorCopy[language]}
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

          <section className="results-grid">
            {visibleResults.map((result, idx) => (
              <div
                key={result.id}
                className="result-card-wrapper"
                style={{ animationDelay: `${idx * 45}ms` }}
              >
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
          </section>
        </>
      )}
    </div>
  );

  if (embedded) {
    return <div className="search-embedded">{content}</div>;
  }

  return (
    <div className="page-shell">
      <main className="page">{content}</main>
    </div>
  );
}
