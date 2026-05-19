"""Evaluation pipeline for retrieval quality."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.evaluation.dataset import ground_truth_docs, load_dataset
from src.evaluation.metrics import (
    aggregate_metrics,
    hit_at_k,
    ndcg_at_k,
    recall_at_k,
)
from src.retrieval.hybrid_search import HybridSearcher
from src.retrieval.query_processor import QueryProcessor
from src.retrieval.reranker import ChunkReranker
from src.utils.config import get_settings
from src.utils.logger import logger


class Evaluator:
    def __init__(self, use_reranker: bool = False) -> None:
        self.settings = get_settings()
        self.use_reranker = use_reranker
        self.searcher = HybridSearcher()
        self.query_processor = QueryProcessor()
        self.reranker = ChunkReranker() if use_reranker else None

    def _retrieve_doc_ids(
        self,
        question: str,
        queries: list[str],
        rerank_top_m: int | None = None,
    ) -> list[str]:
        result = self.searcher.search(queries)
        chunks = result.chunks
        if self.reranker:
            top_m = rerank_top_m or self.settings.retrieval.rerank_top_m
            chunks = self.reranker.rerank(question, chunks, top_m=top_m)

        retrieved: list[str] = []
        for chunk in chunks:
            if chunk.doc_id and chunk.doc_id not in retrieved:
                retrieved.append(chunk.doc_id)
        return retrieved

    def load_dataset(self, path: str | Path) -> list[dict]:
        return load_dataset(path)

    def evaluate(
        self,
        dataset: list[dict],
        k_values: list[int] | None = None,
    ) -> dict:
        k_values = k_values or [1, 5, 10]
        rerank_top_m = (
            max(max(k_values), self.settings.retrieval.rerank_top_m)
            if self.use_reranker
            else None
        )
        per_query: list[dict[str, float]] = []
        details: list[dict] = []

        for item in dataset:
            question = item["question"]
            relevant = ground_truth_docs(item)

            complexity, queries = self.query_processor.process(question)
            retrieved_doc_ids = self._retrieve_doc_ids(question, queries, rerank_top_m=rerank_top_m)

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
            [
                self._retrieve_doc_ids(
                    item["question"],
                    self.query_processor.process(item["question"])[1],
                    rerank_top_m=rerank_top_m,
                )
                for item in dataset
            ],
            [ground_truth_docs(item) for item in dataset],
        )

        aggregated = aggregate_metrics(per_query)
        aggregated["mrr"] = mrr_score

        return {
            "use_reranker": self.use_reranker,
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
        mode = "with reranker" if self.use_reranker else "no reranker"
        logger.info("Evaluating %d questions (%s)", len(dataset), mode)
        report = self.evaluate(dataset, k_values)

        out_dir = Path(output_dir or get_settings().project_root / "reports")
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        prefix = "eval_rerank" if self.use_reranker else "eval"
        out_path = out_dir / f"{prefix}_{ts}.json"
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
