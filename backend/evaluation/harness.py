from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class EvaluationCase:
    case_id: str
    query: str
    expected_documents: list[str]
    expected_pages: list[int]
    expected_facts: list[str]
    answer_type: str


def load_cases(path: str | Path) -> list[EvaluationCase]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        EvaluationCase(
            case_id=str(item["case_id"]),
            query=str(item["query"]),
            expected_documents=[str(value) for value in item.get("expected_documents") or []],
            expected_pages=[int(value) for value in item.get("expected_pages") or []],
            expected_facts=[str(value) for value in item.get("expected_facts") or []],
            answer_type=str(item.get("answer_type") or "fact"),
        )
        for item in raw
    ]


def evaluate_retrieval(cases: list[EvaluationCase], search_fn, *, top_k: int = 5) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    metrics = {
        "cases": len(cases),
        "document_hit_at_k": 0,
        "page_hit_at_k": 0,
        "fact_hit_at_k": 0,
    }
    for case in cases:
        response = search_fn(case.query, top_k=top_k)
        results = list(response.get("results") or [])
        documents = [str((item.get("payload") or {}).get("document_name") or "") for item in results]
        pages = [
            int((item.get("payload") or {}).get("page"))
            for item in results
            if (item.get("payload") or {}).get("page") is not None
        ]
        contents = [str((item.get("payload") or {}).get("content") or "") for item in results]
        document_hit = any(expected in documents for expected in case.expected_documents) if case.expected_documents else False
        page_hit = any(expected in pages for expected in case.expected_pages) if case.expected_pages else False
        fact_hit = any(
            expected_fact.lower() in content.lower()
            for expected_fact in case.expected_facts
            for content in contents
        ) if case.expected_facts else False

        metrics["document_hit_at_k"] += int(document_hit)
        metrics["page_hit_at_k"] += int(page_hit)
        metrics["fact_hit_at_k"] += int(fact_hit)
        rows.append(
            {
                "case_id": case.case_id,
                "query": case.query,
                "document_hit_at_k": document_hit,
                "page_hit_at_k": page_hit,
                "fact_hit_at_k": fact_hit,
                "top_document_names": documents[:top_k],
                "top_pages": pages[:top_k],
            }
        )

    total = max(metrics["cases"], 1)
    summary = {
        **metrics,
        "document_hit_rate": metrics["document_hit_at_k"] / total,
        "page_hit_rate": metrics["page_hit_at_k"] / total,
        "fact_hit_rate": metrics["fact_hit_at_k"] / total,
        "top_k": top_k,
    }
    return {"summary": summary, "cases": rows}
