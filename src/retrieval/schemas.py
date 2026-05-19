"""Retrieval request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    question: str
    top_k: int | None = None
    rerank_top_m: int | None = None


class RetrievedChunk(BaseModel):
    chunk_id: str
    doc_id: str
    file_path: str
    title_path: str = ""
    page: int = 0
    chunk_type: str = "text"
    text: str
    score: float = 0.0
    rank: int = 0


class SearchResult(BaseModel):
    question: str
    queries: list[str] = Field(default_factory=list)
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    complexity: str = "SIMPLE"


class AnswerResult(BaseModel):
    question: str
    answer: str
    sources: list[dict] = Field(default_factory=list)
    queries: list[str] = Field(default_factory=list)
    complexity: str = "SIMPLE"


class GenerationTrace(BaseModel):
    complexity: str = "SIMPLE"
    queries: list[str] = Field(default_factory=list)
    retrieval_ms: float = 0.0
    rerank_ms: float = 0.0
    llm_ms: float = 0.0
    chunk_count: int = 0


class DetailedAnswerResult(BaseModel):
    question: str
    answer: str
    sources: list[dict] = Field(default_factory=list)
    trace: GenerationTrace = Field(default_factory=GenerationTrace)
