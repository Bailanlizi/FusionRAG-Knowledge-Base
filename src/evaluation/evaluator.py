"""Evaluation pipeline for retrieval quality."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.evaluation.metrics import (
    aggregate_metrics,
    hit_at_k,
    ndcg_at_k,
    recall_at_k,
)
from src.retrieval.hybrid_search import HybridSearcher
from src.retrieval.query_processor import QueryProcessor
from src.utils.config import get_settings
from src.utils.logger import logger


class Evaluator:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.searcher = HybridSearcher()
        self.query_processor = QueryProcessor()

    def load_dataset(self, path: str | Path) -> list[dict]:
        path = Path(path)
        if path.is_dir():
            items = []
            for fp in path.glob("*.json"):
                items.extend(self._load_json_file(fp))
            return items
        return self._load_json_file(path)

    @staticmethod
    def _load_json_file(path: Path) -> list[dict]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "items" in data:
            return data["items"]
        return [data]

    def evaluate(
        self,
        dataset: list[dict],
        k_values: list[int] | None = None,
    ) -> dict:
        k_values = k_values or [1, 5, 10]
        per_query: list[dict[str, float]] = []
        details: list[dict] = []

        for item in dataset:
            question = item["question"]
            relevant = set(item.get("ground_truth_docs", []))

            complexity, queries = self.query_processor.process(question)
            result = self.searcher.search(queries)
            retrieved_doc_ids = [c.doc_id for c in result.chunks]

            metrics: dict[str, float] = {}
            for k in k_values:
                metrics[f"recall@{k}"] = recall_at_k(retrieved_doc_ids, relevant, k)
                metrics[f"hit@{k}"] = hit_at_k(retrieved_doc_ids, relevant, k)
                metrics[f"ndcg@{k}"] = ndcg_at_k(retrieved_doc_ids, relevant, k)

            per_query.append(metrics)
            details.append(
                {
                    "question": question,
                    "complexity": complexity,
                    "queries": queries,
                    "retrieved_doc_ids": retrieved_doc_ids[:10],
                    "ground_truth": list(relevant),
                    "metrics": metrics,
                }
            )

        from src.evaluation.metrics import mrr

        mrr_score = mrr(
            [[c.doc_id for c in self.searcher.search(self.query_processor.process(item["question"])[1]).chunks]
             for item in dataset],
            [set(item.get("ground_truth_docs", [])) for item in dataset],
        )

        aggregated = aggregate_metrics(per_query)
        aggregated["mrr"] = mrr_score

        return {
            "summary": aggregated,
            "per_query": details,
            "total": len(dataset),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def run_and_save(
        self,
        dataset_path: str | Path,
        output_dir: str | Path | None = None,
        k_values: list[int] | None = None,
    ) -> Path:
        dataset = self.load_dataset(dataset_path)
        logger.info("Evaluating %d questions", len(dataset))
        report = self.evaluate(dataset, k_values)

        out_dir = Path(output_dir or get_settings().project_root / "reports")
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"eval_{ts}.json"
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        logger.info("Report saved to %s", out_path)
        self._print_summary(report["summary"])
        return out_path

    @staticmethod
    def _print_summary(summary: dict[str, float]) -> None:
        print("\n=== Evaluation Summary ===")
        for k, v in sorted(summary.items()):
            print(f"  {k}: {v:.4f}")
        print()
