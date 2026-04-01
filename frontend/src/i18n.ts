export type Language = "ru" | "en";

export type Copy = {
  title: string;
  queryPlaceholder: string;
  topKHint: string;
  searchButton: string;
  loading: string;
  empty: string;
  relevance: string;
  rawScore: string;
  content: string;
  keywords: string;
  noContent: string;
  noKeywords: string;
  errorPrefix: string;
};

export const copy: Record<Language, Copy> = {
  ru: {
    title: "Сервис поиска параграфов",
    queryPlaceholder: "Введите запрос",
    topKHint: "Количество результатов (по умолчанию 5)",
    searchButton: "Искать",
    loading: "Идет поиск...",
    empty: "Ничего не найдено",
    relevance: "Релевантность",
    rawScore: "Score (raw)",
    content: "Контент",
    keywords: "Ключевые слова",
    noContent: "Контент отсутствует",
    noKeywords: "Ключевые слова отсутствуют",
    errorPrefix: "Ошибка"
  },
  en: {
    title: "Paragraph Search Service",
    queryPlaceholder: "Enter query",
    topKHint: "Number of results (default 5)",
    searchButton: "Search",
    loading: "Searching...",
    empty: "No results found",
    relevance: "Relevance",
    rawScore: "Score (raw)",
    content: "Content",
    keywords: "Keywords",
    noContent: "No content",
    noKeywords: "No keywords",
    errorPrefix: "Error"
  }
};

export const STORAGE_LANG_KEY = "language";
