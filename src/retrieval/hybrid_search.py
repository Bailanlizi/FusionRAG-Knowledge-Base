"""Hybrid search: dense + BM25 sparse with RRF fusion."""

from __future__ import annotations

from src.retrieval.rrf import reciprocal_rank_fusion
from src.retrieval.schemas import RetrievedChunk, SearchRequest, SearchResult
from src.utils.api_clients import get_embedding_client
from src.utils.config import get_settings
from src.utils.db import MilvusStore, PostgresClient


class HybridSearcher:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.milvus = MilvusStore()
        self.pg = PostgresClient()
        self.embedder = get_embedding_client()

    def search(self, queries: list[str], top_n: int | None = None) -> SearchResult:
        if not queries:
            raise ValueError("At least one query is required")

        top_n = top_n or self.settings.retrieval.candidate_top_n
        dense_k = self.settings.retrieval.dense_top_k
        sparse_k = self.settings.retrieval.sparse_top_k
        rrf_k = self.settings.retrieval.rrf_k

        all_ranked_lists: list[list[str]] = []
        chunk_map: dict[str, dict] = {}

        for query in queries:
            query_vector = self.embedder.embed([query])[0]

            dense_hits = self.milvus.dense_search(query_vector, dense_k)
            sparse_hits = self.milvus.sparse_search(query, sparse_k)

            for hit in dense_hits + sparse_hits:
                cid = hit["chunk_id"]
                chunk_map[cid] = hit

            dense_ids = [h["chunk_id"] for h in dense_hits]
            sparse_ids = [h["chunk_id"] for h in sparse_hits]
            all_ranked_lists.append(dense_ids)
            all_ranked_lists.append(sparse_ids)

        fused = reciprocal_rank_fusion(all_ranked_lists, k=rrf_k, top_n=top_n)

        chunks: list[RetrievedChunk] = []
        for rank, (chunk_id, score) in enumerate(fused, start=1):
            hit = chunk_map.get(chunk_id, {})
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    doc_id=hit.get("doc_id", ""),
                    file_path=hit.get("file_path", ""),
                    title_path=hit.get("title_path", ""),
                    page=hit.get("page", 0),
                    chunk_type=hit.get("chunk_type", "text"),
                    text=hit.get("text", ""),
                    score=score,
                    rank=rank,
                )
            )

        return SearchResult(
            question=queries[0],
            queries=queries,
            chunks=chunks,
        )

    def search_single(self, request: SearchRequest) -> SearchResult:
        return self.search([request.question], top_n=request.top_k)
