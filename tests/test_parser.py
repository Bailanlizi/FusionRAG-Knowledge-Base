"""Tests for document parser."""

from pathlib import Path

from src.ingestion.parser import DocumentParser, resolve_doc_id

DEMO_MD = Path(__file__).resolve().parents[1] / "data" / "documents" / "demo.md"
CONFLUENCE_MD = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "documents"
    / "confluence"
    / "confluence_markdown"
    / "dsid_01eaeaf6045941beaeaf74e6170aceea__responder-rotation-synthesis-and-deferred-postmortem-protocol-2026.md"
)


def test_parse_markdown():
    parser = DocumentParser()
    doc = parser.parse(DEMO_MD)
    assert doc.doc_id
    assert len(doc.pages) >= 1
    assert "FusionRAG" in doc.full_markdown
    assert doc.content_hash


def test_resolve_doc_id_uses_path_hash_for_generic_files():
    doc_id = resolve_doc_id(DEMO_MD.resolve())
    assert len(doc_id) == 16
    assert not doc_id.startswith("dsid_")


def test_resolve_doc_id_uses_dsid_from_confluence_filename():
    assert CONFLUENCE_MD.exists(), "confluence fixture missing"
    doc_id = resolve_doc_id(CONFLUENCE_MD.resolve())
    assert doc_id == "dsid_01eaeaf6045941beaeaf74e6170aceea"


def test_parse_confluence_markdown_uses_dsid():
    assert CONFLUENCE_MD.exists(), "confluence fixture missing"
    doc = DocumentParser().parse(CONFLUENCE_MD)
    assert doc.doc_id == "dsid_01eaeaf6045941beaeaf74e6170aceea"
