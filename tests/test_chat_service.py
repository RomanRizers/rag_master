import unittest
from unittest.mock import patch

from backend.services.chat_service import (
    NO_ANSWER_MESSAGE,
    _apply_search_filters,
    _build_context,
    _compress_history,
    _select_context_results,
    _should_return_no_answer,
)


class ChatServiceRankingTestCase(unittest.TestCase):
    @patch("backend.services.chat_service.Config.RERANK_TOP_N", 2)
    @patch("backend.services.chat_service.Config.RERANK_SEMANTIC_WEIGHT", 0.3)
    @patch("backend.services.chat_service.Config.RERANK_LEXICAL_WEIGHT", 0.5)
    @patch("backend.services.chat_service.Config.RERANK_KEYWORD_WEIGHT", 0.15)
    @patch("backend.services.chat_service.Config.RERANK_METADATA_WEIGHT", 0.05)
    def test_rerank_prioritizes_lexical_match_when_weighted(self):
        results = [
            {
                "id": "semantic-only",
                "score": 0.95,
                "payload": {"content": "Совсем другой текст без совпадений"},
            },
            {
                "id": "lexical-hit",
                "score": 0.70,
                "payload": {"content": "Гарри Поттер вернулся в Хогвартс"},
            },
            {
                "id": "low-all",
                "score": 0.10,
                "payload": {"content": "Случайный абзац"},
            },
        ]

        selected = _select_context_results("гарри поттер", results)

        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0]["id"], "lexical-hit")

    @patch("backend.services.chat_service.Config.RERANK_TOP_N", 1)
    def test_select_context_results_limits_to_top_n(self):
        results = [
            {"id": "a", "score": 0.9, "payload": {"content": "one"}},
            {"id": "b", "score": 0.8, "payload": {"content": "two"}},
        ]
        selected = _select_context_results("one", results)
        self.assertEqual(len(selected), 1)

    def test_build_context_respects_character_budget(self):
        results = [
            {"id": "a", "payload": {"content": "a " * 100, "token_count": 100}},
            {"id": "b", "payload": {"content": "b " * 100, "token_count": 100}},
        ]
        context = _build_context(results, max_chars=120)
        self.assertIn("[1]", context)
        self.assertNotIn("[2]", context)

    def test_build_context_skips_duplicates(self):
        results = [
            {"id": "a", "payload": {"document_id": "d1", "page": 1, "section": "S", "content": "same", "token_count": 1}},
            {"id": "b", "payload": {"document_id": "d1", "page": 1, "section": "S", "content": "same", "token_count": 1}},
        ]
        context = _build_context(results, max_chars=10)
        self.assertEqual(context.count("[1]"), 1)
        self.assertNotIn("[2]", context)

    @patch("backend.services.chat_service.Config.CHAT_HISTORY_MAX_MESSAGES", 2)
    def test_compress_history_keeps_recent_turns(self):
        history = [
            {"role": "system", "content": "ignored"},
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "u2"},
        ]
        compressed = _compress_history(history)
        self.assertEqual([item["content"] for item in compressed], ["a1", "u2"])

    @patch("backend.services.chat_service.Config.CHAT_MIN_RESULTS_REQUIRED", 1)
    @patch("backend.services.chat_service.Config.CHAT_MIN_RERANK_SCORE", 0.5)
    def test_should_return_no_answer_uses_rerank_threshold(self):
        self.assertTrue(_should_return_no_answer([]))
        self.assertTrue(_should_return_no_answer([{"rerank_score": 0.3}]))
        self.assertFalse(_should_return_no_answer([{"rerank_score": 0.7}]))
        self.assertTrue(NO_ANSWER_MESSAGE.startswith("Ответ, который вы ищете"))

    def test_apply_search_filters_by_document_name(self):
        results = [
            {"id": "a", "payload": {"document_name": "A.pdf", "tags": ["x"]}},
            {"id": "b", "payload": {"document_name": "B.pdf", "tags": ["y"]}},
        ]
        filtered = _apply_search_filters(results, {"document_names": ["b.pdf"]})
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["id"], "b")

    def test_apply_search_filters_by_tags(self):
        results = [
            {"id": "a", "payload": {"document_name": "A.pdf", "tags": ["finance", "sales"]}},
            {"id": "b", "payload": {"document_name": "B.pdf", "tags": ["hr"]}},
        ]
        filtered = _apply_search_filters(results, {"tags": ["sales"]})
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["id"], "a")

    def test_apply_search_filters_combines_name_and_tags(self):
        results = [
            {"id": "a", "payload": {"document_name": "A.pdf", "tags": ["finance"]}},
            {"id": "b", "payload": {"document_name": "A.pdf", "tags": ["hr"]}},
        ]
        filtered = _apply_search_filters(results, {"document_names": ["A.pdf"], "tags": ["finance"]})
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["id"], "a")

    def test_apply_search_filters_by_knowledge_base(self):
        results = [
            {"id": "a", "payload": {"document_name": "A.pdf", "tags": ["finance"], "knowledge_base": "kb-a"}},
            {"id": "b", "payload": {"document_name": "B.pdf", "tags": ["finance"], "knowledge_base": "kb-b"}},
        ]
        filtered = _apply_search_filters(results, {"knowledge_bases": ["kb-b"]})
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["id"], "b")


if __name__ == "__main__":
    unittest.main()
