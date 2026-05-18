"""Rerank retrieved chunks using Qwen Reranker."""

from __future__ import annotations

from src.retrieval.schemas import RetrievedChunk
from src.utils.api_clients import get_rerank_client
from src.utils.config import get_settings


class ChunkReranker:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = get_rerank_client()

    def rerank(
        self, query: str, chunks: list[RetrievedChunk], top_m: int | None = None
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []

        top_m = top_m or self.settings.retrieval.rerank_top_m
        documents = [c.text for c in chunks]

        ranked = self.client.rerank(query, documents, top_n=min(top_m, len(documents)))

        result: list[RetrievedChunk] = []
        for rank, (idx, score) in enumerate(ranked, start=1):
            chunk = chunks[idx].model_copy()
            chunk.score = score
            chunk.rank = rank
            result.append(chunk)

        return result
