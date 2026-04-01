export type SearchResult = {
  id: string;
  score: number;
  payload: {
    content?: string;
    keywords?: string[];
  };
};

export type SearchResponse = {
  results: SearchResult[];
  total: number;
};

export type SearchRequest = {
  query: string;
  top_k: number;
};

export type ApiErrorResponse = {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
};
