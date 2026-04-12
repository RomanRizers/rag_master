import uuid
import re

import structlog
import qdrant_client
from qdrant_client.models import Distance, FieldCondition, Filter, MatchAny, MatchValue, PointStruct, VectorParams

from backend.core.config import Config
from backend.core.exceptions import StorageError

logger = structlog.get_logger("qdrant")
_TOKEN_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9]+")


class QdrantService:
    def __init__(self):
        """Инициализирует подключение к Qdrant и задает имя коллекции."""
        self.client = qdrant_client.QdrantClient(url=Config.QDRANT_URL)
        self.collection_name = Config.COLLECTION_NAME
        logger.info("qdrant_client_initialized", qdrant_url=Config.QDRANT_URL, collection_name=self.collection_name)

    def search(self, query_vector, top_k, keywords=None, filters=None, lexical_terms=None):
        """Выполняет hybrid retrieval: dense + lexical fusion."""
        normalized_keywords = _normalize_keywords(keywords)
        normalized_lexical_terms = _normalize_keywords(lexical_terms) or normalized_keywords
        query_filter = _build_query_filter(normalized_keywords, filters)
        logger.info("qdrant_search_started", top_k=top_k, keywords_count=len(normalized_keywords))

        dense_results = self._dense_search(
            query_vector,
            limit=max(top_k, Config.DENSE_RETRIEVE_TOP_N),
            query_filter=query_filter,
        )
        lexical_results = self._lexical_search(
            filters=filters,
            keywords=normalized_lexical_terms,
            limit=max(top_k, Config.SPARSE_RETRIEVE_TOP_N),
        )
        search_result = _fuse_ranked_results(
            dense_results=dense_results,
            lexical_results=lexical_results,
            limit=max(top_k, Config.FUSED_RETRIEVE_TOP_N),
        )
        logger.info(
            "qdrant_search_finished",
            results_count=len(search_result),
            dense_count=len(dense_results),
            lexical_count=len(lexical_results),
        )
        return search_result[:top_k]

    def index_document(self, document_name, content_vector, content, keywords, dataframe=None, metadata=None):
        """Индексирует документ в коллекции Qdrant."""
        document_id = str(uuid.uuid4())
        logger.info(
            "qdrant_index_started",
            document_id=document_id,
            document_name=document_name,
            keywords_count=len(keywords) if keywords else 0,
            has_dataframe=dataframe is not None,
        )

        if keywords:
            keywords = [kw.lower() for kw in keywords]

        payload = {
            "document_name": document_name,
            "content": content,
            "keywords": keywords,
            "dataframe": dataframe
        }
        if isinstance(metadata, dict):
            payload.update(metadata)

        point = PointStruct(
            id=document_id,
            vector=content_vector.tolist(),
            payload=payload
        )

        try:
            self._ensure_collection(vector_size=len(content_vector))
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
        except Exception as error:
            raise StorageError(message="Qdrant upsert failed", details={"reason": str(error)}) from error
        logger.info("qdrant_index_finished", document_id=document_id)

    def delete_document_chunks(self, document_id: str):
        logger.info("qdrant_delete_document_chunks_started", document_id=document_id)
        if not self._collection_exists():
            logger.info("qdrant_delete_document_chunks_skipped_missing_collection", document_id=document_id)
            return
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id),
                        )
                    ]
                ),
                wait=True,
            )
        except Exception as error:
            raise StorageError(message="Qdrant delete failed", details={"reason": str(error)}) from error
        logger.info("qdrant_delete_document_chunks_finished", document_id=document_id)

    def count_document_chunks(self, document_id: str) -> int:
        logger.info("qdrant_count_document_chunks_started", document_id=document_id)
        if not self._collection_exists():
            logger.info("qdrant_count_document_chunks_missing_collection", document_id=document_id, chunks_count=0)
            return 0
        try:
            response = self.client.count(
                collection_name=self.collection_name,
                count_filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id),
                        )
                    ]
                ),
                exact=True,
            )
        except Exception as error:
            raise StorageError(message="Qdrant count failed", details={"reason": str(error)}) from error
        count = int(getattr(response, "count", 0))
        logger.info("qdrant_count_document_chunks_finished", document_id=document_id, chunks_count=count)
        return count

    def list_indexed_document_ids(self, batch_size: int = 256) -> list[str]:
        logger.info("qdrant_list_indexed_document_ids_started", batch_size=batch_size)
        if batch_size < 1:
            batch_size = 1
        if not self._collection_exists():
            logger.info("qdrant_list_indexed_document_ids_missing_collection", documents_count=0)
            return []

        ids: set[str] = set()
        offset = None
        try:
            while True:
                points, next_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=batch_size,
                    offset=offset,
                    with_payload=["document_id"],
                    with_vectors=False,
                )
                for point in points:
                    payload = getattr(point, "payload", None) or {}
                    document_id = payload.get("document_id")
                    if isinstance(document_id, str) and document_id:
                        ids.add(document_id)
                if next_offset is None:
                    break
                if next_offset == offset:
                    break
                offset = next_offset
        except Exception as error:
            raise StorageError(message="Qdrant list ids failed", details={"reason": str(error)}) from error

        result = sorted(ids)
        logger.info("qdrant_list_indexed_document_ids_finished", documents_count=len(result))
        return result

    def get_document_index_summary(self, document_id: str, batch_size: int = 128) -> dict:
        logger.info("qdrant_get_document_index_summary_started", document_id=document_id)
        if not self._collection_exists():
            return {"chunks_count": 0, "keywords": [], "document_keywords": [], "index_profile": None}

        chunk_count = 0
        keyword_counts: dict[str, int] = {}
        document_keyword_counts: dict[str, int] = {}
        index_profile = None
        offset = None
        try:
            while True:
                points, next_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(
                                key="document_id",
                                match=MatchValue(value=document_id),
                            )
                        ]
                    ),
                    limit=batch_size,
                    offset=offset,
                    with_payload=["keywords", "document_keywords", "index_profile"],
                    with_vectors=False,
                )
                if not points:
                    break
                for point in points:
                    payload = getattr(point, "payload", None) or {}
                    chunk_count += 1
                    for keyword in payload.get("keywords") or []:
                        normalized = str(keyword).strip().lower()
                        if normalized:
                            keyword_counts[normalized] = keyword_counts.get(normalized, 0) + 1
                    for keyword in payload.get("document_keywords") or []:
                        normalized = str(keyword).strip().lower()
                        if normalized:
                            document_keyword_counts[normalized] = document_keyword_counts.get(normalized, 0) + 1
                    if index_profile is None and isinstance(payload.get("index_profile"), dict):
                        index_profile = dict(payload["index_profile"])
                if next_offset is None or next_offset == offset:
                    break
                offset = next_offset
        except Exception as error:
            raise StorageError(message="Qdrant document summary failed", details={"reason": str(error)}) from error

        return {
            "chunks_count": chunk_count,
            "keywords": _top_keywords(keyword_counts, 12),
            "document_keywords": _top_keywords(document_keyword_counts, 16),
            "index_profile": index_profile,
        }

    def get_document_chunks(self, document_id: str, batch_size: int = 128) -> list[dict]:
        if not self._collection_exists():
            return []
        offset = None
        rows: list[dict] = []
        try:
            while True:
                points, next_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(
                                key="document_id",
                                match=MatchValue(value=document_id),
                            )
                        ]
                    ),
                    limit=batch_size,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )
                for point in points:
                    payload = getattr(point, "payload", None) or {}
                    rows.append(
                        {
                            "chunk_id": str(payload.get("chunk_id") or point.id),
                            "chunk_index": int(payload.get("chunk_index") or 0),
                            "content": str(payload.get("content") or ""),
                            "keywords": list(payload.get("keywords") or []),
                            "page": payload.get("page"),
                            "section": payload.get("section"),
                            "token_count": int(payload.get("token_count") or 0),
                            "block_type": payload.get("block_type"),
                            "heading_path": list(payload.get("heading_path") or []),
                            "document_id": payload.get("document_id"),
                            "document_name": payload.get("document_name"),
                        }
                    )
                if next_offset is None or next_offset == offset:
                    break
                offset = next_offset
        except Exception as error:
            raise StorageError(message="Qdrant document chunks failed", details={"reason": str(error)}) from error
        rows.sort(key=lambda item: (int(item.get("chunk_index") or 0), str(item.get("chunk_id") or "")))
        return rows

    def iter_points(self, filters: dict | None = None, batch_size: int = 128) -> list[dict]:
        if not self._collection_exists():
            return []
        offset = None
        rows: list[dict] = []
        query_filter = _build_query_filter(None, filters)
        try:
            while True:
                points, next_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=query_filter,
                    limit=batch_size,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )
                for point in points:
                    rows.append(
                        {
                            "id": point.id,
                            "payload": getattr(point, "payload", None) or {},
                        }
                    )
                if next_offset is None or next_offset == offset:
                    break
                offset = next_offset
        except Exception as error:
            raise StorageError(message="Qdrant scroll failed", details={"reason": str(error)}) from error
        return rows

    def _dense_search(self, query_vector, *, limit: int, query_filter: Filter | None) -> list[dict]:
        try:
            if hasattr(self.client, "query_points"):
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    query_filter=query_filter,
                    limit=limit,
                )
                hits = response.points
            else:
                hits = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    query_filter=query_filter,
                    limit=limit,
                )
        except Exception as error:
            raise StorageError(message="Qdrant dense search failed", details={"reason": str(error)}) from error
        return [{"id": hit.id, "payload": hit.payload, "score": float(hit.score)} for hit in hits]

    def _lexical_search(self, *, filters: dict | None, keywords: list[str], limit: int) -> list[dict]:
        rows = self.iter_points(filters=filters, batch_size=128)
        ranked: list[dict] = []
        for row in rows:
            payload = row.get("payload") or {}
            lexical_score = _lexical_score_for_payload(keywords, payload)
            if lexical_score <= 0:
                continue
            ranked.append({"id": row["id"], "payload": payload, "score": lexical_score})
        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[:limit]

    def _ensure_collection(self, vector_size: int):
        if self._collection_exists():
            return
        try:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=int(vector_size), distance=Distance.COSINE),
            )
        except Exception as error:
            raise StorageError(message="Qdrant collection create failed", details={"reason": str(error)}) from error
        logger.info("qdrant_collection_created", collection_name=self.collection_name, vector_size=int(vector_size))

    def _collection_exists(self) -> bool:
        try:
            if hasattr(self.client, "collection_exists"):
                return bool(self.client.collection_exists(self.collection_name))
            self.client.get_collection(self.collection_name)
            return True
        except Exception:
            return False


