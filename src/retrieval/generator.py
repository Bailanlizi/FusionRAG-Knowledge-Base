"""Answer generation with source citations."""

from __future__ import annotations

from src.retrieval.hybrid_search import HybridSearcher
from src.retrieval.query_processor import QueryProcessor
from src.retrieval.reranker import ChunkReranker
from src.retrieval.schemas import AnswerResult, RetrievedChunk
from src.utils.api_clients import get_llm_client
from src.utils.config import PROJECT_ROOT, get_settings

PROMPT_PATH = PROJECT_ROOT / "config" / "prompts" / "generate.txt"


class AnswerGenerator:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.query_processor = QueryProcessor()
        self.searcher = HybridSearcher()
        self.reranker = ChunkReranker()
        self.llm = get_llm_client()
        self._prompt_template = PROMPT_PATH.read_text(encoding="utf-8")

    def generate(self, question: str) -> AnswerResult:
        complexity, queries = self.query_processor.process(question)

        search_result = self.searcher.search(queries)
        reranked = self.reranker.rerank(question, search_result.chunks)

        context, sources = self._build_context(reranked)
        prompt = self._prompt_template.format(context=context, question=question)

        answer = self.llm.chat(
            [
                {"role": "system", "content": "你是知识库问答助手，请基于上下文准确回答。"},
                {"role": "user", "content": prompt},
            ]
        )

        return AnswerResult(
            question=question,
            answer=answer,
            sources=sources,
            queries=queries,
            complexity=complexity,
        )

    def _build_context(self, chunks: list[RetrievedChunk]) -> tuple[str, list[dict]]:
        parts = []
        sources = []
        for i, chunk in enumerate(chunks, start=1):
            header = f"[{i}] {chunk.title_path} (p.{chunk.page}) — {chunk.file_path}"
            parts.append(f"{header}\n{chunk.text}")
            sources.append(
                {
                    "index": i,
                    "chunk_id": chunk.chunk_id,
                    "doc_id": chunk.doc_id,
                    "file_path": chunk.file_path,
                    "title_path": chunk.title_path,
                    "page": chunk.page,
                }
            )
        return "\n\n---\n\n".join(parts), sources
