"""Reciprocal Rank Fusion for merging multiple ranked lists."""

from __future__ import annotations

from collections import defaultdict


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]],
    k: int = 60,
    top_n: int = 20,
) -> list[tuple[str, float]]:
    """
    Merge multiple ranked lists of chunk_ids using RRF.

    Args:
        ranked_lists: Each list is chunk_ids ordered by relevance (best first).
        k: RRF constant (default 60).
        top_n: Number of results to return.

    Returns:
        List of (chunk_id, rrf_score) sorted by score descending.
    """
    scores: dict[str, float] = defaultdict(float)

    for ranked in ranked_lists:
        for rank, chunk_id in enumerate(ranked, start=1):
            scores[chunk_id] += 1.0 / (k + rank)

    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_items[:top_n]
