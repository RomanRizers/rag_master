export type Language = "ru" | "en";

export type Copy = {
  title: string;
  subtitle: string;
  queryPlaceholder: string;
  topKLabel: string;
  topKHint: string;
  searchButton: string;
  loading: string;
  empty: string;
  found: string;
  relevance: string;
  rawScore: string;
  content: string;
  keywords: string;
  noContent: string;
  noKeywords: string;
  errorPrefix: string;
  unexpectedError: string;
  sortLabel: string;
  filterLabel: string;
  clearFilters: string;
  sortRelevanceDesc: string;
  sortRelevanceAsc: string;
  sortContentLengthDesc: string;
  sortContentLengthAsc: string;
  copyContent: string;
  copyKeywords: string;
  copied: string;
};

export const copy: Record<Language, Copy> = {
  ru: {
    title: "Paragraph Search",
    subtitle: "Семантический поиск по документам с быстрым просмотром релевантных фрагментов",
    queryPlaceholder: "Введите запрос",
    topKLabel: "Результатов",
    topKHint: "Количество результатов (1-50)",
    searchButton: "Найти",
    loading: "Идет поиск...",
    empty: "Ничего не найдено",
    found: "Показано результатов",
    relevance: "Релевантность",
    rawScore: "Raw score",
    content: "Контент",
    keywords: "Ключевые слова",
    noContent: "Контент отсутствует",
    noKeywords: "Ключевые слова отсутствуют",
    errorPrefix: "Ошибка",
    unexpectedError: "Непредвиденная ошибка",
    sortLabel: "Сортировка",
    filterLabel: "Фильтр по ключевым словам",
    clearFilters: "Сбросить",
    sortRelevanceDesc: "Сначала самые релевантные",
    sortRelevanceAsc: "Сначала наименее релевантные",
    sortContentLengthDesc: "Сначала длинные фрагменты",
    sortContentLengthAsc: "Сначала короткие фрагменты",
    copyContent: "Копировать контент",
    copyKeywords: "Копировать ключевые слова",
    copied: "Скопировано"
  },
  en: {
    title: "Paragraph Search",
    subtitle: "Semantic document search with fast preview of relevant snippets",
    queryPlaceholder: "Enter query",
    topKLabel: "Results",
    topKHint: "Number of results (1-50)",
    searchButton: "Search",
    loading: "Searching...",
    empty: "No results found",
    found: "Visible results",
    relevance: "Relevance",
    rawScore: "Raw score",
    content: "Content",
    keywords: "Keywords",
    noContent: "No content",
    noKeywords: "No keywords",
    errorPrefix: "Error",
    unexpectedError: "Unexpected error",
    sortLabel: "Sort",
    filterLabel: "Filter by keywords",
    clearFilters: "Clear",
    sortRelevanceDesc: "Most relevant first",
    sortRelevanceAsc: "Least relevant first",
    sortContentLengthDesc: "Longest snippets first",
    sortContentLengthAsc: "Shortest snippets first",
    copyContent: "Copy content",
    copyKeywords: "Copy keywords",
    copied: "Copied"
  }
};

export const STORAGE_LANG_KEY = "language";
