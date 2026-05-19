"""API request/response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class KbStatsResponse(BaseModel):
    document_count: int
    chunk_count: int
    last_updated_at: datetime | None = None


class DocumentItem(BaseModel):
    doc_id: str
    file_name: str
    file_path: str
    source_type: str
    chunk_count: int
    page_count: int
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentItem]
    total: int
    page: int
    page_size: int


class ChunkItem(BaseModel):
    chunk_id: str
    doc_id: str
    title_path: str
    page: int
    chunk_type: str
    content: str
    token_count: int


class ChunkDetailResponse(BaseModel):
    chunk_id: str
    doc_id: str
    file_name: str
    file_path: str
    title_path: str
    page: int
    chunk_type: str
    content: str


class UploadResponse(BaseModel):
    doc_id: str
    file_name: str
    chunk_count: int
    message: str


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class SourceItem(BaseModel):
    index: int
    chunk_id: str
    doc_id: str
    file_name: str = ""
    file_path: str = ""
    title_path: str = ""
    page: int = 0
    score: float | None = None


class TraceInfo(BaseModel):
    complexity: str
    queries: list[str]
    original_question: str = ""
    standalone_query: str = ""
    is_follow_up: bool = False
    rewrite_ms: float = 0.0
    retrieval_ms: float
    rerank_ms: float
    llm_ms: float
    chunk_count: int


class MessageItem(BaseModel):
    id: str
    role: str
    content: str
    sources: list[SourceItem] = Field(default_factory=list)
    trace: TraceInfo | None = None
    created_at: datetime


class ConversationDetail(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageItem]


class SendMessageRequest(BaseModel):
    content: str = ""
    regenerate: bool = False
    target_message_id: str | None = None


class AssistantMessageResponse(BaseModel):
    message_id: str
    role: str = "assistant"
    content: str
    sources: list[SourceItem] = Field(default_factory=list)
    trace: TraceInfo
    user_message_id: str | None = None
