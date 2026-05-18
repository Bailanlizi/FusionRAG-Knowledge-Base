"""Retrieval evaluation metrics: Recall@K, MRR, nDCG, Hit@K."""

from __future__ import annotations

import math


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for doc in top_k if doc in relevant)
    return hits / len(relevant)


def hit_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    top_k = retrieved[:k]
    return 1.0 if any(doc in relevant for doc in top_k) else 0.0


def mrr(retrieved_lists: list[list[str]], relevant_sets: list[set[str]]) -> float:
    scores = []
    for retrieved, relevant in zip(retrieved_lists, relevant_sets):
        if not relevant:
            continue
        rr = 0.0
        for rank, doc in enumerate(retrieved, start=1):
            if doc in relevant:
                rr = 1.0 / rank
                break
        scores.append(rr)
    return sum(scores) / len(scores) if scores else 0.0


def ndcg_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0

    def dcg(scores: list[float]) -> float:
        return sum(s / math.log2(i + 2) for i, s in enumerate(scores))

    gains = [1.0 if doc in relevant else 0.0 for doc in retrieved[:k]]
    ideal_gains = sorted([1.0] * min(len(relevant), k) + [0.0] * max(0, k - len(relevant)), reverse=True)

    dcg_val = dcg(gains)
    idcg_val = dcg(ideal_gains)
    return dcg_val / idcg_val if idcg_val > 0 else 0.0


def aggregate_metrics(
    per_query_metrics: list[dict[str, float]],
) -> dict[str, float]:
    if not per_query_metrics:
        return {}
    keys = per_query_metrics[0].keys()
    return {k: sum(m[k] for m in per_query_metrics) / len(per_query_metrics) for k in keys}
