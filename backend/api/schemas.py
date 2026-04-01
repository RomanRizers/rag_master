from pydantic import BaseModel, Field, field_validator

from backend.core.config import Config


class SearchRequest(BaseModel):
    query: str
    top_k: int = Config.TOP_K_DEFAULT
    keywords: list[str] | None = None

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
