#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from backend.evaluation.harness import evaluate_retrieval, load_cases
from backend.services.api_service import ApiService


def main() -> int:
    parser = argparse.ArgumentParser(description="Run offline RAG retrieval evaluation.")
    parser.add_argument(
        "--cases",
        default="backend/evaluation/golden_questions.sample.json",
        help="Path to JSON file with golden questions.",
    )
    parser.add_argument("--top-k", type=int, default=5, help="Retrieval cutoff for hit@k metrics.")
    args = parser.parse_args()

    api_service = ApiService()
    cases = load_cases(args.cases)
    report = evaluate_retrieval(
        cases,
        lambda query, top_k: api_service.search_query(query, top_k=top_k),
        top_k=args.top_k,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