def _top_keywords(counts: dict[str, int], limit: int) -> list[str]:
    return [
        keyword
        for keyword, _ in sorted(counts.items(), key=lambda item: (-item[1], len(item[0]), item[0]))[:limit]
    ]


def _normalize_keywords(keywords) -> list[str]:
    if not keywords:
        return []
    if isinstance(keywords, str):
        return [keywords.strip().lower()] if keywords.strip() else []
    return [str(keyword).strip().lower() for keyword in keywords if str(keyword).strip()]


def _build_query_filter(keywords: list[str] | None, filters: dict | None) -> Filter | None:
    must_conditions = []
    if keywords:
        must_conditions.append(FieldCondition(key="keywords", match=MatchAny(any=keywords)))
    knowledge_bases = filters.get("knowledge_bases") if isinstance(filters, dict) else None
    if knowledge_bases:
        must_conditions.append(
            FieldCondition(
                key="knowledge_base",
                match=MatchAny(any=[str(item).strip() for item in knowledge_bases if str(item).strip()]),
            )
        )
    return Filter(must=must_conditions) if must_conditions else None


def _fuse_ranked_results(*, dense_results: list[dict], lexical_results: list[dict], limit: int) -> list[dict]:
    fused: dict[str, dict] = {}
    for rank, item in enumerate(dense_results, start=1):
        key = str(item["id"])
        fused.setdefault(key, {"id": item["id"], "payload": item.get("payload") or {}, "score": 0.0, "score_details": {}})
        fused[key]["score"] += 1.0 / (60 + rank)
        fused[key]["score_details"]["dense_rank"] = rank
        fused[key]["score_details"]["dense_score"] = item.get("score")
    for rank, item in enumerate(lexical_results, start=1):
        key = str(item["id"])
        fused.setdefault(key, {"id": item["id"], "payload": item.get("payload") or {}, "score": 0.0, "score_details": {}})
        fused[key]["score"] += 1.0 / (60 + rank)
        fused[key]["score_details"]["lexical_rank"] = rank
        fused[key]["score_details"]["lexical_score"] = item.get("score")
    return sorted(fused.values(), key=lambda item: float(item.get("score") or 0.0), reverse=True)[:limit]


def _lexical_score_for_payload(query_terms: list[str], payload: dict) -> float:
    if not query_terms:
        return 0.0
    corpus_parts = [
        str(payload.get("content") or ""),
        str(payload.get("document_name") or ""),
        str(payload.get("section") or ""),
        " ".join(str(item) for item in (payload.get("keywords") or [])),
        " ".join(str(item) for item in (payload.get("document_keywords") or [])),
        " ".join(str(item) for item in (payload.get("heading_path") or [])),
    ]
    corpus_text = " ".join(part for part in corpus_parts if part).lower()
    corpus_tokens = set(_TOKEN_RE.findall(corpus_text))
    if not corpus_tokens:
        return 0.0
    matched = 0.0
    for term in query_terms:
        term_tokens = _TOKEN_RE.findall(term.lower())
        if not term_tokens:
            continue
        if all(token in corpus_tokens for token in term_tokens):
            matched += 1.5 if len(term_tokens) > 1 else 1.0
    return matched / float(max(len(query_terms), 1))
