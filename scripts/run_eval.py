#!/usr/bin/env python3
"""Run retrieval evaluation on a JSON dataset."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.evaluator import Evaluator
from src.utils.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate FusionRAG retrieval")
    parser.add_argument(
        "--dataset",
        type=str,
        default=str(
            get_settings().project_root
            / "data"
            / "documents"
            / "confluence"
            / "confluence_questions.jsonl"
        ),
        help="Path to eval JSON/JSONL file or directory (default: Confluence benchmark)",
    )
    parser.add_argument(
        "--k",
        type=str,
        default="1,5,10",
        help="Comma-separated K values",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(get_settings().project_root / "reports"),
        help="Output directory for reports",
    )
    parser.add_argument(
        "--with-reranker",
        action="store_true",
        help="Rerank RRF candidates with ChunkReranker before computing metrics",
    )
    args = parser.parse_args()

    k_values = [int(k.strip()) for k in args.k.split(",")]
    evaluator = Evaluator(use_reranker=args.with_reranker)
    evaluator.run_and_save(args.dataset, args.output, k_values)


if __name__ == "__main__":
    main()
