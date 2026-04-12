export type SearchResult = {
  id: string;
  score: number;
  payload: {
    content?: string;
    keywords?: string[];
    document_name?: string;
    page?: number;
    knowledge_base?: string;
  };
};

export type SearchResponse = {
  results: SearchResult[];
  total: number;
};

export type SearchRequest = {
  query: string;
  top_k: number;
  filters?: {
    knowledge_bases?: string[];
  };
};

export type ApiErrorResponse = {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
};

export type DocumentItem = {
  document_id: string;
  file_name: string;
  mime_type: string;
  size_bytes: number;
  status: string;
  source_name?: string | null;
  tags: string[];
  knowledge_base: string;
  created_at: string;
};

export type DocumentListResponse = {
  documents: DocumentItem[];
};

export type DocumentUploadResponse = {
  document_id: string;
  file_name: string;
  mime_type: string;
  size_bytes: number;
  status: string;
  knowledge_base: string;
  created_at: string;
};

export type DocumentDeleteResponse = {
  status: string;
  document: DocumentItem;
};

export type DocumentIndexResponse = {
  job_id: string;
  status: string;
  document_id: string;
};

export type JobItem = {
  job_id: string;
  document_id: string;
  status: string;
  progress: number;
  attempt: number;
  error_code?: string | null;
  error_message?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
};

export type JobListResponse = {
  jobs: JobItem[];
};

export type DocumentIndexStatsResponse = {
  document_id: string;
  status: string;
  chunks_count: number;
  keywords: string[];
  index_profile?: {
    profile_mode?: string;
    chunk_size_tokens?: number;
    chunk_overlap_tokens?: number;
    chunk_keyword_limit?: number;
  } | null;
  latest_job?: JobItem | null;
};

export type DocumentChunkItem = {
  chunk_id: string;
  chunk_index: number;
  content: string;
  keywords: string[];
  page?: number | null;
  section?: string | null;
  token_count: number;
  block_type?: string | null;
  heading_path: string[];
  document_id?: string | null;
  document_name?: string | null;
};

export type DocumentChunksResponse = {
  document_id: string;
  file_name: string;
  chunks: DocumentChunkItem[];
};

export type ChatCitation = {
  document_id?: string | null;
  document_name?: string | null;
  knowledge_base?: string | null;
  chunk_id?: string | null;
  page?: number | null;
  snippet?: string | null;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system" | string;
  content: string;
  citations: ChatCitation[];
  created_at: string;
};

export type ChatSession = {
  session_id: string;
  created_at: string;
  message_count: number;
  last_message_at?: string | null;
};

export type ChatSessionListResponse = {
  sessions: ChatSession[];
};

export type ChatSessionCreateResponse = {
  session_id: string;
  created_at: string;
};

export type ChatSessionDeleteResponse = {
  status: string;
  session: ChatSession;
};

export type ChatMessagesResponse = {
  session_id: string;
  messages: ChatMessage[];
};

export type ChatFilters = {
  document_names?: string[];
  tags?: string[];
  knowledge_bases?: string[];
};

export type ChatMessageRequest = {
  message: string;
  top_k?: number;
  keywords?: string[];
  filters?: ChatFilters;
};

export type ChatSendMessageResponse = {
  session_id: string;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
};

export type KnowledgeBaseItem = {
  name: string;
  document_count: number;
  created_at?: string | null;
  profile_mode: "precision" | "balanced" | "recall" | string;
  chunk_size_tokens: number;
  chunk_overlap_tokens: number;
  chunk_keyword_limit: number;
};

export type KnowledgeBaseListResponse = {
  knowledge_bases: KnowledgeBaseItem[];
};

export type KnowledgeBaseCreateResponse = {
  name: string;
  document_count: number;
  created_at?: string | null;
  profile_mode: "precision" | "balanced" | "recall" | string;
  chunk_size_tokens: number;
  chunk_overlap_tokens: number;
  chunk_keyword_limit: number;
};

export type KnowledgeBaseResponse = {
  name: string;
  document_count: number;
  created_at?: string | null;
  profile_mode: "precision" | "balanced" | "recall" | string;
  chunk_size_tokens: number;
  chunk_overlap_tokens: number;
  chunk_keyword_limit: number;
};

export type KnowledgeBaseDeleteResponse = {
  status: string;
  knowledge_base: KnowledgeBaseResponse;
};

export type KnowledgeBaseUpdateRequest = {
  name?: string;
  profile_mode?: "precision" | "balanced" | "recall" | string;
  chunk_size_tokens?: number;
  chunk_overlap_tokens?: number;
  chunk_keyword_limit?: number;
};

export type KnowledgeBaseReindexResponse = {
  knowledge_base: string;
  queued_jobs: number;
};
