"""Answer generation with source citations."""

from __future__ import annotations

import time
from pathlib import Path

from src.retrieval.hybrid_search import HybridSearcher
from src.retrieval.query_processor import QueryProcessor
from src.retrieval.query_rewriter import QueryRewriter
from src.retrieval.reranker import ChunkReranker
from src.retrieval.schemas import (
    AnswerResult,
    ChatTurn,
    DetailedAnswerResult,
    GenerationTrace,
    RetrievedChunk,
)
from src.utils.api_clients import get_llm_client
from src.utils.config import PROJECT_ROOT, get_settings

PROMPT_PATH = PROJECT_ROOT / "config" / "prompts" / "generate.txt"


class AnswerGenerator:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.query_processor = QueryProcessor()
        self.query_rewriter = QueryRewriter()
        self.searcher = HybridSearcher()
        self.reranker = ChunkReranker()
        self.llm = get_llm_client()
        self._prompt_template = PROMPT_PATH.read_text(encoding="utf-8")

    def generate(self, question: str, history: list[ChatTurn] | None = None) -> AnswerResult:
        detailed = self.generate_detailed(question, history=history)
        return AnswerResult(
            question=detailed.question,
            answer=detailed.answer,
            sources=detailed.sources,
            queries=detailed.trace.queries,
            complexity=detailed.trace.complexity,
        )

    def generate_detailed(
        self, question: str, history: list[ChatTurn] | None = None
    ) -> DetailedAnswerResult:
        history = history or []
        t0 = time.perf_counter()
        rewrite = self.query_rewriter.rewrite(question, history)
        t1 = time.perf_counter()

        search_question = rewrite.standalone_query
        complexity, queries = self.query_processor.process(search_question)
        t2 = time.perf_counter()

        search_result = self.searcher.search(queries)
        t3 = time.perf_counter()

        reranked = self.reranker.rerank(search_question, search_result.chunks)
        t4 = time.perf_counter()

        context, sources = self._build_context(reranked)
        prompt = self._prompt_template.format(context=context, question=question)

        answer = self.llm.chat(
            [
                {"role": "system", "content": "你是知识库问答助手，请基于上下文准确回答。"},
                {"role": "user", "content": prompt},
            ]
        )
        t5 = time.perf_counter()

        trace = GenerationTrace(
            complexity=complexity,
            queries=queries,
            original_question=rewrite.original_question,
            standalone_query=rewrite.standalone_query,
            is_follow_up=rewrite.is_follow_up,
            rewrite_ms=round((t1 - t0) * 1000, 1),
            retrieval_ms=round((t3 - t2) * 1000, 1),
            rerank_ms=round((t4 - t3) * 1000, 1),
            llm_ms=round((t5 - t4) * 1000, 1),
            chunk_count=len(reranked),
        )
        return DetailedAnswerResult(
            question=question,
            answer=answer,
            sources=sources,
            trace=trace,
        )

    def _build_context(self, chunks: list[RetrievedChunk]) -> tuple[str, list[dict]]:
        parts = []
        sources = []
        for i, chunk in enumerate(chunks, start=1):
            file_name = Path(chunk.file_path).name
            header = f"[{i}] {chunk.title_path} (p.{chunk.page}) — {chunk.file_path}"
            parts.append(f"{header}\n{chunk.text}")
            sources.append(
                {
                    "index": i,
                    "chunk_id": chunk.chunk_id,
                    "doc_id": chunk.doc_id,
                    "file_name": file_name,
                    "file_path": chunk.file_path,
                    "title_path": chunk.title_path,
                    "page": chunk.page,
                    "score": round(float(chunk.score), 4),
                }
            )
        return "\n\n---\n\n".join(parts), sources
