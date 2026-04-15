import json
import tempfile
import unittest

from backend.evaluation.harness import evaluate_retrieval, load_cases
from backend.services.query_normalization import normalize_query


class QueryNormalizationTestCase(unittest.TestCase):
    def test_normalize_query_expands_aliases_and_identifiers(self):
        result = normalize_query("ГОСТ 17375 для ЗРА")
        self.assertIn("зра", result["expanded_terms"])
        self.assertIn("государственный стандарт", result["expanded_terms"])
        self.assertIn("17375", result["exact_identifiers"])
        self.assertIn("Синонимы и расширения запроса", result["expanded_query"])


class EvaluationHarnessTestCase(unittest.TestCase):
    def test_load_and_evaluate_cases(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".json", encoding="utf-8") as handle:
            json.dump(
                [
                    {
                        "case_id": "case-1",
                        "query": "Что такое ЗРА?",
                        "expected_documents": ["doc-a.pdf"],
                        "expected_pages": [2],
                        "expected_facts": ["запорно-регулирующая арматура"],
                        "answer_type": "definition",
                    }
                ],
                handle,
                ensure_ascii=False,
            )
            handle.flush()
            cases = load_cases(handle.name)

        report = evaluate_retrieval(
            cases,
            lambda _query, top_k: {
                "results": [
                    {
                        "payload": {
                            "document_name": "doc-a.pdf",
                            "page": 2,
                            "content": "Здесь описана запорно-регулирующая арматура.",
                        }
                    }
                ][:top_k]
            },
            top_k=3,
        )
        self.assertEqual(report["summary"]["document_hit_rate"], 1.0)
        self.assertEqual(report["summary"]["page_hit_rate"], 1.0)
        self.assertEqual(report["summary"]["fact_hit_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
