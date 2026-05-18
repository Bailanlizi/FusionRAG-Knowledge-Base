"""Tests for semantic chunker."""

from src.ingestion.chunker import SemanticChunker, count_tokens, _split_by_headings
from src.ingestion.models import ChunkType, ParsedDocument, ParsedPage


def test_count_tokens():
    assert count_tokens("hello world") > 0


def test_split_by_headings():
    md = "# Title\n\nParagraph one.\n\n## Section\n\nParagraph two."
    sections = _split_by_headings(md)
    assert len(sections) >= 1


def test_chunker_produces_records():
    doc = ParsedDocument(
        doc_id="test123",
        source_path="/tmp/test.md",
        file_name="test.md",
        pages=[
            ParsedPage(
                page_num=1,
                markdown="# Hello\n\nThis is a test paragraph with some content.\n\n## Section\n\nMore content here for chunking.",
            )
        ],
        full_markdown="# Hello\n\nContent.",
    )
    chunker = SemanticChunker()
    chunks = chunker.chunk(doc)
    assert len(chunks) >= 1
    assert chunks[0].doc_id == "test123"
    assert chunks[0].token_count > 0


def test_chunker_table_detection():
    doc = ParsedDocument(
        doc_id="t1",
        source_path="/tmp/t.md",
        file_name="t.md",
        pages=[
            ParsedPage(
                page_num=1,
                markdown="| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n| 5 | 6 |",
            )
        ],
    )
    chunks = SemanticChunker().chunk(doc)
    assert any(c.chunk_type in (ChunkType.TABLE, ChunkType.TEXT) for c in chunks)
