from pydantic import BaseModel, Field, field_validator

from backend.core.config import Config


class SearchRequest(BaseModel):
    query: str
    top_k: int = Config.TOP_K_DEFAULT
    keywords: list[str] | None = None
    filters: "SearchFilters | None" = None

    @field_validator("query", mode="before")
    @classmethod
    def validate_query(cls, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Query is required")
        return value.strip()

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, value: int):
        if value < 1 or value > Config.TOP_K_MAX:
            raise ValueError(f"'top_k' must be between 1 and {Config.TOP_K_MAX}")
        return value

    @field_validator("keywords", mode="before")
    @classmethod
    def validate_keywords(cls, value):
        if value is None:
            return None
        if not isinstance(value, list):
            raise ValueError("'keywords' must be a list of non-empty strings")

        normalized = []
        for keyword in value:
            if not isinstance(keyword, str) or not keyword.strip():
                raise ValueError("'keywords' must be a list of non-empty strings")
            normalized.append(keyword.strip())
        return normalized


class IndexDocument(BaseModel):
    content: str
    dataframe: str | None = None
    keywords: list[str] = Field(default_factory=list)
    metadata: dict | None = None

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Each document must include non-empty 'content'")
        return value.strip()

    @field_validator("dataframe", mode="before")
    @classmethod
    def validate_dataframe(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("'dataframe' must be a string when provided")
        return value

    @field_validator("keywords", mode="before")
    @classmethod
    def validate_keywords(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("'keywords' must be a list of non-empty strings")

        normalized = []
        for keyword in value:
            if not isinstance(keyword, str) or not keyword.strip():
                raise ValueError("'keywords' must be a list of non-empty strings")
            normalized.append(keyword.strip())
        return normalized

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata(cls, value):
        if value is None:
            return None
        if not isinstance(value, dict):
            raise ValueError("'metadata' must be an object when provided")
        return value


class IndexingRequest(BaseModel):
    document_name: str
    documents: list[IndexDocument]

    @field_validator("document_name", mode="before")
    @classmethod
    def validate_document_name(cls, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("No document name provided")
        return value.strip()

    @field_validator("documents", mode="before")
    @classmethod
    def validate_documents(cls, value):
        if not isinstance(value, list) or len(value) == 0:
            raise ValueError("No documents to index")
        return value


class ChatCitation(BaseModel):
    document_id: str | None = None
    document_name: str | None = None
    chunk_id: str | None = None
    page: int | None = None
    snippet: str | None = None


class ChatMessageItem(BaseModel):
    id: str
    role: str
    content: str
    citations: list[ChatCitation] = Field(default_factory=list)
    created_at: str


class ChatSessionCreateResponse(BaseModel):
    session_id: str
    created_at: str


class ChatSessionListItem(BaseModel):
    session_id: str
    created_at: str
    message_count: int
    last_message_at: str | None = None


class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSessionListItem]


class ChatSessionMessagesResponse(BaseModel):
    session_id: str
    messages: list[ChatMessageItem]


class ChatFilters(BaseModel):
    document_names: list[str] | None = None
    tags: list[str] | None = None
    knowledge_bases: list[str] | None = None

    @field_validator("document_names", "tags", "knowledge_bases", mode="before")
    @classmethod
    def validate_string_list(cls, value):
        if value is None:
            return None
        if not isinstance(value, list):
            raise ValueError("Filters fields must be lists of non-empty strings")

        normalized = []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("Filters fields must be lists of non-empty strings")
            normalized.append(item.strip())
        return normalized


class ChatMessageRequest(BaseModel):
    message: str
    top_k: int = Config.TOP_K_DEFAULT
    keywords: list[str] | None = None
    filters: ChatFilters | None = None

    @field_validator("message", mode="before")
    @classmethod
    def validate_message(cls, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Message is required")
        return value.strip()

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, value: int):
        if value < 1 or value > Config.TOP_K_MAX:
            raise ValueError(f"'top_k' must be between 1 and {Config.TOP_K_MAX}")
        return value

    @field_validator("keywords", mode="before")
    @classmethod
    def validate_keywords(cls, value):
        if value is None:
            return None
        if not isinstance(value, list):
            raise ValueError("'keywords' must be a list of non-empty strings")

        normalized = []
        for keyword in value:
            if not isinstance(keyword, str) or not keyword.strip():
                raise ValueError("'keywords' must be a list of non-empty strings")
            normalized.append(keyword.strip())
        return normalized


class ChatSendMessageResponse(BaseModel):
    session_id: str
    user_message: ChatMessageItem
    assistant_message: ChatMessageItem


class DocumentUploadResponse(BaseModel):
    document_id: str
    file_name: str
    mime_type: str
    size_bytes: int
    status: str
    knowledge_base: str
    created_at: str


class DocumentIndexResponse(BaseModel):
    job_id: str
    status: str
    document_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    document_id: str
    status: str
    progress: int
    attempt: int = 0
    error_code: str | None = None
    error_message: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


class JobListResponse(BaseModel):
    jobs: list[JobStatusResponse]


class DocumentIndexStatsResponse(BaseModel):
    document_id: str
    status: str
    chunks_count: int
    keywords: list[str] = Field(default_factory=list)
    document_keywords: list[str] = Field(default_factory=list)
    index_profile: dict | None = None
    latest_job: JobStatusResponse | None = None


class OrphanCleanupRequest(BaseModel):
    dry_run: bool = True


class OrphanCleanupResponse(BaseModel):
    dry_run: bool
    indexed_documents_count: int
    existing_documents_count: int
    orphan_document_ids: list[str]
    deleted_documents_count: int


class DocumentListItem(BaseModel):
    document_id: str
    file_name: str
    mime_type: str
    size_bytes: int
    status: str
    source_name: str | None = None
    tags: list[str] = Field(default_factory=list)
    knowledge_base: str
    created_at: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentListItem]


class KnowledgeBaseListItem(BaseModel):
    name: str
    document_count: int
    created_at: str | None = None
    profile_mode: str
    chunk_size_tokens: int
    chunk_overlap_tokens: int
    chunk_keyword_limit: int
    document_keyword_limit: int


class KnowledgeBaseListResponse(BaseModel):
    knowledge_bases: list[KnowledgeBaseListItem]


class KnowledgeBaseCreateRequest(BaseModel):
    name: str


class KnowledgeBaseCreateResponse(BaseModel):
    name: str
    document_count: int
    created_at: str | None = None
    profile_mode: str
    chunk_size_tokens: int
    chunk_overlap_tokens: int
    chunk_keyword_limit: int
    document_keyword_limit: int


class KnowledgeBaseRenameRequest(BaseModel):
    name: str | None = None
    profile_mode: str | None = None
    chunk_size_tokens: int | None = None
    chunk_overlap_tokens: int | None = None
    chunk_keyword_limit: int | None = None
    document_keyword_limit: int | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_optional_name(cls, value):
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise ValueError("name must be a non-empty string")
        return value.strip()


class KnowledgeBaseResponse(BaseModel):
    name: str
    document_count: int
    created_at: str | None = None
    profile_mode: str
    chunk_size_tokens: int
    chunk_overlap_tokens: int
    chunk_keyword_limit: int
    document_keyword_limit: int


class KnowledgeBaseReindexResponse(BaseModel):
    knowledge_base: str
    queued_jobs: int


class SearchFilters(BaseModel):
    knowledge_bases: list[str] | None = None

    @field_validator("knowledge_bases", mode="before")
    @classmethod
    def validate_string_list(cls, value):
        if value is None:
            return None
        if not isinstance(value, list):
            raise ValueError("Filters fields must be lists of non-empty strings")

        normalized = []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("Filters fields must be lists of non-empty strings")
            normalized.append(item.strip())
        return normalized


SearchRequest.model_rebuild()
