"""Pydantic data models for ingestion pipeline."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ChunkType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    MIXED = "mixed"


class ContentBlock(BaseModel):
    """A single content block within a page."""

    block_type: ChunkType = ChunkType.TEXT
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParsedPage(BaseModel):
    page_num: int
    markdown: str
    blocks: list[ContentBlock] = Field(default_factory=list)
    has_images: bool = False
    has_complex_table: bool = False
    ocr_confidence: float = 1.0
    needs_ocr_enhance: bool = False


class ParsedDocument(BaseModel):
    doc_id: str
    source_path: str
    file_name: str
    pages: list[ParsedPage] = Field(default_factory=list)
    full_markdown: str = ""
    complexity_score: float = 0.0
    content_hash: str = ""


class ChunkRecord(BaseModel):
    chunk_id: str
    doc_id: str
    file_path: str
    title_path: str = ""
    page: int = 0
    chunk_type: ChunkType = ChunkType.TEXT
    content: str
    token_count: int = 0
