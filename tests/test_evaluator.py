"""Tests for evaluation dataset loading and ground-truth fields."""

import json
from pathlib import Path

from src.evaluation.dataset import ground_truth_docs, load_dataset

SAMPLE_JSON = Path(__file__).resolve().parents[1] / "data" / "eval_dataset" / "sample.json"
CONFLUENCE_JSONL = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "documents"
    / "confluence"
    / "confluence_questions.jsonl"
)


def test_ground_truth_docs_from_expected_doc_ids():
    item = {"expected_doc_ids": ["dsid_abc123"]}
    assert ground_truth_docs(item) == {"dsid_abc123"}


def test_ground_truth_docs_merges_both_fields():
    item = {
        "ground_truth_docs": ["demo_doc"],
        "expected_doc_ids": ["dsid_abc123"],
    }
    assert ground_truth_docs(item) == {"demo_doc", "dsid_abc123"}


def test_load_json_dataset():
    items = load_dataset(SAMPLE_JSON)
    assert len(items) == 3
    assert all("question" in item for item in items)


def test_load_jsonl_dataset():
    items = load_dataset(CONFLUENCE_JSONL)
    assert len(items) >= 1
    first = items[0]
    assert "question" in first
    assert ground_truth_docs(first)


def test_load_jsonl_roundtrip(tmp_path: Path):
    path = tmp_path / "mini.jsonl"
    rows = [
        {"question": "q1", "expected_doc_ids": ["dsid_x"]},
        {"question": "q2", "ground_truth_docs": ["demo"]},
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    loaded = load_dataset(path)
    assert len(loaded) == 2
    assert ground_truth_docs(loaded[0]) == {"dsid_x"}
    assert ground_truth_docs(loaded[1]) == {"demo"}
