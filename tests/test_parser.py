"""Tests for document parser."""

from pathlib import Path

from src.ingestion.parser import DocumentParser

DEMO_MD = Path(__file__).resolve().parents[1] / "data" / "documents" / "demo.md"


def test_parse_markdown():
    parser = DocumentParser()
    doc = parser.parse(DEMO_MD)
    assert doc.doc_id
    assert len(doc.pages) >= 1
    assert "FusionRAG" in doc.full_markdown
    assert doc.content_hash
