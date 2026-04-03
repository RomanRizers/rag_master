import unittest
from tempfile import TemporaryDirectory

import numpy as np

from backend.infrastructure.chat_store.memory import InMemoryChatStore
from backend.infrastructure.document_store.memory import InMemoryDocumentStore
from backend.infrastructure.job_store.memory import InMemoryJobStore
from backend.infrastructure.storage.local import LocalFileStorageAdapter
from backend.services.api_service import ApiService
from backend.services.chat_service import ChatService
from backend.services.document_service import DocumentService
from backend.services.ingestion_service import IngestionService


class _FakeVectorizer:
    def vectorize_text(self, _text: str):
        return np.array([0.1, 0.2, 0.3], dtype=float)


class _FakeQdrantService:
    def __init__(self):
        self._rows: list[dict] = []

    def index_document(self, document_name, content_vector, content, keywords, dataframe=None, metadata=None):
        metadata = metadata or {}
        self._rows.append(
            {
                "id": f"row-{len(self._rows) + 1}",
                "vector": np.array(content_vector, dtype=float),
                "payload": {
                    "content": content,
                    "keywords": list(keywords or []),
                    "document_name": document_name,
                    "document_id": metadata.get("document_id"),
                    "chunk_id": metadata.get("chunk_id"),
                    "page": metadata.get("page"),
                    "tags": list(metadata.get("tags") or []),
                },
            }
        )

    def search(self, query_vector, top_k, keywords=None):
        query_vector = np.array(query_vector, dtype=float)
        rows = []
        for row in self._rows:
            payload = row["payload"]
            row_keywords = set(str(item).lower() for item in payload.get("keywords") or [])
            if keywords:
                needed = set(str(item).lower() for item in keywords)
                if not needed.issubset(row_keywords):
                    continue
            score = float(np.dot(row["vector"], query_vector))
            rows.append({"id": row["id"], "score": score, "payload": payload})
        rows.sort(key=lambda item: item["score"], reverse=True)
        return rows[:top_k]

    def delete_document_chunks(self, document_id):
        self._rows = [row for row in self._rows if row["payload"].get("document_id") != document_id]

    def count_document_chunks(self, document_id):
        return sum(1 for row in self._rows if row["payload"].get("document_id") == document_id)

    def list_indexed_document_ids(self):
        return sorted({row["payload"].get("document_id") for row in self._rows if row["payload"].get("document_id")})


class _FakeLLMProvider:
    def generate(self, messages, temperature=0.2, max_tokens=700):
        _ = (temperature, max_tokens)
        user_messages = [item["content"] for item in messages if item.get("role") == "user"]
        return f"Ответ: {user_messages[-1]}" if user_messages else "Ответ"

    def stream_chat(self, messages, temperature=0.2, max_tokens=700):
        _ = (messages, temperature, max_tokens)
        yield "Ответ"


class RagE2EFlowTestCase(unittest.TestCase):
    def test_upload_index_and_chat_returns_citations(self):
        with TemporaryDirectory() as temp_dir:
            document_service = DocumentService(
                storage=LocalFileStorageAdapter(temp_dir),
                store=InMemoryDocumentStore(),
            )
            api_service = ApiService(
                qdrant_service=_FakeQdrantService(),
                vectorizer=_FakeVectorizer(),
            )
            ingestion_service = IngestionService(
                document_service=document_service,
                api_service=api_service,
                job_store=InMemoryJobStore(),
            )

            document = document_service.create_document(
                file_name="story.txt",
                mime_type="text/plain",
                content_bytes="Harry Potter wears glasses and lives with the Dursleys.".encode("utf-8"),
                source_name="books",
                tags=["fiction", "hp"],
            )
            document_id = document["document_id"]

            job = ingestion_service.start_indexing(document_id)
            claimed = ingestion_service.claim_next_job()
            self.assertIsNotNone(claimed)
            self.assertEqual(claimed["job_id"], job["job_id"])

            ingestion_service.process_job(job["job_id"])
            done_job = ingestion_service.get_job(job["job_id"])
            self.assertEqual(done_job["status"], "done")

            chat_service = ChatService(
                llm_provider=_FakeLLMProvider(),
                retriever=lambda query, top_k, keywords, filters=None: api_service.search_query(query, top_k, keywords),
                chat_store=InMemoryChatStore(),
            )

            session = chat_service.create_session()
            user_message, assistant_message = chat_service.send_message(
                session["session_id"],
                "Who wears glasses?",
                top_k=3,
            )

            self.assertEqual(user_message["role"], "user")
            self.assertEqual(assistant_message["role"], "assistant")
            self.assertGreater(len(assistant_message["citations"]), 0)

            citation = assistant_message["citations"][0]
            self.assertEqual(citation["document_name"], "story.txt")
            self.assertTrue((citation.get("snippet") or "").strip())


if __name__ == "__main__":
    unittest.main()
